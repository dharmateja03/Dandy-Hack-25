"""
Linear Integration Service
Sync tasks and issues from Linear
"""

import logging
from typing import Dict, List, Optional
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class LinearService:
    """Linear integration for task management"""

    def __init__(self, api_key: str, team_id: str = None):
        self.api_key = api_key
        self.team_id = team_id
        self.base_url = "https://api.linear.app/graphql"
        self.headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }

    def test_connection(self) -> bool:
        """Test Linear API connection"""
        query = """
        query {
            viewer {
                id
                name
            }
        }
        """

        try:
            response = requests.post(
                self.base_url,
                json={"query": query},
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'viewer' in data['data']:
                    logger.info(f"Connected to Linear as: {data['data']['viewer']['name']}")
                    return True

            logger.error(f"Linear connection failed: {response.status_code}")
            return False

        except Exception as e:
            logger.error(f"Linear connection error: {e}")
            return False

    async def sync_issues(self, assignee_id: str = None) -> List[Dict]:
        """Fetch issues from Linear"""
        query = """
        query($teamId: String, $assigneeId: String) {
            issues(
                filter: {
                    team: { id: { eq: $teamId } }
                    assignee: { id: { eq: $assigneeId } }
                }
                orderBy: updatedAt
            ) {
                nodes {
                    id
                    title
                    description
                    state {
                        name
                        type
                    }
                    priority
                    assignee {
                        id
                        name
                        email
                    }
                    createdAt
                    updatedAt
                    completedAt
                }
            }
        }
        """

        variables = {}
        if self.team_id:
            variables['teamId'] = self.team_id
        if assignee_id:
            variables['assigneeId'] = assignee_id

        try:
            response = requests.post(
                self.base_url,
                json={"query": query, "variables": variables},
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                issues = data.get('data', {}).get('issues', {}).get('nodes', [])

                # Transform to our format
                tasks = []
                for issue in issues:
                    task = {
                        'external_id': issue['id'],
                        'title': issue['title'],
                        'description': issue.get('description', ''),
                        'status': self._map_status(issue['state']['type']),
                        'priority': self._map_priority(issue.get('priority', 0)),
                        'assignee_email': issue['assignee']['email'] if issue.get('assignee') else None,
                        'created_at': issue.get('createdAt'),
                        'updated_at': issue.get('updatedAt'),
                        'completed_at': issue.get('completedAt')
                    }
                    tasks.append(task)

                logger.info(f"Synced {len(tasks)} issues from Linear")
                return tasks

            logger.error(f"Failed to fetch Linear issues: {response.status_code}")
            return []

        except Exception as e:
            logger.error(f"Error syncing Linear issues: {e}")
            return []

    def _map_status(self, linear_state: str) -> str:
        """Map Linear state to our task status"""
        mapping = {
            'backlog': 'not_started',
            'unstarted': 'not_started',
            'started': 'in_progress',
            'completed': 'completed',
            'canceled': 'completed'
        }
        return mapping.get(linear_state.lower(), 'not_started')

    def _map_priority(self, linear_priority: int) -> str:
        """Map Linear priority (0-4) to our priority"""
        if linear_priority >= 3:
            return 'high'
        elif linear_priority >= 2:
            return 'medium'
        else:
            return 'low'

    async def create_issue(self, task_data: Dict) -> Optional[str]:
        """Create an issue in Linear"""
        mutation = """
        mutation($teamId: String!, $title: String!, $description: String, $priority: Int) {
            issueCreate(
                input: {
                    teamId: $teamId
                    title: $title
                    description: $description
                    priority: $priority
                }
            ) {
                success
                issue {
                    id
                    title
                }
            }
        }
        """

        if not self.team_id:
            logger.error("Cannot create issue: team_id not set")
            return None

        variables = {
            'teamId': self.team_id,
            'title': task_data.get('title', 'Untitled Task'),
            'description': task_data.get('description', ''),
            'priority': self._reverse_map_priority(task_data.get('priority', 'medium'))
        }

        try:
            response = requests.post(
                self.base_url,
                json={"query": mutation, "variables": variables},
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('data', {}).get('issueCreate', {}).get('success'):
                    issue_id = data['data']['issueCreate']['issue']['id']
                    logger.info(f"Created Linear issue: {issue_id}")
                    return issue_id

            logger.error(f"Failed to create Linear issue: {response.status_code}")
            return None

        except Exception as e:
            logger.error(f"Error creating Linear issue: {e}")
            return None

    def _reverse_map_priority(self, our_priority: str) -> int:
        """Map our priority to Linear priority (0-4)"""
        mapping = {
            'low': 1,
            'medium': 2,
            'high': 3
        }
        return mapping.get(our_priority.lower(), 2)
