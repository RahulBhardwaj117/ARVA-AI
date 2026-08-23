"""Redis-backed background simulation runner."""

import logging
import time

import redis
from sqlalchemy import select

from app.config import get_settings
from app.database.session import SessionLocal
from app.logging import configure_logging
from app.models.domain import Simulation, SimulationStatus
from app.services.platform import PlatformService

HEARTBEAT_KEY = "arva:worker:heartbeat"


def run() -> None:
    """Publish health and advance every running simulation."""
    configure_logging()
    logger = logging.getLogger("arva.worker")
    client = redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
    logger.info("worker_started")
    while True:
        client.set(HEARTBEAT_KEY, str(time.time()), ex=30)
        try:
            with SessionLocal() as session:
                simulations = session.scalars(
                    select(Simulation).where(
                        Simulation.status == SimulationStatus.RUNNING.value
                    )
                ).all()
                for simulation in simulations:
                    PlatformService(session, simulation.organization_id).tick(
                        max(1, int(simulation.speed))
                    )
        except Exception:
            logger.exception("simulation_tick_failed")
        time.sleep(2)


if __name__ == "__main__":
    run()
