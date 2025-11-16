"""
Blockers API endpoints
"""

from fastapi import APIRouter, Request, HTTPException
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def get_all_blockers(request: Request):
    """Get all active blockers"""
    try:
        db = request.app.state.db
        async with db.async_session() as session:
            from services.database import Blocker
            from sqlalchemy import select
            
            result = await session.execute(
                select(Blocker).where(Blocker.resolved == False).order_by(Blocker.created_at.desc())
            )
            blockers = result.scalars().all()
            
            return [
                {
                    "id": str(b.id),
                    "user_id": b.user_id,
                    "user_name": b.user_name,
                    "description": b.description,
                    "severity": b.severity,
                    "resolved": b.resolved,
                    "created_at": b.created_at.isoformat() if b.created_at else None,
                }
                for b in blockers
            ]
    except Exception as e:
        logger.error(f"Error fetching blockers: {e}")
        return []


@router.get("/queue/active")
async def get_active_blockers_queue(request: Request = None):
    """Get active blockers queue for dashboard"""
    try:
        from datetime import datetime
        mcp = request.app.state.mcp
        db = mcp.database

        # Get active blockers from database
        async with db.async_session() as session:
            from services.database import BlockerAlert, User
            from sqlalchemy import select

            result = await session.execute(
                select(BlockerAlert, User).join(
                    User, BlockerAlert.user_id == User.id
                ).where(
                    BlockerAlert.is_resolved == False
                )
            )
            blocker_user_pairs = result.all()

            blockers = []
            for blocker, user in blocker_user_pairs:
                # Calculate time since creation in hours
                time_since = datetime.utcnow() - blocker.created_at if blocker.created_at else None
                time_since_hours = time_since.total_seconds() / 3600 if time_since else 0

                blockers.append({
                    "id": blocker.id,
                    "user_id": blocker.user_id,
                    "user_name": user.name,
                    "description": blocker.description,
                    "severity": blocker.severity or "medium",
                    "is_resolved": blocker.is_resolved,
                    "time_since_creation_hours": time_since_hours,
                    "created_at": blocker.created_at.isoformat() if blocker.created_at else None
                })

            return {
                "status": "success",
                "blockers": blockers,
                "count": len(blockers)
            }

    except Exception as e:
        logger.error(f"Error getting active blockers: {e}")
        return {
            "status": "success",
            "blockers": [],
            "count": 0
        }
