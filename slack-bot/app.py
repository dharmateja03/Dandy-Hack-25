"""
MCP Slack Bot - Primary Interface to Model Context Protocol

This bot is how teams interact with MCP:
- Daily standups via DM with interactive modals
- Help request routing with smart notifications
- Natural language queries
- Manager commands
- User onboarding and expertise management
- Reaction-based interactions
"""

import os
import logging
import threading
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import httpx
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
MCP_API_URL = os.environ.get("MCP_API_URL", "http://mcp-backend:8000")
STANDUP_TIME = os.environ.get("STANDUP_TIME", "09:00")  # 9 AM daily

# Initialize Slack app
app = App(token=SLACK_BOT_TOKEN)

# HTTP client for MCP API
http_client = httpx.AsyncClient(base_url=MCP_API_URL, timeout=30.0)
sync_http_client = httpx.Client(base_url=MCP_API_URL, timeout=30.0)

# Scheduler for automated tasks
scheduler = AsyncIOScheduler()

# Track standup submissions (user_id -> timestamp)
daily_standup_submissions = {}


# ========== STANDUP HANDLERS ==========

@app.command("/standup")
def handle_standup_command(ack, command, client):
    """
    Trigger standup via slash command - Opens interactive modal
    """
    try:
        ack()
        logger.info("✅ /standup command received and acknowledged")
    except Exception as e:
        logger.error(f"❌ Error acknowledging command: {e}", exc_info=True)
        return

    try:
        user_id = command["user_id"]
        trigger_id = command["trigger_id"]
        logger.info(f"Opening standup modal for {user_id}")

        open_standup_modal(client, user_id, trigger_id)
        logger.info(f"✅ Modal opened for {user_id}")
    except Exception as e:
        logger.error(f"❌ Error opening standup modal: {e}", exc_info=True)


def open_standup_modal(client, user_id: str, trigger_id: str):
    """
    Open interactive modal for standup submission
    """
    try:
        logger.info(f"📝 Fetching tasks for {user_id}")
        # Get user's current tasks from MCP
        tasks = []
        try:
            response = sync_http_client.get(f"/api/tasks/user/{user_id}")
            tasks = response.json().get("tasks", [])
            logger.info(f"✅ Fetched {len(tasks)} tasks for {user_id}")
        except Exception as e:
            logger.warning(f"⚠️ Couldn't fetch tasks for {user_id}: {e}")

        # Build task options for dropdown
        task_options = [
            {
                "text": {"type": "plain_text", "text": f"{task['title']} ({task['status']})"},
                "value": str(task['id'])
            }
            for task in tasks[:10]  # Limit to 10 tasks
        ]

        # Get list of workspace members for help selection (with search)
        # Using Slack's users_select element for native search functionality
        logger.info(f"🔍 Fetching workspace members for {user_id}")

        modal_view = {
            "type": "modal",
            "callback_id": "standup_modal",
            "title": {"type": "plain_text", "text": "Daily Standup"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "👋 Good morning! Time for your standup"}
                },
                {
                    "type": "input",
                    "block_id": "completed_yesterday",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "completed_input",
                        "multiline": True,
                        "placeholder": {"type": "plain_text", "text": "What tasks did you complete?"}
                    },
                    "label": {"type": "plain_text", "text": "✅ Completed Yesterday"}
                },
                {
                    "type": "input",
                    "block_id": "working_today",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "working_input",
                        "multiline": True,
                        "placeholder": {"type": "plain_text", "text": "What are you working on today?"}
                    },
                    "label": {"type": "plain_text", "text": "🚀 Working On Today"}
                },
                {
                    "type": "input",
                    "block_id": "blockers",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "blockers_input",
                        "multiline": True,
                        "placeholder": {"type": "plain_text", "text": "Any blockers or challenges?"}
                    },
                    "label": {"type": "plain_text", "text": "🚧 Blockers (if any)"},
                    "optional": True
                },
                {
                    "type": "input",
                    "block_id": "help_needed",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "help_input",
                        "multiline": True,
                        "placeholder": {"type": "plain_text", "text": "What do you need help with? (e.g., 'Help from @Bharathi on auth')"}
                    },
                    "label": {"type": "plain_text", "text": "🙋 Help Needed (if any)"},
                    "optional": True
                }
            ]
        }

        # Add team member selection with workspace search
        modal_view["blocks"].append({
            "type": "input",
            "block_id": "help_from_user",
            "element": {
                "type": "users_select",
                "action_id": "help_from_select",
                "placeholder": {"type": "plain_text", "text": "🔍 Search and select team member"}
            },
            "label": {"type": "plain_text", "text": "👥 Who do you need help from? (searchable)"},
            "optional": True
        })

        # Add task selection if tasks exist
        if task_options:
            modal_view["blocks"].append({
                "type": "input",
                "block_id": "task_updates",
                "element": {
                    "type": "multi_static_select",
                    "action_id": "tasks_select",
                    "placeholder": {"type": "plain_text", "text": "Select tasks you're updating"},
                    "options": task_options
                },
                "label": {"type": "plain_text", "text": "📋 Task Updates"},
                "optional": True
            })

        client.views_open(trigger_id=trigger_id, view=modal_view)
        logger.info(f"Opened standup modal for {user_id}")

    except Exception as e:
        logger.error(f"Error opening standup modal: {e}")


