"""
Task API endpoints
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Optional, List
from services.database import TaskStatus
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("")
async def get_all_tasks(request: Request = None):
    """
    Get all tasks for dashboard
    """
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        tasks = await db.get_all_tasks()

        return {"tasks": tasks}

    except Exception as e:
        logger.error(f"Error getting all tasks: {e}")
        return {"tasks": []}


@router.get("/user/{user_id}")
async def get_user_tasks(
    user_id: str,
    status: Optional[str] = None,
    filter: Optional[str] = None,
    sort_by: Optional[str] = None,
    request: Request = None
):
    """
    Get tasks for a user with optional filtering and sorting

    Query Parameters:
    - status: Filter by status (not_started, in_progress, blocked, completed)
    - filter: Filter type (all, high, medium, low, in_progress, blocked)
    - sort_by: Sort field (priority, due_date, created_at)

    Used by Slack bot to:
    - Display user's tasks in standup modal
    - Show task list in DMs
    - Support /my-tasks command with priority sorting
    """
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        # Convert status string to enum if provided (legacy parameter)
        task_status = None
        if status:
            try:
                task_status = TaskStatus[status.upper()]
            except KeyError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        # Get user tasks
        tasks = await db.get_user_tasks(user_id, status=task_status)

        # Apply filter if specified
        if filter and filter.lower() != "all":
            filter_type = filter.lower()
            if filter_type in ["high", "medium", "low"]:
                # Filter by priority
                tasks = [t for t in tasks if t.get("priority", "").lower() == filter_type]
            elif filter_type in ["in_progress", "blocked", "not_started", "completed"]:
                # Filter by status
                tasks = [t for t in tasks if t.get("status", "").lower() == filter_type]

        # Sort if specified
        if sort_by:
            sort_field = sort_by.lower()
            if sort_field == "priority":
                # Sort by priority: HIGH -> MEDIUM -> LOW
                priority_order = {"high": 0, "medium": 1, "low": 2}
                tasks.sort(key=lambda t: (priority_order.get(t.get("priority", "medium").lower(), 99), t.get("created_at", "")))
            elif sort_field == "due_date":
                # Sort by due date (soonest first)
                tasks.sort(key=lambda t: t.get("due_date", "9999-12-31"))
            elif sort_field == "created_at":
                # Sort by creation date (newest first)
                tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)

        return {"tasks": tasks}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tasks for user {user_id}: {e}")
        return {"tasks": []}  # Return empty list on error to avoid breaking Slack bot


@router.post("/assign")
async def assign_task(
    task_title: str,
    assignee_id: str,
    priority: str = "medium",
    request: Request = None
):
    """
    Assign a task (manager action)

    Used by Slack bot for /mcp-assign command
    """
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        # Create the task
        task_id = await db.create_task({
            "title": task_title,
            "assignee_id": assignee_id,
            "priority": priority,
            "status": TaskStatus.NOT_STARTED
        })

        logger.info(f"Task {task_id} assigned to {assignee_id}")

        return {
            "status": "success",
            "task_id": task_id,
            "message": f"Task assigned to {assignee_id}"
        }

    except Exception as e:
        logger.error(f"Error assigning task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{task_id}/status")
async def update_task_status(
    task_id: int,
    status: str,
    progress: Optional[int] = None,
    request: Request = None
):
    """
    Update task status

    Used by Slack bot for task updates
    """
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        # Validate status
        try:
            TaskStatus[status.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        await db.update_task(
            task_id,
            status=TaskStatus[status.upper()],
            progress_percentage=progress
        )

        logger.info(f"Task {task_id} status updated to {status}")

        return {
            "status": "success",
            "task_id": task_id,
            "new_status": status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
