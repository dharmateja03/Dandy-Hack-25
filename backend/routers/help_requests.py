"""
Help Request API endpoints
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def get_all_help_requests(request: Request):
    """Get all help requests"""
    try:
        db = request.app.state.db
        async with db.async_session() as session:
            from services.database import HelpRequest, HelpRequestStatus
            from sqlalchemy import select
            
            result = await session.execute(
                select(HelpRequest).order_by(HelpRequest.created_at.desc())
            )
            requests = result.scalars().all()
            
            return [
                {
                    "id": str(r.id),
                    "requester_id": r.requester_id,
                    "requester_name": r.requester_name,
                    "topic": r.topic,
                    "description": r.description,
                    "status": r.status.value if r.status else "pending",
                    "expert_id": r.expert_id,
                    "expert_name": r.expert_name,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in requests
            ]
    except Exception as e:
        logger.error(f"Error fetching help requests: {e}")
        return []


# Request/Response Models
class HelpRequestCreate(BaseModel):
    requester_id: str
    topic: str
    details: str
    urgency: Optional[str] = "medium"


@router.post("/create")
async def create_help_request(help_request: HelpRequestCreate, request: Request):
    """
    Create and route a new help request

    Used by Slack bot when users:
    - Request help via modal
    - React with 🙋 emoji
    - Mention need for help in standup
    """
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        # Route help request using MCP's intelligent routing
        expert = await mcp.route_help_request(
            requester_id=help_request.requester_id,
            topic=help_request.topic,
            context=help_request.details
        )

        # Create help request in database
        help_req_id = await db.create_help_request(
            from_user=help_request.requester_id,
            to_user=expert["user_id"] if expert else None,
            topic=help_request.topic,
            context=help_request.details,
            urgency=help_request.urgency
        )

        logger.info(f"Help request {help_req_id} created and routed")

        return {
            "status": "success",
            "help_request_id": help_req_id,
            "assigned_to": expert["user_id"] if expert else None,
            "message": f"Help request routed to expert"
        }

    except Exception as e:
        logger.error(f"Error creating help request: {e}")
        # Return success without routing if routing fails
        return {
            "status": "success",
            "help_request_id": None,
            "assigned_to": None,
            "message": "Help request created, routing in progress"
        }


@router.get("/queue/active")
async def get_active_help_requests(request: Request = None):
    """Get active help requests queue for dashboard"""
    try:
        from datetime import datetime
        mcp = request.app.state.mcp
        db = mcp.database

        # Get pending help requests
        async with db.async_session() as session:
            from services.database import HelpRequest, HelpRequestStatus, User
            from sqlalchemy import select

            result = await session.execute(
                select(HelpRequest, User).join(
                    User, HelpRequest.from_user_id == User.id
                ).where(
                    HelpRequest.status == HelpRequestStatus.PENDING
                )
            )
            request_user_pairs = result.all()

            requests = []
            for req, user in request_user_pairs:
                # Calculate wait time in hours
                wait_time = datetime.utcnow() - req.created_at if req.created_at else None
                wait_time_hours = wait_time.total_seconds() / 3600 if wait_time else 0

                requests.append({
                    "id": req.id,
                    "from_user_id": req.from_user_id,
                    "requester_name": user.name,
                    "helper_name": None,  # TODO: Get helper name when assigned
                    "topic": req.topic,
                    "urgency": req.urgency or "medium",
                    "status": req.status.value if req.status else "pending",
                    "wait_time_hours": wait_time_hours,
                    "created_at": req.created_at.isoformat() if req.created_at else None
                })

            return {
                "status": "success",
                "help_requests": requests,
                "count": len(requests)
            }

    except Exception as e:
        logger.error(f"Error getting active help requests: {e}")
        return {
            "status": "success",
            "help_requests": [],
            "count": 0
        }


@router.get("/stale")
async def get_stale_help_requests(hours: int = 6, request: Request = None):
    """
    Get help requests with no response for X hours

    Used by Slack bot scheduler to send follow-up reminders
    """
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        stale_requests = await db.get_stale_help_requests(hours=hours)

        # Format for Slack bot
        formatted_requests = [
            {
                "id": req["id"],
                "requester_id": req["from_user_id"],
                "assigned_to": req["to_user_id"],
                "topic": req["topic"],
                "created_at": req["created_at"].isoformat() if req.get("created_at") else None
            }
            for req in stale_requests
        ]

        return {"requests": formatted_requests}

    except Exception as e:
        logger.error(f"Error getting stale help requests: {e}")
        return {"requests": []}


@router.get("/pending")
async def get_pending_help_requests(user_id: str, request: Request = None):
    """Get pending help requests for a user"""
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        # Get help requests assigned to this user
        async with db.async_session() as session:
            from services.database import HelpRequest, HelpRequestStatus
            from sqlalchemy import select

            result = await session.execute(
                select(HelpRequest).where(
                    HelpRequest.to_user_id == user_id,
                    HelpRequest.status == HelpRequestStatus.PENDING
                )
            )
            requests = result.scalars().all()

            return {
                "help_requests": [
                    {
                        "id": req.id,
                        "from_user_id": req.from_user_id,
                        "topic": req.topic,
                        "context": req.context,
                        "urgency": req.urgency,
                        "created_at": req.created_at.isoformat()
                    }
                    for req in requests
                ]
            }

    except Exception as e:
        logger.error(f"Error getting pending help requests: {e}")
        return {"help_requests": []}


@router.post("/{request_id}/accept")
async def accept_help_request(request_id: int, request: Request = None):
    """Accept a help request"""
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        async with db.async_session() as session:
            from services.database import HelpRequest, HelpRequestStatus
            from sqlalchemy import select, update
            from datetime import datetime

            await session.execute(
                update(HelpRequest)
                .where(HelpRequest.id == request_id)
                .values(
                    status=HelpRequestStatus.ACCEPTED,
                    accepted_at=datetime.utcnow()
                )
            )
            await session.commit()

        logger.info(f"Help request {request_id} accepted")

        return {"status": "accepted", "request_id": request_id}

    except Exception as e:
        logger.error(f"Error accepting help request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{request_id}/resolve")
async def resolve_help_request(
    request_id: int,
    resolution_notes: str,
    request: Request = None
):
    """Mark help request as resolved"""
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        async with db.async_session() as session:
            from services.database import HelpRequest, HelpRequestStatus
            from sqlalchemy import select, update
            from datetime import datetime

            await session.execute(
                update(HelpRequest)
                .where(HelpRequest.id == request_id)
                .values(
                    status=HelpRequestStatus.RESOLVED,
                    resolved_at=datetime.utcnow(),
                    resolution_notes=resolution_notes
                )
            )
            await session.commit()

        logger.info(f"Help request {request_id} resolved")

        return {"status": "resolved", "request_id": request_id}

    except Exception as e:
        logger.error(f"Error resolving help request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/received-today")
async def get_received_help_requests_today(user_id: str, request: Request = None):
    """
    Get help requests that this user received today, sorted by priority

    Used by /my-help-requests Slack command
    """
    try:
        from datetime import datetime, timedelta
        mcp = request.app.state.mcp
        db = mcp.database

        # Get help requests received by this user today
        async with db.async_session() as session:
            from services.database import HelpRequest, User
            from sqlalchemy import select, and_

            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            result = await session.execute(
                select(HelpRequest, User).join(
                    User, HelpRequest.from_user_id == User.id
                ).where(
                    and_(
                        HelpRequest.to_user_id == user_id,
                        HelpRequest.created_at >= today_start
                    )
                ).order_by(
                    # Sort by urgency/priority (high first)
                    HelpRequest.urgency.desc(),
                    HelpRequest.created_at.desc()
                )
            )
            request_user_pairs = result.all()

            help_requests = []
            for req, requester_user in request_user_pairs:
                help_requests.append({
                    "id": req.id,
                    "topic": req.topic,
                    "from_user_id": req.from_user_id,
                    "from_user_name": requester_user.name,
                    "priority": (req.urgency or "medium").upper(),
                    "status": (req.status.value if req.status else "pending").lower(),
                    "created_at": req.created_at.isoformat() if req.created_at else None,
                    "context": req.context
                })

            return {
                "status": "success",
                "help_requests": help_requests,
                "count": len(help_requests)
            }

    except Exception as e:
        logger.error(f"Error getting received help requests for {user_id}: {e}")
        return {
            "status": "success",
            "help_requests": [],
            "count": 0
        }


@router.get("/user/{user_id}/helping-with-today")
async def get_helping_with_today(user_id: str, request: Request = None):
    """
    Get help requests this user is helping with today (assigned_to = user_id)

    Used by /my-helping Slack command
    """
    try:
        from datetime import datetime, timedelta
        mcp = request.app.state.mcp
        db = mcp.database

        # Get help requests assigned to this user today
        async with db.async_session() as session:
            from services.database import HelpRequest, User
            from sqlalchemy import select, and_

            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            result = await session.execute(
                select(HelpRequest, User).join(
                    User, HelpRequest.from_user_id == User.id
                ).where(
                    and_(
                        HelpRequest.to_user_id == user_id,
                        HelpRequest.created_at >= today_start
                    )
                ).order_by(
                    HelpRequest.created_at.desc()
                )
            )
            request_user_pairs = result.all()

            helping_items = []
            for req, requester_user in request_user_pairs:
                # Calculate duration if accepted/resolved
                duration_minutes = 0
                if req.accepted_at and req.resolved_at:
                    duration = req.resolved_at - req.accepted_at
                    duration_minutes = int(duration.total_seconds() / 60)
                elif req.accepted_at:
                    duration = datetime.utcnow() - req.accepted_at
                    duration_minutes = int(duration.total_seconds() / 60)

                helping_items.append({
                    "id": req.id,
                    "topic": req.topic,
                    "to_user_id": req.from_user_id,
                    "to_user_name": requester_user.name,
                    "status": (req.status.value if req.status else "pending").lower(),
                    "duration_minutes": duration_minutes,
                    "created_at": req.created_at.isoformat() if req.created_at else None
                })

            return {
                "status": "success",
                "helping_items": helping_items,
                "count": len(helping_items)
            }

    except Exception as e:
        logger.error(f"Error getting helping-with for {user_id}: {e}")
        return {
            "status": "success",
            "helping_items": [],
            "count": 0
        }