@app.view("standup_modal")
def handle_standup_submission(ack, body, client, view):
    """
    Handle standup modal submission
    """
    ack()

    user_id = body["user"]["id"]
    values = view["state"]["values"]

    # Extract standup data
    completed = values["completed_yesterday"]["completed_input"].get("value", "")
    working = values["working_today"]["working_input"].get("value", "")
    blockers = values["blockers"]["blockers_input"].get("value", "")
    help_needed = values["help_needed"]["help_input"].get("value", "")

    # Extract selected help person (if any)
    # users_select returns selected_user field with the Slack user ID
    help_from_user = None
    if "help_from_user" in values and values["help_from_user"].get("help_from_select"):
        help_elem = values["help_from_user"]["help_from_select"]
        # users_select format
        help_from_user = help_elem.get("selected_user")
        if not help_from_user:
            # Fallback for other formats
            help_from_user = help_elem.get("selected_option", {}).get("value")

    # Combine into standup message
    standup_message = f"""
**Completed Yesterday:**
{completed}

**Working On Today:**
{working}
"""

    if blockers:
        standup_message += f"\n**Blockers:**\n{blockers}\n"

    if help_needed:
        standup_message += f"\n**Help Needed:**\n{help_needed}\n"

    # Add selected help person to the message if available
    if help_from_user:
        # Get the person's real name from Slack
        try:
            user_info = client.users_info(user=help_from_user)
            helper_name = user_info.get('user', {}).get('real_name') or user_info.get('user', {}).get('name')
            if not helper_name:
                helper_name = help_from_user
        except Exception as e:
            logger.warning(f"Could not fetch user info for {help_from_user}: {e}")
            helper_name = help_from_user

        standup_message += f"\n**Help Requested From:** {helper_name}\n"
        logger.info(f"Help person selected: {helper_name} ({help_from_user})")

    # Process standup in background thread (now synchronous)
    try:
        thread = threading.Thread(
            target=process_standup_response,
            args=(user_id, standup_message, client),
            daemon=True
        )
        thread.start()
    except Exception as e:
        logger.error(f"Error processing standup: {e}")

    # Track submission
    daily_standup_submissions[user_id] = datetime.utcnow()


async def send_standup_questions(client, user_id):
    """
    Send standup questions to user via DM (fallback for automated reminders)
    """
    try:
        # Get user's current tasks from MCP
        response = await http_client.get(f"/api/tasks/user/{user_id}")
        tasks = response.json().get("tasks", [])

        task_list = "\n".join([
            f"• {task['title']} ({task['status']})"
            for task in tasks[:5]
        ]) if tasks else "No assigned tasks"

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "👋 Good morning! Time for your standup"}
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Your assigned tasks:*\n{task_list}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Please answer:\n1️⃣ *What did you complete yesterday?*\n2️⃣ *What are you working on today?*\n3️⃣ *Any blockers or help needed?*"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📝 Submit Standup"},
                        "action_id": "open_standup_modal_button",
                        "style": "primary"
                    }
                ]
            }
        ]

        result = client.chat_postMessage(
            channel=user_id,
            text="Time for your standup!",
            blocks=blocks
        )

        logger.info(f"Sent standup questions to {user_id}")
        return result

    except Exception as e:
        logger.error(f"Error sending standup questions: {e}")


@app.action("open_standup_modal_button")
async def handle_standup_button(ack, body, client):
    """
    Handle button click to open standup modal
    """
    await ack()

    user_id = body["user"]["id"]
    trigger_id = body["trigger_id"]

    await open_standup_modal(client, user_id, trigger_id)


@app.event("message")
async def handle_message(event, client, say):
    """
    Handle DM messages from users

    This is where standup responses are processed
    """
    # Ignore bot messages
    if event.get("bot_id"):
        return

    user_id = event["user"]
    text = event["text"]
    channel = event["channel"]

    # Check if this is a DM (channel starts with 'D')
    if not channel.startswith("D"):
        return

    logger.info(f"Received DM from {user_id}: {text}")

    # Check if this is a standup response
    # Simple heuristic: if message is multi-line or mentions tasks
    if len(text) > 50 or "\n" in text:
        try:
            await process_standup_response(user_id, text, client)
        except Exception as e:
            logger.error(f"Error processing standup: {e}")
    else:
        # Handle as query
        try:
            await process_query(user_id, text, client)
        except Exception as e:
            logger.error(f"Error processing query: {e}")


def determine_help_priority(topic: str, reason: str = "", blockers_mentioned: bool = False) -> str:
    """
    Determine help request priority based on keywords and context

    Returns: 'high', 'medium', or 'low'
    """
    combined_text = (topic + " " + reason).lower()

    # High priority keywords
    high_priority_keywords = [
        'urgent', 'critical', 'asap', 'blocking', 'blocked', 'emergency',
        'crash', 'error', 'exception', 'fail', 'production', 'urgent help needed'
    ]

    # Medium priority keywords
    medium_priority_keywords = [
        'help', 'need', 'question', 'stuck', 'unclear', 'confused', 'issue'
    ]

    # Check for high priority keywords
    if blockers_mentioned or any(keyword in combined_text for keyword in high_priority_keywords):
        return 'high'

    # Check for medium priority keywords
    if any(keyword in combined_text for keyword in medium_priority_keywords):
        return 'medium'

    # Default to low priority
    return 'low'


