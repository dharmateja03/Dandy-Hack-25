# 🚀 MCP Setup Guide

Complete step-by-step guide to get MCP running.

## ⚡ Prerequisites

Before starting, ensure you have:

- [ ] Docker Desktop installed ([Download](https://www.docker.com/products/docker-desktop))
- [ ] Docker Compose installed (included with Docker Desktop)
- [ ] A Slack workspace where you can create apps
- [ ] Google account (for Gemini API)

## 📋 Step-by-Step Setup

### Step 1: Get Google Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key (starts with `AIza...`)
4. Save it - you'll need it in Step 4

### Step 2: Create Slack App

#### 2.1 Create the App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"**
3. Select **"From scratch"**
4. Name: `MCP` (or whatever you prefer)
5. Pick your workspace
6. Click **"Create App"**

#### 2.2 Configure OAuth & Permissions

1. In left sidebar, click **"OAuth & Permissions"**
2. Scroll to **"Scopes"** → **"Bot Token Scopes"**
3. Add these scopes:
   - `chat:write`
   - `im:write`
   - `im:read`
   - `im:history`
   - `users:read`
   - `channels:read`
   - `groups:write`
   - `mpim:write`
   - `commands`
4. Scroll up and click **"Install to Workspace"**
5. Click **"Allow"**
6. **Copy the "Bot User OAuth Token"** (starts with `xoxb-`)
   - Save this as `SLACK_BOT_TOKEN`

#### 2.3 Enable Socket Mode

1. In left sidebar, click **"Socket Mode"**
2. Toggle **"Enable Socket Mode"** → ON
3. Give it a name: `MCP Socket`
4. **Copy the "App-Level Token"** (starts with `xapp-`)
   - Save this as `SLACK_APP_TOKEN`

#### 2.4 Enable Events

1. In left sidebar, click **"Event Subscriptions"**
2. Toggle **"Enable Events"** → ON
3. Under **"Subscribe to bot events"**, add:
   - `message.im`
   - `app_mention`
4. Click **"Save Changes"**

#### 2.5 Create Slash Commands

1. In left sidebar, click **"Slash Commands"**
2. Click **"Create New Command"**

**Command 1:**
- Command: `/standup`
- Description: `Start your daily standup`
- Usage Hint: `(no parameters needed)`

**Command 2:**
- Command: `/mcp-summary`
- Description: `Get team summary (managers only)`
- Usage Hint: `[days]`

**Command 3:**
- Command: `/mcp-assign`
- Description: `Assign a task (managers only)`
- Usage Hint: `@user task description [priority]`

3. Click **"Save"**

### Step 3: Clone the Repository

```bash
git clone <your-repo-url>
cd Dandy-Hack-25
```

### Step 4: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your favorite editor
nano .env
# or
vim .env
# or
code .env
```

**Fill in these values:**

```env
# Google Gemini (from Step 1)
GEMINI_API_KEY=AIza...your-key-here

# Slack Bot Token (from Step 2.2)
SLACK_BOT_TOKEN=xoxb-your-bot-token

# Slack App Token (from Step 2.3)
SLACK_APP_TOKEN=xapp-your-app-token
```

**Leave the rest as default for now.**

### Step 5: Start MCP

```bash
# Start all services with Docker Compose
docker-compose up -d

# This will:
# - Pull Docker images
# - Build backend, slack-bot, and dashboard
# - Start PostgreSQL, Qdrant, and all services
```

**First time will take 2-5 minutes to download and build everything.**

### Step 6: Verify Services

```bash
# Check that all services are running
docker-compose ps

# You should see:
# - mcp-backend (running)
# - slack-bot (running)
# - qdrant (running)
# - postgres (running)
# - dashboard (running)
```

**Check logs:**

```bash
# View all logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View specific service
docker-compose logs slack-bot
```

### Step 7: Test the Setup

#### 7.1 Test Backend API

Open browser: http://localhost:8000

You should see:
```json
{
  "status": "healthy",
  "service": "MCP - Model Context Protocol",
  "version": "0.1.0"
}
```

**API Docs:** http://localhost:8000/docs

#### 7.2 Test Dashboard

Open browser: http://localhost:3000

You should see the MCP Dashboard.

#### 7.3 Test Slack Bot

1. Open Slack
2. Find the MCP bot in "Apps"
3. Send it a DM: `hello`
4. Type: `/standup`

**You should get a response from MCP!**

### Step 8: First Standup

Let's do a full test:

**In Slack, DM the MCP bot:**

```
Yesterday: Set up the development environment
Today: Testing MCP for the first time
Planning to: Integrate with our Jira
Blockers: None yet!
```

**MCP should:**
- ✅ Acknowledge your standup
- ✅ Process it with Gemini
- ✅ Store in vector DB
- ✅ Show in dashboard

**Check the dashboard:** http://localhost:3000

## 🎉 You're Done!

MCP is now running! Here's what you can do next:

### For Developers

**Try a help request:**
```
Working on OAuth integration, need help from someone who knows OAuth
```

MCP will search for an expert (might not find one yet since it's new).

### For Managers

**Get team summary:**
```
/mcp-summary 7
```

**Assign a task:**
```
/mcp-assign @your-name Test MCP integration high
```

## 🛠️ Troubleshooting

### Problem: Slack bot not responding

**Check logs:**
```bash
docker-compose logs slack-bot
```

**Common issues:**
- Wrong `SLACK_BOT_TOKEN` or `SLACK_APP_TOKEN`
- Socket Mode not enabled
- Bot not installed to workspace

**Fix:**
1. Double-check tokens in `.env`
2. Restart: `docker-compose restart slack-bot`

### Problem: Backend errors

**Check logs:**
```bash
docker-compose logs mcp-backend
```

**Common issues:**
- Missing `GEMINI_API_KEY`
- Qdrant or Postgres not ready

**Fix:**
1. Verify API key in `.env`
2. Restart services: `docker-compose restart`

### Problem: Database connection errors

**Reset database:**
```bash
docker-compose down -v
docker-compose up -d
```

**⚠️ This deletes all data!**

### Problem: Port conflicts

If ports 8000, 3000, 5432, or 6333 are in use:

**Edit `docker-compose.yml`:**
```yaml
ports:
  - "8001:8000"  # Change 8000 -> 8001
```

### View all running containers

```bash
docker ps
```

### Restart everything

```bash
docker-compose down
docker-compose up -d
```

### Stop everything

```bash
docker-compose down
```

### Clean restart (deletes data)

```bash
docker-compose down -v
docker-compose up -d
```

## 📊 Next Steps

1. **Invite team members** to Slack
2. **Create demo tasks** to test help routing
3. **Try manager commands** like `/mcp-summary`
4. **Check the dashboard** for insights
5. **Set up Jira integration** (optional)

## 🎯 Advanced Configuration

### Jira Integration

Add to `.env`:
```env
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your_jira_api_token
ENABLE_JIRA_SYNC=true
```

Get Jira API token: [Atlassian Account](https://id.atlassian.com/manage-profile/security/api-tokens)

### Daily Standup Reminders

Coming soon! Will use APScheduler to send reminders at 9 AM.

### Production Deployment

For production, use:
- Railway / Render / Fly.io for hosting
- Managed Postgres (Railway, Supabase)
- Qdrant Cloud
- Environment variable secrets management

## 💬 Need Help?

- Check logs: `docker-compose logs -f`
- GitHub Issues: [Open an issue](https://github.com/your-repo/issues)
- Documentation: See `README.md`

---

**Happy building! 🚀**
