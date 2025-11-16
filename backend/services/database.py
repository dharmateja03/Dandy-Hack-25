"""
Database Service using SQLAlchemy
Handles structured data: users, tasks, help requests, hierarchy
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, ForeignKey,
    Text, Enum, Float, select, func
)
from sqlalchemy.dialects.postgresql import JSON
import enum

logger = logging.getLogger(__name__)

Base = declarative_base()


# Enums
class UserRole(enum.Enum):
    INTERN = "intern"
    DEVELOPER = "developer"
    SENIOR_DEVELOPER = "senior_developer"
    TECH_LEAD = "tech_lead"
    MANAGER = "manager"


class TaskStatus(enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class HelpRequestStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


# Models
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)  # Slack user ID
    name = Column(String, nullable=False)
    email = Column(String)
    role = Column(Enum(UserRole), default=UserRole.DEVELOPER)
    manager_id = Column(String, ForeignKey("users.id"))
    team = Column(String)
    slack_user_id = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Expertise and preferences
    expertise_tags = Column(JSON)  # List of skills/topics
    timezone = Column(String, default="UTC")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    assignee_id = Column(String, ForeignKey("users.id"))
    status = Column(Enum(TaskStatus), default=TaskStatus.NOT_STARTED)
    priority = Column(String)  # low, medium, high
    progress_percentage = Column(Integer, default=0)

    # External integrations
    jira_id = Column(String, unique=True)
    github_issue_id = Column(String)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    due_date = Column(DateTime)

    # Dependencies
    blocked_by_task_id = Column(Integer, ForeignKey("tasks.id"))


class Standup(Base):
    __tablename__ = "standups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    parsed_data = Column(JSON)  # Gemini-parsed structured data
    timestamp = Column(DateTime, default=datetime.utcnow)
    date = Column(String)  # YYYY-MM-DD for easy grouping


class HelpRequest(Base):
    __tablename__ = "help_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(String, ForeignKey("users.id"))
    task_id = Column(Integer, ForeignKey("tasks.id"))

    topic = Column(String, nullable=False)
    context = Column(Text)
    urgency = Column(String, default="medium")  # low, medium, high
    status = Column(Enum(HelpRequestStatus), default=HelpRequestStatus.PENDING)

    # Slack thread for 3-person group chat
    slack_thread_id = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime)
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)


class BlockerAlert(Base):
    __tablename__ = "blocker_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    manager_id = Column(String, ForeignKey("users.id"))
    task_id = Column(Integer, ForeignKey("tasks.id"))

    description = Column(Text, nullable=False)
    severity = Column(String, default="medium")  # low, medium, high
    is_resolved = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    reminder_type = Column(String)  # standup, help_request_response, task_update
    message = Column(Text)
    related_id = Column(Integer)  # ID of related entity

    scheduled_for = Column(DateTime, nullable=False)
    sent_at = Column(DateTime)
    is_sent = Column(Boolean, default=False)


class GitHubCommit(Base):
    __tablename__ = "github_commits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sha = Column(String, unique=True, nullable=False)
    user_id = Column(String, ForeignKey("users.id"))
    github_username = Column(String, nullable=False)

    repo_name = Column(String, nullable=False)
    message = Column(Text)
    files_changed = Column(JSON)  # List of changed files
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)

    commit_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class GitHubPullRequest(Base):
    __tablename__ = "github_pull_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pr_number = Column(Integer, nullable=False)
    repo_name = Column(String, nullable=False)

    user_id = Column(String, ForeignKey("users.id"))
    github_username = Column(String, nullable=False)

    title = Column(String, nullable=False)
    state = Column(String)  # open, closed, merged
    merged = Column(Boolean, default=False)

    created_at_github = Column(DateTime)
    merged_at = Column(DateTime)
    closed_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class GitHubReview(Base):
    __tablename__ = "github_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(String, unique=True)
    pr_number = Column(Integer, nullable=False)
    repo_name = Column(String, nullable=False)

    user_id = Column(String, ForeignKey("users.id"))
    github_username = Column(String, nullable=False)

    state = Column(String)  # APPROVED, CHANGES_REQUESTED, COMMENTED
    submitted_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)


class UserExpertise(Base):
    __tablename__ = "user_expertise"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Expertise domains
    domain = Column(String, nullable=False)  # e.g., "python", "react", "docker"
    score = Column(Float, default=0.0)  # 0-100

    # Evidence
    commit_count = Column(Integer, default=0)
    pr_count = Column(Integer, default=0)
    review_count = Column(Integer, default=0)
    help_count = Column(Integer, default=0)  # Times helped others

    # Metadata
    last_activity = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class CollaborationMetric(Base):
    __tablename__ = "collaboration_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Collaboration scores
    help_requests_received = Column(Integer, default=0)
    help_requests_resolved = Column(Integer, default=0)
    avg_resolution_time_minutes = Column(Float, default=0.0)

    code_reviews_given = Column(Integer, default=0)
    code_reviews_received = Column(Integer, default=0)

    # Cross-team collaboration
    teams_collaborated_with = Column(JSON)  # List of team names

    # Time period
    week_start = Column(String)  # YYYY-MM-DD format

    created_at = Column(DateTime, default=datetime.utcnow)


class MeetingEvent(Base):
    __tablename__ = "meeting_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, unique=True)  # Google Calendar event ID

    title = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer)

    attendees = Column(JSON)  # List of user IDs
    organizer_id = Column(String, ForeignKey("users.id"))

    was_necessary = Column(Boolean)  # AI determination
    could_be_async = Column(Boolean)

    created_at = Column(DateTime, default=datetime.utcnow)


class HelpInboxThread(Base):
    __tablename__ = "help_inbox_threads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    help_request_id = Column(Integer, ForeignKey("help_requests.id"), nullable=False)

    # Slack thread info
    expert_dm_channel_id = Column(String)  # Expert's Help Inbox DM channel
    thread_ts = Column(String, unique=True)  # Slack thread timestamp

    # Participants (sender is auto-added to thread only)
    sender_id = Column(String, ForeignKey("users.id"), nullable=False)
    expert_id = Column(String, ForeignKey("users.id"), nullable=False)
    additional_experts = Column(JSON)  # For multi-expert threads

    # Status
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)


# Database Service
class DatabaseService:
    """Manages all structured data in PostgreSQL"""

    def __init__(self, database_url: str):
        # Convert to async URL if needed
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

        self.database_url = database_url
        self.engine = None
        self.async_session = None

    async def initialize(self):
        """Initialize database connection and create tables"""
        try:
            self.engine = create_async_engine(
                self.database_url,
                echo=False,  # Set to True for SQL logging
                future=True
            )

            self.async_session = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def close(self):
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()

    async def health_check(self) -> str:
        """Check database health"""
        try:
            async with self.async_session() as session:
                result = await session.execute(select(func.count(User.id)))
                user_count = result.scalar()
                return f"healthy ({user_count} users)"
        except Exception as e:
            return f"unhealthy: {str(e)}"

    # User operations
    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if user:
                return {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role.value if user.role else None,
                    "manager_id": user.manager_id,
                    "team": user.team,
                    "expertise_tags": user.expertise_tags or []
                }
            return None

    async def create_user(self, user_data: Dict) -> str:
        """Create a new user"""
        async with self.async_session() as session:
            user = User(**user_data)
            session.add(user)
            await session.commit()
            return user.id

    # Task operations
    async def get_user_tasks(
        self,
        user_id: str,
        status: Optional[TaskStatus] = None
    ) -> List[Dict]:
        """Get tasks for a user"""
        async with self.async_session() as session:
            query = select(Task).where(Task.assignee_id == user_id)

            if status:
                query = query.where(Task.status == status)

            result = await session.execute(query)
            tasks = result.scalars().all()

            return [
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status.value if task.status else None,
                    "priority": task.priority,
                    "progress_percentage": task.progress_percentage,
                    "jira_id": task.jira_id
                }
                for task in tasks
            ]

    async def get_all_tasks(self) -> List[Dict]:
        """Get all tasks for dashboard"""
        async with self.async_session() as session:
            result = await session.execute(select(Task))
            tasks = result.scalars().all()

            return [
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "assignee_id": task.assignee_id,
                    "status": task.status.value if task.status else None,
                    "priority": task.priority,
                    "progress_percentage": task.progress_percentage,
                    "jira_id": task.jira_id,
                    "created_at": task.created_at.isoformat() if task.created_at else None
                }
                for task in tasks
            ]

    async def update_task_status(
        self,
        user_id: str,
        task_name: str,
        status: str,
        progress: Optional[int] = None
    ):
        """Update task status"""
        async with self.async_session() as session:
            # Find task by name and user
            result = await session.execute(
                select(Task).where(
                    Task.assignee_id == user_id,
                    Task.title.ilike(f"%{task_name}%")
                )
            )
            task = result.scalar_one_or_none()

            if task:
                if status:
                    task.status = TaskStatus[status.upper()]
                if progress is not None:
                    task.progress_percentage = progress

                if status == "in_progress" and not task.started_at:
                    task.started_at = datetime.utcnow()
                elif status == "completed":
                    task.completed_at = datetime.utcnow()
                    task.progress_percentage = 100

                await session.commit()

    async def get_user_workload(self, user_id: str) -> int:
        """Get number of active tasks for a user"""
        async with self.async_session() as session:
            result = await session.execute(
                select(func.count(Task.id)).where(
                    Task.assignee_id == user_id,
                    Task.status.in_([TaskStatus.IN_PROGRESS, TaskStatus.NOT_STARTED])
                )
            )
            return result.scalar() or 0

    # Help request operations
    async def create_help_request(
        self,
        from_user: str,
        to_user: str,
        topic: str,
        context: str,
        urgency: str
    ) -> int:
        """Create a help request"""
        async with self.async_session() as session:
            help_req = HelpRequest(
                from_user_id=from_user,
                to_user_id=to_user,
                topic=topic,
                context=context,
                urgency=urgency
            )
            session.add(help_req)
            await session.commit()
            return help_req.id

    # Blocker operations
    async def create_blocker_alert(
        self,
        user_id: str,
        manager_id: str,
        blocker_description: str,
        severity: str
    ):
        """Create a blocker alert"""
        async with self.async_session() as session:
            alert = BlockerAlert(
                user_id=user_id,
                manager_id=manager_id,
                description=blocker_description,
                severity=severity
            )
            session.add(alert)
            await session.commit()

    # Standup operations
    async def save_standup(
        self,
        user_id: str,
        message: str,
        parsed_data: Dict
    ):
        """Save standup to database"""
        async with self.async_session() as session:
            standup = Standup(
                user_id=user_id,
                message=message,
                parsed_data=parsed_data,
                date=datetime.utcnow().strftime("%Y-%m-%d")
            )
            session.add(standup)
            await session.commit()

    async def get_recent_standups(
        self,
        days: int = 7,
        user_id: Optional[str] = None
    ) -> List[Dict]:
        """Get recent standups"""
        async with self.async_session() as session:
            since = datetime.utcnow() - timedelta(days=days)

            # Get standups
            query = select(Standup).where(Standup.timestamp >= since)

            if user_id:
                query = query.where(Standup.user_id == user_id)

            query = query.order_by(Standup.timestamp.desc())

            result = await session.execute(query)
            standups_list = result.scalars().all()

            # For each standup, try to get user name, fallback to user_id if not found
            standups_with_names = []
            for s in standups_list:
                # Try to find user by ID first
                user_result = await session.execute(
                    select(User).where(User.id == s.user_id)
                )
                user = user_result.scalar()

                # If not found by ID, try by slack_user_id
                if not user:
                    user_result = await session.execute(
                        select(User).where(User.slack_user_id == s.user_id)
                    )
                    user = user_result.scalar()

                # Use actual user name if found, otherwise use user_id as fallback
                user_name = user.name if user else s.user_id

                standups_with_names.append({
                    "user_id": s.user_id,
                    "user_name": user_name,
                    "message": s.message,
                    "date": s.date,
                    "timestamp": s.timestamp,
                    "parsed_data": s.parsed_data
                })

            return standups_with_names

    # ========== SCHEDULER SUPPORT METHODS ==========

    async def get_all_active_users(self) -> List[Dict]:
        """Get all active users"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.is_active == True)
            )
            users = result.scalars().all()

            return [
                {
                    "id": u.id,
                    "name": u.name,
                    "email": u.email,
                    "role": u.role.value if u.role else None,
                    "slack_user_id": u.slack_user_id
                }
                for u in users
            ]

    async def user_has_standup_today(self, user_id: str, date: str) -> bool:
        """Check if user has submitted standup for given date"""
        async with self.async_session() as session:
            result = await session.execute(
                select(func.count(Standup.id)).where(
                    Standup.user_id == user_id,
                    Standup.date == date
                )
            )
            count = result.scalar()
            return count > 0

    async def create_reminder(
        self,
        user_id: str,
        reminder_type: str,
        message: str,
        scheduled_for: datetime,
        related_id: Optional[int] = None
    ):
        """Create a reminder"""
        async with self.async_session() as session:
            reminder = Reminder(
                user_id=user_id,
                reminder_type=reminder_type,
                message=message,
                scheduled_for=scheduled_for,
                related_id=related_id
            )
            session.add(reminder)
            await session.commit()

    async def get_pending_reminders(self) -> List[Dict]:
        """Get all pending reminders that should be sent now"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Reminder).where(
                    Reminder.is_sent == False,
                    Reminder.scheduled_for <= datetime.utcnow()
                )
            )
            reminders = result.scalars().all()

            return [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "reminder_type": r.reminder_type,
                    "message": r.message,
                    "related_id": r.related_id
                }
                for r in reminders
            ]

    async def mark_reminder_sent(self, reminder_id: int):
        """Mark reminder as sent"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Reminder).where(Reminder.id == reminder_id)
            )
            reminder = result.scalar_one_or_none()

            if reminder:
                reminder.is_sent = True
                reminder.sent_at = datetime.utcnow()
                await session.commit()

    async def get_stale_help_requests(self, hours: int = 6) -> List[Dict]:
        """Get help requests with no response for X hours"""
        async with self.async_session() as session:
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            result = await session.execute(
                select(HelpRequest).where(
                    HelpRequest.status == HelpRequestStatus.PENDING,
                    HelpRequest.created_at <= cutoff
                )
            )
            requests = result.scalars().all()

            return [
                {
                    "id": req.id,
                    "from_user_id": req.from_user_id,
                    "from_user_name": req.from_user_id,  # TODO: Join
                    "to_user_id": req.to_user_id,
                    "topic": req.topic,
                    "created_at": req.created_at
                }
                for req in requests
            ]

    async def get_long_standing_blockers(self, days: int = 2) -> List[Dict]:
        """Get blockers that have been active for X days"""
        async with self.async_session() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)

            result = await session.execute(
                select(BlockerAlert).where(
                    BlockerAlert.is_resolved == False,
                    BlockerAlert.created_at <= cutoff
                )
            )
            blockers = result.scalars().all()

            return [
                {
                    "id": b.id,
                    "user_id": b.user_id,
                    "user_name": b.user_id,  # TODO: Join
                    "manager_id": b.manager_id,
                    "description": b.description,
                    "severity": b.severity,
                    "created_at": b.created_at
                }
                for b in blockers
            ]

    async def get_users_by_role(self, role: str) -> List[Dict]:
        """Get all users with a specific role"""
        async with self.async_session() as session:
            role_enum = UserRole[role.upper()]

            result = await session.execute(
                select(User).where(
                    User.role == role_enum,
                    User.is_active == True
                )
            )
            users = result.scalars().all()

            return [
                {
                    "id": u.id,
                    "name": u.name,
                    "email": u.email,
                    "slack_user_id": u.slack_user_id
                }
                for u in users
            ]

    # ========== JIRA INTEGRATION METHODS ==========

    async def get_task_by_jira_id(self, jira_id: str) -> Optional[Dict]:
        """Get task by Jira ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Task).where(Task.jira_id == jira_id)
            )
            task = result.scalar_one_or_none()

            if task:
                return {
                    "id": task.id,
                    "title": task.title,
                    "jira_id": task.jira_id,
                    "status": task.status.value if task.status else None
                }
            return None

    async def create_task(self, task_data: Dict) -> int:
        """Create a new task"""
        async with self.async_session() as session:
            task = Task(**task_data)
            session.add(task)
            await session.commit()
            return task.id

    async def update_task(self, task_id: int, **kwargs):
        """Update task fields"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()

            if task:
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)

                await session.commit()

    # ========== GITHUB INTEGRATION METHODS ==========

    async def save_github_commit(self, commit_data: Dict) -> int:
        """Save GitHub commit"""
        async with self.async_session() as session:
            # Check if commit already exists
            result = await session.execute(
                select(GitHubCommit).where(GitHubCommit.sha == commit_data['sha'])
            )
            existing = result.scalar_one_or_none()

            if existing:
                return existing.id

            commit = GitHubCommit(**commit_data)
            session.add(commit)
            await session.commit()
            return commit.id

    async def save_github_pr(self, pr_data: Dict) -> int:
        """Save GitHub PR"""
        async with self.async_session() as session:
            # Check if PR already exists
            result = await session.execute(
                select(GitHubPullRequest).where(
                    GitHubPullRequest.pr_number == pr_data['pr_number'],
                    GitHubPullRequest.repo_name == pr_data['repo_name']
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing PR
                for key, value in pr_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                await session.commit()
                return existing.id

            pr = GitHubPullRequest(**pr_data)
            session.add(pr)
            await session.commit()
            return pr.id

    async def save_github_review(self, review_data: Dict) -> int:
        """Save GitHub review"""
        async with self.async_session() as session:
            result = await session.execute(
                select(GitHubReview).where(
                    GitHubReview.review_id == review_data['review_id']
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                return existing.id

            review = GitHubReview(**review_data)
            session.add(review)
            await session.commit()
            return review.id

    async def get_user_commits(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get user's recent commits"""
        async with self.async_session() as session:
            since = datetime.utcnow() - timedelta(days=days)
            result = await session.execute(
                select(GitHubCommit).where(
                    GitHubCommit.user_id == user_id,
                    GitHubCommit.commit_date >= since
                ).order_by(GitHubCommit.commit_date.desc())
            )
            commits = result.scalars().all()

            return [
                {
                    "sha": c.sha,
                    "repo_name": c.repo_name,
                    "message": c.message,
                    "files_changed": c.files_changed,
                    "additions": c.additions,
                    "deletions": c.deletions,
                    "commit_date": c.commit_date
                }
                for c in commits
            ]

    async def get_user_prs(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get user's recent PRs"""
        async with self.async_session() as session:
            since = datetime.utcnow() - timedelta(days=days)
            result = await session.execute(
                select(GitHubPullRequest).where(
                    GitHubPullRequest.user_id == user_id,
                    GitHubPullRequest.created_at_github >= since
                ).order_by(GitHubPullRequest.created_at_github.desc())
            )
            prs = result.scalars().all()

            return [
                {
                    "pr_number": pr.pr_number,
                    "repo_name": pr.repo_name,
                    "title": pr.title,
                    "state": pr.state,
                    "merged": pr.merged,
                    "created_at": pr.created_at_github,
                    "merged_at": pr.merged_at
                }
                for pr in prs
            ]

    async def get_user_reviews(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get user's recent code reviews"""
        async with self.async_session() as session:
            since = datetime.utcnow() - timedelta(days=days)
            result = await session.execute(
                select(GitHubReview).where(
                    GitHubReview.user_id == user_id,
                    GitHubReview.submitted_at >= since
                ).order_by(GitHubReview.submitted_at.desc())
            )
            reviews = result.scalars().all()

            return [
                {
                    "pr_number": r.pr_number,
                    "repo_name": r.repo_name,
                    "state": r.state,
                    "submitted_at": r.submitted_at
                }
                for r in reviews
            ]

    # ========== EXPERTISE METHODS ==========

    async def update_user_expertise(
        self,
        user_id: str,
        domain: str,
        score: float,
        commit_count: int = 0,
        pr_count: int = 0,
        review_count: int = 0,
        help_count: int = 0
    ):
        """Update or create user expertise in a domain"""
        async with self.async_session() as session:
            result = await session.execute(
                select(UserExpertise).where(
                    UserExpertise.user_id == user_id,
                    UserExpertise.domain == domain
                )
            )
            expertise = result.scalar_one_or_none()

            if expertise:
                expertise.score = score
                expertise.commit_count += commit_count
                expertise.pr_count += pr_count
                expertise.review_count += review_count
                expertise.help_count += help_count
                expertise.last_activity = datetime.utcnow()
                expertise.updated_at = datetime.utcnow()
            else:
                expertise = UserExpertise(
                    user_id=user_id,
                    domain=domain,
                    score=score,
                    commit_count=commit_count,
                    pr_count=pr_count,
                    review_count=review_count,
                    help_count=help_count,
                    last_activity=datetime.utcnow()
                )
                session.add(expertise)

            await session.commit()

    async def get_user_expertise(self, user_id: str) -> List[Dict]:
        """Get all expertise domains for a user"""
        async with self.async_session() as session:
            result = await session.execute(
                select(UserExpertise).where(
                    UserExpertise.user_id == user_id
                ).order_by(UserExpertise.score.desc())
            )
            expertise_list = result.scalars().all()

            return [
                {
                    "domain": e.domain,
                    "score": e.score,
                    "commit_count": e.commit_count,
                    "pr_count": e.pr_count,
                    "review_count": e.review_count,
                    "help_count": e.help_count,
                    "last_activity": e.last_activity
                }
                for e in expertise_list
            ]

    async def find_expert(self, domain: str, limit: int = 5) -> List[Dict]:
        """Find users with expertise in a domain"""
        async with self.async_session() as session:
            result = await session.execute(
                select(UserExpertise, User).join(
                    User, UserExpertise.user_id == User.id
                ).where(
                    UserExpertise.domain.ilike(f"%{domain}%"),
                    User.is_active == True
                ).order_by(UserExpertise.score.desc()).limit(limit)
            )
            results = result.all()

            return [
                {
                    "user_id": expertise.user_id,
                    "user_name": user.name,
                    "domain": expertise.domain,
                    "score": expertise.score,
                    "commit_count": expertise.commit_count,
                    "pr_count": expertise.pr_count,
                    "review_count": expertise.review_count,
                    "help_count": expertise.help_count
                }
                for expertise, user in results
            ]

    # ========== COLLABORATION METRICS ==========

    async def update_collaboration_metrics(self, user_id: str, week_start: str, **metrics):
        """Update collaboration metrics for a user in a given week"""
        async with self.async_session() as session:
            result = await session.execute(
                select(CollaborationMetric).where(
                    CollaborationMetric.user_id == user_id,
                    CollaborationMetric.week_start == week_start
                )
            )
            metric = result.scalar_one_or_none()

            if metric:
                for key, value in metrics.items():
                    if hasattr(metric, key):
                        setattr(metric, key, value)
            else:
                metric = CollaborationMetric(
                    user_id=user_id,
                    week_start=week_start,
                    **metrics
                )
                session.add(metric)

            await session.commit()

    async def get_collaboration_metrics(self, user_id: str, weeks: int = 4) -> List[Dict]:
        """Get collaboration metrics for a user"""
        async with self.async_session() as session:
            result = await session.execute(
                select(CollaborationMetric).where(
                    CollaborationMetric.user_id == user_id
                ).order_by(CollaborationMetric.week_start.desc()).limit(weeks)
            )
            metrics = result.scalars().all()

            return [
                {
                    "week_start": m.week_start,
                    "help_requests_received": m.help_requests_received,
                    "help_requests_resolved": m.help_requests_resolved,
                    "avg_resolution_time_minutes": m.avg_resolution_time_minutes,
                    "code_reviews_given": m.code_reviews_given,
                    "code_reviews_received": m.code_reviews_received,
                    "teams_collaborated_with": m.teams_collaborated_with
                }
                for m in metrics
            ]

    # ========== HELP INBOX METHODS ==========

    async def create_help_inbox_thread(
        self,
        help_request_id: int,
        sender_id: str,
        expert_id: str,
        expert_dm_channel_id: str,
        thread_ts: str,
        additional_experts: Optional[List[str]] = None
    ) -> int:
        """Create a help inbox thread"""
        async with self.async_session() as session:
            thread = HelpInboxThread(
                help_request_id=help_request_id,
                sender_id=sender_id,
                expert_id=expert_id,
                expert_dm_channel_id=expert_dm_channel_id,
                thread_ts=thread_ts,
                additional_experts=additional_experts or []
            )
            session.add(thread)
            await session.commit()
            return thread.id

    async def get_expert_inbox_threads(self, expert_id: str, active_only: bool = True) -> List[Dict]:
        """Get all threads in an expert's help inbox"""
        async with self.async_session() as session:
            query = select(HelpInboxThread, HelpRequest).join(
                HelpRequest, HelpInboxThread.help_request_id == HelpRequest.id
            ).where(HelpInboxThread.expert_id == expert_id)

            if active_only:
                query = query.where(HelpInboxThread.is_active == True)

            result = await session.execute(query.order_by(HelpInboxThread.created_at.desc()))
            results = result.all()

            return [
                {
                    "thread_id": thread.id,
                    "thread_ts": thread.thread_ts,
                    "sender_id": thread.sender_id,
                    "help_request_id": thread.help_request_id,
                    "topic": help_req.topic,
                    "context": help_req.context,
                    "status": help_req.status.value,
                    "created_at": thread.created_at,
                    "is_active": thread.is_active
                }
                for thread, help_req in results
            ]

    async def resolve_help_inbox_thread(self, thread_id: int, resolution_notes: str = ""):
        """Mark a help inbox thread as resolved"""
        async with self.async_session() as session:
            # Get thread
            result = await session.execute(
                select(HelpInboxThread).where(HelpInboxThread.id == thread_id)
            )
            thread = result.scalar_one_or_none()

            if thread:
                thread.is_active = False
                thread.resolved_at = datetime.utcnow()

                # Update help request status
                help_result = await session.execute(
                    select(HelpRequest).where(HelpRequest.id == thread.help_request_id)
                )
                help_req = help_result.scalar_one_or_none()

                if help_req:
                    help_req.status = HelpRequestStatus.RESOLVED
                    help_req.resolved_at = datetime.utcnow()
                    help_req.resolution_notes = resolution_notes

                await session.commit()

    # ========== MEETING METHODS ==========

    async def save_meeting_event(self, event_data: Dict) -> int:
        """Save a meeting event from calendar"""
        async with self.async_session() as session:
            result = await session.execute(
                select(MeetingEvent).where(
                    MeetingEvent.event_id == event_data['event_id']
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                for key, value in event_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                await session.commit()
                return existing.id

            meeting = MeetingEvent(**event_data)
            session.add(meeting)
            await session.commit()
            return meeting.id

    async def get_user_meetings(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get user's meeting history"""
        async with self.async_session() as session:
            since = datetime.utcnow() - timedelta(days=days)
            result = await session.execute(
                select(MeetingEvent).where(
                    MeetingEvent.start_time >= since
                ).order_by(MeetingEvent.start_time.desc())
            )
            all_meetings = result.scalars().all()

            # Filter meetings where user is an attendee
            user_meetings = [
                m for m in all_meetings
                if m.attendees and user_id in m.attendees
            ]

            return [
                {
                    "event_id": m.event_id,
                    "title": m.title,
                    "start_time": m.start_time,
                    "end_time": m.end_time,
                    "duration_minutes": m.duration_minutes,
                    "attendees": m.attendees,
                    "was_necessary": m.was_necessary,
                    "could_be_async": m.could_be_async
                }
                for m in user_meetings
            ]