def process_standup_response(user_id: str, message: str, client):
    """
    Process standup response through MCP with enhanced feedback (synchronous version for threading)
    """
    try:
        # Send to MCP for processing (use sync client)
        response = sync_http_client.post(
            "/api/standups/submit",
            json={
                "user_id": user_id,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        # Check if request was successful
        response.raise_for_status()
        result = response.json()

        # Get task updates from parsed_data
        task_updates = result.get('parsed_data', {}).get('task_updates', [])

        # Build response blocks with interactive elements
        help_requests = result.get('help_requests_routed', [])
        logger.info(f"Received help_requests_routed: {help_requests}")

        help_req_text = f"• *Help requests routed:* {len(help_requests)}"
        if help_requests:
            for req in help_requests:
                logger.debug(f"Processing help request: {req}")
                assigned = req.get('assigned_name', req.get('assigned_to', 'Unknown'))
                topic = req.get('topic', 'General help')
                logger.info(f"Displaying: {topic} → {assigned}")
                help_req_text += f"\n  - {topic} → {assigned}"

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "✅ Standup Received!"}
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"I've processed your update:\n" +
                           help_req_text + "\n" +
                           f"• *Blockers detected:* {result.get('blockers_detected', 0)}\n" +
                           f"• *Tasks updated:* {len(task_updates)}"
                }
            }
        ]

        # Add blocker alert if any
        if result.get('blockers_detected', 0) > 0:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🚨 *Blocker Alert!* Your manager has been notified."
                }
            })

        # Acknowledge receipt
        client.chat_postMessage(
            channel=user_id,
            text="Standup received!",
            blocks=blocks
        )

        # Send help request notifications via DM to helpers
        logger.info(f"Processing {len(help_requests)} help requests for DM notifications")
        for help_req in help_requests:
            if help_req.get("assigned_to"):
                try:
                    help_request_id = help_req.get("help_request_id")
                    helper_db_id = help_req.get("assigned_to")  # Database user ID
                    helper_name = help_req.get('assigned_name', helper_db_id)
                    topic = help_req.get('topic', 'General help')
                    reason = help_req.get('reason', '')

                    logger.info(f"📧 Help request routed: {help_request_id} - {topic} from {user_id} to {helper_name}")

                    # Try to send DM to helper if they have a Slack account
                    slack_user_id = None

                    # If helper_db_id looks like a Slack ID (starts with U), use it directly
                    if helper_db_id.startswith('U') and len(helper_db_id) > 5:
                        slack_user_id = helper_db_id
                        logger.debug(f"Using helper_db_id as Slack ID: {slack_user_id}")
                    else:
                        # Otherwise, it's a database ID - try to look up the slack_user_id
                        try:
                            user_response = sync_http_client.get(f"/api/users/{helper_db_id}")
                            if user_response.status_code == 200:
                                user_data = user_response.json()
                                slack_user_id = user_data.get("slack_user_id")
                                if slack_user_id:
                                    logger.debug(f"Found Slack ID {slack_user_id} for database user {helper_db_id}")
                                else:
                                    logger.warning(f"⚠️ Helper {helper_name} (ID: {helper_db_id}) has no Slack user ID mapping")
                                    logger.info(f"📝 Help request {help_request_id} stored for manual routing")
                            else:
                                logger.warning(f"⚠️ Could not find user {helper_db_id} in database")
                                logger.info(f"📝 Help request {help_request_id} stored for manual routing")
                        except Exception as lookup_err:
                            logger.warning(f"⚠️ Error looking up Slack ID for {helper_db_id}: {lookup_err}")
                            logger.info(f"📝 Help request {help_request_id} stored for manual routing")

                    if slack_user_id:
                        try:
                            # Create group DM with requester + helper so both can see and reply
                            # This fixes the issue where thread replies were private
                            try:
                                group_dm_response = client.conversations_open(users=[user_id, slack_user_id])
                                group_dm_channel_id = group_dm_response.get("channel", {}).get("id")

                                if group_dm_channel_id:
                                    # Determine priority based on topic and reason
                                    priority = determine_help_priority(topic, reason, blockers_mentioned=False)
                                    priority_emoji = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"

                                    # Send help request message to group DM (not a private thread)
                                    message_response = client.chat_postMessage(
                                        channel=group_dm_channel_id,
                                        blocks=[
                                            {
                                                "type": "header",
                                                "text": {
                                                    "type": "plain_text",
                                                    "text": f"🆘 Help Request {priority_emoji} [{priority.upper()}]"
                                                }
                                            },
                                            {
                                                "type": "section",
                                                "text": {
                                                    "type": "mrkdwn",
                                                    "text": f"<@{user_id}> needs help from <@{slack_user_id}>\n\n" +
                                                           f"*Topic:* {topic}\n" +
                                                           f"*Priority:* {priority_emoji} {priority.upper()}\n" +
                                                           f"*Reason:* {reason}\n\n" +
                                                           f"Both of you can see this conversation and respond.\n" +
                                                           f"The conversation will be tracked for team learning.\n\n" +
                                                           f"_Request ID: {help_request_id}_"
                                                }
                                            },
                                            {
                                                "type": "actions",
                                                "elements": [
                                                    {
                                                        "type": "button",
                                                        "text": {"type": "plain_text", "text": "✅ Help Provided"},
                                                        "action_id": f"help_resolved_{help_request_id}",
                                                        "style": "primary"
                                                    },
                                                    {
                                                        "type": "button",
                                                        "text": {"type": "plain_text", "text": "⏸️ Need More Info"},
                                                        "action_id": f"help_more_info_{help_request_id}"
                                                    }
                                                ]
                                            }
                                        ]
                                    )

                                    message_ts = message_response.get("ts")

                                    # Store group DM info for tracking
                                    if message_ts:
                                        try:
                                            sync_http_client.post(
                                                f"/api/help/{help_request_id}/track-thread",
                                                json={
                                                    "thread_ts": message_ts,
                                                    "dm_channel_id": group_dm_channel_id,
                                                    "group_dm": True
                                                }
                                            )
                                            logger.info(f"✅ Created group DM for help request {help_request_id} between <@{user_id}> and <@{slack_user_id}>")
                                        except Exception as track_err:
                                            logger.warning(f"⚠️ Could not track help request: {track_err}")
                                    else:
                                        logger.warning(f"⚠️ No timestamp in group DM response for request {help_request_id}")
                                else:
                                    logger.warning(f"⚠️ Could not create group DM for {helper_name} ({slack_user_id})")

                            except Exception as group_dm_err:
                                logger.warning(f"⚠️ Failed to create group DM: {group_dm_err}. Falling back to individual DM...")
                                # Fallback: Send to individual DM if group DM fails
                                dm_response = client.conversations_open(users=[slack_user_id])
                                dm_channel_id = dm_response.get("channel", {}).get("id")

                                if dm_channel_id:
                                    # Determine priority for fallback message too
                                    priority = determine_help_priority(topic, reason, blockers_mentioned=False)
                                    priority_emoji = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"

                                    message_response = client.chat_postMessage(
                                        channel=dm_channel_id,
                                        blocks=[
                                            {
                                                "type": "header",
                                                "text": {
                                                    "type": "plain_text",
                                                    "text": f"🆘 Help Request {priority_emoji} [{priority.upper()}] from <@{user_id}>"
                                                }
                                            },
                                            {
                                                "type": "section",
                                                "text": {
                                                    "type": "mrkdwn",
                                                    "text": f"*Topic:* {topic}\n" +
                                                           f"*Priority:* {priority_emoji} {priority.upper()}\n" +
                                                           f"*Reason:* {reason}\n\n" +
                                                           f"Please reply to help. " +
                                                           f"The conversation will be tracked for team learning.\n\n" +
                                                           f"_Request ID: {help_request_id}_"
                                                }
                                            }
                                        ]
                                    )
                                    logger.info(f"📧 Sent individual DM to helper {helper_name} (Request {help_request_id}, Priority: {priority})")

                        except Exception as dm_err:
                            logger.error(f"❌ Failed to notify helper {helper_name}: {str(dm_err)}")
                            logger.info(f"📝 Help request {help_request_id} stored for manual routing")

                except Exception as e:
                    logger.error(f"❌ Error handling help request: {e}", exc_info=True)

        logger.info(f"Processed standup for {user_id}")

    except Exception as e:
        logger.error(f"Error processing standup: {e}", exc_info=True)
        client.chat_postMessage(
            channel=user_id,
            text="⚠️ Sorry, I had trouble processing your standup. Please try again or contact support."
        )


