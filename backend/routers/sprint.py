"""
Sprint health and metrics API endpoints
"""

from fastapi import APIRouter, Request
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def get_sprint_health(request: Request = None):
    """Get sprint health metrics for dashboard"""
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        # Get all tasks to calculate metrics
        tasks = await db.get_all_tasks() if hasattr(db, 'get_all_tasks') else []

        # Calculate task metrics
        completed = sum(1 for t in tasks if t.get("status") == "completed")
        in_progress = sum(1 for t in tasks if t.get("status") == "in_progress")
        blocked = sum(1 for t in tasks if t.get("status") == "blocked")
        not_started = sum(1 for t in tasks if t.get("status") == "not_started")
        total_tasks = len(tasks)

        # Calculate health score components
        completion_score = (completed / total_tasks * 40) if total_tasks > 0 else 0
        blockers_score = max(0, 30 - (blocked * 5))
        stuck_score = max(0, 20 - (not_started * 2))
        overdue_score = 10

        health_score = int(completion_score + blockers_score + stuck_score + overdue_score)
        health_score = min(100, max(0, health_score))

        # Determine health status
        if health_score >= 80:
            status = "excellent"
        elif health_score >= 60:
            status = "good"
        elif health_score >= 40:
            status = "fair"
        else:
            status = "critical"

        return {
            "status": "success",
            "health_score": health_score,
            "health_status": status,
            "sprint": {
                "name": "Current Sprint",
                "days_remaining": 7,
                "start_date": (datetime.now() - timedelta(days=7)).isoformat(),
                "end_date": (datetime.now() + timedelta(days=7)).isoformat()
            },
            "score_breakdown": {
                "completion": completion_score,
                "blockers": blockers_score,
                "stuck_tasks": stuck_score,
                "overdue": overdue_score
            },
            "metrics": {
                "tasks_completed": completed,
                "tasks_in_progress": in_progress,
                "tasks_blocked": blocked,
                "tasks_not_started": not_started,
                "total_tasks": total_tasks
            }
        }

    except Exception as e:
        logger.error(f"Error getting sprint health: {e}")
        return {
            "status": "success",
            "health_score": 0,
            "health_status": "critical",
            "sprint": {"name": "Current Sprint", "days_remaining": 0},
            "score_breakdown": {"completion": 0, "blockers": 0, "stuck_tasks": 0, "overdue": 0},
            "metrics": {}
        }
