# 🧠 MCP - Model Context Protocol

**AI Mission Control for Engineering Teams**

MCP is an intelligent coordination system that maintains context of everything happening in your team, routes information intelligently, and provides managers with real-time visibility.

## 🎯 The Problem

- **Information overload**: Slack has 100+ channels, critical updates get lost
- **Scattered context**: No single source of truth for team activities
- **Blind managers**: Hard to know what's blocking the team
- **Inefficient help**: People @ mention the wrong person or nobody responds

## ✨ The Solution

**One AI entity** that:
- 🧠 **Knows everything** - Maintains context of all team activities
- 🎯 **Routes intelligently** - Connects the right people based on expertise
- 📊 **Provides visibility** - Managers get real-time insights
- 🤖 **Learns continuously** - Gets smarter from every interaction

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         MCP Core (The Brain)            │
│  ┌───────────────────────────────────┐  │
│  │  Vector DB (Qdrant)               │  │
│  │  - All context as embeddings      │  │
│  │  - Semantic search capability     │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Intelligence (Gemini)            │  │
│  │  - Parse standups                 │  │
│  │  - Route help requests            │  │
│  │  - Generate insights              │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Database (PostgreSQL)            │  │
│  │  - Users, tasks, hierarchy        │  │
│  │  - Structured data                │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
              ↕️ REST API
    ┌──────────┬───────────┬──────────┐
    │          │           │          │
┌───▼────┐ ┌──▼─────┐ ┌───▼────┐ ┌──▼─────┐
│ Slack  │ │  Web   │ │ Future │ │ Jira   │
│  Bot   │ │Dashboard│ │Clients │ │Webhook │
└────────┘ └────────┘ └────────┘ └────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Google Gemini API key ([Get it here](https://makersuite.google.com/app/apikey))
- Slack workspace (for bot integration)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd Dandy-Hack-25

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 2. Configure Slack Bot

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name it "MCP" and select your workspace

**Required Bot Token Scopes:**
- `chat:write`
- `im:write`
- `im:history`
- `users:read`
- `channels:read`
- `groups:write`
- `mpim:write`

**Event Subscriptions:**
- Enable Socket Mode
- Subscribe to: `message.im`, `app_mention`

**Slash Commands:**
- `/standup` - Trigger daily standup
- `/mcp-summary` - Get team summary (managers)
- `/mcp-assign` - Assign tasks (managers)

4. Copy **Bot Token** (`xoxb-...`) to `.env` as `SLACK_BOT_TOKEN`
5. Enable Socket Mode and copy **App Token** (`xapp-...`) to `.env` as `SLACK_APP_TOKEN`

### 3. Start MCP

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Verify services are running
docker-compose ps
```

**Services:**
- Backend API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- Dashboard: http://localhost:3000
- Qdrant: http://localhost:6333
- PostgreSQL: localhost:5432

### 4. Test the Bot

In Slack:
1. DM the MCP bot
2. Type `/standup`
3. Answer the questions
4. Watch MCP process your update!

## 📚 Usage

### Daily Standups

**Trigger via command:**
```
/standup
```

**Or just DM MCP:**
```
Yesterday: Completed user auth API
Today: Working on Redis caching, need help with session management
Blockers: Waiting on design mockups
```

MCP will:
- ✅ Parse and extract structured data
- ✅ Route help requests to experts
- ✅ Alert manager about blockers
- ✅ Update task statuses

### Help Requests

**In your standup, mention help needed:**
```
Working on OAuth integration, need help from someone with OAuth experience
```

MCP will:
1. 🔍 Search for team members with OAuth expertise
2. ✅ Find available expert (not overloaded)
3. 💬 Create 3-person group chat (you + expert + MCP)
4. 📝 Learn from the conversation

### Manager Commands

**Get team summary:**
```
/mcp-summary 7
```

**Assign a task:**
```
/mcp-assign @john Implement Redis caching high
```

**Ask questions:**
```
@MCP what's blocking Sarah?
@MCP who knows about Docker?
@MCP summarize this week
```

### Natural Language Queries

Just ask MCP anything:
- "Who worked on the authentication system?"
- "Show me tasks blocked more than 2 days"
- "What are the top blockers this week?"

## 🛠️ Development

### Project Structure

```
mcp-product/
├── backend/                # FastAPI backend (MCP Core)
│   ├── main.py            # FastAPI app
│   ├── config.py          # Configuration
│   ├── services/          # Core services
│   │   ├── mcp_core.py   # MCP intelligence
│   │   ├── vector_db.py  # Qdrant interface
│   │   └── database.py   # PostgreSQL models
│   └── routers/           # API endpoints
├── slack-bot/             # Slack integration
│   └── app.py            # Bolt app
├── dashboard/             # Web dashboard
│   └── index.html        # Minimal UI
└── docker-compose.yml     # Infrastructure
```

### Adding Features

**Add a new context source:**

```python
# Any service can add context to MCP
await mcp_core.add_context({
    "type": "github_commit",
    "user_id": "john",
    "text": "Fixed OAuth bug in user service",
    "metadata": {"repo": "backend", "commit": "abc123"}
})
```

**Query context semantically:**

```python
# Semantic search across all context
results = await mcp_core.query(
    query="Who fixed OAuth bugs recently?",
    user_id="manager_id"
)
```

### API Endpoints

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Submit Standup:**
```bash
curl -X POST http://localhost:8000/api/standups/submit \
  -H "Content-Type: application/json" \
  -d '{"user_id": "john", "message": "Working on feature X"}'
```

**Query MCP:**
```bash
curl -X POST "http://localhost:8000/api/mcp/query?query=who%20knows%20React&user_id=john"
```

## 🎯 Roadmap

### Phase 1: MVP (Current) ✅
- [x] Core MCP backend
- [x] Vector DB for context storage
- [x] Gemini integration
- [x] Slack bot (standups, help routing)
- [x] Minimal dashboard

### Phase 2: Intelligence
- [ ] Advanced help routing (workload balancing)
- [ ] Proactive blocker detection
- [ ] Recurring issue tracking
- [ ] Velocity analytics

### Phase 3: Integrations
- [ ] Jira two-way sync
- [ ] GitHub webhook integration
- [ ] Calendar integration
- [ ] Linear, Asana support

### Phase 4: Scale
- [ ] Multi-team support
- [ ] Advanced analytics dashboard
- [ ] Dependency graph visualization
- [ ] Predictive insights

## 🤝 Contributing

This is a YC application project. Contributions welcome!

1. Fork the repo
2. Create feature branch
3. Make changes
4. Submit pull request

## 📄 License

MIT License

## 🙋 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Slack**: Join our community
- **Email**: support@mcp.dev

---

Built with ❤️ for engineering teams who want to move faster.

**MCP - One AI that knows everything, so you don't have to.**
