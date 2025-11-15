"""
User Management Router
Handles user profile, expertise, and team hierarchy endpoints
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class ProfileUpdateRequest(BaseModel):
    expertise_tags: Optional[List[str]] = None
    timezone: Optional[str] = None
    standup_time: Optional[str] = None


@router.get("/{user_id}")
async def get_user(user_id: str, request: Request):
    """
    Get user by ID with manager and expertise info

    Used by Slack bot to:
    - Get manager ID for blocker notifications
    - Display user info
    """
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        user = await db.get_user(user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_users(request: Request):
    """
    Get all active users

    Used by Slack bot for:
    - Daily standup reminders
    - Team roster
    """
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        users = await db.get_all_active_users()

        return {"users": users}

    except Exception as e:
        logger.error(f"Error getting active users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/profile")
async def update_user_profile(
    user_id: str,
    profile_update: ProfileUpdateRequest,
    request: Request
):
    """
    Update user profile with expertise and preferences

    Used by Slack bot during onboarding to save:
    - Expertise tags for help request routing
    - Timezone for scheduling
    - Preferred standup time
    """
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        # Check if user exists, create if not
        user = await db.get_user(user_id)

        if not user:
            # Create new user with Slack user ID
            await db.create_user({
                "id": user_id,
                "name": f"User {user_id}",  # Placeholder, should be updated
                "slack_user_id": user_id,
                "expertise_tags": profile_update.expertise_tags or [],
                "timezone": profile_update.timezone or "UTC"
            })
            logger.info(f"Created new user {user_id}")
        else:
            # Update existing user
            async with db.async_session() as session:
                from services.database import User
                from sqlalchemy import select, update

                # Build update dict
                update_data = {}
                if profile_update.expertise_tags is not None:
                    update_data["expertise_tags"] = profile_update.expertise_tags
                if profile_update.timezone is not None:
                    update_data["timezone"] = profile_update.timezone

                if update_data:
                    await session.execute(
                        update(User)
                        .where(User.id == user_id)
                        .values(**update_data)
                    )
                    await session.commit()
                    logger.info(f"Updated profile for user {user_id}")

        return {
            "status": "success",
            "user_id": user_id,
            "message": "Profile updated successfully"
        }

    except Exception as e:
        logger.error(f"Error updating user profile {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/team")
async def get_user_team(user_id: str, request: Request):
    """
    Get user's team members (same manager)

    Useful for:
    - Team standups view
    - Finding teammates
    """
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        user = await db.get_user(user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        manager_id = user.get("manager_id")

        if not manager_id:
            return {"team_members": []}

        # Get all users with same manager
        async with db.async_session() as session:
            from services.database import User
            from sqlalchemy import select

            result = await session.execute(
                select(User).where(
                    User.manager_id == manager_id,
                    User.is_active == True,
                    User.id != user_id  # Exclude self
                )
            )
            team_members = result.scalars().all()

            return {
                "team_members": [
                    {
                        "id": member.id,
                        "name": member.name,
                        "role": member.role.value if member.role else None,
                        "expertise_tags": member.expertise_tags or []
                    }
                    for member in team_members
                ]
            }

    except Exception as e:
        logger.error(f"Error getting team for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