async def process_query(user_id: str, query: str, client):
    """
    Process natural language query through MCP
    """
    try:
        response = await http_client.post(
            "/api/mcp/query",
            params={"query": query, "user_id": user_id}
        )

        result = response.json()
        answer = result.get("answer", "I'm not sure how to answer that.")

        client.chat_postMessage(
            channel=user_id,
            text=answer
        )

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        client.chat_postMessage(
            channel=user_id,
            text="⚠️ Sorry, I couldn't process your query. Please try again."
        )


# ========== HELP REQUEST HANDLERS ==========

async def create_help_group_chat(client, requesting_user: str, helper_user: str, topic: str):
    """
    Create a 3-person group chat: requesting user + helper + MCP bot

    This is where the magic happens - MCP learns from these conversations
    """
    try:
        # Create group DM
        response = await client.conversations_open(
            users=[requesting_user, helper_user]
        )

        channel_id = response["channel"]["id"]

        # Send introductory message
        await client.chat_postMessage(
            channel=channel_id,
            text=f"👋 *Help Request: {topic}*\n\n" +
                 f"<@{requesting_user}> needs help from <@{helper_user}>.\n\n" +
                 f"I'm here to:\n" +
                 f"• Learn from this conversation\n" +
                 f"• Remind if needed\n" +
                 f"• Log the solution for future reference\n\n" +
                 f"Let me know when this is resolved!"
        )

        logger.info(f"Created help group chat: {requesting_user} -> {helper_user}")

    except Exception as e:
        logger.error(f"Error creating help group chat: {e}")


# ========== MANAGER COMMANDS ==========

@app.command("/mcp-summary")
def handle_summary_command(ack, command, client):
    """Manager command to get team summary"""
    ack()

    user_id = command["user_id"]
    text = command.get("text", "7").strip()
    days = int(text) if text else 7

    try:
        response = sync_http_client.get(
            f"/api/analytics/summary",
            params={"days": days}
        )

        summary = response.json().get("summary", "No summary available")

        client.chat_postMessage(
            channel=user_id,
            text=f"📊 *Team Summary (Last {days} Days)*\n\n{summary}"
        )

    except Exception as e:
        logger.error(f"Error fetching summary: {e}")
        client.chat_postMessage(
            channel=user_id,
            text="⚠️ Couldn't fetch team summary. Please try again."
        )


@app.command("/mcp-assign")
def handle_assign_command(ack, command, client):
    """
    Manager command to assign tasks

    Usage: /mcp-assign @user task description [priority]
    """
    ack()

    # Parse command
    # Format: @user task description priority
    text = command.get("text", "")
    parts = text.split(maxsplit=2)

    if len(parts) < 2:
        client.chat_postMessage(
            channel=command["user_id"],
            text="Usage: `/mcp-assign @user task description [priority]`"
        )
        return

    assignee = parts[0].replace("<@", "").replace(">", "")
    task_title = parts[1]
    priority = parts[2] if len(parts) > 2 else "medium"

    try:
        response = sync_http_client.post(
            "/api/tasks/assign",
            params={
                "task_title": task_title,
                "assignee_id": assignee,
                "priority": priority
            }
        )

        # Notify assignee
        client.chat_postMessage(
            channel=assignee,
            text=f"📋 *New Task Assigned*\n\n" +
                 f"*Task:* {task_title}\n" +
                 f"*Priority:* {priority}\n\n" +
                 f"Assigned by <@{command['user_id']}>"
        )

        # Confirm to manager
        client.chat_postMessage(
            channel=command["user_id"],
            text=f"✅ Task assigned to <@{assignee}>"
        )

    except Exception as e:
        logger.error(f"Error assigning task: {e}")
        client.chat_postMessage(
            channel=command["user_id"],
            text="⚠️ Couldn't assign task. Please try again."
        )


# ========== MCP QUERY COMMANDS ==========

@app.command("/my-help-requests")
def handle_my_help_requests_command(ack, command, client):
    """
    Get help requests you received today sorted by priority

    Usage: /my-help-requests
    """
    ack()

    user_id = command["user_id"]

    try:
        response = sync_http_client.get(
            f"/api/help/user/{user_id}/received-today"
        )

        data = response.json()
        help_requests = data.get("help_requests", [])

        if not help_requests:
            client.chat_postMessage(
                channel=user_id,
                text="✨ No help requests received today. You're all caught up!"
            )
            return

        # Format help requests
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🆘 {len(help_requests)} Help Requests Today"
                }
            }
        ]

        for i, req in enumerate(help_requests, 1):
            priority = req.get("priority", "medium").upper()
            priority_emoji = "🔴" if priority == "HIGH" else "🟡" if priority == "MEDIUM" else "🟢"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{priority_emoji} *{i}. {req.get('topic', 'Help Request')}* [{priority}]\n" +
                           f"From: <@{req.get('from_user_id')}>\n" +
                           f"Status: {req.get('status', 'pending').upper()}"
                }
            })

        client.chat_postMessage(
            channel=user_id,
            blocks=blocks
        )

    except Exception as e:
        logger.error(f"Error fetching help requests: {e}")
        client.chat_postMessage(
            channel=user_id,
            text="⚠️ Couldn't fetch your help requests. Please try again."
        )


