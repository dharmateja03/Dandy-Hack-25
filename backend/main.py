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
from routers import standups, tasks, help_requests, analytics, users
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup MCP core services"""
    global mcp_core, scheduler

    logger.info("🚀 Initializing MCP (Model Context Protocol)...")

    # Initialize services
    vector_db = VectorDBService(settings.QDRANT_URL)
    database = DatabaseService(settings.DATABASE_URL)

    # Initialize MCP Core
    mcp_core = MCPCore(
        vector_db=vector_db,
        database=database,
        gemini_api_key=settings.GEMINI_API_KEY
    )

    await mcp_core.initialize()
    logger.info("✅ MCP initialized successfully")

    # Initialize Scheduler
    scheduler = SchedulerService(mcp_core)
    await scheduler.initialize()
    logger.info("✅ Scheduler initialized")

    # Make MCP available to routers
    app.state.mcp = mcp_core

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
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])

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
