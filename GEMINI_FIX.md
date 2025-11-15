# 🔧 Gemini API Model Update - Using Gemini 2.0 (Free Tier)

**Latest Update:** January 2025 - Using Gemini 2.0 Flash

## Current Models (Free Tier)

MCP now uses the **latest free Gemini models**:

✅ **Generative Model:** `gemini-2.0-flash`
- Latest Gemini 2.0 Flash (stable)
- **Free tier:** 15 RPM (requests per minute)
- Faster and more capable than 1.5
- Good for standup processing, summaries, parsing

✅ **Embedding Model:** `text-embedding-004`
- Latest embedding model
- **Free tier:** 1500 requests per day
- 768 dimensions
- Used for semantic search

## Model History

Google has updated model names multiple times:

| Date | Old Model | New Model |
|------|-----------|-----------|
| Jan 2025 | `gemini-pro` | `gemini-1.5-flash` |
| Jan 2025 | `gemini-1.5-flash` | `gemini-2.0-flash` |
| Jan 2025 | `embedding-001` | `text-embedding-004` |

## Free Tier Limits

**Gemini 2.0 Flash:**
- ✅ 15 requests per minute (RPM)
- ✅ 1,500 requests per day (RPD)
- ✅ 1 million tokens per minute (TPM)

**Text Embedding 004:**
- ✅ 1,500 requests per day
- ✅ 100 requests per minute

**More than enough for:**
- Small to medium teams (5-20 people)
- Daily standups
- Help request routing
- Team summaries

## Alternative Models

If you need more capacity or different capabilities:

### Production Models (Paid)

**`gemini-2.0-flash-001`** (Stable production version)
- More stable than `exp`
- Same capabilities
- Requires billing

**`gemini-1.5-pro-002`** (Most capable)
- Best quality
- 2M token context window
- Higher cost

### How to Switch Models

Edit `backend/config.py`:

```python
# For free tier (current)
GEMINI_MODEL: str = "gemini-2.0-flash"

# For maximum quality (paid)
GEMINI_MODEL: str = "gemini-1.5-pro-002"

# For experimental features (free)
GEMINI_MODEL: str = "gemini-2.0-flash-exp"
```

## If You See Errors

### Error: "404 model not found"

**Cause:** Google updated model names

**Solution:**
```bash
git pull origin claude/ai-standup-bot-hackathon-01JuN1kBvgSr3X2mxsQkSAQd
docker-compose restart mcp-backend
./seed_data.sh
```

### Error: "Quota exceeded"

**Cause:** Free tier limits reached

**Solutions:**
1. Wait for quota reset (resets daily)
2. Reduce frequency of requests
3. Upgrade to paid tier
4. Use caching to reduce API calls

### Error: "API key invalid"

**Cause:** Missing or wrong API key

**Solution:**
1. Get key from https://makersuite.google.com/app/apikey
2. Add to `.env`:
   ```env
   GEMINI_API_KEY=AIza...your-key-here
   ```
3. Restart: `docker-compose restart mcp-backend`

## Rate Limiting Strategy

MCP handles rate limits gracefully:

1. **Fallback embeddings** - Uses hash-based if quota exceeded
2. **Error logging** - Logs when hitting limits
3. **Retry logic** - Can add exponential backoff if needed

## Free Tier Usage Estimates

**For a team of 10 people:**

Daily usage:
- 10 standups/day × 1 request = 10 requests
- 5 help requests/day × 2 requests = 10 requests
- 1 summary/day × 1 request = 1 request
- **Total: ~21 requests/day**

**Well within free tier limits!** (1,500 RPD)

## Verify Current Model

```bash
# Check health endpoint
curl http://localhost:8000/health

# Should show:
{
  "llm": "gemini-2.0-flash (free)"
}
```

## Resources

- **Gemini API Docs:** https://ai.google.dev/docs
- **Pricing:** https://ai.google.dev/pricing
- **Model List:** https://ai.google.dev/models/gemini
- **Get API Key:** https://makersuite.google.com/app/apikey

---

**Current setup uses 100% free tier models!** 🎉

No credit card required for basic testing and small teams.