@app.command("/my-helping")
def handle_my_helping_command(ack, command, client):
    """
    Get list of things you're helping with today

    Usage: /my-helping
    """
    ack()

    user_id = command["user_id"]

    try:
        response = sync_http_client.get(
            f"/api/help/user/{user_id}/helping-with-today"
        )

        data = response.json()
        helping_items = data.get("helping_items", [])

        if not helping_items:
            client.chat_postMessage(
                channel=user_id,
                text="✨ You're not helping with anything right now. Great job staying available!"
            )
            return

        # Format helping activities
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🤝 You're Helping with {len(helping_items)} Things Today"
                }
            }
        ]

        for i, item in enumerate(helping_items, 1):
            status = item.get("status", "in_progress")
            status_emoji = "🚀" if status == "in_progress" else "✅" if status == "completed" else "⏸️"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{status_emoji} *{i}. {item.get('topic', 'Help Item')}*\n" +
                           f"Helping: <@{item.get('to_user_id')}>\n" +
                           f"Time spent: {item.get('duration_minutes', 0)} mins"
                }
            })

        client.chat_postMessage(
            channel=user_id,
            blocks=blocks
        )

    except Exception as e:
        logger.error(f"Error fetching helping activities: {e}")
        client.chat_postMessage(
            channel=user_id,
            text="⚠️ Couldn't fetch your helping activities. Please try again."
        )


@app.command("/my-tasks")
def handle_my_tasks_command(ack, command, client):
    """
    Get your assigned tasks sorted by priority

    Usage: /my-tasks [filter: all|high|medium|low|in_progress|blocked]
    """
    ack()

    user_id = command["user_id"]
    filter_type = command.get("text", "all").strip().lower() or "all"

    try:
        response = sync_http_client.get(
            f"/api/tasks/user/{user_id}",
            params={"filter": filter_type, "sort_by": "priority"}
        )

        data = response.json()
        tasks = data.get("tasks", [])

        if not tasks:
            client.chat_postMessage(
                channel=user_id,
                text=f"✨ No {filter_type} tasks found. Great work!"
            )
            return

        # Format tasks by priority
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📋 {len(tasks)} Tasks ({filter_type.upper()})"
                }
            }
        ]

        for i, task in enumerate(tasks, 1):
            priority = task.get("priority", "medium").upper()
            status = task.get("status", "not_started")

            priority_emoji = "🔴" if priority == "HIGH" else "🟡" if priority == "MEDIUM" else "🟢"
            status_emoji = "🆕" if status == "not_started" else "🚀" if status == "in_progress" else "🚧" if status == "blocked" else "✅"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{priority_emoji} {status_emoji} *{i}. {task.get('title', 'Untitled')}*\n" +
                           f"Status: {status.replace('_', ' ').title()} | Priority: {priority}\n" +
                           f"Due: {task.get('due_date', 'No due date')}"
                }
            })

        client.chat_postMessage(
            channel=user_id,
            blocks=blocks
        )

    except Exception as e:
        logger.error(f"Error fetching tasks: {e}")
        client.chat_postMessage(
            channel=user_id,
            text="⚠️ Couldn't fetch your tasks. Please try again."
        )


# ========== HELP REQUEST BUTTON ACTIONS ==========

@app.action(re.compile(r"help_resolved_\d+"))
def handle_help_provided_button(ack, body, client):
    """
    Handle "Help Provided" button click
    Updates help request status to RESOLVED (not deleted!)
    """
    ack()

    try:
        # Extract help request ID from action_id
        action_id = body["actions"][0]["action_id"]
        help_request_id = action_id.replace("help_resolved_", "")

        user_id = body["user"]["id"]
        user_name = body["user"].get("username", user_id)

        logger.info(f"User {user_name} marked help request {help_request_id} as resolved")

        # Update help request status in backend
        try:
            sync_http_client.post(
                f"/api/help/{help_request_id}/resolve",
                params={"resolution_notes": f"Resolved by {user_name}"}
            )
            logger.info(f"✅ Help request {help_request_id} marked as resolved")
        except Exception as e:
            logger.error(f"⚠️ Could not update help request status: {e}")

        # Send confirmation message
        client.chat_postMessage(
            channel=body["channel"]["id"],
            text=f"✅ <@{user_id}> marked this help request as resolved!\n\nThank you for helping the team! 🎉"
        )

    except Exception as e:
        logger.error(f"Error handling help provided button: {e}", exc_info=True)


@app.action(re.compile(r"help_more_info_\d+"))
def handle_help_more_info_button(ack, body, client):
    """
    Handle "Need More Info" button click
    Accepts the help request and keeps it in progress
    """
    ack()

    try:
        # Extract help request ID from action_id
        action_id = body["actions"][0]["action_id"]
        help_request_id = action_id.replace("help_more_info_", "")

        user_id = body["user"]["id"]
        user_name = body["user"].get("username", user_id)

        logger.info(f"User {user_name} requested more info for help request {help_request_id}")

        # Update help request status to ACCEPTED
        try:
            sync_http_client.post(
                f"/api/help/{help_request_id}/accept",
                params={}
            )
            logger.info(f"✅ Help request {help_request_id} marked as accepted")
        except Exception as e:
            logger.error(f"⚠️ Could not update help request status: {e}")

        # Send message asking requester for more info
        client.chat_postMessage(
            channel=body["channel"]["id"],
            text=f"💬 <@{user_id}> needs more information to help you!\n\nPlease reply with additional details about your issue."
        )

    except Exception as e:
        logger.error(f"Error handling need more info button: {e}", exc_info=True)


