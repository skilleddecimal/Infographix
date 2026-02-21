"""Task queue implementation."""

import asyncio
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class TaskStatus(str, Enum):
    """Task status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """Task definition."""
    id: str
    name: str
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "args": list(self.args),
            "kwargs": self.kwargs,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            args=tuple(data.get("args", [])),
            kwargs=data.get("kwargs", {}),
            status=TaskStatus(data.get("status", "pending")),
            result=data.get("result"),
            error=data.get("error"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
        )


class InMemoryTaskQueue:
    """In-memory task queue for development."""

    def __init__(self, queue_name: str = "default"):
        self.queue_name = queue_name
        self._tasks: dict[str, Task] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._handlers: dict[str, Callable] = {}

    async def enqueue(
        self,
        name: str,
        *args,
        **kwargs,
    ) -> str:
        """Add task to queue."""
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            name=name,
            args=args,
            kwargs=kwargs,
        )
        self._tasks[task_id] = task
        await self._queue.put(task_id)
        return task_id

    async def get_task(self, task_id: str) -> Task | None:
        """Get task by ID."""
        return self._tasks.get(task_id)

    async def process_one(self) -> Task | None:
        """Process one task from queue."""
        try:
            task_id = self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

        task = self._tasks.get(task_id)
        if not task:
            return None

        handler = self._handlers.get(task.name)
        if not handler:
            task.status = TaskStatus.FAILED
            task.error = f"No handler for task: {task.name}"
            return task

        task.status = TaskStatus.PROCESSING
        task.started_at = datetime.utcnow()

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(*task.args, **task.kwargs)
            else:
                result = handler(*task.args, **task.kwargs)

            task.result = result
            task.status = TaskStatus.COMPLETED
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED

        task.completed_at = datetime.utcnow()
        return task

    def register(self, name: str, handler: Callable) -> None:
        """Register a task handler."""
        self._handlers[name] = handler

    async def process_all(self) -> int:
        """Process all pending tasks."""
        count = 0
        while not self._queue.empty():
            await self.process_one()
            count += 1
        return count


class RedisTaskQueue:
    """Redis-based task queue for production."""

    def __init__(
        self,
        redis_url: str | None = None,
        queue_name: str = "default",
    ):
        if not REDIS_AVAILABLE:
            raise ImportError("redis package not installed")

        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.queue_name = queue_name
        self._redis: aioredis.Redis | None = None
        self._handlers: dict[str, Callable] = {}

    async def _get_redis(self) -> aioredis.Redis:
        """Get Redis connection."""
        if self._redis is None:
            self._redis = aioredis.from_url(self.redis_url)
        return self._redis

    def _queue_key(self) -> str:
        return f"tasks:{self.queue_name}:queue"

    def _task_key(self, task_id: str) -> str:
        return f"tasks:{self.queue_name}:task:{task_id}"

    async def enqueue(
        self,
        name: str,
        *args,
        **kwargs,
    ) -> str:
        """Add task to queue."""
        redis = await self._get_redis()

        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            name=name,
            args=args,
            kwargs=kwargs,
        )

        # Store task
        await redis.set(
            self._task_key(task_id),
            json.dumps(task.to_dict()),
            ex=86400 * 7,  # 7 days
        )

        # Add to queue
        await redis.lpush(self._queue_key(), task_id)

        return task_id

    async def get_task(self, task_id: str) -> Task | None:
        """Get task by ID."""
        redis = await self._get_redis()
        data = await redis.get(self._task_key(task_id))
        if not data:
            return None
        return Task.from_dict(json.loads(data))

    async def process_one(self, timeout: int = 5) -> Task | None:
        """Process one task from queue."""
        redis = await self._get_redis()

        # Block until task available
        result = await redis.brpop(self._queue_key(), timeout=timeout)
        if not result:
            return None

        _, task_id = result
        task = await self.get_task(task_id)
        if not task:
            return None

        handler = self._handlers.get(task.name)
        if not handler:
            task.status = TaskStatus.FAILED
            task.error = f"No handler for task: {task.name}"
            await self._save_task(task)
            return task

        task.status = TaskStatus.PROCESSING
        task.started_at = datetime.utcnow()
        await self._save_task(task)

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(*task.args, **task.kwargs)
            else:
                result = handler(*task.args, **task.kwargs)

            task.result = result
            task.status = TaskStatus.COMPLETED
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED

        task.completed_at = datetime.utcnow()
        await self._save_task(task)
        return task

    async def _save_task(self, task: Task) -> None:
        """Save task to Redis."""
        redis = await self._get_redis()
        await redis.set(
            self._task_key(task.id),
            json.dumps(task.to_dict()),
            ex=86400 * 7,
        )

    def register(self, name: str, handler: Callable) -> None:
        """Register a task handler."""
        self._handlers[name] = handler

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None


# Type alias for task queue
TaskQueue = InMemoryTaskQueue | RedisTaskQueue

# Global queue instance
_queue_instance: TaskQueue | None = None


def get_task_queue(
    redis_url: str | None = None,
    queue_name: str = "default",
) -> TaskQueue:
    """Get task queue instance.

    Returns Redis queue if available, otherwise in-memory queue.
    """
    global _queue_instance

    if _queue_instance is not None:
        return _queue_instance

    if REDIS_AVAILABLE:
        try:
            _queue_instance = RedisTaskQueue(redis_url, queue_name)
            return _queue_instance
        except Exception:
            pass

    _queue_instance = InMemoryTaskQueue(queue_name)
    return _queue_instance
