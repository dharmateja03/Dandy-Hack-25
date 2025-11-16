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


@router.get("/sprint-prediction")
async def predict_sprint_deadline(sprint_end_date: Optional[str] = None, request: Request = None):
    """
    Predict if sprint will be completed on time based on current velocity
    """
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        # Get current velocity (last 4 weeks)
        velocity = await get_team_velocity(weeks=4, request=request)
        avg_velocity = velocity['average_velocity']

        # Get outstanding tasks
        async with db.async_session() as session:
            from services.database import Task, TaskStatus
            from sqlalchemy import select, func

            # Count in-progress and not-started tasks
            result = await session.execute(
                select(func.count(Task.id)).where(
                    Task.status.in_([TaskStatus.IN_PROGRESS, TaskStatus.NOT_STARTED])
                )
            )
            outstanding_tasks = result.scalar() or 0

            # Get blocked tasks
            blocked_result = await session.execute(
                select(func.count(Task.id)).where(
                    Task.status == TaskStatus.BLOCKED
                )
            )
            blocked_tasks = blocked_result.scalar() or 0

        # Calculate time needed based on velocity
        weeks_needed = outstanding_tasks / avg_velocity if avg_velocity > 0 else float('inf')

        # Parse sprint end date if provided
        days_remaining = 14  # Default 2-week sprint
        if sprint_end_date:
            end_date = datetime.fromisoformat(sprint_end_date)
            days_remaining = (end_date - datetime.utcnow()).days

        # Prediction
        on_track = weeks_needed * 7 <= days_remaining
        completion_probability = min(100, max(0, (days_remaining / (weeks_needed * 7)) * 100)) if weeks_needed > 0 else 100

        # Identify risks
        risks = []
        if blocked_tasks > 0:
            risks.append(f"{blocked_tasks} tasks are blocked")
        if avg_velocity < 5:
            risks.append("Team velocity is low")
        if outstanding_tasks > avg_velocity * 2:
            risks.append("Too many outstanding tasks for current velocity")

        return {
            "on_track": on_track,
            "completion_probability": round(completion_probability, 1),
            "outstanding_tasks": outstanding_tasks,
            "blocked_tasks": blocked_tasks,
            "average_velocity": avg_velocity,
            "weeks_needed": round(weeks_needed, 2),
            "days_remaining": days_remaining,
            "risks": risks,
            "recommendation": _get_sprint_recommendation(on_track, risks)
        }

    except Exception as e:
        logger.error(f"Error predicting sprint: {e}")
        return {
            "on_track": None,
            "completion_probability": 0,
            "error": str(e)
        }


@router.get("/bottleneck-heatmap")
async def get_bottleneck_heatmap(request: Request = None):
    """
    Generate bottleneck heatmap showing where work is stuck
    """
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        async with db.async_session() as session:
            from services.database import Task, TaskStatus, User, HelpRequest, HelpRequestStatus
            from sqlalchemy import select, func

            # Find users with most blocked tasks
            blocked_by_user = await session.execute(
                select(
                    Task.assignee_id,
                    User.name,
                    func.count(Task.id).label('blocked_count')
                ).join(User, Task.assignee_id == User.id)
                .where(Task.status == TaskStatus.BLOCKED)
                .group_by(Task.assignee_id, User.name)
            )
            blocked_data = blocked_by_user.all()

            # Find users with most pending help requests
            pending_help = await session.execute(
                select(
                    HelpRequest.to_user_id,
                    User.name,
                    func.count(HelpRequest.id).label('pending_count')
                ).join(User, HelpRequest.to_user_id == User.id)
                .where(HelpRequest.status == HelpRequestStatus.PENDING)
                .group_by(HelpRequest.to_user_id, User.name)
            )
            help_data = pending_help.all()

            # Find stalled tasks (no update in 3+ days)
            three_days_ago = datetime.utcnow() - timedelta(days=3)
            stalled = await session.execute(
                select(
                    Task.assignee_id,
                    User.name,
                    func.count(Task.id).label('stalled_count')
                ).join(User, Task.assignee_id == User.id)
                .where(
                    Task.status == TaskStatus.IN_PROGRESS,
                    Task.started_at < three_days_ago
                )
                .group_by(Task.assignee_id, User.name)
            )
            stalled_data = stalled.all()

        # Combine into heatmap
        heatmap = {}

        for user_id, name, count in blocked_data:
            if user_id not in heatmap:
                heatmap[user_id] = {"user_id": user_id, "user_name": name, "blocked": 0, "pending_help": 0, "stalled": 0}
            heatmap[user_id]["blocked"] = count

        for user_id, name, count in help_data:
            if user_id not in heatmap:
                heatmap[user_id] = {"user_id": user_id, "user_name": name, "blocked": 0, "pending_help": 0, "stalled": 0}
            heatmap[user_id]["pending_help"] = count

        for user_id, name, count in stalled_data:
            if user_id not in heatmap:
                heatmap[user_id] = {"user_id": user_id, "user_name": name, "blocked": 0, "pending_help": 0, "stalled": 0}
            heatmap[user_id]["stalled"] = count

        # Calculate bottleneck score
        for user_id, data in heatmap.items():
            data["bottleneck_score"] = (data["blocked"] * 3) + (data["pending_help"] * 2) + (data["stalled"] * 1)

        # Sort by score
        sorted_heatmap = sorted(heatmap.values(), key=lambda x: x["bottleneck_score"], reverse=True)

        return {
            "heatmap": sorted_heatmap,
            "total_bottlenecks": len(sorted_heatmap),
            "critical_users": [h for h in sorted_heatmap if h["bottleneck_score"] >= 5]
        }

    except Exception as e:
        logger.error(f"Error generating bottleneck heatmap: {e}")
        return {"heatmap": [], "total_bottlenecks": 0, "critical_users": []}


