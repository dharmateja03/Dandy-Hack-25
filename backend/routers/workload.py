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

        # Format for dashboard
        team_workload = []
        if isinstance(users, list):
            for user in users:
                user_id = user.get("id")
                user_name = user.get("name")

                # Get task counts for this user
                tasks = await db.get_user_tasks(user_id)

                in_progress = sum(1 for t in tasks if t.get("status") == "in_progress")
                blocked = sum(1 for t in tasks if t.get("status") == "blocked")
                completed = sum(1 for t in tasks if t.get("status") == "completed")

                workload_score = min(100, (in_progress * 10) + (blocked * 15))

                if workload_score < 30:
                    status_class = "low"
                    emoji = "😎"
                elif workload_score < 70:
                    status_class = "moderate"
                    emoji = "😊"
                else:
                    status_class = "high"
                    emoji = "😰"

                team_workload.append({
                    "user_id": user_id,
                    "user_name": user_name,
                    "role": user.get("role", "Developer"),
                    "workload_status": status_class,
                    "workload_emoji": emoji,
                    "workload_score": workload_score,
                    "tasks": {
                        "in_progress": in_progress,
                        "blocked": blocked,
                        "completed": completed,
                        "total_assigned": in_progress + blocked + completed
                    },
                    "help": {
                        "requests_made": 0,  # TODO: Get from database
                        "requests_received": 0  # TODO: Get from database
                    }
                })

        return {
            "status": "success",
            "team_workload": team_workload
        }

    except Exception as e:
        logger.error(f"Error getting team workload heatmap: {e}")
        return {
            "status": "success",
            "team_workload": []
        }
