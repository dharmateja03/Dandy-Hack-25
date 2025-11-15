"""
MCP Slack Bot - Primary Interface to Model Context Protocol

This bot is how teams interact with MCP:
- Daily standups via DM
- Help request routing
- Natural language queries
- Manager commands
"""

import os
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import httpx
from datetime import datetime

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

# Initialize Slack app
app = App(token=SLACK_BOT_TOKEN)

# HTTP client for MCP API
http_client = httpx.AsyncClient(base_url=MCP_API_URL)


# ========== STANDUP HANDLERS ==========

@app.command("/standup")
async def handle_standup_command(ack, command, client):
    """
    Trigger standup via slash command
    """
    await ack()

    user_id = command["user_id"]

    # Send standup questions via DM
    await send_standup_questions(client, user_id)


async def send_standup_questions(client, user_id):
    """
    Send standup questions to user via DM
    """
    try:
        # Get user's current tasks from MCP
        response = await http_client.get(f"/api/tasks/user/{user_id}")
        tasks = response.json().get("tasks", [])

        task_list = "\n".join([
            f"• {task['title']} ({task['status']})"
            for task in tasks
        ]) if tasks else "No assigned tasks"

        message = f"""
👋 *Good morning! Time for your standup*

Your assigned tasks:
{task_list}

Please answer the following:
1️⃣ *What did you complete yesterday?*
2️⃣ *What are you working on today?*
3️⃣ *Any blockers or help needed?*
4️⃣ *Updates on your assigned tasks?*

Feel free to add any additional context!
"""

        result = await client.chat_postMessage(
            channel=user_id,
            text=message,
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": message}
                }
            ]
        )

        logger.info(f"Sent standup questions to {user_id}")
        return result

    except Exception as e:
        logger.error(f"Error sending standup questions: {e}")


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
        await process_standup_response(user_id, text, client)
    else:
        # Handle as query
        await process_query(user_id, text, client)


async def process_standup_response(user_id: str, message: str, client):
    """
    Process standup response through MCP
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

        result = response.json()

        # Acknowledge receipt
        await client.chat_postMessage(
            channel=user_id,
            text=f"✅ *Standup received!*\n\nI've processed your update and:\n" +
                 f"• Routed {len(result.get('help_requests_routed', []))} help requests\n" +
                 f"• Detected {result.get('blockers_detected', 0)} blockers\n\n" +
                 "I'll notify the right people and keep your manager updated!"
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

        logger.info(f"Processed standup for {user_id}")

    except Exception as e:
        logger.error(f"Error processing standup: {e}")
        await client.chat_postMessage(
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

        await client.chat_postMessage(
            channel=user_id,
            text=answer
        )

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        await client.chat_postMessage(
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
async def handle_summary_command(ack, command, client):
    """Manager command to get team summary"""
    await ack()

    user_id = command["user_id"]
    days = int(command.get("text", "7"))

    try:
        response = await http_client.get(
            f"/api/analytics/summary",
            params={"days": days}
        )

        summary = response.json().get("summary", "No summary available")

        await client.chat_postMessage(
            channel=user_id,
            text=f"📊 *Team Summary (Last {days} Days)*\n\n{summary}"
        )

    except Exception as e:
        logger.error(f"Error fetching summary: {e}")
        await client.chat_postMessage(
            channel=user_id,
            text="⚠️ Couldn't fetch team summary. Please try again."
        )


@app.command("/mcp-assign")
async def handle_assign_command(ack, command, client):
    """
    Manager command to assign tasks

    Usage: /mcp-assign @user task description [priority]
    """
    await ack()

    # Parse command
    # Format: @user task description priority
    text = command.get("text", "")
    parts = text.split(maxsplit=2)

    if len(parts) < 2:
        await client.chat_postMessage(
            channel=command["user_id"],
            text="Usage: `/mcp-assign @user task description [priority]`"
        )
        return

    assignee = parts[0].replace("<@", "").replace(">", "")
    task_title = parts[1]
    priority = parts[2] if len(parts) > 2 else "medium"

    try:
        response = await http_client.post(
            "/api/tasks/assign",
            params={
                "task_title": task_title,
                "assignee_id": assignee,
                "priority": priority
            }
        )

        # Notify assignee
        await client.chat_postMessage(
            channel=assignee,
            text=f"📋 *New Task Assigned*\n\n" +
                 f"*Task:* {task_title}\n" +
                 f"*Priority:* {priority}\n\n" +
                 f"Assigned by <@{command['user_id']}>"
        )

        # Confirm to manager
        await client.chat_postMessage(
            channel=command["user_id"],
            text=f"✅ Task assigned to <@{assignee}>"
        )

    except Exception as e:
        logger.error(f"Error assigning task: {e}")
        await client.chat_postMessage(
            channel=command["user_id"],
            text="⚠️ Couldn't assign task. Please try again."
        )


# ========== APP MENTION ==========

@app.event("app_mention")
async def handle_mention(event, client):
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
        response = await http_client.post(
            "/api/mcp/query",
            params={"query": query, "user_id": user_id}
        )

        result = response.json()
        answer = result.get("answer", "I'm not sure how to answer that.")

        await client.chat_postMessage(
            channel=channel,
            thread_ts=event.get("ts"),
            text=f"<@{user_id}> {answer}"
        )

    except Exception as e:
        logger.error(f"Error handling mention: {e}")


# ========== SCHEDULED JOBS ==========

# TODO: Add APScheduler for daily standup reminders


# ========== MAIN ==========

if __name__ == "__main__":
    logger.info("🚀 Starting MCP Slack Bot...")

    if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
        logger.error("Missing Slack tokens! Set SLACK_BOT_TOKEN and SLACK_APP_TOKEN")
        exit(1)

    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
