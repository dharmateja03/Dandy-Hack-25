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
        1. Parse with Gemini to extract structured data
        2. Store in vector DB for semantic search
        3. Update task statuses in database
        4. Identify help requests and route them
        5. Detect blockers and alert manager
        """
        timestamp = timestamp or datetime.utcnow()

        logger.info(f"Processing standup for user {user_id}")

        try:
            # Step 1: Parse with Gemini
            parsed_data = await self._parse_standup_with_gemini(user_id, message)

            # Step 2: Store in vector DB
            context_id = await self.vector_db.add_standup(
                user_id=user_id,
                text=message,
                parsed_data=parsed_data,
                timestamp=timestamp
            )

            # Step 3: Update task statuses
            await self._update_task_statuses(user_id, parsed_data)

            # Step 4: Route help requests
            help_requests = parsed_data.get("help_requests", [])
            routed_requests = []
            for help_req in help_requests:
                routed = await self._route_help_request(user_id, help_req)
                routed_requests.append(routed)

            # Step 5: Detect blockers
            blockers = parsed_data.get("blockers", [])
            if blockers:
                await self._alert_manager_blockers(user_id, blockers)

            return {
                "status": "success",
                "context_id": context_id,
                "parsed_data": parsed_data,
                "help_requests_routed": routed_requests,
                "blockers_detected": len(blockers)
            }

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
            "urgency": "low|medium|high"
        }}
    ],
    "task_updates": [
        {{
            "task_name": "task name",
            "progress_percentage": 0-100,
            "status": "not_started|in_progress|blocked|completed"
        }}
    ],
    "sentiment": "positive|neutral|negative|frustrated",
    "key_points": ["important points to remember"]
}}

Return ONLY valid JSON, no markdown.
"""

        try:
            response = self.model.generate_content(prompt)
            parsed_json = json.loads(response.text.strip())
            return parsed_json

        except json.JSONDecodeError:
            logger.warning("Gemini response was not valid JSON, using fallback")
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
            logger.error(f"Error parsing with Gemini: {e}")
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

    async def _route_help_request(
        self,
        requesting_user_id: str,
        help_request: Dict
    ) -> Dict[str, Any]:
        """
        Intelligently route help requests

        1. Search vector DB for who has expertise
        2. Check who is available (not overloaded)
        3. Return best person to help
        """
        topic = help_request.get("topic", "")
        urgency = help_request.get("urgency", "medium")

        # Semantic search for expertise
        experts = await self.vector_db.find_experts(topic, limit=5)

        # Check availability
        available_expert = None
        for expert in experts:
            workload = await self.database.get_user_workload(expert["user_id"])
            if workload < 5:  # Not overloaded
                available_expert = expert
                break

        if not available_expert and experts:
            available_expert = experts[0]  # Take top expert even if busy

        if available_expert:
            # Create help request in database
            help_req_id = await self.database.create_help_request(
                from_user=requesting_user_id,
                to_user=available_expert["user_id"],
                topic=topic,
                context=help_request.get("context", ""),
                urgency=urgency
            )

            return {
                "help_request_id": help_req_id,
                "assigned_to": available_expert["user_id"],
                "reason": f"Expert in {topic}",
                "confidence": available_expert.get("score", 0)
            }
        else:
            # No expert found, escalate to manager
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
