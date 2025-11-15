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
            query = select(Standup).where(Standup.timestamp >= since)

            if user_id:
                query = query.where(Standup.user_id == user_id)

            query = query.order_by(Standup.timestamp.desc())

            result = await session.execute(query)
            standups = result.scalars().all()

            return [
                {
                    "user_id": s.user_id,
                    "user_name": s.user_id,  # TODO: Join with user table
                    "message": s.message,
                    "date": s.date,
                    "timestamp": s.timestamp,
                    "parsed_data": s.parsed_data
                }
                for s in standups
            ]
