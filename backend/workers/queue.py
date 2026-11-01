"""
Decoupled Task Queue Port (Hexagonal Architecture).
Provides in-process worker pool for HomeLab/Local deployments, pre-architected
for drop-in Celery + Redis replacement for Enterprise AWS scaling.
"""

import threading
import queue
import uuid
import time
from typing import Callable, Any, Dict, Optional

class TaskQueue:
    """In-process bounded task queue with progress and status tracking."""

    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self._queue = queue.Queue(maxsize=100)
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._workers = []
        self._running = True
        self._start_workers()

    def _start_workers(self):
        for i in range(self.max_workers):
            t = threading.Thread(target=self._worker_loop, daemon=True, name=f"TaskWorker-{i}")
            t.start()
            self._workers.append(t)

    def _worker_loop(self):
        while self._running:
            try:
                task_id, fn, args, kwargs = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            with self._lock:
                self._tasks[task_id]["status"] = "running"
                self._tasks[task_id]["started_at"] = time.time()

            try:
                result = fn(*args, **kwargs)
                with self._lock:
                    self._tasks[task_id]["status"] = "completed"
                    self._tasks[task_id]["result"] = result
                    self._tasks[task_id]["completed_at"] = time.time()
            except Exception as e:
                with self._lock:
                    self._tasks[task_id]["status"] = "failed"
                    self._tasks[task_id]["error"] = str(e)
                    self._tasks[task_id]["completed_at"] = time.time()
            finally:
                self._queue.task_done()

    def submit(self, fn: Callable, *args, **kwargs) -> str:
        task_id = str(uuid.uuid4())
        with self._lock:
            self._tasks[task_id] = {
                "id": task_id,
                "status": "queued",
                "submitted_at": time.time(),
                "progress": 0.0
            }
        self._queue.put((task_id, fn, args, kwargs))
        return task_id

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._tasks.get(task_id)

    def shutdown(self):
        self._running = False

_default_queue = None

def get_task_queue() -> TaskQueue:
    global _default_queue
    if _default_queue is None:
        _default_queue = TaskQueue()
    return _default_queue
