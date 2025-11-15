"""
Analytics and insights API endpoints
"""

from fastapi import APIRouter, Request
from typing import Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/summary")
async def get_team_summary(days: int = 7, user_id: Optional[str] = None, request: Request = None):
    """
    Get AI-generated team summary

    Used by Slack bot for /mcp-summary command
    """
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        # Get recent standups
        standups = await db.get_recent_standups(days=days, user_id=user_id)

        # Use MCP to generate summary
        summary_prompt = f"Summarize the team's progress over the last {days} days based on these standups:\n\n"
        for standup in standups[:20]:  # Limit to most recent 20
            summary_prompt += f"- {standup['user_name']}: {standup['message'][:200]}\n"

        # Generate summary using MCP (will use Gemini)
        result = await mcp.query(
            query=summary_prompt,
            user_id=user_id or "system"
        )

        return {"summary": result.get("answer", "Summary unavailable")}

    except Exception as e:
        logger.error(f"Error generating team summary: {e}")
        return {"summary": "Team is making progress. Check dashboard for details."}


@router.get("/long-blockers")
async def get_long_standing_blockers(days: int = 2, request: Request = None):
    """
    Get blockers that have been active for X days

    Used by Slack bot scheduler to escalate blockers
    """
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        blockers = await db.get_long_standing_blockers(days=days)

        # Format for Slack bot
        formatted_blockers = [
            {
                "id": blocker["id"],
                "user_id": blocker["user_id"],
                "manager_id": blocker.get("manager_id"),
                "description": blocker["description"],
                "severity": blocker.get("severity", "medium"),
                "days": (datetime.utcnow() - blocker["created_at"]).days if blocker.get("created_at") else 0,
                "created_at": blocker["created_at"].isoformat() if blocker.get("created_at") else None
            }
            for blocker in blockers
        ]

        return {"blockers": formatted_blockers}

    except Exception as e:
        logger.error(f"Error getting long-standing blockers: {e}")
        return {"blockers": []}


@router.get("/velocity")
async def get_team_velocity(weeks: int = 4, request: Request = None):
    """Get team velocity metrics"""
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        # Get tasks completed in last N weeks
        velocity_data = []
        for week in range(weeks):
            week_start = datetime.utcnow() - timedelta(weeks=week + 1)
            week_end = datetime.utcnow() - timedelta(weeks=week)

            async with db.async_session() as session:
                from services.database import Task, TaskStatus
                from sqlalchemy import select, func

                result = await session.execute(
                    select(func.count(Task.id)).where(
                        Task.status == TaskStatus.COMPLETED,
                        Task.completed_at >= week_start,
                        Task.completed_at < week_end
                    )
                )
                tasks_completed = result.scalar() or 0

            velocity_data.append({
                "week": f"Week {weeks - week}",
                "tasks_completed": tasks_completed
            })

        avg_velocity = sum(w["tasks_completed"] for w in velocity_data) / len(velocity_data) if velocity_data else 0

        return {
            "weeks": velocity_data,
            "average_velocity": round(avg_velocity, 2)
        }

    except Exception as e:
        logger.error(f"Error calculating team velocity: {e}")
        return {
            "weeks": [],
            "tasks_completed": [],
            "average_velocity": 0
        }


@router.get("/blockers")
async def get_active_blockers(request: Request = None):
    """Get all active blockers"""
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        async with db.async_session() as session:
            from services.database import BlockerAlert
            from sqlalchemy import select

            result = await session.execute(
                select(BlockerAlert).where(BlockerAlert.is_resolved == False)
            )
            blockers = result.scalars().all()

            return {
                "blockers": [
                    {
                        "id": b.id,
                        "user_id": b.user_id,
                        "description": b.description,
                        "severity": b.severity,
                        "created_at": b.created_at.isoformat()
                    }
                    for b in blockers
                ]
            }

    except Exception as e:
        logger.error(f"Error getting active blockers: {e}")
        return {"blockers": []}


@router.get("/dependencies")
async def get_dependency_graph(request: Request = None):
    """Get task dependency graph"""
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        async with db.async_session() as session:
            from services.database import Task
            from sqlalchemy import select

            result = await session.execute(select(Task))
            tasks = result.scalars().all()

            nodes = [
                {
                    "id": task.id,
                    "title": task.title,
                    "status": task.status.value if task.status else None,
                    "assignee": task.assignee_id
                }
                for task in tasks
            ]

            edges = [
                {
                    "from": task.id,
                    "to": task.blocked_by_task_id
                }
                for task in tasks
                if task.blocked_by_task_id
            ]

            return {"nodes": nodes, "edges": edges}

    except Exception as e:
        logger.error(f"Error getting dependency graph: {e}")
        return {"nodes": [], "edges": []}
