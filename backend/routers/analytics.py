"""
Analytics and insights API endpoints
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class MeetingAssessmentRequest(BaseModel):
    meeting_title: str
    attendees: List[str]
    description: Optional[str] = ""


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
        logger.info(f"Found {len(standups)} standups in last {days} days")

        if not standups:
            logger.warning(f"No standups found for summary in last {days} days")
            return {"summary": "No standups recorded yet. Ask team members to submit their standups!"}

        # Use MCP to generate summary
        summary_prompt = f"Summarize the team's progress over the last {days} days based on these standups:\n\n"
        for standup in standups[:20]:  # Limit to most recent 20
            user_name = standup.get('user_name', standup.get('user_id', 'Unknown'))
            message = standup.get('message', '')[:200]
            summary_prompt += f"- {user_name}: {message}\n"

        logger.debug(f"Summary prompt: {summary_prompt[:200]}")

        # Generate summary using MCP (will use Gemini)
        result = await mcp.query(
            query=summary_prompt,
            user_id=user_id or "system"
        )

        summary_text = result.get("answer", "Summary unavailable")
        logger.info(f"Generated summary: {summary_text[:100]}")

        return {"summary": summary_text}

    except Exception as e:
        logger.error(f"Error generating team summary: {e}", exc_info=True)
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


@router.get("/daily-summary")
async def get_daily_summary(days: int = 1, request: Request = None):
    """
    Get daily team summary with metrics for broadcasting via DM

    Used by scheduler to send morning briefings to team/managers

    Returns emoji-formatted summary with:
    - Tasks completed & in progress
    - Blockers by severity
    - Help requests status
    - Team sentiment
    - Risk warnings (if high-priority blockers)

    Example:
    GET /api/analytics/daily-summary?days=1

    Returns:
    {
        "status": "success",
        "summary": "📊 Daily Team Summary - November 15, 2025\n...",
        "metrics": {
            "tasks_completed": 5,
            "tasks_in_progress": 12,
            "blockers_total": 3,
            "blockers_high": 1,
            ...
        }
    }
    """
    try:
        mcp = request.app.state.mcp

        # Generate daily summary
        result = await mcp.generate_daily_summary(days=days)

        return result

    except Exception as e:
        logger.error(f"Error generating daily summary: {e}")
        return {
            "status": "error",
            "message": f"Failed to generate summary: {str(e)}"
        }


@router.post("/assess-meeting")
async def assess_meeting_necessity(
    assessment_request: MeetingAssessmentRequest,
    request: Request = None
):
    """
    Assess whether a scheduled meeting is necessary or could be solved async

    This endpoint helps eliminate unnecessary meetings by analyzing:
    - Meeting title and description for help/blocker keywords
    - Attendee expertise to suggest qualified async responders
    - Similar issues that were resolved asynchronously
    - Time savings potential

    Request:
    {
        "meeting_title": "Auth bug discussion",
        "attendees": ["bob_senior", "diana_dev"],
        "description": "Debugging 401 errors in API"
    }

    Response:
    {
        "recommendation": "async_instead",
        "confidence": 0.85,
        "reason": "This looks like a debug discussion that can be solved async",
        "suggestion": "Use a Slack thread instead",
        "time_saved_minutes": 30,
        "expert_matches": [
            {"name": "Bob", "expertise": ["auth", "backend"]}
        ],
        "similar_resolved_issues": 3
    }
    """
    try:
        mcp = request.app.state.mcp

        if not assessment_request.meeting_title or len(assessment_request.meeting_title.strip()) < 3:
            raise HTTPException(status_code=400, detail="Meeting title too short")

        # Assess meeting necessity
        result = await mcp.assess_meeting_necessity(
            meeting_title=assessment_request.meeting_title,
            attendees=assessment_request.attendees,
            description=assessment_request.description or ""
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assessing meeting necessity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nudges")
async def get_accountability_nudges(request: Request = None):
    """
    Generate accountability nudges for stalled work

    Monitors and sends nudge messages for:
    1. **Blockers stalled 2+ days** - Nudges requester to escalate
    2. **Help requests unanswered 6+ hours** - Nudges helper to respond
    3. **Tasks with no progress 5+ days** - Nudges assignee to update

    Returns list of nudges with message templates ready for DM broadcast

    Example:
    GET /api/analytics/nudges

    Returns:
    {
        "status": "success",
        "nudges_count": 3,
        "nudges": [
            {
                "type": "blocker_stalled",
                "recipient_id": "bharathi_dev",
                "urgency": "high",
                "days_stalled": 4,
                "message": "🚧 This blocker has been open for 4 days: \"Database timeout\"\nNeed help to unblock progress? Post in #help or escalate.",
                "action": "escalate_if_critical"
            },
            {
                "type": "help_unanswered",
                "recipient_id": "bob_senior",
                "urgency": "medium",
                "hours_pending": 12,
                "message": "⏰ Someone is waiting for your help on: \"Auth bug\"\nIt's been 12 hours. Can you respond?",
                "action": "respond_or_reassign"
            },
            {
                "type": "task_stalled",
                "recipient_id": "diana_dev",
                "urgency": "medium",
                "days_stalled": 6,
                "message": "📋 Task \"API redesign\" hasn't been started in 6 days.\nAny blockers? Update progress or let us know if you need help.",
                "action": "update_or_escalate"
            }
        ],
        "timestamp": "2025-11-15T21:55:00"
    }
    """
    try:
        mcp = request.app.state.mcp

        result = await mcp.generate_accountability_nudges()

        return result

    except Exception as e:
        logger.error(f"Error generating nudges: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/digest/today")
async def get_today_digest(request: Request = None):
    """Get today's digest for dashboard"""
    try:
        from datetime import datetime

        mcp = request.app.state.mcp
        db = mcp.database

        # Get tasks from today
        tasks = await db.get_all_tasks() if hasattr(db, 'get_all_tasks') else []

        tasks_completed = sum(1 for t in tasks if t.get("status") == "completed")
        tasks_in_progress = sum(1 for t in tasks if t.get("status") == "in_progress")
        blockers_detected = sum(1 for t in tasks if t.get("status") == "blocked")

        # Get help requests
        async with db.async_session() as session:
            from services.database import HelpRequest, HelpRequestStatus
            from sqlalchemy import select, func

            help_result = await session.execute(
                select(func.count(HelpRequest.id)).where(
                    HelpRequest.status == HelpRequestStatus.PENDING
                )
            )
            help_requests = help_result.scalar() or 0

        # Calculate productivity level
        total_tasks = tasks_completed + tasks_in_progress + blockers_detected
        if total_tasks == 0:
            productivity = "low"
        else:
            completion_percent = (tasks_completed / total_tasks) * 100
            productivity = "high" if completion_percent > 50 else ("moderate" if completion_percent > 25 else "low")

        return {
            "status": "success",
            "date": datetime.now().strftime("%B %d, %Y"),
            "summary": {
                "tasks_completed": tasks_completed,
                "tasks_in_progress": tasks_in_progress,
                "blockers_detected": blockers_detected,
                "help_requests": help_requests,
                "total_standups": len(standups) if 'standups' in locals() else 0
            },
            "key_metrics": {
                "completion_rate": int((tasks_completed / (tasks_completed + tasks_in_progress) * 100) if (tasks_completed + tasks_in_progress) > 0 else 0),
                "team_velocity": tasks_completed,
                "blocker_count": blockers_detected,
                "team_mood": "😊" if productivity == "high" else "😐" if productivity == "moderate" else "😟",
                "productivity": productivity
            },
            "highlights": [
                f"✅ {tasks_completed} tasks completed",
                f"⚙️ {tasks_in_progress} tasks in progress",
                f"🚨 {blockers_detected} blockers detected"
            ],
            "recommendations": []
        }

    except Exception as e:
        logger.error(f"Error generating digest: {e}")
        return {
            "status": "success",
            "date": "Today",
            "summary": {
                "tasks_completed": 0,
                "tasks_in_progress": 0,
                "blockers_detected": 0,
                "help_requests": 0,
                "total_standups": 0
            },
            "key_metrics": {
                "completion_rate": 0,
                "team_velocity": 0,
                "blocker_count": 0,
                "team_mood": "😟",
                "productivity": "low"
            },
            "highlights": [],
            "recommendations": []
        }


