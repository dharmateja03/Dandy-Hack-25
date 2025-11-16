"""
GitHub Integration Routers
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

router = APIRouter(prefix="/api/github", tags=["github"])


class SyncRequest(BaseModel):
    days: int = 30


class ExpertiseResponse(BaseModel):
    user_id: str
    user_name: str
    expertise: List[Dict]


@router.post("/sync/commits")
async def sync_commits(request: SyncRequest):
    """Sync commits from GitHub"""
    from backend.main import github_service, db

    if not github_service:
        raise HTTPException(status_code=503, detail="GitHub integration not configured")

    try:
        commits = await github_service.sync_commits(since_days=request.days)

        # Save to database and map to users
        saved_count = 0
        for commit in commits:
            # Try to map GitHub username to our user
            # For now, we'll save with github_username and map later
            await db.save_github_commit(commit)
            saved_count += 1

        return {
            "status": "success",
            "commits_synced": len(commits),
            "commits_saved": saved_count
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/pull-requests")
async def sync_pull_requests(request: SyncRequest):
    """Sync pull requests from GitHub"""
    from backend.main import github_service, db

    if not github_service:
        raise HTTPException(status_code=503, detail="GitHub integration not configured")

    try:
        prs = await github_service.sync_pull_requests(since_days=request.days)

        saved_count = 0
        for pr in prs:
            await db.save_github_pr(pr)
            saved_count += 1

        return {
            "status": "success",
            "prs_synced": len(prs),
            "prs_saved": saved_count
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/reviews")
async def sync_reviews(request: SyncRequest):
    """Sync code reviews from GitHub"""
    from backend.main import github_service, db

    if not github_service:
        raise HTTPException(status_code=503, detail="GitHub integration not configured")

    try:
        reviews = await github_service.sync_code_reviews(since_days=request.days)

        saved_count = 0
        for review in reviews:
            await db.save_github_review(review)
            saved_count += 1

        return {
            "status": "success",
            "reviews_synced": len(reviews),
            "reviews_saved": saved_count
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/all")
async def sync_all_github_data(request: SyncRequest):
    """Sync all GitHub data (commits, PRs, reviews)"""
    from backend.main import github_service, db

    if not github_service:
        raise HTTPException(status_code=503, detail="GitHub integration not configured")

    try:
        # Sync commits
        commits = await github_service.sync_commits(since_days=request.days)
        for commit in commits:
            await db.save_github_commit(commit)

        # Sync PRs
        prs = await github_service.sync_pull_requests(since_days=request.days)
        for pr in prs:
            await db.save_github_pr(pr)

        # Sync reviews
        reviews = await github_service.sync_code_reviews(since_days=request.days)
        for review in reviews:
            await db.save_github_review(review)

        return {
            "status": "success",
            "commits_synced": len(commits),
            "prs_synced": len(prs),
            "reviews_synced": len(reviews)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/activity")
async def get_user_github_activity(user_id: str, days: int = 30):
    """Get user's GitHub activity"""
    from backend.main import db

    try:
        commits = await db.get_user_commits(user_id, days=days)
        prs = await db.get_user_prs(user_id, days=days)
        reviews = await db.get_user_reviews(user_id, days=days)

        return {
            "user_id": user_id,
            "period_days": days,
            "commits": commits,
            "pull_requests": prs,
            "code_reviews": reviews,
            "summary": {
                "total_commits": len(commits),
                "total_prs": len(prs),
                "total_reviews": len(reviews),
                "prs_merged": len([pr for pr in prs if pr.get('merged')])
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deployments")
async def get_recent_deployments(days: int = 7):
    """Get recent deployments (merged PRs)"""
    from backend.main import github_service

    if not github_service:
        raise HTTPException(status_code=503, detail="GitHub integration not configured")

    try:
        deployments = await github_service.get_recent_deployments(days=days)

        return {
            "period_days": days,
            "deployments": deployments,
            "total_deployments": len(deployments)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-expertise/{user_id}")
async def analyze_user_expertise(user_id: str):
    """Analyze and update user's expertise based on GitHub activity"""
    from backend.main import db, github_service

    if not github_service:
        raise HTTPException(status_code=503, detail="GitHub integration not configured")

    try:
        # Get user's GitHub activity
        commits = await db.get_user_commits(user_id, days=90)
        prs = await db.get_user_prs(user_id, days=90)
        reviews = await db.get_user_reviews(user_id, days=90)

        # Analyze expertise
        expertise_scores = await github_service.analyze_user_expertise(commits, prs, reviews)

        # Update database
        for domain, metrics in expertise_scores.items():
            await db.update_user_expertise(
                user_id=user_id,
                domain=domain,
                score=metrics['score'],
                commit_count=metrics['commit_count'],
                pr_count=metrics['pr_count'],
                review_count=metrics['review_count']
            )

        return {
            "user_id": user_id,
            "expertise": expertise_scores
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
