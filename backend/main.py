"""
MCP (Model Context Protocol) - Main FastAPI Application
Central intelligence for team coordination and context management
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from services.mcp_core import MCPCore
from services.vector_db import VectorDBService
from services.database import DatabaseService
from services.scheduler import SchedulerService
from services.github_service import GitHubService
from services.linear_service import LinearService
from services.calendar_service import GoogleCalendarService
from services.expert_matcher import ExpertMatcher
from routers import standups, tasks, help_requests, analytics, users, github, expertise, blockers, workload, sprint
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
mcp_core = None
scheduler = None
db = None
github_service = None
linear_service = None
calendar_service = None
expert_matcher = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup MCP core services"""
    global mcp_core, scheduler, db, github_service, linear_service, calendar_service, expert_matcher

    logger.info("🚀 Initializing MCP (Model Context Protocol)...")

    # Initialize core services
    vector_db = VectorDBService(settings.QDRANT_URL)
    database = DatabaseService(settings.DATABASE_URL)
    db = database

    # Initialize MCP Core
    mcp_core = MCPCore(
        vector_db=vector_db,
        database=database,
        gemini_api_key=settings.GEMINI_API_KEY
    )

    await mcp_core.initialize()
    logger.info("✅ MCP initialized successfully")

    # Initialize GitHub integration (if configured)
    if settings.ENABLE_GITHUB_SYNC and settings.GITHUB_TOKEN:
        try:
            repo_list = settings.GITHUB_REPOS.split(',') if settings.GITHUB_REPOS else []
            github_service = GitHubService(
                github_token=settings.GITHUB_TOKEN,
                org_name=settings.GITHUB_ORG,
                repo_names=repo_list
            )
            if await github_service.test_connection():
                logger.info("✅ GitHub service initialized")
            else:
                logger.warning("⚠️ GitHub connection test failed")
                github_service = None
        except Exception as e:
            logger.error(f"❌ GitHub initialization failed: {e}")
            github_service = None
    else:
        logger.info("ℹ️ GitHub integration disabled")

    # Initialize Linear integration (if configured)
    if settings.ENABLE_LINEAR_SYNC and settings.LINEAR_API_KEY:
        try:
            linear_service = LinearService(
                api_key=settings.LINEAR_API_KEY,
                team_id=settings.LINEAR_TEAM_ID
            )
            if linear_service.test_connection():
                logger.info("✅ Linear service initialized")
            else:
                logger.warning("⚠️ Linear connection test failed")
                linear_service = None
        except Exception as e:
            logger.error(f"❌ Linear initialization failed: {e}")
            linear_service = None
    else:
        logger.info("ℹ️ Linear integration disabled")

    # Initialize Google Calendar integration (if configured)
    if settings.ENABLE_CALENDAR_SYNC and settings.GOOGLE_CALENDAR_CREDENTIALS:
        try:
            calendar_service = GoogleCalendarService(
                credentials_path=settings.GOOGLE_CALENDAR_CREDENTIALS,
                token_path=settings.GOOGLE_CALENDAR_TOKEN
            )
            if await calendar_service.initialize():
                logger.info("✅ Google Calendar service initialized")
            else:
                logger.warning("⚠️ Calendar initialization skipped (no credentials)")
                calendar_service = None
        except Exception as e:
            logger.error(f"❌ Calendar initialization failed: {e}")
            calendar_service = None
    else:
        logger.info("ℹ️ Google Calendar integration disabled")

    # Initialize Expert Matcher
    expert_matcher = ExpertMatcher(db_service=database, github_service=github_service)
    logger.info("✅ Expert Matcher initialized")

    # Initialize Scheduler
    scheduler = SchedulerService(mcp_core)
    await scheduler.initialize()
    logger.info("✅ Scheduler initialized")

    # Make services available to routers
    app.state.mcp = mcp_core
    app.state.db = database
    app.state.github = github_service
    app.state.linear = linear_service
    app.state.calendar = calendar_service
    app.state.expert_matcher = expert_matcher

    yield

    # Cleanup
    logger.info("🔄 Shutting down MCP...")
    if scheduler:
        await scheduler.shutdown()
    await mcp_core.cleanup()
    logger.info("✅ MCP shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="MCP - Model Context Protocol",
    description="Central intelligence for team coordination and context management",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(standups.router, prefix="/api/standups", tags=["Standups"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(help_requests.router, prefix="/api/help", tags=["Help Requests"])
app.include_router(blockers.router, prefix="/api/blockers", tags=["Blockers"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(workload.router, prefix="/api/workload", tags=["Workload"])
app.include_router(sprint.router, prefix="/api/sprint", tags=["Sprint"])
app.include_router(github.router, tags=["GitHub"])
app.include_router(expertise.router, tags=["Expertise"])

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "MCP - Model Context Protocol",
        "version": "0.1.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    global mcp_core

    if mcp_core is None:
        raise HTTPException(status_code=503, detail="MCP not initialized")

    health_status = await mcp_core.health_check()
    return health_status

@app.get("/api/mcp/query")
async def query_mcp(query: str, user_id: str):
    """
    Query MCP with natural language
    This is the core protocol interface
    """
    global mcp_core

    if mcp_core is None:
        raise HTTPException(status_code=503, detail="MCP not initialized")

    result = await mcp_core.query(query=query, user_id=user_id)
    return result

@app.post("/api/mcp/add-context")
async def add_context(context_data: dict):
    """
    Add context to MCP
    Any interface can use this to feed information
    """
    global mcp_core

    if mcp_core is None:
        raise HTTPException(status_code=503, detail="MCP not initialized")

    result = await mcp_core.add_context(context_data)
    return {"status": "success", "context_id": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
