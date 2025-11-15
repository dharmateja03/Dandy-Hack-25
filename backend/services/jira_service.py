"""
Jira Integration Service
Read-only integration to sync tasks from Jira
"""

import logging
from typing import Dict, List, Optional
from jira import JIRA
from datetime import datetime

logger = logging.getLogger(__name__)


class JiraService:
    """
    Jira Integration for MCP

    Features:
    - Read tasks from Jira
    - Sync task metadata to MCP
    - Optional: Update Jira when status changes in MCP
    """

    def __init__(
        self,
        jira_url: str,
        email: str,
        api_token: str,
        enabled: bool = False
    ):
        self.jira_url = jira_url
        self.email = email
        self.api_token = api_token
        self.enabled = enabled
        self.client = None

    async def initialize(self):
        """Initialize Jira client"""
        if not self.enabled:
            logger.info("Jira integration disabled")
            return

        try:
            self.client = JIRA(
                server=self.jira_url,
                basic_auth=(self.email, self.api_token)
            )

            # Test connection
            self.client.myself()
            logger.info("✅ Jira integration initialized")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Jira: {e}")
            self.enabled = False

    async def get_user_tasks(
        self,
        assignee_email: str,
        status_filter: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get tasks assigned to a user from Jira

        Args:
            assignee_email: User's email (Jira assignee)
            status_filter: Optional list of statuses to filter (e.g., ["In Progress", "To Do"])

        Returns:
            List of task dictionaries
        """
        if not self.enabled or not self.client:
            return []

        try:
            # Build JQL query
            jql = f'assignee = "{assignee_email}"'

            if status_filter:
                statuses = ', '.join([f'"{s}"' for s in status_filter])
                jql += f' AND status IN ({statuses})'

            # Search issues
            issues = self.client.search_issues(jql, maxResults=100)

            tasks = []
            for issue in issues:
                task = self._convert_jira_issue_to_task(issue)
                tasks.append(task)

            logger.info(f"Retrieved {len(tasks)} tasks from Jira for {assignee_email}")
            return tasks

        except Exception as e:
            logger.error(f"Error fetching Jira tasks: {e}")
            return []

    async def get_project_tasks(
        self,
        project_key: str,
        limit: int = 100
    ) -> List[Dict]:
        """Get all tasks for a Jira project"""
        if not self.enabled or not self.client:
            return []

        try:
            jql = f'project = "{project_key}" ORDER BY updated DESC'
            issues = self.client.search_issues(jql, maxResults=limit)

            tasks = []
            for issue in issues:
                task = self._convert_jira_issue_to_task(issue)
                tasks.append(task)

            logger.info(f"Retrieved {len(tasks)} tasks from Jira project {project_key}")
            return tasks

        except Exception as e:
            logger.error(f"Error fetching Jira project tasks: {e}")
            return []

    async def sync_task_to_mcp(self, jira_id: str, database_service) -> Optional[int]:
        """
        Sync a Jira task to MCP database

        Returns:
            Task ID in MCP database, or None if failed
        """
        if not self.enabled or not self.client:
            return None

        try:
            issue = self.client.issue(jira_id)
            task_data = self._convert_jira_issue_to_task(issue)

            # Check if task already exists
            existing_task = await database_service.get_task_by_jira_id(jira_id)

            if existing_task:
                # Update existing task
                await database_service.update_task(
                    task_id=existing_task['id'],
                    **task_data
                )
                return existing_task['id']
            else:
                # Create new task
                task_id = await database_service.create_task(task_data)
                return task_id

        except Exception as e:
            logger.error(f"Error syncing Jira task {jira_id}: {e}")
            return None

    async def update_jira_status(
        self,
        jira_id: str,
        new_status: str
    ) -> bool:
        """
        Update Jira issue status (optional, for two-way sync)

        Args:
            jira_id: Jira issue ID
            new_status: New status (e.g., "In Progress", "Done")

        Returns:
            True if successful
        """
        if not self.enabled or not self.client:
            return False

        try:
            issue = self.client.issue(jira_id)

            # Get available transitions
            transitions = self.client.transitions(issue)

            # Find matching transition
            target_transition = None
            for t in transitions:
                if t['name'].lower() == new_status.lower():
                    target_transition = t['id']
                    break

            if target_transition:
                self.client.transition_issue(issue, target_transition)
                logger.info(f"Updated Jira {jira_id} status to {new_status}")
                return True
            else:
                logger.warning(f"No transition found for status: {new_status}")
                return False

        except Exception as e:
            logger.error(f"Error updating Jira status: {e}")
            return False

    def _convert_jira_issue_to_task(self, issue) -> Dict:
        """
        Convert Jira issue to MCP task format

        Extracts relevant fields and maps to MCP schema
        """
        # Map Jira status to MCP status
        status_mapping = {
            "To Do": "not_started",
            "In Progress": "in_progress",
            "Blocked": "blocked",
            "Done": "completed",
            "Closed": "completed"
        }

        jira_status = issue.fields.status.name
        mcp_status = status_mapping.get(jira_status, "not_started")

        # Extract priority
        priority_mapping = {
            "Highest": "high",
            "High": "high",
            "Medium": "medium",
            "Low": "low",
            "Lowest": "low"
        }

        jira_priority = getattr(issue.fields.priority, 'name', 'Medium') if issue.fields.priority else 'Medium'
        mcp_priority = priority_mapping.get(jira_priority, "medium")

        # Get assignee
        assignee_id = None
        if issue.fields.assignee:
            assignee_id = issue.fields.assignee.emailAddress

        # Calculate progress (if available)
        progress_percentage = 0
        if hasattr(issue.fields, 'progress') and issue.fields.progress:
            total = getattr(issue.fields.progress, 'total', 0)
            progress = getattr(issue.fields.progress, 'progress', 0)
            if total > 0:
                progress_percentage = int((progress / total) * 100)

        return {
            "jira_id": issue.key,
            "title": issue.fields.summary,
            "description": getattr(issue.fields, 'description', '') or '',
            "assignee_id": assignee_id,
            "status": mcp_status,
            "priority": mcp_priority,
            "progress_percentage": progress_percentage,
            "created_at": self._parse_jira_datetime(issue.fields.created),
            "due_date": self._parse_jira_datetime(getattr(issue.fields, 'duedate', None))
        }

    def _parse_jira_datetime(self, jira_datetime_str: Optional[str]) -> Optional[datetime]:
        """Parse Jira datetime string to Python datetime"""
        if not jira_datetime_str:
            return None

        try:
            # Jira format: 2023-10-15T14:30:00.000+0000
            return datetime.fromisoformat(jira_datetime_str.replace('Z', '+00:00'))
        except Exception as e:
            logger.warning(f"Failed to parse Jira datetime: {jira_datetime_str}")
            return None

    async def bulk_sync_project(
        self,
        project_key: str,
        database_service
    ) -> Dict[str, int]:
        """
        Bulk sync entire Jira project to MCP

        Returns:
            Stats: {"synced": X, "failed": Y}
        """
        if not self.enabled or not self.client:
            return {"synced": 0, "failed": 0}

        tasks = await self.get_project_tasks(project_key)

        synced = 0
        failed = 0

        for task in tasks:
            try:
                jira_id = task['jira_id']
                result = await self.sync_task_to_mcp(jira_id, database_service)

                if result:
                    synced += 1
                else:
                    failed += 1

            except Exception as e:
                logger.error(f"Error syncing task: {e}")
                failed += 1

        logger.info(f"Bulk sync complete: {synced} synced, {failed} failed")

        return {"synced": synced, "failed": failed}
