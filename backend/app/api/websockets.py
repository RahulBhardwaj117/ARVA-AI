"""Authenticated live channels for operational state."""

import asyncio
import json
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from redis import RedisError
from redis.asyncio import Redis
from sqlalchemy import select

from app.auth.tokens import decode_access_token
from app.config import get_settings
from app.database.session import SessionLocal
from app.events import organization_channel
from app.models.domain import Decision, Experiment, Incident, MetricSample, Risk
from app.models.user import User
from app.services.platform import PlatformService

router = APIRouter()


def authenticate(token: str | None) -> User | None:
    """Resolve a socket user from the same JWT contract as REST."""
    claims = decode_access_token(token or "")
    if claims is None:
        return None
    with SessionLocal() as session:
        user = session.scalar(
            select(User).where(
                User.id == uuid.UUID(str(claims.sub)),
                User.organization_id == claims.organization_id,
                User.is_active.is_(True),
            )
        )
        if user:
            session.expunge(user)
        return user


async def stream(
    websocket: WebSocket,
    token: str | None,
    producer: Callable[[PlatformService], Any],
) -> None:
    """Send reconnect-safe snapshots until the client disconnects."""
    user = authenticate(token)
    if user is None:
        await websocket.close(code=4401, reason="Authentication required")
        return
    await websocket.accept()
    redis_client: Redis | None = None
    pubsub: Any | None = None
    try:
        try:
            redis_client = Redis.from_url(get_settings().redis_url, decode_responses=True)
            await redis_client.ping()
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(organization_channel(user.organization_id))
        except RedisError:
            pubsub = None
        while True:
            with SessionLocal() as session:
                payload = producer(PlatformService(session, user.organization_id))
            await websocket.send_json(
                jsonable_encoder({"type": "snapshot", "data": payload})
            )
            if pubsub is None:
                await asyncio.sleep(2)
                continue
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=15,
                    ),
                    timeout=16,
                )
                if message and message.get("data"):
                    await websocket.send_json(
                        {
                            "type": "event",
                            "data": json.loads(str(message["data"])),
                        }
                    )
            except TimeoutError:
                continue
    except WebSocketDisconnect:
        return
    finally:
        if pubsub is not None:
            await pubsub.aclose()
        if redis_client is not None:
            await redis_client.aclose()


@router.websocket("/ws/telemetry")
async def telemetry(websocket: WebSocket, token: str | None = None) -> None:
    await stream(websocket, token, lambda service: service.summary())


@router.websocket("/ws/risks")
async def risks(websocket: WebSocket, token: str | None = None) -> None:
    await stream(websocket, token, lambda service: service.list_entities(Risk, limit=25))


@router.websocket("/ws/decisions")
async def decisions(websocket: WebSocket, token: str | None = None) -> None:
    await stream(
        websocket, token, lambda service: service.list_entities(Decision, limit=25)
    )


@router.websocket("/ws/incidents")
async def incidents(websocket: WebSocket, token: str | None = None) -> None:
    await stream(
        websocket, token, lambda service: service.list_entities(Incident, limit=25)
    )


@router.websocket("/ws/simulation")
async def simulation(websocket: WebSocket, token: str | None = None) -> None:
    await stream(
        websocket,
        token,
        lambda service: {
            "simulation": service.list_entities(MetricSample, limit=1),
            "summary": service.summary(),
        },
    )


@router.websocket("/ws/experiments")
async def experiments(websocket: WebSocket, token: str | None = None) -> None:
    await stream(
        websocket, token, lambda service: service.list_entities(Experiment, limit=25)
    )


@router.websocket("/ws/metrics")
async def metrics(websocket: WebSocket, token: str | None = None) -> None:
    await stream(
        websocket,
        token,
        lambda service: service.metric_series(metric="gpu_utilization", limit=60),
    )
