"""
Expertise and Expert Matching Routers
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict

router = APIRouter(prefix="/api/expertise", tags=["expertise"])


class FindExpertRequest(BaseModel):
    blocker_text: str
    requester_id: str
    limit: int = 3


class ExpertResponse(BaseModel):
    user_id: str
    user_name: str
    confidence: float
    domain: str
    expertise_metrics: Dict


@router.get("/user/{user_id}")
async def get_user_expertise(user_id: str):
    """Get user's expertise across all domains"""
    from backend.main import db

    try:
        expertise = await db.get_user_expertise(user_id)

        return {
            "user_id": user_id,
            "expertise": expertise,
            "total_domains": len(expertise)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domain/{domain}")
async def find_experts_by_domain(domain: str, limit: int = 5):
    """Find experts in a specific domain"""
    from backend.main import db

    try:
        experts = await db.find_expert(domain, limit=limit)

        return {
            "domain": domain,
            "experts": experts,
            "total_found": len(experts)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match")
async def match_expert_to_blocker(request: FindExpertRequest):
    """Match the best expert(s) to help with a blocker"""
    from backend.main import expert_matcher

    if not expert_matcher:
        raise HTTPException(status_code=503, detail="Expert matcher not initialized")

    try:
        experts = await expert_matcher.find_best_expert(
            blocker_text=request.blocker_text,
            requester_id=request.requester_id,
            limit=request.limit
        )

        # Rank with additional context
        ranked_experts = await expert_matcher.rank_experts_with_context(
            experts,
            {"urgency": "medium"}  # Can be enhanced
        )

        # Get alternative solutions
        keywords = expert_matcher._extract_keywords(request.blocker_text)
        suggestions = await expert_matcher.suggest_alternative_solutions(
            request.blocker_text,
            keywords
        )

        return {
            "blocker": request.blocker_text,
            "keywords_extracted": keywords,
            "matched_experts": ranked_experts,
            "alternative_solutions": suggestions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team/overview")
async def get_team_expertise_overview():
    """Get team-wide expertise overview"""
    from backend.main import db

    try:
        # Get all active users
        users = await db.get_all_active_users()

        team_expertise = []
        for user in users:
            expertise = await db.get_user_expertise(user['id'])

            # Get top 3 domains
            top_domains = sorted(expertise, key=lambda x: x['score'], reverse=True)[:3]

            team_expertise.append({
                "user_id": user['id'],
                "user_name": user['name'],
                "top_expertise": top_domains,
                "total_domains": len(expertise)
            })

        return {
            "team_size": len(users),
            "team_expertise": team_expertise
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collaboration/user/{user_id}")
async def get_user_collaboration_metrics(user_id: str, weeks: int = 4):
    """Get user's collaboration metrics"""
    from backend.main import db

    try:
        metrics = await db.get_collaboration_metrics(user_id, weeks=weeks)

        # Calculate aggregated stats
        total_helped = sum(m['help_requests_resolved'] for m in metrics)
        total_reviews = sum(m['code_reviews_given'] for m in metrics)
        avg_response_time = sum(m['avg_resolution_time_minutes'] for m in metrics) / len(metrics) if metrics else 0

        return {
            "user_id": user_id,
            "weekly_metrics": metrics,
            "aggregated": {
                "total_help_requests_resolved": total_helped,
                "total_code_reviews_given": total_reviews,
                "avg_resolution_time_minutes": round(avg_response_time, 2)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
