import asyncio
import uuid
from typing import Dict, Any, Callable, Coroutine
import time

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}

    async def create_task(self, coroutine: Coroutine, task_type: str) -> str:
        """Create and manage an async task"""
        task_id = str(uuid.uuid4())

        # Create task dictionary
        task_info = {
            "id": task_id,
            "type": task_type,
            "status": "running",
            "created_at": time.time(),
            "result": None,
            "error": None
        }

        # Save task information
        self.tasks[task_id] = task_info

        # Create and run task
        task = asyncio.create_task(self._run_task(task_id, coroutine))

        return task_id

    async def _run_task(self, task_id: str, coroutine: Coroutine):
        """Run task and handle results"""
        try:
            result = await coroutine
            self.tasks[task_id]["result"] = result
            self.tasks[task_id]["status"] = "completed"
            self.tasks[task_id]["completed_at"] = time.time()
        except Exception as e:
            self.tasks[task_id]["error"] = str(e)
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["completed_at"] = time.time()

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status"""
        if task_id not in self.tasks:
            return {"status": "not_found"}

        return self.tasks[task_id]

    def clean_old_tasks(self, max_age_seconds: int = 3600):
        """Clean up old completed tasks"""
        current_time = time.time()
        task_ids_to_remove = []

        for task_id, task_info in self.tasks.items():
            if task_info["status"] in ["completed", "failed"]:
                if current_time - task_info.get("completed_at", 0) > max_age_seconds:
                    task_ids_to_remove.append(task_id)

        for task_id in task_ids_to_remove:
            del self.tasks[task_id]
