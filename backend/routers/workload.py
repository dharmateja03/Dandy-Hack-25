"""
Workload and capacity API endpoints
"""

from fastapi import APIRouter, Request
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/team-heatmap")
async def get_team_workload_heatmap(request: Request = None):
    """Get team workload heatmap for dashboard"""
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        # Get all active users
        users = await db.get_all_active_users()

        # Return empty heatmap structure
        return {
            "status": "success",
            "heatmap": [
                {
                    "user_id": user.get("id"),
                    "name": user.get("name"),
                    "workload_percentage": 0,
                    "active_tasks": 0,
                    "pending_help_requests": 0
                }
                for user in users
            ] if isinstance(users, list) else []
        }

    except Exception as e:
        logger.error(f"Error getting team workload heatmap: {e}")
        return {
            "status": "success",
            "heatmap": []
        }
