"""Durable Redis event stream and live fan-out boundary."""

import json
import logging
import uuid
from datetime import UTC, datetime

import redis

from app.config import get_settings

logger = logging.getLogger("arva.events")
EVENT_STREAM = "arva:events"


def organization_channel(organization_id: uuid.UUID) -> str:
    """Return the tenant-specific Redis pub/sub channel."""
    return f"arva:organization:{organization_id}"


def publish_event(
    organization_id: uuid.UUID,
    event_type: str,
    payload: dict[str, object] | None = None,
) -> bool:
    """Persist and fan out a domain event, failing open if Redis is unavailable."""
    event = {
        "id": str(uuid.uuid4()),
        "organization_id": str(organization_id),
        "type": event_type,
        "occurred_at": datetime.now(UTC).isoformat(),
        "payload": payload or {},
    }
    try:
        client = redis.Redis.from_url(
            get_settings().redis_url,
            decode_responses=True,
            socket_connect_timeout=0.15,
            socket_timeout=0.25,
        )
        encoded = json.dumps(event, separators=(",", ":"), default=str)
        pipeline = client.pipeline(transaction=False)
        pipeline.xadd(
            EVENT_STREAM,
            {
                "event_id": event["id"],
                "organization_id": event["organization_id"],
                "event_type": event_type,
                "occurred_at": event["occurred_at"],
                "payload": json.dumps(payload or {}, separators=(",", ":"), default=str),
            },
            maxlen=10_000,
            approximate=True,
        )
        pipeline.publish(organization_channel(organization_id), encoded)
        pipeline.execute()
        return True
    except redis.RedisError:
        logger.warning(
            "event_publication_unavailable",
            extra={"organization_id": str(organization_id), "event_type": event_type},
        )
        return False


def read_recent_events(
    organization_id: uuid.UUID,
    *,
    limit: int = 100,
) -> list[dict[str, object]]:
    """Read recent tenant events from the durable Redis stream."""
    try:
        client = redis.Redis.from_url(
            get_settings().redis_url,
            decode_responses=True,
            socket_connect_timeout=0.15,
            socket_timeout=0.25,
        )
        records = client.xrevrange(EVENT_STREAM, count=min(limit * 5, 1000))
        events: list[dict[str, object]] = []
        for stream_id, fields in records:
            if fields.get("organization_id") != str(organization_id):
                continue
            events.append(
                {
                    "stream_id": stream_id,
                    "event_id": fields.get("event_id"),
                    "organization_id": fields.get("organization_id"),
                    "type": fields.get("event_type"),
                    "occurred_at": fields.get("occurred_at"),
                    "payload": json.loads(fields.get("payload", "{}")),
                }
            )
            if len(events) >= limit:
                break
        return events
    except (redis.RedisError, json.JSONDecodeError):
        return []
