"""
MCP Core - The Brain of the System
Maintains context of everything happening in the team
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

import google.generativeai as genai

from services.vector_db import VectorDBService
from services.database import DatabaseService

logger = logging.getLogger(__name__)


class MCPCore:
    """
    Model Context Protocol - Central Intelligence

    This is the brain that:
    - Maintains context of all team activities
    - Processes standups and extracts structured data
    - Routes help requests intelligently
    - Provides semantic search across all context
    - Generates insights and summaries
    """

    def __init__(
        self,
        vector_db: VectorDBService,
        database: DatabaseService,
        gemini_api_key: str
    ):
        self.vector_db = vector_db
        self.database = database
        self.gemini_api_key = gemini_api_key
        self.model = None

        logger.info("MCP Core initialized")

    async def initialize(self):
        """Initialize MCP services"""
        try:
            # Initialize Gemini 2.0 (free tier)
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            logger.info("✅ Gemini 2.0 Flash initialized (free tier)")

            # Initialize Vector DB
            await self.vector_db.initialize()
            logger.info("✅ Vector DB initialized")

            # Initialize Database
            await self.database.initialize()
            logger.info("✅ Database initialized")

        except Exception as e:
            logger.error(f"❌ MCP initialization failed: {e}")
            raise

    async def cleanup(self):
        """Cleanup resources"""
        await self.vector_db.close()
        await self.database.close()

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all MCP components"""
        return {
            "mcp_status": "healthy",
            "vector_db": await self.vector_db.health_check(),
            "database": await self.database.health_check(),
            "llm": "gemini-2.0-flash (free)" if self.model else "not initialized"
        }

    async def process_standup(
        self,
        user_id: str,
        message: str,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Process a standup update

        This is where the magic happens:
        1. Ensure user exists in database
        2. Parse with Gemini to extract structured data
        3. Store in vector DB for semantic search
        4. Update task statuses in database
        5. Identify help requests and route them
        6. Detect blockers and alert manager
        """
        timestamp = timestamp or datetime.utcnow()

        logger.info(f"Processing standup for user {user_id}")

        try:
            # Step 0: Ensure user exists in database
            user = await self.database.get_user(user_id)
            if not user:
                logger.info(f"Creating new user {user_id} in database")
                await self.database.create_user({
                    "id": user_id,
                    "name": user_id
                })

            # Step 1: Parse with Gemini
            parsed_data = await self._parse_standup_with_gemini(user_id, message)
            logger.debug(f"Parsed data from Gemini: {parsed_data}")

            # Step 2: Store in vector DB
            context_id = await self.vector_db.add_standup(
                user_id=user_id,
                text=message,
                parsed_data=parsed_data,
                timestamp=timestamp
            )

            # Step 3: Update task statuses
            await self._update_task_statuses(user_id, parsed_data)

            # Step 3.5: Update user expertise tags from standup
            expertise_tags = parsed_data.get("expertise_tags", [])
            if expertise_tags:
                await self._update_user_expertise(user_id, expertise_tags)

            # Step 4: Route help requests
            help_requests = parsed_data.get("help_requests", [])
            logger.info(f"Found {len(help_requests)} help requests to route: {help_requests}")
            routed_requests = []
            for help_req in help_requests:
                routed = await self._route_help_request(user_id, help_req)
                routed_requests.append(routed)
            logger.info(f"Routed requests: {routed_requests}")

            # Step 5: Detect blockers and suggest solutions
            blockers = parsed_data.get("blockers", [])
            blocker_suggestions = []
            if blockers:
                await self._alert_manager_blockers(user_id, blockers)
                # Suggest solutions based on past blockers
                for blocker in blockers:
                    suggestions = await self._suggest_blocker_solutions(user_id, blocker)
                    blocker_suggestions.extend(suggestions)

            result = {
                "status": "success",
                "context_id": context_id,
                "parsed_data": parsed_data,
                "help_requests_routed": routed_requests,
                "blockers_detected": len(blockers),
                "blocker_suggestions": blocker_suggestions
            }
            logger.info(f"Final result to return: {result}")
            return result

        except Exception as e:
            logger.error(f"Error processing standup: {e}")
            raise

    async def _parse_standup_with_gemini(
        self,
        user_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Use Gemini to parse standup into structured data
        """
        # Get user context
        user = await self.database.get_user(user_id)
        assigned_tasks = await self.database.get_user_tasks(user_id)

        # Handle case where user might not exist in database
        user_name = user.get('name', user_id) if user else user_id
        task_list = ', '.join([t['title'] for t in assigned_tasks]) if assigned_tasks else "No assigned tasks"

        prompt = f"""
You are parsing a standup update from a team member. Extract structured information.

User: {user_name}
Assigned Tasks: {task_list}

Standup Message:
{message}

CRITICAL INSTRUCTIONS FOR EXTRACTING HELP REQUESTS:
- Look for ALL mentions of people asking for help (e.g., "@name", "from John", "with Sarah", "help from X")
- If MULTIPLE people are mentioned in context of help, create SEPARATE help_requests for each person
- Example: "Need help from Bob on testing and Diana on performance" → Create 2 help requests, one for Bob (topic: testing), one for Diana (topic: performance)
- Extract person's FIRST NAME or SHORT NAME ONLY - no technical IDs, underscores, or suffixes
- Examples: "@john_smith" → "John", "help from Sarah Lee" → "Sarah", "@bharathi" → "Bharathi"
- If no specific person mentioned, set requested_from to null

Extract the following in JSON format:
{{
    "tasks_completed": ["list of completed tasks"],
    "tasks_in_progress": ["tasks being worked on"],
    "tasks_planned": ["tasks planned for today"],
    "blockers": [
        {{
            "description": "what is blocking",
            "type": "technical|dependency|resource",
            "severity": "low|medium|high"
        }}
    ],
    "help_requests": [
        {{
            "topic": "what help is needed",
            "context": "additional context",
            "urgency": "low|medium|high",
            "requested_from": "person's first name/short name ONLY (e.g., 'John', 'Bharathi', 'Sarah'), or null if no person specified. ONE person per help request."
        }}
    ],
    "task_updates": [
        {{
            "task_name": "task name",
            "progress_percentage": 0-100,
            "status": "not_started|in_progress|blocked|completed"
        }}
    ],
    "expertise_tags": ["technologies, skills, or domains user is working with (e.g., 'Kubernetes', 'React', 'DevOps', 'Database optimization'). Extract from mentions like 'working on X', 'experienced with Y', 'fixed Z issue'"],
    "sentiment": "positive|neutral|negative|frustrated",
    "key_points": ["important points to remember"]
}}

Return ONLY valid JSON, no markdown.
"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            logger.debug(f"Gemini raw response: {text[:200]}...")

            # Try to extract JSON from markdown code blocks if present
            if "```" in text:
                # Extract content between markdown code blocks
                start = text.find("```") + 3
                # Skip "json" if it's there
                if text[start:start+4] == "json":
                    start += 4
                end = text.rfind("```")
                text = text[start:end].strip()

            parsed_json = json.loads(text)
            logger.info(f"✅ Parsed JSON from Gemini: help_requests={parsed_json.get('help_requests', [])}")
            return parsed_json

        except json.JSONDecodeError as e:
            logger.warning(f"Gemini response was not valid JSON: {e}")
            logger.debug(f"Response text was: {response.text[:200]}")
            # Fallback: basic parsing
            return {
                "tasks_completed": [],
                "tasks_in_progress": [],
                "tasks_planned": [],
                "blockers": [],
                "help_requests": [],
                "task_updates": [],
                "sentiment": "neutral",
                "key_points": [message]
            }
        except Exception as e:
            logger.error(f"Error parsing with Gemini: {e}", exc_info=True)
            raise

    async def _update_task_statuses(self, user_id: str, parsed_data: Dict):
        """Update task statuses based on standup"""
        task_updates = parsed_data.get("task_updates", [])

        for update in task_updates:
            await self.database.update_task_status(
                user_id=user_id,
                task_name=update.get("task_name"),
                status=update.get("status"),
                progress=update.get("progress_percentage")
            )

    async def _update_user_expertise(self, user_id: str, expertise_tags: List[str]):
        """
        Update user's expertise tags based on standup mentions
        Learns what skills/domains user is working with
        """
        if not expertise_tags:
            return

        try:
            logger.info(f"Updating expertise for {user_id}: {expertise_tags}")
            await self.database.update_user_expertise_tags(user_id, expertise_tags)
            logger.info(f"✅ Updated expertise tags for {user_id}")
        except Exception as e:
            logger.warning(f"Failed to update expertise tags: {e}")

    async def _calculate_skill_score(self, user_id: str, topic: str) -> float:
        """
        Calculate skill score for a user for a given topic
        Factors:
        - Exact expertise tag match: +2.0
        - Partial tag match: +1.0
        - Resolved help requests for this topic: +0.5 per request
        - Success rate bonus: +0.0-1.0
        """
        score = 0.0

        try:
            user = await self.database.get_user(user_id)
            if not user:
                return 0.0

            expertise_tags = user.get('expertise_tags', [])
            topic_lower = topic.lower()

            # Check for exact and partial expertise matches
            for tag in expertise_tags:
                tag_lower = tag.lower()
                if tag_lower == topic_lower:
                    score += 2.0  # Exact match
                    logger.debug(f"User {user_id}: exact match on '{tag}'")
                elif topic_lower in tag_lower or tag_lower in topic_lower:
                    score += 1.0  # Partial match
                    logger.debug(f"User {user_id}: partial match '{tag}' with topic '{topic}'")

            # Get help requests resolved by this user for this topic
            resolved_requests = await self.database.get_resolved_help_requests(user_id, topic)
            if resolved_requests:
                score += len(resolved_requests) * 0.5  # +0.5 per resolved request
                logger.debug(f"User {user_id}: {len(resolved_requests)} resolved requests for '{topic}'")

                # Calculate success rate bonus (how well they resolved these)
                # For now, just count resolved as success
                success_rate = 1.0  # 100% success if marked resolved
                score += success_rate  # +1.0 for success rate

            logger.debug(f"Skill score for {user_id} on topic '{topic}': {score}")
            return score

        except Exception as e:
            logger.warning(f"Error calculating skill score for {user_id}: {e}")
            return 0.0

    async def _route_help_request(
        self,
        requesting_user_id: str,
        help_request: Dict
    ) -> Dict[str, Any]:
        """
        Intelligently route help requests

        1. If someone is explicitly requested, find them by name
        2. Otherwise, search vector DB for who has expertise
        3. Check who is available (not overloaded)
        4. Return best person to help
        """
        topic = help_request.get("topic", "")
        urgency = help_request.get("urgency", "medium")
        requested_from = help_request.get("requested_from")

        available_expert = None
        logger.debug(f"Routing help request: topic={topic}, requested_from={requested_from}")

        # Check if someone is explicitly requested
        if requested_from:
            logger.info(f"Help request explicitly mentions: {requested_from}")
            # Search for user by name (case-insensitive)
            users = await self.database.get_all_active_users()
            logger.debug(f"Found {len(users)} users in database")
            for user in users:
                user_name = user.get('name', '').lower()
                user_original_name = user.get('name', '')  # Keep original casing
                logger.debug(f"Checking user {user_original_name} (id={user['id']}) against {requested_from}")
                if requested_from.lower() in user_name or user_name in requested_from.lower():
                    # Store with ORIGINAL name casing, not lowercase
                    available_expert = {"user_id": user['id'], "name": user_original_name}
                    logger.info(f"✅ Found requested user: {available_expert}")
                    break

        # If no specific person requested, use skill-based expertise matching
        if not available_expert:
            logger.info(f"No explicit person mentioned, searching for experts in '{topic}'")

            # Get all users and calculate skill scores for this topic
            all_users = await self.database.get_all_active_users()
            experts_with_scores = []

            for user in all_users:
                user_id = user.get('id')
                skill_score = await self._calculate_skill_score(user_id, topic)

                if skill_score > 0:  # Only consider users with relevant skills
                    expertise_tags = user.get('expertise_tags', [])
                    workload = await self.database.get_user_workload(user_id)

                    # Combine skill score with workload (prefer less loaded experts)
                    availability_factor = 1.0 / (1 + workload / 5.0)  # Higher score if less loaded
                    final_score = skill_score * availability_factor

                    experts_with_scores.append({
                        "user_id": user_id,
                        "name": user.get('name', user_id),
                        "skill_score": skill_score,
                        "workload": workload,
                        "final_score": final_score,
                        "expertise_tags": expertise_tags
                    })

            # Sort by final score (skill + availability)
            experts_with_scores.sort(key=lambda x: x["final_score"], reverse=True)
            logger.debug(f"Ranked experts for '{topic}': {[(e['name'], e['final_score']) for e in experts_with_scores[:3]]}")

            if experts_with_scores:
                available_expert = experts_with_scores[0]
                logger.info(f"✅ Selected expert by skill match: {available_expert['name']} (score: {available_expert['final_score']:.2f}, workload: {available_expert['workload']})")
            else:
                # Fallback to semantic search if no skill-tagged experts
                logger.info(f"No skill-tagged experts, falling back to semantic search")
                experts = await self.vector_db.find_experts(topic, limit=5)
                if experts:
                    available_expert = experts[0]
                    logger.info(f"Using semantic search result: {available_expert}")

        if available_expert:
            # Prevent self-help - don't route someone to themselves
            if available_expert['user_id'] == requesting_user_id:
                logger.warning(f"⚠️ Attempted self-help routing for {requesting_user_id}, finding alternative")
                # Try to find another expert
                all_users = await self.database.get_all_active_users()
                for user in all_users:
                    if user.get('id') != requesting_user_id:
                        available_expert = {"user_id": user['id'], "name": user.get('name', user['id'])}
                        logger.info(f"✅ Using alternative expert: {available_expert}")
                        break
                else:
                    logger.warning(f"❌ No alternative expert found, escalating")
                    return {
                        "help_request_id": None,
                        "assigned_to": None,
                        "escalated": True,
                        "reason": "No expert available (self-help prevention)"
                    }

            logger.debug(f"Creating help request: from={requesting_user_id}, to={available_expert['user_id']}, topic={topic}")
            # Create help request in database
            help_req_id = await self.database.create_help_request(
                from_user=requesting_user_id,
                to_user=available_expert["user_id"],
                topic=topic,
                context=help_request.get("context", ""),
                urgency=urgency
            )

            # Include skill score details in response
            skill_score = available_expert.get("skill_score", 0)
            expertise_tags = available_expert.get("expertise_tags", [])

            response = {
                "help_request_id": help_req_id,
                "assigned_to": available_expert["user_id"],
                "assigned_name": available_expert.get("name", available_expert.get("user_id")),
                "topic": topic,
                "reason": f"Requested: {requested_from}" if requested_from else f"Expert in {topic} (skill match)",
                "skill_score": skill_score,
                "expertise_tags": expertise_tags,
                "workload": available_expert.get("workload", 0),
                "final_score": available_expert.get("final_score", available_expert.get("score", 0))
            }
            logger.info(f"✅ Help request routed with skill matching: {response}")
            return response
        else:
            # No expert found, escalate to manager
            logger.warning(f"❌ No expert found for topic '{topic}'")
            return {
                "help_request_id": None,
                "assigned_to": None,
                "escalated": True,
                "reason": "No expert found"
            }

    async def _alert_manager_blockers(self, user_id: str, blockers: List[Dict]):
        """Alert manager about blockers"""
        # Get user's manager
        user = await self.database.get_user(user_id)
        manager_id = user.get("manager_id")

        if manager_id:
            for blocker in blockers:
                await self.database.create_blocker_alert(
                    user_id=user_id,
                    manager_id=manager_id,
                    blocker_description=blocker.get("description"),
                    severity=blocker.get("severity", "medium")
                )

    async def _suggest_blocker_solutions(
        self,
        user_id: str,
        blocker: Dict
    ) -> List[Dict[str, Any]]:
        """
        Search for similar past blockers and suggest solutions

        Flow:
        1. Search vector DB for similar blocker descriptions
        2. Find help threads that resolved those blockers
        3. Extract solutions from resolution notes
        4. Rank by success rate (how many people it helped)
        5. Return top suggestions
        """
        blocker_description = blocker.get("description", "")
        severity = blocker.get("severity", "medium")

        if not blocker_description:
            return []

        try:
            logger.info(f"Searching for solutions to blocker: {blocker_description}")

            # Step 1: Search vector DB for similar blockers
            similar_contexts = await self.vector_db.semantic_search(
                query=blocker_description,
                limit=5,
                filter_type="standup"
            )
            logger.debug(f"Found {len(similar_contexts)} similar blocker contexts")

            if not similar_contexts:
                logger.info(f"No similar blockers found for '{blocker_description}'")
                return []

            # Step 2 & 3: Extract solutions from help threads that might have solved similar issues
            suggestions = []
            for context in similar_contexts:
                # Get parsed_data which might contain help resolutions
                parsed_data = context.get("payload", {}).get("parsed_data", {})
                help_requests = parsed_data.get("help_requests", [])

                # Look for resolved help requests in this context
                for help_req in help_requests:
                    if help_req.get("topic"):
                        # Find resolved help requests for this topic
                        resolved = await self.database.get_resolved_help_requests(
                            context.get("payload", {}).get("user_id"),
                            help_req.get("topic")
                        )

                        for resolved_req in resolved:
                            suggestion = {
                                "blocker_description": blocker_description,
                                "severity": severity,
                                "similar_to": context.get("payload", {}).get("text", "")[:100],
                                "suggested_solution": resolved_req.get("resolution_notes", ""),
                                "topic": resolved_req.get("topic"),
                                "resolved_at": resolved_req.get("resolved_at"),
                                "confidence": 0.8  # Matched from similar context
                            }
                            suggestions.append(suggestion)

            # Sort by confidence and limit to top 3
            suggestions.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            top_suggestions = suggestions[:3]

            if top_suggestions:
                logger.info(f"Found {len(top_suggestions)} possible solutions for blocker")
                # Log a summary for the user
                for i, suggestion in enumerate(top_suggestions, 1):
                    logger.info(f"  Solution {i}: {suggestion.get('suggested_solution', 'N/A')[:80]}")

            return top_suggestions

        except Exception as e:
            logger.warning(f"Error suggesting blocker solutions: {e}")
            return []

    async def query(self, query: str, user_id: str) -> Dict[str, Any]:
        """
        Natural language query to MCP

        Examples:
        - "Who knows about OAuth?"
        - "What's blocking Sarah?"
        - "Summarize last week"
        """
        # Use semantic search to find relevant context
        results = await self.vector_db.semantic_search(query, limit=10)

        # Use Gemini to generate answer based on context
        context_text = "\n\n".join([r["text"] for r in results])

        prompt = f"""
Based on the following team context, answer the question.

Question: {query}

Context:
{context_text}

Provide a clear, concise answer.
"""

        response = self.model.generate_content(prompt)

        return {
            "query": query,
            "answer": response.text,
            "sources": results[:3]  # Top 3 sources
        }

    async def add_context(self, context_data: Dict) -> str:
        """
        Add arbitrary context to MCP
        This is the protocol interface - any system can add context
        """
        return await self.vector_db.add_context(context_data)

    async def generate_summary(
        self,
        user_id: Optional[str] = None,
        days: int = 1
    ) -> str:
        """Generate summary of team activity"""
        # Get recent standups
        standups = await self.database.get_recent_standups(days=days, user_id=user_id)

        if not standups:
            return "No standup data available for the specified period."

        # Prepare context for Gemini
        standup_text = "\n\n".join([
            f"**{s['user_name']}** ({s['date']}):\n{s['message']}"
            for s in standups
        ])

        prompt = f"""
Generate a concise summary of team activity based on these standups:

{standup_text}

Include:
- Key accomplishments
- Active blockers
- Help requests and collaboration
- Overall team sentiment
- Suggested actions

Keep it under 300 words.
"""

        response = self.model.generate_content(prompt)
        return response.text

    async def generate_daily_summary(self, days: int = 1) -> Dict[str, Any]:
        """
        Generate structured daily team summary for DM broadcast

        Returns emoji-formatted summary with:
        - Team accomplishments
        - Active blockers (with severity)
        - Pending help requests
        - Team sentiment
        - Key risks/concerns
        """
        try:
            logger.info(f"Generating daily summary for past {days} day(s)")

            # Get recent standups
            standups = await self.database.get_recent_standups(days=days)
            if not standups:
                return {
                    "status": "no_data",
                    "message": "No standup data available",
                    "summary": "No standups submitted yet."
                }

            # Aggregate data from standups
            all_tasks_completed = []
            all_tasks_in_progress = []
            all_blockers = []
            all_help_requests = []
            sentiment_scores = {"positive": 0, "neutral": 0, "negative": 0, "frustrated": 0}
            team_members_count = len(set(s['user_id'] for s in standups))

            for standup in standups:
                parsed = standup.get('parsed_data', {})
                all_tasks_completed.extend(parsed.get('tasks_completed', []))
                all_tasks_in_progress.extend(parsed.get('tasks_in_progress', []))
                all_blockers.extend(parsed.get('blockers', []))
                all_help_requests.extend(parsed.get('help_requests', []))

                sentiment = parsed.get('sentiment', 'neutral')
                if sentiment in sentiment_scores:
                    sentiment_scores[sentiment] += 1

            # Count help requests by status
            pending_help = await self.database.get_pending_help_requests()
            resolved_help = len([h for h in all_help_requests if h.get('status') == 'resolved'])

            # Count blockers by severity
            blockers_by_severity = {"high": 0, "medium": 0, "low": 0}
            for blocker in all_blockers:
                severity = blocker.get('severity', 'medium').lower()
                if severity in blockers_by_severity:
                    blockers_by_severity[severity] += 1

            # Determine overall sentiment
            sentiment_data = sentiment_scores
            if sentiment_data['positive'] > sentiment_data['negative']:
                overall_sentiment = "😊 Positive"
            elif sentiment_data['negative'] > sentiment_data['positive']:
                overall_sentiment = "😟 At Risk"
            else:
                overall_sentiment = "😐 Neutral"

            # Build formatted summary
            summary_lines = [
                f"📊 Daily Team Summary - {datetime.utcnow().strftime('%B %d, %Y')}",
                "",
                f"👥 Team Activity: {team_members_count} members reported",
                "",
                f"✅ Completed: {len(all_tasks_completed)} tasks",
                f"🚀 In Progress: {len(all_tasks_in_progress)} tasks",
                "",
                "🚧 Blockers:",
                f"   🔴 HIGH: {blockers_by_severity['high']}",
                f"   🟡 MEDIUM: {blockers_by_severity['medium']}",
                f"   🟢 LOW: {blockers_by_severity['low']}",
                "",
                "🆘 Help Requests:",
                f"   ⏳ Pending: {len(pending_help)}",
                f"   ✅ Resolved: {resolved_help}",
                "",
                f"😊 Team Sentiment: {overall_sentiment}",
            ]

            # Add key concerns if any
            if blockers_by_severity['high'] > 0:
                summary_lines.extend([
                    "",
                    "⚠️  HIGH PRIORITY BLOCKERS DETECTED - Action needed!"
                ])

            summary_text = "\n".join(summary_lines)

            return {
                "status": "success",
                "summary": summary_text,
                "metrics": {
                    "tasks_completed": len(all_tasks_completed),
                    "tasks_in_progress": len(all_tasks_in_progress),
                    "blockers_total": len(all_blockers),
                    "blockers_high": blockers_by_severity['high'],
                    "blockers_medium": blockers_by_severity['medium'],
                    "blockers_low": blockers_by_severity['low'],
                    "help_requests_pending": len(pending_help),
                    "help_requests_resolved": resolved_help,
                    "team_members_active": team_members_count,
                    "sentiment": overall_sentiment
                }
            }

        except Exception as e:
            logger.error(f"Error generating daily summary: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to generate summary: {str(e)}"
            }

    async def assess_meeting_necessity(
        self,
        meeting_title: str,
        attendees: List[str],
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Assess whether a meeting is necessary or could be solved async

        Decision logic:
        1. Check if meeting title/description matches help/blocker patterns
        2. Check if attendees are already collaborating in help threads
        3. Check if similar issues have been resolved async
        4. Return recommendation with confidence score

        Returns:
            - recommendation: "async_instead" or "hold_meeting"
            - confidence: 0-1.0
            - reason: explanation
            - suggestion: what to do instead (if async_instead)
        """
        try:
            logger.info(f"Assessing meeting necessity: {meeting_title}")

            # Keywords that suggest meeting could be async
            async_keywords = [
                "debug", "fix", "help", "issue", "problem", "blockers",
                "review", "discuss", "clarify", "explain", "troubleshoot",
                "technical", "auth", "database", "error", "timeout"
            ]

            meeting_text = f"{meeting_title} {description}".lower()
            matched_keywords = [k for k in async_keywords if k in meeting_text]

            # Check if this looks like a help/blocker discussion
            is_help_topic = len(matched_keywords) > 0
            async_confidence = min(len(matched_keywords) * 0.2, 0.8)

            # Search for similar resolved topics in help threads
            similar_resolutions = []
            if is_help_topic:
                # Try to find similar topics that were resolved
                resolution_search = await self.vector_db.semantic_search(
                    query=meeting_title,
                    limit=3
                )
                if resolution_search:
                    async_confidence += 0.2  # Boost if similar issues found

                    for result in resolution_search:
                        payload = result.get("payload", {})
                        if payload.get("type") == "standup":
                            help_reqs = payload.get("parsed_data", {}).get("help_requests", [])
                            similar_resolutions.extend(help_reqs)

            # Build recommendation
            if async_confidence > 0.6:
                # Suggest async approach
                suggestion = "Use a Slack thread instead"

                # Get attendee info to find experts
                expert_matches = []
                for attendee in attendees[:3]:  # Check first 3 attendees
                    user = await self.database.get_user(attendee)
                    if user:
                        expertise = user.get("expertise_tags", [])
                        if expertise:
                            expert_matches.append({
                                "name": user.get("name"),
                                "expertise": expertise[:2]  # Top 2 skills
                            })

                recommendation = {
                    "recommendation": "async_instead",
                    "confidence": min(async_confidence, 1.0),
                    "reason": f"This looks like a {', '.join(matched_keywords[:2])} discussion that can be solved async",
                    "suggestion": suggestion,
                    "time_saved_minutes": 30,
                    "expert_matches": expert_matches,
                    "similar_resolved_issues": len(similar_resolutions)
                }
            else:
                # Keep meeting
                recommendation = {
                    "recommendation": "hold_meeting",
                    "confidence": 1.0 - async_confidence,
                    "reason": "This appears to need real-time discussion or decision-making",
                    "suggestion": "Proceed with meeting as scheduled"
                }

            logger.info(f"Meeting assessment: {recommendation['recommendation']} (confidence: {recommendation['confidence']:.2f})")
            return recommendation

        except Exception as e:
            logger.warning(f"Error assessing meeting necessity: {e}")
            return {
                "recommendation": "hold_meeting",
                "confidence": 0.5,
                "reason": "Could not assess meeting necessity",
                "suggestion": "Proceed with meeting"
            }

    async def generate_documentation_from_resolution(
        self,
        help_request_id: int,
        resolution_notes: str
    ) -> Dict[str, Any]:
        """
        Auto-generate markdown documentation from a resolved help request

        Creates searchable documentation from:
        - Help request problem statement
        - Resolution steps and notes
        - Related standup context
        - Auto-extracted skills/tags

        Returns markdown-formatted doc ready for wiki/knowledge base
        """
        try:
            logger.info(f"Generating documentation from help request {help_request_id}")

            # Get help request details
            help_request = await self.database.get_help_request(help_request_id)
            if not help_request:
                return {
                    "status": "error",
                    "message": f"Help request {help_request_id} not found"
                }

            topic = help_request.get("topic", "Unknown Issue")
            from_user = help_request.get("from_user_id", "Team Member")
            context = help_request.get("context", "")

            # Generate documentation using Gemini
            prompt = f"""
Create a well-formatted markdown documentation article from this help request resolution.

Problem Title: {topic}
Original Context: {context}
Resolution Notes: {resolution_notes}

Generate markdown with these sections:
1. ## Problem Description
   - What issue was this solving?
   - When might someone encounter this?

2. ## Solution Steps
   - Clear, numbered steps to solve this
   - Code examples if applicable

3. ## Key Tags
   - Skills/technologies involved

4. ## Related Resources
   - Links or references

Keep it concise and practical. Make it searchable.

Return ONLY markdown, no code blocks.
"""

            response = self.model.generate_content(prompt)
            doc_content = response.text.strip()

            # Build complete documentation object
            doc = {
                "title": f"How to: {topic}",
                "content": doc_content,
                "topic": topic,
                "source": "help_request",
                "source_id": help_request_id,
                "created_from_user": from_user,
                "created_at": datetime.utcnow().isoformat(),
                "searchable": True,
                "tags": self._extract_tags_from_topic(topic)
            }

            # Store in database
            doc_id = await self.database.save_documentation(doc)

            return {
                "status": "success",
                "doc_id": doc_id,
                "title": doc["title"],
                "content": doc_content,
                "tags": doc["tags"]
            }

        except Exception as e:
            logger.error(f"Error generating documentation: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to generate documentation: {str(e)}"
            }

    def _extract_tags_from_topic(self, topic: str) -> List[str]:
        """Extract relevant tags from topic string"""
        topic_lower = topic.lower()

        # Common technical tags
        tag_keywords = {
            "auth": ["auth", "login", "authentication", "401", "403"],
            "database": ["db", "database", "postgres", "mysql", "query"],
            "api": ["api", "endpoint", "rest", "graphql"],
            "frontend": ["ui", "react", "javascript", "css", "frontend"],
            "backend": ["backend", "server", "node", "python"],
            "devops": ["deploy", "docker", "k8s", "kubernetes", "ci/cd"],
            "performance": ["slow", "timeout", "performance", "optimization"],
            "security": ["security", "vulnerability", "xss", "injection"],
        }

        extracted_tags = []
        for tag, keywords in tag_keywords.items():
            if any(kw in topic_lower for kw in keywords):
                extracted_tags.append(tag)

        return extracted_tags if extracted_tags else ["general"]

    async def generate_accountability_nudges(self) -> Dict[str, Any]:
        """
        Generate nudge messages for stalled work

        Monitors:
        1. Blockers open 2+ days → nudge requester
        2. Help requests unanswered 6+ hours → nudge helper
        3. Tasks in-progress 5+ days → nudge assignee

        Returns list of nudges with message templates ready for DM
        """
        try:
            logger.info("Generating accountability nudges")

            nudges = []
            now = datetime.utcnow()

            # Check 1: Stalled blockers (2+ days)
            blocker_alerts = await self.database.get_blocker_alerts()
            for alert in blocker_alerts:
                created = alert.get("created_at")
                if created:
                    # Parse ISO format datetime
                    if isinstance(created, str):
                        alert_time = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    else:
                        alert_time = created

                    days_stalled = (now - alert_time).days

                    if days_stalled >= 2:
                        user_id = alert.get("user_id")
                        description = alert.get("description", "blocker")

                        nudges.append({
                            "type": "blocker_stalled",
                            "recipient_id": user_id,
                            "urgency": "high" if days_stalled >= 4 else "medium",
                            "days_stalled": days_stalled,
                            "message": f"🚧 This blocker has been open for {days_stalled} days: \"{description}\"\n"
                                       f"Need help to unblock progress? Post in #help or escalate.",
                            "action": "escalate_if_critical"
                        })

            # Check 2: Unanswered help requests (6+ hours)
            pending_help = await self.database.get_pending_help_requests()
            for help_req in pending_help:
                created = help_req.get("created_at")
                if created:
                    if isinstance(created, str):
                        help_time = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    else:
                        help_time = created

                    hours_pending = (now - help_time).total_seconds() / 3600

                    if hours_pending >= 6:
                        helper_id = help_req.get("to_user_id")
                        topic = help_req.get("topic", "request")

                        nudges.append({
                            "type": "help_unanswered",
                            "recipient_id": helper_id,
                            "urgency": "high" if hours_pending >= 24 else "medium",
                            "hours_pending": int(hours_pending),
                            "message": f"⏰ Someone is waiting for your help on: \"{topic}\"\n"
                                       f"It's been {int(hours_pending)} hours. Can you respond?",
                            "action": "respond_or_reassign"
                        })

            # Check 3: Long-stalled tasks (5+ days with no progress)
            async with self.database.async_session() as session:
                from services.database import Task
                from sqlalchemy import select

                result = await session.execute(
                    select(Task).where(Task.status != TaskStatus.COMPLETED)
                )
                tasks = result.scalars().all()

                for task in tasks:
                    if task.progress_percentage == 0 and task.created_at:
                        days_stalled = (now - task.created_at).days

                        if days_stalled >= 5:
                            assignee_id = task.assignee_id
                            title = task.title

                            nudges.append({
                                "type": "task_stalled",
                                "recipient_id": assignee_id,
                                "urgency": "medium",
                                "days_stalled": days_stalled,
                                "message": f"📋 Task \"{title}\" hasn't been started in {days_stalled} days.\n"
                                           f"Any blockers? Update progress or let us know if you need help.",
                                "action": "update_or_escalate"
                            })

            logger.info(f"Generated {len(nudges)} accountability nudges")

            return {
                "status": "success",
                "nudges_count": len(nudges),
                "nudges": nudges,
                "timestamp": now.isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating nudges: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to generate nudges: {str(e)}"
            }
