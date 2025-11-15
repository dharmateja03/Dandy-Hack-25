# 🧪 MCP Testing Guide

Complete guide to test all MCP features locally.

## 🚀 Quick Start (Automated)

```bash
# One command to test everything
./test_mcp.sh
```

This script will:
1. ✅ Check prerequisites (Docker, Docker Compose)
2. ✅ Verify .env configuration
3. ✅ Start all services
4. ✅ Wait for readiness
5. ✅ Seed demo data
6. ✅ Run API tests
7. ✅ Verify dashboard

---

## 📋 Manual Testing (Step-by-Step)

### Prerequisites

**Install:**
- Docker Desktop ([Download](https://www.docker.com/products/docker-desktop))
- Git (if you haven't cloned the repo yet)

**Get API Key:**
- Google Gemini API key from [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)

---

### Step 1: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Gemini API key
nano .env
# or
code .env
```

**Required:**
```env
GEMINI_API_KEY=AIza...your-key-here
```

**Optional (for Slack integration):**
```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

---

### Step 2: Start Services

```bash
# Clean start (removes old data)
docker-compose down -v

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

**Expected output:**
```
NAME                 STATUS
mcp-backend          Up
slack-bot            Up
qdrant               Up
postgres             Up
dashboard            Up
```

**View logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f mcp-backend
```

---

### Step 3: Wait for Services

Services need ~30-60 seconds to initialize.

**Check backend is ready:**
```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "mcp_status": "healthy",
  "vector_db": "healthy (1 collections)",
  "database": "healthy (0 users)",
  "llm": "gemini-pro"
}
```

If you see errors, check logs:
```bash
docker-compose logs mcp-backend
```

---

### Step 4: Seed Demo Data

```bash
./seed_data.sh
```

**This creates:**
- 5 users (Alice, Bob, Charlie, Diana, Eve)
- 7 tasks (various statuses)
- 8 standups (last 3 days)
- 3 help requests
- 1 blocker alert

**Expected output:**
```
🌱 Seeding MCP Demo Data...

Initializing services...
✅ Services initialized

👥 Creating demo users...
  ✅ Created user: Alice Johnson (manager)
  ✅ Created user: Bob Smith (senior_developer)
  ...

📋 Creating demo tasks...
  ✅ Created task: Implement OAuth 2.0 Authentication
  ...

💬 Creating demo standups...
  ✅ Standup from Bob Smith (0 days ago)
     🚨 Blockers: 1
     🤝 Help requests: 1
  ...

✅ Demo data seeded successfully!
```

---

### Step 5: Test Dashboard

**Open in browser:**
```
http://localhost:3000
```

**Check each tab:**

#### 1. Overview Tab
- ✅ 4 stat cards show numbers (standups, tasks, blockers, help requests)
- ✅ Weekly velocity chart displays (line chart)
- ✅ Recent activity shows standup items

#### 2. Standups Tab
- ✅ List of recent standups
- ✅ Shows user names, timestamps
- ✅ Tags for blockers/help requests/completed tasks

#### 3. Tasks Tab
- ✅ Grid of tasks
- ✅ Color-coded status badges
- ✅ Shows assignees

#### 4. Analytics Tab
- ✅ Task completion doughnut chart
- ✅ Blocker analysis bar chart

#### 5. Dependencies Tab
- ✅ Graphviz dependency graph renders
- ✅ Shows task relationships

**Auto-refresh:** Dashboard refreshes every 30 seconds

---

### Step 6: Test API Endpoints

**Open API docs:**
```
http://localhost:8000/docs
```

#### Test 1: Health Check
```bash
curl http://localhost:8000/health
```

#### Test 2: Get Recent Standups
```bash
curl http://localhost:8000/api/standups/recent?days=7
```

**Expected:** JSON with array of standups

#### Test 3: Query MCP (Semantic Search)
```bash
curl "http://localhost:8000/api/mcp/query?query=who%20knows%20OAuth&user_id=alice_manager"
```

**Expected:** JSON with:
```json
{
  "query": "who knows OAuth",
  "answer": "Based on the team context, Bob is the expert...",
  "sources": [...]
}
```

#### Test 4: Submit Standup
```bash
curl -X POST http://localhost:8000/api/standups/submit \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "message": "Yesterday: Set up testing environment\nToday: Running all tests\nNo blockers"
  }'
```

**Expected:** JSON with parsed data, help requests, etc.

#### Test 5: Get Team Summary
```bash
curl "http://localhost:8000/api/analytics/summary?days=7"
```

**Expected:** AI-generated summary of team activity

---

### Step 7: Test Scheduler (APScheduler)

**Check scheduler is running:**
```bash
docker-compose logs mcp-backend | grep -i scheduler
```

**Expected:**
```
✅ Scheduler initialized
```

**Scheduled jobs:**
- Daily 9 AM: Standup reminders
- Every 6 hours: Help request follow-ups
- Every 12 hours: Blocker escalation
- Friday 4 PM: Weekly summaries

**To test immediately** (modify scheduler time):
Edit `backend/services/scheduler.py` and change cron times to next minute.

---

### Step 8: Test Vector DB (Semantic Search)

**Verify Qdrant is working:**
```bash
curl http://localhost:6333/collections
```

**Test semantic search:**
```bash
# Query for OAuth expertise
curl -X POST "http://localhost:8000/api/mcp/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "who fixed authentication bugs", "user_id": "alice_manager"}'
```

Should return relevant results even if exact words don't match.

---

### Step 9: Test Slack Bot (Optional)

**If you have Slack configured:**

1. Open Slack workspace
2. Find MCP bot in Apps
3. Send DM: `/standup`
4. Bot should ask questions
5. Respond with standup update
6. Check dashboard - new standup should appear

**Test manager commands:**
```
/mcp-summary 7
/mcp-assign @user task description high
```

---

## 🐛 Troubleshooting

### Problem: Backend won't start

**Check logs:**
```bash
docker-compose logs mcp-backend
```

**Common issues:**
1. Missing `GEMINI_API_KEY` in .env
2. Qdrant or Postgres not ready

**Solution:**
```bash
docker-compose down -v
docker-compose up -d
# Wait 60 seconds
./seed_data.sh
```

---

### Problem: "MCP not initialized"

**Cause:** Backend hasn't finished starting

**Solution:** Wait longer, then check:
```bash
curl http://localhost:8000/health
```

---

### Problem: No standups in dashboard

**Cause:** Demo data not seeded

**Solution:**
```bash
./seed_data.sh
```

Refresh dashboard.

---

### Problem: Semantic search returns nothing

**Cause:** Vector DB not populated

**Check:**
```bash
curl http://localhost:6333/collections/mcp_context
```

**Solution:** Re-seed data.

---

### Problem: Dashboard shows "Failed to load"

**Check backend is running:**
```bash
curl http://localhost:8000/api/standups/recent
```

**Check CORS:** Backend should allow `localhost:3000`

**Solution:** Check browser console for errors.

---

### Problem: Port conflicts

**Error:** `port is already allocated`

**Solution:** Change ports in `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Change 8000 to 8001
```

---

## 📊 Expected Results

After successful testing:

### Dashboard Stats
- **Standups This Week:** 8
- **Active Tasks:** 7
- **Active Blockers:** 1
- **Help Requests:** 3

### Standups Tab
- 8 standup entries from 5 users
- Tags showing blockers, help requests, completed tasks

### Analytics
- Velocity chart showing upward trend
- Completion rate: ~14% completed, ~57% in progress
- Blockers by type distribution

### Dependencies Graph
- Visual graph showing task relationships
- Color-coded by status

---

## ✅ Verification Checklist

- [ ] Docker services running (5/5)
- [ ] Backend health check passes
- [ ] Qdrant has 1 collection
- [ ] Postgres has users table
- [ ] Demo data seeded (5 users, 7 tasks, 8 standups)
- [ ] Dashboard loads successfully
- [ ] All 5 tabs working
- [ ] Charts render correctly
- [ ] API endpoints respond
- [ ] Semantic search returns results
- [ ] Scheduler logs show initialization

---

## 🎯 Performance Benchmarks

**Startup time:** ~30-60 seconds for all services

**API response times:**
- Health check: <50ms
- Get standups: <200ms
- Submit standup (with Gemini): 1-3 seconds
- MCP query (semantic): 500ms-2s

**Dashboard load:** <1 second

---

## 🧹 Cleanup

**Stop services:**
```bash
docker-compose down
```

**Stop and remove all data:**
```bash
docker-compose down -v
```

**Remove Docker images:**
```bash
docker-compose down --rmi all
```

---

## 📝 Next Steps

After successful testing:

1. **Slack Integration:** Add bot tokens to `.env`, test in real workspace
2. **Jira Integration:** Add Jira credentials, test task sync
3. **Production Deploy:** Deploy to Railway/Render
4. **Custom Data:** Replace demo data with your team
5. **Customize:** Adjust scheduler times, add features

---

## 🆘 Still Having Issues?

1. Check logs: `docker-compose logs -f`
2. Verify .env file has valid API key
3. Try clean restart: `docker-compose down -v && docker-compose up -d`
4. Check [GitHub Issues](https://github.com/your-repo/issues)
5. Review SETUP_GUIDE.md

---

**Happy Testing! 🚀**