@router.get("/collaboration-score")
async def get_team_collaboration_score(weeks: int = 4, request: Request = None):
    """
    Calculate team collaboration scores
    """
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        # Get all active users
        users = await db.get_all_active_users()

        collaboration_scores = []
        for user in users:
            # Get collaboration metrics
            metrics = await db.get_collaboration_metrics(user['id'], weeks=weeks)

            if metrics:
                # Calculate aggregate score
                total_helped = sum(m['help_requests_resolved'] for m in metrics)
                total_reviews = sum(m['code_reviews_given'] for m in metrics)
                avg_response_time = sum(m['avg_resolution_time_minutes'] for m in metrics) / len(metrics)

                # Score calculation
                help_score = min(50, total_helped * 5)
                review_score = min(30, total_reviews * 3)
                response_score = max(0, 20 - (avg_response_time / 10))  # Faster = better

                total_score = help_score + review_score + response_score

                collaboration_scores.append({
                    "user_id": user['id'],
                    "user_name": user['name'],
                    "score": round(total_score, 1),
                    "help_requests_resolved": total_helped,
                    "code_reviews_given": total_reviews,
                    "avg_response_time_minutes": round(avg_response_time, 1)
                })

        # Sort by score
        collaboration_scores.sort(key=lambda x: x['score'], reverse=True)

        return {
            "collaboration_scores": collaboration_scores,
            "top_collaborators": collaboration_scores[:5] if len(collaboration_scores) >= 5 else collaboration_scores
        }

    except Exception as e:
        logger.error(f"Error calculating collaboration scores: {e}")
        return {"collaboration_scores": [], "top_collaborators": []}


@router.get("/meeting-time-saved")
async def get_meeting_time_saved(days: int = 30, request: Request = None):
    """
    Calculate time saved by reducing meetings
    """
    try:
        calendar_service = request.app.state.calendar

        if not calendar_service:
            return {
                "time_saved_hours": 0,
                "meetings_eliminated": 0,
                "message": "Calendar integration not configured"
            }

        # Get all users
        mcp = request.app.state.mcp
        db = mcp.database
        users = await db.get_all_active_users()

        total_meeting_time = 0
        unnecessary_meeting_time = 0
        total_meetings = 0
        unnecessary_meetings = 0

        for user in users:
            # Get user's meetings
            meetings = await db.get_user_meetings(user['id'], days=days)

            for meeting in meetings:
                total_meetings += 1
                total_meeting_time += meeting.get('duration_minutes', 0)

                # Check if meeting was deemed unnecessary
                if meeting.get('could_be_async') or not meeting.get('was_necessary'):
                    unnecessary_meetings += 1
                    unnecessary_meeting_time += meeting.get('duration_minutes', 0)

        return {
            "total_meetings": total_meetings,
            "total_meeting_time_hours": round(total_meeting_time / 60, 2),
            "unnecessary_meetings": unnecessary_meetings,
            "time_saved_hours": round(unnecessary_meeting_time / 60, 2),
            "time_saved_percentage": round((unnecessary_meeting_time / total_meeting_time * 100) if total_meeting_time > 0 else 0, 1),
            "avg_meeting_duration_minutes": round(total_meeting_time / total_meetings) if total_meetings > 0 else 0
        }

    except Exception as e:
        logger.error(f"Error calculating meeting time saved: {e}")
        return {
            "time_saved_hours": 0,
            "meetings_eliminated": 0,
            "error": str(e)
        }


def _get_sprint_recommendation(on_track: bool, risks: list) -> str:
    """Generate sprint recommendation based on status"""
    if on_track and not risks:
        return "Sprint is on track! Keep up the good work."
    elif on_track but risks:
        return f"Sprint is on track but watch out for: {', '.join(risks)}"
    elif not on_track and len(risks) <= 1:
        return "Sprint is at risk. Consider reassigning tasks or extending deadline."
    else:
        return f"Sprint is at high risk! Immediate action needed: {', '.join(risks[:2])}"