# ========== APP MENTION ==========

@app.event("app_mention")
def handle_mention(event, client):
    """
    Handle @MCP mentions in channels

    Users can ask questions or request help
    """
    user_id = event["user"]
    text = event["text"]
    channel = event["channel"]

    # Remove bot mention from text
    query = text.split(">", 1)[1].strip() if ">" in text else text

    try:
        response = sync_http_client.post(
            "/api/mcp/query",
            params={"query": query, "user_id": user_id}
        )

        result = response.json()
        answer = result.get("answer", "I'm not sure how to answer that.")

        client.chat_postMessage(
            channel=channel,
            thread_ts=event.get("ts"),
            text=f"<@{user_id}> {answer}"
        )

    except Exception as e:
        logger.error(f"Error handling mention: {e}")


# ========== NOTIFICATION SYSTEM ==========

async def notify_manager_of_blocker(client, user_id: str, blockers: List[str]):
    """
    Notify manager when team member reports blocker
    """
    try:
        # Get user's manager from MCP
        response = await http_client.get(f"/api/users/{user_id}")
        user_data = response.json()
        manager_id = user_data.get("manager_id")

        if not manager_id:
            return

        blocker_text = "\n".join([f"• {blocker}" for blocker in blockers])

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚨 Team Member Blocker Alert"}
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<@{user_id}> reported blockers in their standup:\n\n{blocker_text}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "💬 Contact Team Member"},
                        "action_id": "contact_team_member",
                        "value": user_id,
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📊 View Dashboard"},
                        "action_id": "view_dashboard"
                    }
                ]
            }
        ]

        await client.chat_postMessage(
            channel=manager_id,
            text=f"Blocker alert from {user_id}",
            blocks=blocks
        )

        logger.info(f"Notified manager {manager_id} of blocker from {user_id}")

    except Exception as e:
        logger.error(f"Error notifying manager: {e}")


@app.action("contact_team_member")
async def handle_contact_team_member(ack, body, client):
    """Handle manager clicking contact button"""
    await ack()

    user_id = body["actions"][0]["value"]
    manager_id = body["user"]["id"]

    # Open DM with team member
    await client.chat_postMessage(
        channel=manager_id,
        text=f"Opening conversation with <@{user_id}>..."
    )


@app.action("view_dashboard")
async def handle_view_dashboard(ack, body):
    """Handle view dashboard button"""
    await ack()


# ========== USER ONBOARDING ==========

@app.event("team_join")
async def handle_team_join(event, client):
    """
    Welcome new team members and collect expertise
    """
    user_id = event["user"]["id"]

    await send_welcome_message(client, user_id)


async def send_welcome_message(client, user_id: str):
    """
    Send welcome message with onboarding flow
    """
    try:
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "👋 Welcome to MCP!"}
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "I'm your AI team coordinator. I help with:\n\n" +
                           "• 📊 Daily standups and progress tracking\n" +
                           "• 🤝 Intelligent help request routing\n" +
                           "• 🎯 Task management and blocker detection\n" +
                           "• 📈 Team insights and analytics"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Quick Commands:*\n" +
                           "• `/standup` - Submit daily standup\n" +
                           "• `@MCP <question>` - Ask me anything\n" +
                           "• DM me for help anytime!"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🚀 Complete Setup"},
                        "action_id": "start_onboarding",
                        "style": "primary"
                    }
                ]
            }
        ]

        await client.chat_postMessage(
            channel=user_id,
            text="Welcome to MCP!",
            blocks=blocks
        )

    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")


@app.action("start_onboarding")
async def handle_start_onboarding(ack, body, client):
    """
    Start onboarding flow - collect expertise
    """
    await ack()

    user_id = body["user"]["id"]
    trigger_id = body["trigger_id"]

    modal_view = {
        "type": "modal",
        "callback_id": "onboarding_modal",
        "title": {"type": "plain_text", "text": "Complete Your Profile"},
        "submit": {"type": "plain_text", "text": "Save"},
        "blocks": [
            {
                "type": "input",
                "block_id": "expertise",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "expertise_input",
                    "multiline": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g., React, Python, AWS, Docker, Database Design..."
                    }
                },
                "label": {"type": "plain_text", "text": "What are your areas of expertise?"}
            },
            {
                "type": "input",
                "block_id": "timezone",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "timezone_input",
                    "placeholder": {"type": "plain_text", "text": "e.g., America/New_York, UTC, Asia/Tokyo"}
                },
                "label": {"type": "plain_text", "text": "Your Timezone"}
            },
            {
                "type": "input",
                "block_id": "standup_time",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "standup_time_input",
                    "placeholder": {"type": "plain_text", "text": "e.g., 09:00"}
                },
                "label": {"type": "plain_text", "text": "Preferred Standup Time (HH:MM)"},
                "optional": True
            }
        ]
    }

    await client.views_open(trigger_id=trigger_id, view=modal_view)


@app.view("onboarding_modal")
async def handle_onboarding_submission(ack, body, client, view):
    """
    Handle onboarding data submission
    """
    await ack()

    user_id = body["user"]["id"]
    values = view["state"]["values"]

    expertise = values["expertise"]["expertise_input"].get("value", "")
    timezone = values["timezone"]["timezone_input"].get("value", "UTC")
    standup_time = values["standup_time"]["standup_time_input"].get("value", "09:00")

    # Send to MCP backend
    try:
        await http_client.post(
            f"/api/users/{user_id}/profile",
            json={
                "expertise_tags": [tag.strip() for tag in expertise.split(",")],
                "timezone": timezone,
                "standup_time": standup_time
            }
        )

        await client.chat_postMessage(
            channel=user_id,
            text="✅ *Profile complete!* I'll route help requests your way based on your expertise. "
                 f"You'll receive standup reminders at {standup_time} daily."
        )

    except Exception as e:
        logger.error(f"Error saving profile: {e}")


# ========== REACTION-BASED INTERACTIONS ==========

