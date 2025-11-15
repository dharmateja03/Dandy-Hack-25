"""
Standup API endpoints
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

router = APIRouter()


class StandupSubmission(BaseModel):
    user_id: str
    message: str
    timestamp: Optional[datetime] = None


class StandupResponse(BaseModel):
    status: str
    context_id: str
    parsed_data: Dict[str, Any]
    help_requests_routed: List[Dict]
    blockers_detected: int


@router.post("/submit", response_model=StandupResponse)
async def submit_standup(submission: StandupSubmission, request: Request):
    """
    Submit a standup update

    This is called by the Slack bot when a user submits their standup
    """
    mcp = request.app.state.mcp

    if not mcp:
        raise HTTPException(status_code=503, detail="MCP not initialized")

    try:
        result = await mcp.process_standup(
            user_id=submission.user_id,
            message=submission.message,
            timestamp=submission.timestamp
        )

        # Also save to database
        await mcp.database.save_standup(
            user_id=submission.user_id,
            message=submission.message,
            parsed_data=result.get('parsed_data', {})
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent")
async def get_recent_standups(days: int = 7, user_id: Optional[str] = None, request: Request = None):
    """Get recent standups"""
    mcp = request.app.state.mcp

    if not mcp:
        raise HTTPException(status_code=503, detail="MCP not initialized")

    try:
        standups = await mcp.database.get_recent_standups(days=days, user_id=user_id)
        return {"standups": standups}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}")
async def get_user_standups(user_id: str, limit: int = 10, request: Request = None):
    """Get standups for a specific user"""
    mcp = request.app.state.mcp

    if not mcp:
        raise HTTPException(status_code=503, detail="MCP not initialized")

    try:
        standups = await mcp.database.get_recent_standups(days=30, user_id=user_id)
        return {"standups": standups[:limit]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
