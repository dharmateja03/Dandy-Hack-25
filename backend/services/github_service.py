"""
GitHub Integration Service
Fetches commits, PRs, reviews and analyzes expertise
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from github import Github, GithubException
import re
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class GitHubService:
    """GitHub integration service for tracking commits, PRs, and code reviews"""

    def __init__(self, github_token: str, org_name: str = None, repo_names: List[str] = None):
        self.github = Github(github_token)
        self.org_name = org_name
        self.repo_names = repo_names or []
        self.user = None

        # Technology/file extension mapping
        self.tech_mapping = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'react',
            '.ts': 'typescript',
            '.tsx': 'react',
            '.go': 'golang',
            '.java': 'java',
            '.rb': 'ruby',
            '.php': 'php',
            '.rs': 'rust',
            '.c': 'c',
            '.cpp': 'cpp',
            '.cs': 'csharp',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.sql': 'sql',
            '.sh': 'bash',
            '.yml': 'devops',
            '.yaml': 'devops',
            'dockerfile': 'docker',
            'docker-compose': 'docker',
            '.tf': 'terraform',
            '.html': 'frontend',
            '.css': 'frontend',
            '.scss': 'frontend',
            '.vue': 'vue',
            'requirements.txt': 'python',
            'package.json': 'nodejs',
            'pom.xml': 'java',
            'build.gradle': 'java'
        }

    async def test_connection(self) -> bool:
        """Test GitHub connection"""
        try:
            self.user = self.github.get_user()
            logger.info(f"Connected to GitHub as: {self.user.login}")
            return True
        except GithubException as e:
            logger.error(f"GitHub connection failed: {e}")
            return False

    def get_repos(self) -> List:
        """Get repositories to track"""
        repos = []

        if self.org_name:
            org = self.github.get_organization(self.org_name)
            if self.repo_names:
                for repo_name in self.repo_names:
                    try:
                        repos.append(org.get_repo(repo_name))
                    except GithubException:
                        logger.warning(f"Repo {repo_name} not found in org {self.org_name}")
            else:
                repos = list(org.get_repos())
        else:
            # Personal repos
            if self.repo_names:
                for repo_name in self.repo_names:
                    try:
                        repos.append(self.github.get_repo(repo_name))
                    except GithubException:
                        logger.warning(f"Repo {repo_name} not found")
            else:
                repos = list(self.github.get_user().get_repos())

        return repos

    async def sync_commits(self, since_days: int = 30) -> List[Dict]:
        """Fetch recent commits from all repos"""
        commits_data = []
        since = datetime.utcnow() - timedelta(days=since_days)

        repos = self.get_repos()

        for repo in repos:
            try:
                commits = repo.get_commits(since=since)

                for commit in commits:
                    try:
                        # Get commit details
                        files_changed = []
                        additions = 0
                        deletions = 0

                        for file in commit.files:
                            files_changed.append({
                                'filename': file.filename,
                                'status': file.status,
                                'additions': file.additions,
                                'deletions': file.deletions
                            })
                            additions += file.additions
                            deletions += file.deletions

                        commit_data = {
                            'sha': commit.sha,
                            'github_username': commit.author.login if commit.author else 'unknown',
                            'repo_name': repo.full_name,
                            'message': commit.commit.message,
                            'files_changed': files_changed,
                            'additions': additions,
                            'deletions': deletions,
                            'commit_date': commit.commit.author.date
                        }

                        commits_data.append(commit_data)

                    except Exception as e:
                        logger.error(f"Error processing commit {commit.sha}: {e}")
                        continue

            except GithubException as e:
                logger.error(f"Error fetching commits from {repo.name}: {e}")
                continue

        logger.info(f"Synced {len(commits_data)} commits from {len(repos)} repos")
        return commits_data

    async def sync_pull_requests(self, since_days: int = 30) -> List[Dict]:
        """Fetch recent pull requests"""
        prs_data = []
        since = datetime.utcnow() - timedelta(days=since_days)

        repos = self.get_repos()

        for repo in repos:
            try:
                # Get both open and closed PRs
                prs = repo.get_pulls(state='all', sort='updated', direction='desc')

                for pr in prs:
                    try:
                        # Skip PRs older than since date
                        if pr.created_at < since:
                            continue

                        pr_data = {
                            'pr_number': pr.number,
                            'repo_name': repo.full_name,
                            'github_username': pr.user.login if pr.user else 'unknown',
                            'title': pr.title,
                            'state': pr.state,
                            'merged': pr.merged,
                            'created_at_github': pr.created_at,
                            'merged_at': pr.merged_at,
                            'closed_at': pr.closed_at
                        }

                        prs_data.append(pr_data)

                    except Exception as e:
                        logger.error(f"Error processing PR #{pr.number}: {e}")
                        continue

            except GithubException as e:
                logger.error(f"Error fetching PRs from {repo.name}: {e}")
                continue

        logger.info(f"Synced {len(prs_data)} PRs from {len(repos)} repos")
        return prs_data

    async def sync_code_reviews(self, since_days: int = 30) -> List[Dict]:
        """Fetch recent code reviews"""
        reviews_data = []
        since = datetime.utcnow() - timedelta(days=since_days)

        repos = self.get_repos()

        for repo in repos:
            try:
                prs = repo.get_pulls(state='all', sort='updated', direction='desc')

                for pr in prs:
                    try:
                        if pr.created_at < since:
                            continue

                        reviews = pr.get_reviews()

                        for review in reviews:
                            try:
                                if review.submitted_at and review.submitted_at >= since:
                                    review_data = {
                                        'review_id': str(review.id),
                                        'pr_number': pr.number,
                                        'repo_name': repo.full_name,
                                        'github_username': review.user.login if review.user else 'unknown',
                                        'state': review.state,
                                        'submitted_at': review.submitted_at
                                    }
                                    reviews_data.append(review_data)

                            except Exception as e:
                                logger.error(f"Error processing review {review.id}: {e}")
                                continue

                    except Exception as e:
                        logger.error(f"Error getting reviews for PR #{pr.number}: {e}")
                        continue

            except GithubException as e:
                logger.error(f"Error fetching reviews from {repo.name}: {e}")
                continue

        logger.info(f"Synced {len(reviews_data)} reviews from {len(repos)} repos")
        return reviews_data

    def extract_technologies_from_files(self, files_changed: List[Dict]) -> Dict[str, int]:
        """Extract technologies/languages from changed files"""
        tech_counts = defaultdict(int)

        for file_info in files_changed:
            filename = file_info['filename'].lower()

            # Check exact matches
            if filename in self.tech_mapping:
                tech_counts[self.tech_mapping[filename]] += 1
                continue

            # Check file extensions
            for ext, tech in self.tech_mapping.items():
                if filename.endswith(ext):
                    tech_counts[tech] += 1
                    break

            # Check special files
            if 'docker' in filename:
                tech_counts['docker'] += 1
            elif 'kubernetes' in filename or 'k8s' in filename:
                tech_counts['kubernetes'] += 1
            elif 'terraform' in filename:
                tech_counts['terraform'] += 1
            elif 'nginx' in filename or 'apache' in filename:
                tech_counts['webserver'] += 1

        return dict(tech_counts)

    def calculate_expertise_score(
        self,
        commit_count: int,
        pr_count: int,
        review_count: int,
        help_count: int,
        recency_weight: float = 1.0
    ) -> float:
        """Calculate expertise score (0-100)"""
        # Weights for different activities
        commit_weight = 2.0
        pr_weight = 10.0
        review_weight = 5.0
        help_weight = 8.0

        raw_score = (
            (commit_count * commit_weight) +
            (pr_count * pr_weight) +
            (review_count * review_weight) +
            (help_count * help_weight)
        )

        # Apply recency weight
        raw_score *= recency_weight

        # Normalize to 0-100 scale (using logarithmic scaling)
        import math
        if raw_score == 0:
            return 0.0

        normalized_score = min(100.0, (math.log(raw_score + 1) / math.log(1000)) * 100)

        return round(normalized_score, 2)

    async def analyze_user_expertise(self, commits: List[Dict], prs: List[Dict], reviews: List[Dict]) -> Dict[str, Dict]:
        """Analyze user's expertise based on GitHub activity"""
        expertise_by_domain = defaultdict(lambda: {
            'commit_count': 0,
            'pr_count': 0,
            'review_count': 0,
            'help_count': 0,
            'last_activity': None
        })

        # Analyze commits
        for commit in commits:
            files_changed = commit.get('files_changed', [])
            technologies = self.extract_technologies_from_files(files_changed)
            commit_date = commit.get('commit_date')

            for tech in technologies.keys():
                expertise_by_domain[tech]['commit_count'] += 1

                if not expertise_by_domain[tech]['last_activity'] or \
                   (commit_date and commit_date > expertise_by_domain[tech]['last_activity']):
                    expertise_by_domain[tech]['last_activity'] = commit_date

        # Analyze PRs - infer technologies from repo name and PR title
        for pr in prs:
            repo_name = pr.get('repo_name', '').lower()
            title = pr.get('title', '').lower()

            # Infer tech from repo/PR context
            inferred_techs = []
            for keyword, tech in [
                ('python', 'python'), ('react', 'react'), ('node', 'nodejs'),
                ('java', 'java'), ('go', 'golang'), ('docker', 'docker'),
                ('kubernetes', 'kubernetes'), ('api', 'backend'), ('frontend', 'frontend')
            ]:
                if keyword in repo_name or keyword in title:
                    inferred_techs.append(tech)

            if not inferred_techs:
                inferred_techs = ['general']

            for tech in inferred_techs:
                expertise_by_domain[tech]['pr_count'] += 1

                if pr.get('created_at_github'):
                    if not expertise_by_domain[tech]['last_activity'] or \
                       pr['created_at_github'] > expertise_by_domain[tech]['last_activity']:
                        expertise_by_domain[tech]['last_activity'] = pr['created_at_github']

        # Analyze reviews
        for review in reviews:
            repo_name = review.get('repo_name', '').lower()

            inferred_techs = []
            for keyword, tech in [
                ('python', 'python'), ('react', 'react'), ('node', 'nodejs'),
                ('java', 'java'), ('go', 'golang'), ('docker', 'docker')
            ]:
                if keyword in repo_name:
                    inferred_techs.append(tech)

            if not inferred_techs:
                inferred_techs = ['general']

            for tech in inferred_techs:
                expertise_by_domain[tech]['review_count'] += 1

                if review.get('submitted_at'):
                    if not expertise_by_domain[tech]['last_activity'] or \
                       review['submitted_at'] > expertise_by_domain[tech]['last_activity']:
                        expertise_by_domain[tech]['last_activity'] = review['submitted_at']

        # Calculate scores for each domain
        expertise_scores = {}
        for domain, metrics in expertise_by_domain.items():
            # Calculate recency weight (decay over 90 days)
            recency_weight = 1.0
            if metrics['last_activity']:
                days_ago = (datetime.utcnow() - metrics['last_activity'].replace(tzinfo=None)).days
                recency_weight = max(0.3, 1.0 - (days_ago / 90.0))

            score = self.calculate_expertise_score(
                metrics['commit_count'],
                metrics['pr_count'],
                metrics['review_count'],
                metrics['help_count'],
                recency_weight
            )

            expertise_scores[domain] = {
                'score': score,
                'commit_count': metrics['commit_count'],
                'pr_count': metrics['pr_count'],
                'review_count': metrics['review_count'],
                'help_count': metrics['help_count'],
                'last_activity': metrics['last_activity']
            }

        return expertise_scores

    async def match_expert_for_blocker(
        self,
        blocker_text: str,
        all_user_expertise: Dict[str, Dict[str, Dict]]
    ) -> List[Tuple[str, float, List[str]]]:
        """
        Match experts to a blocker based on keywords

        Returns: List of (user_id, confidence_score, matched_domains)
        """
        # Extract keywords from blocker text
        blocker_lower = blocker_text.lower()

        # Technology keywords to look for
        tech_keywords = [
            'python', 'react', 'javascript', 'nodejs', 'java', 'golang', 'go',
            'docker', 'kubernetes', 'terraform', 'aws', 'devops', 'frontend',
            'backend', 'api', 'database', 'sql', 'postgres', 'mongo',
            'typescript', 'vue', 'angular', 'rust', 'ruby'
        ]

        # Find mentioned technologies
        mentioned_techs = [tech for tech in tech_keywords if tech in blocker_lower]

        if not mentioned_techs:
            # Try to extract from common patterns
            patterns = [
                r'error.*?(\w+)',
                r'stuck.*?(\w+)',
                r'blocked.*?(\w+)',
                r'issue.*?(\w+)',
                r'problem.*?(\w+)'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, blocker_lower)
                if matches:
                    mentioned_techs.extend(matches[:2])

        # Score each user based on expertise in mentioned technologies
        user_scores = []

        for user_id, expertise_dict in all_user_expertise.items():
            total_score = 0.0
            matched_domains = []

            for tech in mentioned_techs:
                # Find matching expertise domains
                for domain, metrics in expertise_dict.items():
                    if tech in domain.lower() or domain.lower() in tech:
                        total_score += metrics['score']
                        matched_domains.append(domain)

            # Normalize score to 0-100
            if total_score > 0:
                confidence = min(100.0, total_score / len(mentioned_techs) if mentioned_techs else total_score)
                user_scores.append((user_id, confidence, matched_domains))

        # Sort by confidence (descending)
        user_scores.sort(key=lambda x: x[1], reverse=True)

        return user_scores[:5]  # Top 5 experts

    async def get_recent_deployments(self, days: int = 7) -> List[Dict]:
        """Get recent deployments (merged PRs)"""
        deployments = []
        since = datetime.utcnow() - timedelta(days=days)

        repos = self.get_repos()

        for repo in repos:
            try:
                prs = repo.get_pulls(state='closed', sort='updated', direction='desc')

                for pr in prs:
                    if pr.merged and pr.merged_at and pr.merged_at >= since:
                        deployments.append({
                            'user': pr.user.login if pr.user else 'unknown',
                            'repo': repo.name,
                            'title': pr.title,
                            'merged_at': pr.merged_at,
                            'pr_number': pr.number
                        })

            except GithubException as e:
                logger.error(f"Error fetching deployments from {repo.name}: {e}")
                continue

        # Sort by merge time (most recent first)
        deployments.sort(key=lambda x: x['merged_at'], reverse=True)

        return deployments
