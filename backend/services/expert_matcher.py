"""
Expert Matcher Service
Matches help requests to experts based on GitHub activity and expertise
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)


class ExpertMatcher:
    """Matches blockers/help requests to team experts"""

    def __init__(self, db_service, github_service=None):
        self.db = db_service
        self.github = github_service

    async def find_best_expert(
        self,
        blocker_text: str,
        requester_id: str,
        limit: int = 3
    ) -> List[Dict]:
        """
        Find the best expert(s) to help with a blocker

        Returns list of experts with confidence scores
        """
        # Extract keywords and technologies from blocker text
        keywords = self._extract_keywords(blocker_text)

        logger.info(f"Extracted keywords from blocker: {keywords}")

        # Get all users and their expertise
        all_experts = []

        for keyword in keywords:
            # Search in user expertise table
            experts = await self.db.find_expert(keyword, limit=10)

            for expert in experts:
                # Skip if expert is the requester
                if expert['user_id'] == requester_id:
                    continue

                # Check availability (workload)
                workload = await self.db.get_user_workload(expert['user_id'])

                # Calculate confidence score
                confidence = expert['score']

                # Adjust confidence based on workload
                if workload > 5:
                    confidence *= 0.7  # Reduce confidence if overloaded
                elif workload < 2:
                    confidence *= 1.1  # Boost if available

                all_experts.append({
                    'user_id': expert['user_id'],
                    'user_name': expert['user_name'],
                    'domain': expert['domain'],
                    'confidence': min(100, confidence),
                    'commit_count': expert['commit_count'],
                    'pr_count': expert['pr_count'],
                    'review_count': expert['review_count'],
                    'help_count': expert['help_count'],
                    'current_workload': workload,
                    'keywords_matched': [keyword]
                })

        # Consolidate experts (same user might match multiple keywords)
        consolidated = {}
        for expert in all_experts:
            user_id = expert['user_id']
            if user_id in consolidated:
                # Combine confidence scores
                consolidated[user_id]['confidence'] = min(
                    100,
                    consolidated[user_id]['confidence'] + (expert['confidence'] * 0.5)
                )
                consolidated[user_id]['keywords_matched'].extend(expert['keywords_matched'])
                consolidated[user_id]['keywords_matched'] = list(set(consolidated[user_id]['keywords_matched']))
            else:
                consolidated[user_id] = expert

        # Sort by confidence
        sorted_experts = sorted(
            consolidated.values(),
            key=lambda x: x['confidence'],
            reverse=True
        )

        return sorted_experts[:limit]

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract technology keywords from text"""
        text_lower = text.lower()

        # Common technology keywords
        tech_keywords = [
            'python', 'javascript', 'react', 'nodejs', 'node', 'java', 'golang', 'go',
            'docker', 'kubernetes', 'k8s', 'terraform', 'aws', 'devops', 'ci/cd',
            'frontend', 'backend', 'api', 'rest', 'graphql',
            'database', 'sql', 'postgres', 'postgresql', 'mysql', 'mongodb', 'mongo',
            'typescript', 'vue', 'angular', 'svelte',
            'rust', 'ruby', 'rails', 'django', 'flask', 'fastapi',
            'redis', 'nginx', 'apache',
            'git', 'github', 'gitlab',
            'linux', 'bash', 'shell',
            'authentication', 'auth', 'oauth', 'jwt',
            'deployment', 'ci', 'cd', 'pipeline',
            'testing', 'jest', 'pytest', 'unit test',
            'ui', 'ux', 'css', 'html', 'styling'
        ]

        # Framework/library patterns
        framework_patterns = [
            r'(\w+)\.js',
            r'requirements\.txt',
            r'package\.json',
            r'dockerfile',
            r'docker-compose'
        ]

        found_keywords = []

        # Direct keyword matching
        for keyword in tech_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)

        # Pattern matching
        for pattern in framework_patterns:
            matches = re.findall(pattern, text_lower)
            found_keywords.extend(matches)

        # Extract error-related context
        error_patterns = [
            r'(\w+)Error',
            r'(\w+)Exception',
            r'error.*?(\w+)',
            r'failed.*?(\w+)'
        ]

        for pattern in error_patterns:
            matches = re.findall(pattern, text)
            for match in matches[:2]:  # Limit to 2 per pattern
                # Check if match is a technology
                if match.lower() in tech_keywords:
                    if match.lower() not in found_keywords:
                        found_keywords.append(match.lower())

        # If no keywords found, try general categories
        if not found_keywords:
            if any(word in text_lower for word in ['frontend', 'ui', 'ux', 'design', 'css']):
                found_keywords.append('frontend')
            elif any(word in text_lower for word in ['backend', 'server', 'api', 'database']):
                found_keywords.append('backend')
            elif any(word in text_lower for word in ['deploy', 'ci', 'cd', 'build']):
                found_keywords.append('devops')

        # Remove duplicates and limit
        found_keywords = list(set(found_keywords))[:5]

        return found_keywords if found_keywords else ['general']

    async def check_multi_domain_blocker(self, keywords: List[str]) -> bool:
        """Check if blocker requires multiple experts from different domains"""
        # Categorize keywords
        categories = {
            'frontend': ['react', 'vue', 'angular', 'javascript', 'typescript', 'html', 'css', 'ui', 'ux'],
            'backend': ['python', 'java', 'golang', 'nodejs', 'api', 'fastapi', 'django', 'flask', 'rest'],
            'devops': ['docker', 'kubernetes', 'terraform', 'aws', 'ci', 'cd', 'deployment', 'nginx'],
            'database': ['sql', 'postgres', 'mysql', 'mongodb', 'database', 'redis']
        }

        matched_categories = set()

        for keyword in keywords:
            for category, category_keywords in categories.items():
                if keyword.lower() in category_keywords:
                    matched_categories.add(category)

        # If more than 1 category matched, it's a multi-domain issue
        return len(matched_categories) > 1

    async def get_expert_availability(self, user_id: str) -> Dict:
        """Get expert's current availability"""
        # Get current workload
        workload = await self.db.get_user_workload(user_id)

        # Get pending help requests
        help_inbox_threads = await self.db.get_expert_inbox_threads(user_id, active_only=True)

        # Get recent activity
        recent_commits = await self.db.get_user_commits(user_id, days=7)

        return {
            'current_tasks': workload,
            'active_help_requests': len(help_inbox_threads),
            'recent_commits_count': len(recent_commits),
            'availability_score': self._calculate_availability_score(
                workload,
                len(help_inbox_threads),
                len(recent_commits)
            )
        }

    def _calculate_availability_score(
        self,
        task_count: int,
        help_request_count: int,
        commit_count: int
    ) -> float:
        """
        Calculate availability score (0-100, higher is more available)
        """
        # Start with 100
        score = 100.0

        # Reduce based on workload
        score -= (task_count * 10)  # Each task reduces by 10 points
        score -= (help_request_count * 15)  # Each help request reduces by 15 points

        # Very active developers (many commits) might be less available
        if commit_count > 20:
            score -= 10
        elif commit_count > 10:
            score -= 5

        return max(0, min(100, score))

    async def rank_experts_with_context(
        self,
        experts: List[Dict],
        blocker_context: Dict
    ) -> List[Dict]:
        """
        Rank experts considering additional context like urgency,
        past collaboration, etc.
        """
        for expert in experts:
            # Get additional context
            availability = await self.get_expert_availability(expert['user_id'])

            # Adjust score based on availability
            availability_weight = availability['availability_score'] / 100
            expert['final_score'] = expert['confidence'] * (0.7 + (availability_weight * 0.3))

            # Add availability info
            expert['availability'] = availability

            # Add estimated response time
            expert['estimated_response_minutes'] = self._estimate_response_time(
                availability['active_help_requests'],
                expert['help_count']
            )

        # Re-sort by final score
        experts.sort(key=lambda x: x['final_score'], reverse=True)

        return experts

    def _estimate_response_time(self, active_requests: int, help_history: int) -> int:
        """Estimate response time in minutes"""
        base_time = 15  # 15 minutes base

        # More active requests = longer wait
        wait_time = active_requests * 20

        # Experienced helpers respond faster
        if help_history > 10:
            base_time *= 0.8
        elif help_history > 5:
            base_time *= 0.9

        return int(base_time + wait_time)

    async def suggest_alternative_solutions(self, blocker_text: str, keywords: List[str]) -> List[Dict]:
        """Suggest alternative solutions like documentation, similar resolved issues, etc."""
        suggestions = []

        # Check for common issues with known solutions
        common_patterns = {
            'dependency': {
                'keywords': ['dependency', 'requirements', 'package', 'install'],
                'suggestion': 'Check requirements.txt version conflicts',
                'type': 'documentation'
            },
            'authentication': {
                'keywords': ['auth', 'login', 'jwt', 'token', 'permission'],
                'suggestion': 'Review authentication flow documentation',
                'type': 'documentation'
            },
            'docker': {
                'keywords': ['docker', 'container', 'image', 'dockerfile'],
                'suggestion': 'Check Docker logs and container configuration',
                'type': 'debugging'
            },
            'database': {
                'keywords': ['database', 'sql', 'migration', 'connection'],
                'suggestion': 'Verify database connection settings',
                'type': 'configuration'
            }
        }

        blocker_lower = blocker_text.lower()

        for issue_type, pattern_info in common_patterns.items():
            if any(keyword in blocker_lower for keyword in pattern_info['keywords']):
                suggestions.append({
                    'type': pattern_info['type'],
                    'suggestion': pattern_info['suggestion'],
                    'category': issue_type
                })

        return suggestions
