"""Background task worker."""

import asyncio
import logging
import os
import signal
from dataclasses import dataclass

from backend.tasks.queue import get_task_queue, TaskQueue

logger = logging.getLogger("infographix.worker")


@dataclass
class WorkerSettings:
    """Worker configuration."""
    queue_name: str = "default"
    redis_url: str | None = None
    max_jobs: int = 0  # 0 = unlimited
    poll_delay: float = 0.5
    shutdown_timeout: float = 30.0


class Worker:
    """Background task worker.

    Processes tasks from the queue continuously.
    """

    def __init__(self, settings: WorkerSettings | None = None):
        self.settings = settings or WorkerSettings()
        self.queue: TaskQueue | None = None
        self._running = False
        self._jobs_processed = 0

    async def startup(self) -> None:
        """Initialize worker."""
        self.queue = get_task_queue(
            redis_url=self.settings.redis_url,
            queue_name=self.settings.queue_name,
        )

        # Register task handlers
        self._register_handlers()

        logger.info(f"Worker started for queue: {self.settings.queue_name}")

    def _register_handlers(self) -> None:
        """Register all task handlers."""
        from backend.tasks.handlers import (
            process_generation_task,
            process_variations_task,
            generate_download_task,
            cleanup_expired_downloads_task,
        )

        self.queue.register("process_generation", process_generation_task)
        self.queue.register("process_variations", process_variations_task)
        self.queue.register("generate_download", generate_download_task)
        self.queue.register("cleanup_downloads", cleanup_expired_downloads_task)

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("Worker shutting down...")
        self._running = False

        if hasattr(self.queue, "close"):
            await self.queue.close()

        logger.info(f"Worker stopped. Processed {self._jobs_processed} jobs.")

    async def run(self) -> None:
        """Run worker main loop."""
        await self.startup()
        self._running = True

        try:
            while self._running:
                # Check job limit
                if self.settings.max_jobs > 0 and self._jobs_processed >= self.settings.max_jobs:
                    logger.info(f"Reached max jobs limit: {self.settings.max_jobs}")
                    break

                # Process one task
                task = await self.queue.process_one()

                if task:
                    self._jobs_processed += 1
                    if task.error:
                        logger.error(f"Task {task.id} failed: {task.error}")
                    else:
                        logger.info(f"Task {task.id} completed")
                else:
                    # No task available, wait before polling again
                    await asyncio.sleep(self.settings.poll_delay)

        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()


async def run_worker(settings: WorkerSettings | None = None) -> None:
    """Run the worker.

    Args:
        settings: Worker settings.
    """
    worker = Worker(settings)

    # Handle signals
    loop = asyncio.get_event_loop()

    def signal_handler():
        worker._running = False

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    await worker.run()


def main():
    """CLI entry point for worker."""
    import argparse

    parser = argparse.ArgumentParser(description="Infographix background worker")
    parser.add_argument("--queue", default="default", help="Queue name")
    parser.add_argument("--redis-url", help="Redis URL")
    parser.add_argument("--max-jobs", type=int, default=0, help="Max jobs to process (0=unlimited)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    settings = WorkerSettings(
        queue_name=args.queue,
        redis_url=args.redis_url,
        max_jobs=args.max_jobs,
    )

    asyncio.run(run_worker(settings))


if __name__ == "__main__":
    main()
