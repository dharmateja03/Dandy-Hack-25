"""
Blockers API endpoints
"""

from fastapi import APIRouter, Request, HTTPException
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/queue/active")
async def get_active_blockers_queue(request: Request = None):
    """Get active blockers queue for dashboard"""
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        # Get active blockers
        blockers = await db.get_active_blockers() if hasattr(db, 'get_active_blockers') else []

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