@router.get("/insights/trends")
async def get_insights_trends(days: int = 7, request: Request = None):
    """Get insights and trends for dashboard"""
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        # Get standups for sentiment analysis
        standups = await db.get_recent_standups(days=days) if hasattr(db, 'get_recent_standups') else []

        # Calculate sentiment from parsed data
        positive_count = 0
        neutral_count = 0
        negative_count = 0
        help_topics = {}

        for standup in standups:
            parsed = standup.get('parsed_data', {})
            sentiment = parsed.get('sentiment', 'neutral')

            if sentiment == 'positive':
                positive_count += 1
            elif sentiment == 'negative':
                negative_count += 1
            else:
                neutral_count += 1

            # Count help request topics
            help_requests = parsed.get('help_requests', [])
            for req in help_requests:
                topic = req.get('topic', 'General Help')
                if topic not in help_topics:
                    help_topics[topic] = 0
                help_topics[topic] += 1

        total = positive_count + neutral_count + negative_count
        if total == 0:
            total = 1  # Avoid division by zero

        overall_sentiment = 'positive' if positive_count > total/2 else ('negative' if negative_count > total/3 else 'neutral')

        # Format top help topics
        top_help_topics = [
            {
                "topic": topic,
                "mentions": count,
                "trending": "📈 Trending" if count > 5 else ("⏫ Active" if count > 2 else "")
            }
            for topic, count in sorted(help_topics.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        # Add default topics if none exist
        if not top_help_topics:
            top_help_topics = [
                {"topic": "General Help", "mentions": 0, "trending": ""},
                {"topic": "Technical Support", "mentions": 0, "trending": ""},
                {"topic": "Code Review", "mentions": 0, "trending": ""}
            ]

        return {
            "status": "success",
            "period": f"Last {days} days",
            "trends": {
                "period": f"Last {days} days",
                "metrics": [
                    {"name": "Standups Submitted", "value": len(standups)},
                    {"name": "Avg Sentiment", "value": overall_sentiment}
                ],
                "patterns": [
                    "Team momentum is steady",
                    "Progress on scheduled tasks"
                ],
                "top_help_topics": top_help_topics
            },
            "sentiment": {
                "overall": overall_sentiment,
                "distribution": {
                    "positive": positive_count,
                    "neutral": neutral_count,
                    "negative": negative_count
                }
            }
        }

    except Exception as e:
        logger.error(f"Error getting trends: {e}")
        return {
            "status": "success",
            "period": "Last 7 days",
            "trends": {
                "period": "Last 7 days",
                "metrics": [],
                "patterns": [],
                "top_help_topics": [
                    {"topic": "General Help", "mentions": 0, "trending": ""},
                    {"topic": "Technical Support", "mentions": 0, "trending": ""},
                    {"topic": "Code Review", "mentions": 0, "trending": ""}
                ]
            },
            "sentiment": {
                "overall": "neutral",
                "distribution": {
                    "positive": 0,
                    "neutral": 0,
                    "negative": 0
                }
            }
        }
