# ⚡ MCP Quick Start

Get MCP running in 5 minutes.

## 🎯 Prerequisites

- Docker Desktop installed
- Google Gemini API key ([Get one](https://makersuite.google.com/app/apikey))

## 🚀 Steps

### 1. Clone & Configure

```bash
# Clone repository
git clone <your-repo-url>
cd Dandy-Hack-25

# Create .env from template
cp .env.example .env

# Edit .env - add your Gemini API key
nano .env
```

**Required in .env:**
```env
GEMINI_API_KEY=AIza...your-key-here
```

### 2. Test Everything

```bash
# One command to rule them all
./test_mcp.sh
```

This will:
- ✅ Start all Docker services
- ✅ Seed demo data (5 users, 7 tasks, 8 standups)
- ✅ Run API tests
- ✅ Verify everything works

**Time:** ~2 minutes

### 3. Explore

**Dashboard:**
```
http://localhost:3000
```

**API Docs:**
```
http://localhost:8000/docs
```

**Try it:**
```bash
# Get team summary
curl "http://localhost:8000/api/analytics/summary?days=7"

# Semantic search
curl "http://localhost:8000/api/mcp/query?query=who%20knows%20OAuth&user_id=alice_manager"
```

## 🎭 Demo Data Included

**Users:**
- Alice (Manager)
- Bob (Senior Dev - OAuth expert)
- Charlie (Dev - React)
- Diana (Dev - DevOps)
- Eve (Intern)

**Tasks:**
- 7 tasks (various statuses)
- OAuth implementation 70% done
- Docker CI/CD completed ✅
- Mobile login blocked 🚨

**Standups:**
- 8 realistic standup updates
- Last 3 days of history
- Blockers, help requests

## 📊 What You'll See

**Dashboard has 5 tabs:**

1. **Overview** - Stats, velocity chart, recent activity
2. **Standups** - All team updates with tags
3. **Tasks** - Task grid with status badges
4. **Analytics** - Completion rate, blocker analysis charts
5. **Dependencies** - Visual task dependency graph

## 🔧 Useful Commands

```bash
# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop everything
docker-compose down

# Clean restart (deletes data)
docker-compose down -v && docker-compose up -d
./seed_data.sh
```

## 🐛 Troubleshooting

**Services not starting?**
```bash
docker-compose down -v
docker-compose up -d
# Wait 60 seconds
./seed_data.sh
```

**No data in dashboard?**
```bash
./seed_data.sh
```

**Port conflicts?**

Edit `docker-compose.yml` and change port numbers.

## 📚 More Info

- **Full Testing Guide:** See `TESTING.md`
- **Setup Guide:** See `SETUP_GUIDE.md`
- **Feature List:** See `FEATURES.md`
- **README:** See `README.md`

## 🎯 Next Steps

1. ✅ **Slack Integration** - Add bot to your workspace
2. ✅ **Jira Sync** - Connect to your Jira
3. ✅ **Deploy** - Deploy to Railway/Render
4. ✅ **Customize** - Adjust for your team

---

**Questions? Check TESTING.md for detailed troubleshooting.**

**Ready to demo? Everything works out of the box!** 🚀
