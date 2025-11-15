# 🔧 Gemini API Model Update Fix

**Issue:** Google updated Gemini API model names on January 15, 2025.

## What Changed

Google renamed their models:
- ❌ Old: `gemini-pro` → ✅ New: `gemini-1.5-flash`
- ❌ Old: `models/embedding-001` → ✅ New: `models/text-embedding-004`

## Fixed Files

1. **backend/config.py** - Updated default model names
2. **backend/services/mcp_core.py** - Updated generative model
3. **backend/services/vector_db.py** - Updated embedding model

## If You See This Error

```
404 models/gemini-pro is not found for API version v1beta
```

**Solution:** Pull latest changes:

```bash
git pull origin claude/ai-standup-bot-hackathon-01JuN1kBvgSr3X2mxsQkSAQd

# Restart services
docker-compose down
docker-compose up -d

# Re-seed data
./seed_data.sh
```

## Manual Fix (If Needed)

If you modified the files locally:

**1. Edit `backend/config.py`:**
```python
GEMINI_MODEL: str = "gemini-1.5-flash"  # Change from "gemini-pro"
GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"  # Add this line
```

**2. Edit `backend/services/mcp_core.py` line 49:**
```python
self.model = genai.GenerativeModel('gemini-1.5-flash')  # Change from 'gemini-pro'
```

**3. Edit `backend/services/vector_db.py` line 90:**
```python
model="models/text-embedding-004",  # Change from "models/embedding-001"
```

**4. Restart:**
```bash
docker-compose restart mcp-backend
```

## Alternative Models

You can also use:
- `gemini-1.5-pro` (more powerful, slower, more expensive)
- `gemini-1.5-flash` (faster, cheaper, recommended)

## Verify Fix

```bash
# Check health endpoint
curl http://localhost:8000/health

# Should show:
{
  "llm": "gemini-1.5-flash"
}
```

---

**This fix is already applied in the latest commit.** Just pull and restart! 🚀
