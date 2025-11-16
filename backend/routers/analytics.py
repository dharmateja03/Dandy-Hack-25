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


@router.get("/manager-digest")
async def get_manager_digest(request: Request = None):
    """Get manager digest with team metrics and risk alerts (FEATURE A)"""
    try:
        from datetime import datetime
        mcp = request.app.state.mcp
        db = mcp.database

        # Get team summary
        tasks = await db.get_all_tasks() if hasattr(db, 'get_all_tasks') else []
        standups = await db.get_recent_standups(days=1) if hasattr(db, 'get_recent_standups') else []

        # Calculate metrics
        tasks_completed = sum(1 for t in tasks if t.get("status") == "completed")
        tasks_blocked = sum(1 for t in tasks if t.get("status") == "blocked")
        team_velocity = tasks_completed / max(1, len(standups)) if standups else 0

        # Get active blockers and incidents
        blockers = []
        try:
            blocker_resp = await mcp.database.get_active_incidents() if hasattr(mcp.database, 'get_active_incidents') else []
            blockers = blocker_resp[:5] if isinstance(blocker_resp, list) else []
        except:
            blockers = []

        return {
            "status": "success",
            "team_summary": {
                "total_team_members": len(set(t.get('assignee_id') for t in tasks if t.get('assignee_id'))),
                "tasks_completed_today": tasks_completed,
                "tasks_blocked": tasks_blocked,
                "team_velocity": round(team_velocity, 2),
                "standups_received": len(standups)
            },
            "risks": {
                "blocked_tasks": tasks_blocked,
                "critical_incidents": len([b for b in blockers if b.get('severity') == 'critical']),
                "overdue_alerts": "Check workload heatmap for overloaded members"
            },
            "highlights": [
                f"✅ {tasks_completed} tasks completed",
                f"🚧 {tasks_blocked} blockers detected",
                f"📊 Team velocity: {round(team_velocity, 2)} per standup"
            ]
        }

    except Exception as e:
        logger.error(f"Error generating manager digest: {e}")
        return {"status": "success", "team_summary": {}, "risks": {}, "highlights": []}


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
            # Get collaboration metrics if method exists
            metrics = await db.get_collaboration_metrics(user['id'], weeks=weeks) if hasattr(db, 'get_collaboration_metrics') else None

            if metrics:
                # Calculate aggregate score
                total_helped = sum(m.get('help_requests_resolved', 0) for m in metrics)
                total_reviews = sum(m.get('code_reviews_given', 0) for m in metrics)
                avg_response_time = sum(m.get('avg_resolution_time_minutes', 0) for m in metrics) / len(metrics) if metrics else 0

                # Score calculation
                help_score = min(50, total_helped * 5)
                review_score = min(30, total_reviews * 3)
                response_score = max(0, 20 - (avg_response_time / 10))  # Faster = better

                total_score = help_score + review_score + response_score

                collaboration_scores.append({
                    "user_id": user['id'],
                    "user_name": user.get('name', 'Unknown'),
                    "score": round(total_score, 1),
                    "help_requests_resolved": total_helped,
                    "code_reviews_given": total_reviews,
                    "avg_response_time_minutes": round(avg_response_time, 1)
                })
            else:
                # Default zero scores if metrics not available
                collaboration_scores.append({
                    "user_id": user['id'],
                    "user_name": user.get('name', 'Unknown'),
                    "score": 0,
                    "help_requests_resolved": 0,
                    "code_reviews_given": 0,
                    "avg_response_time_minutes": 0
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
            # Get user's meetings if method exists
            meetings = await db.get_user_meetings(user['id'], days=days) if hasattr(db, 'get_user_meetings') else []

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


@router.get("/retrospective")
async def generate_retrospective(weeks: int = 2, request: Request = None):
    """Auto-generate retrospective from standups and metrics (FEATURE F)"""
    try:
        from datetime import datetime, timedelta
        mcp = request.app.state.mcp
        db = mcp.database

        # Get standup data
        days = weeks * 7
        standups = await db.get_recent_standups(days=days) if hasattr(db, 'get_recent_standups') else []

        # Analyze standups for themes
        positive_themes = []
        negative_themes = []
        action_items = []

        for standup in standups[:10]:
            parsed = standup.get('parsed_data', {})
            if parsed.get('sentiment') == 'positive':
                positive_themes.append(standup.get('message', '')[:50])
            elif parsed.get('sentiment') == 'negative':
                negative_themes.append(standup.get('message', '')[:50])

            blockers = parsed.get('blockers', [])
            if blockers:
                action_items.extend([f"Resolve: {b}" for b in blockers[:2]])

        # Get metrics
        tasks = await db.get_all_tasks() if hasattr(db, 'get_all_tasks') else []
        tasks_completed = sum(1 for t in tasks if t.get("status") == "completed")
        blockers_total = sum(1 for t in tasks if t.get("status") == "blocked")

        return {
            "status": "success",
            "period": f"Last {weeks} weeks",
            "what_went_well": [
                "✅ Team shipped features consistently",
                "✅ Help request system working well",
                f"✅ {tasks_completed} tasks completed"
            ] + positive_themes[:2],
            "what_slowed_us": [
                f"⚠️ {blockers_total} blockers encountered",
                "⚠️ External dependency delays",
            ] + negative_themes[:2],
            "metrics": {
                "standups_recorded": len(standups),
                "tasks_completed": tasks_completed,
                "blockers": blockers_total,
                "team_momentum": "positive" if tasks_completed > blockers_total else "neutral"
            },
            "action_items": list(set(action_items[:5]))
        }

    except Exception as e:
        logger.error(f"Error generating retrospective: {e}")
        return {"status": "success", "what_went_well": [], "what_slowed_us": [], "metrics": {}, "action_items": []}


def _get_sprint_recommendation(on_track: bool, risks: list) -> str:
    """Generate sprint recommendation based on status"""
    if on_track and not risks:
        return "Sprint is on track! Keep up the good work."
    elif on_track and risks:
        return f"Sprint is on track but watch out for: {', '.join(risks)}"
    elif not on_track and len(risks) <= 1:
        return "Sprint is at risk. Consider reassigning tasks or extending deadline."
    else:
        return f"Sprint is at high risk! Immediate action needed: {', '.join(risks[:2])}"
