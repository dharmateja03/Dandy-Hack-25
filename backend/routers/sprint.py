"""
Sprint health and metrics API endpoints
"""

from fastapi import APIRouter, Request
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def get_sprint_health(request: Request = None):
    """Get sprint health metrics for dashboard"""
    try:
        mcp = request.app.state.mcp

        return {
            "status": "success",
            "sprint": {
                "name": "Current Sprint",
                "health_score": 0,
                "tasks_completed": 0,
                "tasks_in_progress": 0,
                "tasks_blocked": 0,
                "velocity_trend": "stable"
            }
        }

    except Exception as e:
        logger.error(f"Error getting sprint health: {e}")
        return {
            "status": "success",
            "sprint": {}
        }