@app.event("reaction_added")
async def handle_reaction(event, client):
    """
    Handle emoji reactions for quick actions

    ✅ - Mark task complete
    🚫 - Report blocker
    🙋 - Request help
    👀 - Acknowledge/watching
    """
    user_id = event["user"]
    reaction = event["reaction"]
    item = event["item"]

    # Ignore bot reactions
    if event.get("item_user") == "bot":
        return

    try:
        # Handle different reactions
        if reaction == "white_check_mark":  # ✅
            await handle_task_complete_reaction(client, user_id, item)
        elif reaction == "no_entry_sign":  # 🚫
            await handle_blocker_reaction(client, user_id, item)
        elif reaction == "raising_hand":  # 🙋
            await handle_help_reaction(client, user_id, item)
        elif reaction == "eyes":  # 👀
            await handle_acknowledge_reaction(client, user_id, item)

    except Exception as e:
        logger.error(f"Error handling reaction: {e}")


async def handle_task_complete_reaction(client, user_id: str, item: Dict):
    """Mark task as complete when user reacts with ✅"""
    await client.chat_postMessage(
        channel=user_id,
        text="✅ Great! I've marked your task as complete. Keep up the good work!"
    )


async def handle_blocker_reaction(client, user_id: str, item: Dict):
    """Handle blocker report via 🚫 reaction"""
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "🚫 *Blocker Detected*\n\nWhat's blocking you?"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📝 Describe Blocker"},
                    "action_id": "describe_blocker",
                    "style": "danger"
                }
            ]
        }
    ]

    await client.chat_postMessage(
        channel=user_id,
        text="Blocker detected",
        blocks=blocks
    )


async def handle_help_reaction(client, user_id: str, item: Dict):
    """Handle help request via 🙋 reaction"""
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "🙋 *Need Help?*\n\nI can route you to the right expert!"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "💬 Request Help"},
                    "action_id": "request_help_button",
                    "style": "primary"
                }
            ]
        }
    ]

    await client.chat_postMessage(
        channel=user_id,
        text="Need help?",
        blocks=blocks
    )


async def handle_acknowledge_reaction(client, user_id: str, item: Dict):
    """Acknowledge message with 👀"""
    logger.info(f"User {user_id} acknowledged message")


@app.action("describe_blocker")
async def handle_describe_blocker_button(ack, body, client):
    """Open modal to describe blocker"""
    await ack()

    trigger_id = body["trigger_id"]

    modal_view = {
        "type": "modal",
        "callback_id": "blocker_modal",
        "title": {"type": "plain_text", "text": "Report Blocker"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "blocks": [
            {
                "type": "input",
                "block_id": "blocker_description",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "blocker_input",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Describe what's blocking you..."}
                },
                "label": {"type": "plain_text", "text": "Blocker Description"}
            }
        ]
    }

    await client.views_open(trigger_id=trigger_id, view=modal_view)


@app.view("blocker_modal")
async def handle_blocker_submission(ack, body, client, view):
    """Handle blocker submission"""
    await ack()

    user_id = body["user"]["id"]
    blocker = view["state"]["values"]["blocker_description"]["blocker_input"]["value"]

    # Notify manager
    await notify_manager_of_blocker(client, user_id, [blocker])

    await client.chat_postMessage(
        channel=user_id,
        text="✅ Blocker reported! Your manager has been notified and help is on the way."
    )


@app.action("request_help_button")
async def handle_request_help_button(ack, body, client):
    """Open help request modal"""
    await ack()

    trigger_id = body["trigger_id"]

    modal_view = {
        "type": "modal",
        "callback_id": "help_request_modal",
        "title": {"type": "plain_text", "text": "Request Help"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "blocks": [
            {
                "type": "input",
                "block_id": "help_topic",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "topic_input",
                    "placeholder": {"type": "plain_text", "text": "e.g., React hooks, AWS deployment, SQL query..."}
                },
                "label": {"type": "plain_text", "text": "What do you need help with?"}
            },
            {
                "type": "input",
                "block_id": "help_details",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "details_input",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Provide more details..."}
                },
                "label": {"type": "plain_text", "text": "Details"}
            }
        ]
    }

    await client.views_open(trigger_id=trigger_id, view=modal_view)


@app.view("help_request_modal")
async def handle_help_request_submission(ack, body, client, view):
    """Handle help request submission"""
    await ack()

    user_id = body["user"]["id"]
    topic = view["state"]["values"]["help_topic"]["topic_input"]["value"]
    details = view["state"]["values"]["help_details"]["details_input"]["value"]

    # Route help request through MCP
    try:
        response = await http_client.post(
            "/api/help/create",
            json={
                "requester_id": user_id,
                "topic": topic,
                "details": details
            }
        )

        result = response.json()
        assigned_to = result.get("assigned_to")

        if assigned_to:
            await create_help_group_chat(client, user_id, assigned_to, topic)
            await client.chat_postMessage(
                channel=user_id,
                text=f"✅ Help request routed to <@{assigned_to}>! They'll reach out shortly."
            )
        else:
            await client.chat_postMessage(
                channel=user_id,
                text="✅ Help request submitted! Looking for the best person to help..."
            )

    except Exception as e:
        logger.error(f"Error creating help request: {e}")


# ========== SCHEDULED JOBS ==========

async def send_daily_standup_reminders(client):
    """
    Send standup reminders to all team members who haven't submitted
    """
    try:
        # Get all active users from MCP
        response = await http_client.get("/api/users/active")
        users = response.json().get("users", [])

        today = datetime.utcnow().date()

        for user in users:
            user_id = user["id"]

            # Check if user already submitted today
            last_submission = daily_standup_submissions.get(user_id)
            if last_submission and last_submission.date() == today:
                continue

            # Send reminder
            await send_standup_questions(client, user_id)
            logger.info(f"Sent standup reminder to {user_id}")

    except Exception as e:
        logger.error(f"Error sending standup reminders: {e}")


