"""
Background worker process. Intended for jobs such as:
- batch conversation summarization
- knowledge base re-embedding after edits
- scheduled analytics rollups
- stale idempotency-key cleanup

Kept minimal here; wire an actual queue (e.g. arq/RQ backed by Redis) as the
job volume grows. Running this as its own container keeps heavy/background
work off the request path.
"""
import asyncio

from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


async def main() -> None:
    logger.info("worker_started")
    while True:
        # TODO: pop jobs from a Redis/BullMQ-equivalent queue and dispatch
        # to the relevant service (KnowledgeIngestionService, etc.)
        await asyncio.sleep(30)
        logger.info("worker_heartbeat")


if __name__ == "__main__":
    asyncio.run(main())
