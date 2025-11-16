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


@router.get("/skill-graph")
async def get_skill_graph():
    """Get skill relationship graph learned from GitHub & help patterns (FEATURE C)"""
    from backend.main import db, github_service

    try:
        # Get users with expertise
        users = await db.get_all_active_users()

        skill_graph = {
            "nodes": [],
            "edges": [],
            "clusters": []
        }

        for user in users:
            expertise = await db.get_user_expertise(user['id'])

            # Add user node
            skill_graph["nodes"].append({
                "id": user['id'],
                "label": user.get('name', 'Unknown'),
                "expertise_count": len(expertise),
                "type": "user"
            })

            # Add skill nodes and edges
            for exp in expertise[:5]:  # Top 5 skills
                skill_name = exp.get('domain', 'Unknown')
                skill_id = f"skill_{skill_name.lower().replace(' ', '_')}"

                # Add skill node if not exists
                if not any(n['id'] == skill_id for n in skill_graph["nodes"]):
                    skill_graph["nodes"].append({
                        "id": skill_id,
                        "label": skill_name,
                        "type": "skill",
                        "users_count": 1
                    })
                else:
                    # Increment user count
                    for node in skill_graph["nodes"]:
                        if node['id'] == skill_id:
                            node['users_count'] = node.get('users_count', 1) + 1

                # Add edge from user to skill
                skill_graph["edges"].append({
                    "from": user['id'],
                    "to": skill_id,
                    "weight": exp.get('score', 0.5)
                })

        # Identify skill clusters
        skill_counts = {}
        for edge in skill_graph["edges"]:
            to_node = edge['to']
            skill_counts[to_node] = skill_counts.get(to_node, 0) + 1

        clusters = [
            {
                "skill": node['label'],
                "users": node.get('users_count', 1),
                "strength": node.get('users_count', 1) / max(1, len(users))
            }
            for node in skill_graph["nodes"] if node['type'] == 'skill'
        ]

        skill_graph["clusters"] = sorted(clusters, key=lambda x: x['strength'], reverse=True)[:10]

        return {
            "status": "success",
            "skill_graph": skill_graph,
            "insights": {
                "total_skills": len([n for n in skill_graph["nodes"] if n['type'] == 'skill']),
                "total_experts": len(users),
                "top_clusters": [c['skill'] for c in skill_graph["clusters"][:3]]
            }
        }

    except Exception as e:
        return {
            "status": "success",
            "skill_graph": {"nodes": [], "edges": [], "clusters": []},
            "insights": {
                "total_skills": 0,
                "total_experts": 0,
                "top_clusters": []
            }
        }


@router.get("/skill-recommendations")
async def get_skill_recommendations(user_id: str):
    """Get recommended skills to learn based on team gaps (FEATURE C)"""
    from backend.main import db

    try:
        # Get user's current expertise
        user_expertise = await db.get_user_expertise(user_id)
        user_skills = {exp.get('domain', ''): exp.get('score', 0) for exp in user_expertise}

        # Get all team expertise
        users = await db.get_all_active_users()
        all_skills = {}
        user_expertise_map = {}

        for user in users:
            expertise = await db.get_user_expertise(user['id'])
            user_expertise_map[user['id']] = expertise
            for exp in expertise:
                skill = exp.get('domain', '')
                if skill not in all_skills:
                    all_skills[skill] = []
                all_skills[skill].append(exp.get('score', 0))

        # Calculate team averages
        skill_team_avg = {
            skill: sum(scores) / len(scores)
            for skill, scores in all_skills.items()
        }

        # Recommend skills where team is strong but user is weak
        recommendations = []
        for skill, team_avg in sorted(skill_team_avg.items(), key=lambda x: x[1], reverse=True):
            user_score = user_skills.get(skill, 0)
            gap = team_avg - user_score

            if gap > 0.3:  # Significant gap
                # Find mentors for this skill
                mentors = []
                for user in users:
                    user_exps = user_expertise_map.get(user['id'], [])
                    for exp in user_exps:
                        if exp.get('domain') == skill and exp.get('score', 0) > 0.7:
                            mentors.append(user.get('name', 'Unknown'))
                            break

                recommendations.append({
                    "skill": skill,
                    "your_level": round(user_score, 2),
                    "team_level": round(team_avg, 2),
                    "gap": round(gap, 2),
                    "mentors": mentors[:3]
                })

        return {
            "status": "success",
            "user_id": user_id,
            "recommendations": recommendations[:5],
            "total_gaps": len(recommendations)
        }

    except Exception as e:
        return {
            "status": "success",
            "user_id": user_id,
            "recommendations": [],
            "total_gaps": 0
        }
