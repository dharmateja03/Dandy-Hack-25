"""
Scheduler Service using APScheduler
Handles daily standup reminders and recurring tasks
"""

import logging
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import httpx

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Manages scheduled tasks for MCP

    Features:
    - Daily standup reminders
    - Help request follow-ups
    - Blocker escalation
    - Weekly summaries
    """

    def __init__(self, mcp_core, slack_webhook_url: str = None):
        self.scheduler = AsyncIOScheduler()
        self.mcp_core = mcp_core
        self.slack_webhook_url = slack_webhook_url
        self.http_client = httpx.AsyncClient()

    async def initialize(self):
        """Start the scheduler with all jobs"""
        logger.info("Initializing scheduler...")

        # Daily standup reminder at 9 AM
        self.scheduler.add_job(
            self.send_daily_standup_reminders,
            CronTrigger(hour=9, minute=0),
            id='daily_standup',
            name='Daily Standup Reminder',
            replace_existing=True
        )

        # Check for stale help requests every 6 hours
        self.scheduler.add_job(
            self.check_stale_help_requests,
            CronTrigger(hour='*/6'),
            id='check_help_requests',
            name='Check Stale Help Requests',
            replace_existing=True
        )

        # Escalate long-standing blockers every 12 hours
        self.scheduler.add_job(
            self.escalate_blockers,
            CronTrigger(hour='*/12'),
            id='escalate_blockers',
            name='Escalate Blockers',
            replace_existing=True
        )

        # Weekly summary on Friday at 4 PM
        self.scheduler.add_job(
            self.send_weekly_summary,
            CronTrigger(day_of_week='fri', hour=16, minute=0),
            id='weekly_summary',
            name='Weekly Team Summary',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("✅ Scheduler started successfully")

    async def shutdown(self):
        """Shutdown scheduler gracefully"""
        self.scheduler.shutdown()
        await self.http_client.aclose()
        logger.info("Scheduler shut down")

    # ========== SCHEDULED JOBS ==========

    async def send_daily_standup_reminders(self):
        """
        Send standup reminders to all active users at 9 AM

        Checks who hasn't submitted standup yet today
        """
        logger.info("Sending daily standup reminders...")

        try:
            # Get all active users
            users = await self.mcp_core.database.get_all_active_users()

            today = datetime.utcnow().strftime("%Y-%m-%d")

            for user in users:
                # Check if user already submitted standup today
                has_standup = await self.mcp_core.database.user_has_standup_today(
                    user['id'], today
                )

                if not has_standup:
                    await self.send_standup_reminder_to_user(user['id'])

            logger.info(f"Sent standup reminders to users without standup")

        except Exception as e:
            logger.error(f"Error sending standup reminders: {e}")

    async def send_standup_reminder_to_user(self, user_id: str):
        """Send standup reminder to specific user via Slack"""
        # This will be called by Slack bot
        # For now, create a reminder in database
        await self.mcp_core.database.create_reminder(
            user_id=user_id,
            reminder_type='standup',
            message="Time for your daily standup! Use /standup or just DM me your update.",
            scheduled_for=datetime.utcnow()
        )

    async def check_stale_help_requests(self):
        """
        Check for help requests that haven't been responded to

        If no response in 6 hours, remind the helper
        If no response in 24 hours, escalate to manager
        """
        logger.info("Checking stale help requests...")

        try:
            stale_requests = await self.mcp_core.database.get_stale_help_requests(
                hours=6
            )

            for req in stale_requests:
                hours_pending = (datetime.utcnow() - req['created_at']).total_seconds() / 3600

                if hours_pending < 24:
                    # Remind helper
                    await self.mcp_core.database.create_reminder(
                        user_id=req['to_user_id'],
                        reminder_type='help_request_response',
                        message=f"Reminder: {req['from_user_name']} needs help with {req['topic']}",
                        related_id=req['id'],
                        scheduled_for=datetime.utcnow()
                    )
                else:
                    # Escalate to manager
                    from_user = await self.mcp_core.database.get_user(req['from_user_id'])
                    if from_user.get('manager_id'):
                        await self.mcp_core.database.create_reminder(
                            user_id=from_user['manager_id'],
                            reminder_type='help_request_escalation',
                            message=f"⚠️ Help request from {req['from_user_name']} " +
                                  f"pending for 24+ hours: {req['topic']}",
                            related_id=req['id'],
                            scheduled_for=datetime.utcnow()
                        )

            logger.info(f"Processed {len(stale_requests)} stale help requests")

        except Exception as e:
            logger.error(f"Error checking help requests: {e}")

    async def escalate_blockers(self):
        """
        Escalate blockers that have been active for too long

        - 2+ days: Notify manager
        - 5+ days: Flag as critical
        """
        logger.info("Checking long-standing blockers...")

        try:
            long_blockers = await self.mcp_core.database.get_long_standing_blockers(
                days=2
            )

            for blocker in long_blockers:
                days_blocked = (datetime.utcnow() - blocker['created_at']).days

                severity = 'critical' if days_blocked >= 5 else 'high'

                # Notify manager
                if blocker.get('manager_id'):
                    await self.mcp_core.database.create_reminder(
                        user_id=blocker['manager_id'],
                        reminder_type='blocker_escalation',
                        message=f"🚨 {blocker['user_name']} blocked for {days_blocked} days: " +
                              f"{blocker['description']} (Severity: {severity})",
                        related_id=blocker['id'],
                        scheduled_for=datetime.utcnow()
                    )

            logger.info(f"Escalated {len(long_blockers)} long-standing blockers")

        except Exception as e:
            logger.error(f"Error escalating blockers: {e}")

    async def send_weekly_summary(self):
        """
        Generate and send weekly summary to managers on Friday 4 PM
        """
        logger.info("Generating weekly summary...")

        try:
            # Get all managers
            managers = await self.mcp_core.database.get_users_by_role('manager')

            for manager in managers:
                # Generate summary for manager's team
                summary = await self.mcp_core.generate_summary(
                    user_id=None,  # All team
                    days=7
                )

                # Create reminder (will be sent by Slack bot)
                await self.mcp_core.database.create_reminder(
                    user_id=manager['id'],
                    reminder_type='weekly_summary',
                    message=f"📊 Weekly Team Summary:\n\n{summary}",
                    scheduled_for=datetime.utcnow()
                )

            logger.info(f"Generated weekly summaries for {len(managers)} managers")

        except Exception as e:
            logger.error(f"Error generating weekly summary: {e}")

    # ========== MANUAL TRIGGERS ==========

    async def schedule_reminder(
        self,
        user_id: str,
        message: str,
        delay_minutes: int = 60
    ):
        """Schedule a one-time reminder"""
        from datetime import timedelta

        scheduled_time = datetime.utcnow() + timedelta(minutes=delay_minutes)

        await self.mcp_core.database.create_reminder(
            user_id=user_id,
            reminder_type='manual',
            message=message,
            scheduled_for=scheduled_time
        )

        logger.info(f"Scheduled reminder for {user_id} at {scheduled_time}")
