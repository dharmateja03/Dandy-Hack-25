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
    ack()

    user_id = command["user_id"]
    trigger_id = command["trigger_id"]

    # Run async function in new event loop
    try:
        open_standup_modal(client, user_id, trigger_id)
    except Exception as e:
        logger.error(f"Error opening standup modal: {e}")


def open_standup_modal(client, user_id: str, trigger_id: str):
    """
    Open interactive modal for standup submission
    """
    try:
        # Get user's current tasks from MCP
        tasks = []
        try:
            response = sync_http_client.get(f"/api/tasks/user/{user_id}")
            tasks = response.json().get("tasks", [])
        except Exception as e:
            logger.warning(f"Couldn't fetch tasks for {user_id}: {e}")

        # Build task options for dropdown
        task_options = [
            {
                "text": {"type": "plain_text", "text": f"{task['title']} ({task['status']})"},
                "value": str(task['id'])
            }
            for task in tasks[:10]  # Limit to 10 tasks
        ]

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
                        "placeholder": {"type": "plain_text", "text": "What do you need help with?"}
                    },
                    "label": {"type": "plain_text", "text": "🙋 Help Needed (if any)"},
                    "optional": True
                }
            ]
        }

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

    # Process standup (run async function in background)
    try:
        # Create a new event loop for async operations in a background thread
        def run_async_standup():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(process_standup_response(user_id, standup_message, client))
            finally:
                loop.close()

        thread = threading.Thread(target=run_async_standup, daemon=True)
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


async def process_standup_response(user_id: str, message: str, client):
    """
    Process standup response through MCP with enhanced feedback
    """
    try:
        # Send to MCP for processing
        response = await http_client.post(
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
                           f"• *Help requests routed:* {len(result.get('help_requests_routed', []))}\n" +
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

        # If help requests were routed, create group chats
        for help_req in result.get("help_requests_routed", []):
            if help_req.get("assigned_to"):
                await create_help_group_chat(
                    client,
                    requesting_user=user_id,
                    helper_user=help_req["assigned_to"],
                    topic=help_req.get("topic", "Help needed")
                )

        # Notify manager if blockers detected
        if result.get('blockers_detected', 0) > 0:
            blockers_list = result.get('parsed_data', {}).get('blockers', [])
            blocker_descriptions = [b.get('description', str(b)) for b in blockers_list]
            await notify_manager_of_blocker(client, user_id, blocker_descriptions)

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

if __name__ == "__main__":
    logger.info("🚀 Starting MCP Slack Bot...")

    if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
        logger.error("Missing Slack tokens! Set SLACK_BOT_TOKEN and SLACK_APP_TOKEN")
        exit(1)

    # Get Slack client from app
    client = app.client

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