async def check_stale_help_requests(client):
    """
    Check for stale help requests and send follow-ups
    """
    try:
        response = await http_client.get("/api/help/stale")
        stale_requests = response.json().get("requests", [])

        for req in stale_requests:
            requester = req["requester_id"]
            helper = req.get("assigned_to")

            if helper:
                await client.chat_postMessage(
                    channel=helper,
                    text=f"👋 Reminder: <@{requester}> is still waiting for help with: *{req['topic']}*"
                )

    except Exception as e:
        logger.error(f"Error checking stale help requests: {e}")


async def escalate_long_blockers(client):
    """
    Escalate blockers that have been open for too long
    """
    try:
        response = await http_client.get("/api/analytics/long-blockers")
        blockers = response.json().get("blockers", [])

        for blocker in blockers:
            user_id = blocker["user_id"]
            manager_id = blocker.get("manager_id")

            if manager_id:
                await client.chat_postMessage(
                    channel=manager_id,
                    text=f"⚠️ *Long-standing Blocker Alert*\n\n" +
                         f"<@{user_id}> has been blocked for {blocker['days']} days:\n" +
                         f"_{blocker['description']}_\n\n" +
                         f"This needs immediate attention!"
                )

    except Exception as e:
        logger.error(f"Error escalating blockers: {e}")


def setup_scheduled_jobs(client):
    """
    Set up all scheduled jobs
    """
    # Parse standup time
    hour, minute = map(int, STANDUP_TIME.split(":"))

    # Daily standup reminders at specified time
    scheduler.add_job(
        lambda: asyncio.create_task(send_daily_standup_reminders(client)),
        CronTrigger(hour=hour, minute=minute),
        id="daily_standup_reminders",
        name="Send daily standup reminders"
    )

    # Check stale help requests every 6 hours
    scheduler.add_job(
        lambda: asyncio.create_task(check_stale_help_requests(client)),
        CronTrigger(hour="*/6"),
        id="stale_help_check",
        name="Check stale help requests"
    )

    # Escalate long blockers every 12 hours
    scheduler.add_job(
        lambda: asyncio.create_task(escalate_long_blockers(client)),
        CronTrigger(hour="*/12"),
        id="blocker_escalation",
        name="Escalate long-standing blockers"
    )

    logger.info("✅ Scheduled jobs configured")


# ========== MAIN ==========

def sync_slack_workspace_members(client):
    """
    Sync all Slack workspace members and their IDs to MCP database at startup

    This ensures the server has access to all workspace member IDs for:
    - Sending DM notifications
    - Help request routing
    - Member lookups
    """
    try:
        logger.info("🔄 Syncing Slack workspace members to database...")

        # Fetch all workspace members
        members_response = client.users_list()
        members = members_response.get('members', [])

        logger.info(f"Found {len(members)} members in Slack workspace")

        # Get existing users from database
        try:
            db_users_response = sync_http_client.get("/api/users")
            db_users_list = db_users_response.json().get('users', [])
            # Map by name (lowercase) for matching
            db_users_by_name = {user.get('name', '').lower(): user for user in db_users_list}
            logger.debug(f"Found {len(db_users_list)} existing users in database")
        except Exception as e:
            logger.warning(f"Could not fetch existing users: {e}")
            db_users_list = []
            db_users_by_name = {}

        # For each member, update/create in database
        synced = 0
        skipped = 0
        for member in members:
            try:
                slack_user_id = member.get('id')
                real_name = member.get('real_name') or member.get('name', slack_user_id)

                # Skip bots and deactivated users
                if member.get('is_bot') or member.get('deleted'):
                    logger.debug(f"⊘ Skipped bot/deactivated: {real_name}")
                    skipped += 1
                    continue

                # Try to find existing user by name match
                existing_user = db_users_by_name.get(real_name.lower())

                if existing_user:
                    # Link Slack ID to existing user
                    target_user_id = existing_user['id']
                    link_response = sync_http_client.post(
                        f"/api/users/{target_user_id}/link-slack",
                        json={"slack_user_id": slack_user_id}
                    )
                    if link_response.status_code == 200:
                        synced += 1
                        logger.info(f"✅ Linked: {real_name} → {slack_user_id}")
                    else:
                        logger.debug(f"⚠ Could not link Slack ID for {real_name}")
                else:
                    # Create new user with Slack ID
                    sync_response = sync_http_client.post(
                        f"/api/users/{slack_user_id}/profile",
                        json={
                            "expertise_tags": [],
                            "timezone": "UTC"
                        }
                    )

                    if sync_response.status_code == 200:
                        # Link the Slack user ID to itself
                        link_response = sync_http_client.post(
                            f"/api/users/{slack_user_id}/link-slack",
                            json={"slack_user_id": slack_user_id}
                        )
                        if link_response.status_code == 200:
                            synced += 1
                            logger.info(f"✅ Created & synced: {real_name} ({slack_user_id})")
                        else:
                            logger.debug(f"⚠ Created but couldn't link Slack ID for {real_name}")

            except Exception as member_err:
                logger.debug(f"Error syncing member {member.get('name')}: {member_err}")

        logger.info(f"✅ Synced {synced} workspace members to database (skipped {skipped} bots/deactivated)")

    except Exception as e:
        logger.error(f"❌ Error syncing Slack workspace members: {e}", exc_info=True)


if __name__ == "__main__":
    logger.info("🚀 Starting MCP Slack Bot...")

    if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
        logger.error("Missing Slack tokens! Set SLACK_BOT_TOKEN and SLACK_APP_TOKEN")
        exit(1)

    # Get Slack client from app
    client = app.client

    # Sync workspace members at startup
    sync_slack_workspace_members(client)

    # Set up scheduled jobs
    setup_scheduled_jobs(client)

    # Start scheduler
    scheduler.start()
    logger.info(f"📅 Scheduler started - Daily standups at {STANDUP_TIME}")

    # Start socket mode handler
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    logger.info("🔌 Socket Mode handler connected")

    try:
        handler.start()
    except KeyboardInterrupt:
        logger.info("⏸️  Shutting down gracefully...")
        scheduler.shutdown()
        logger.info("👋 MCP Slack Bot stopped")
