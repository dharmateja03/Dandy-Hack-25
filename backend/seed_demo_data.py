"""
Seed Demo Data for MCP
Creates realistic fake users, tasks, standups, and help requests for presentation
"""

import asyncio
import sys
from datetime import datetime, timedelta
import random

from services.database import DatabaseService, UserRole, TaskStatus
from services.mcp_core import MCPCore
from services.vector_db import VectorDBService
from config import settings


# Demo team data
DEMO_USERS = [
    {
        "id": "alice_manager",
        "name": "Alice Johnson",
        "email": "alice@company.com",
        "role": UserRole.MANAGER,
        "manager_id": None,
        "team": "Engineering",
        "slack_user_id": "U001",
        "expertise_tags": ["leadership", "product", "strategy"]
    },
    {
        "id": "bob_senior",
        "name": "Bob Smith",
        "email": "bob@company.com",
        "role": UserRole.SENIOR_DEVELOPER,
        "manager_id": "alice_manager",
        "team": "Engineering",
        "slack_user_id": "U002",
        "expertise_tags": ["python", "backend", "architecture", "oauth", "authentication"]
    },
    {
        "id": "charlie_dev",
        "name": "Charlie Davis",
        "email": "charlie@company.com",
        "role": UserRole.DEVELOPER,
        "manager_id": "alice_manager",
        "team": "Engineering",
        "slack_user_id": "U003",
        "expertise_tags": ["react", "frontend", "ui/ux"]
    },
    {
        "id": "diana_dev",
        "name": "Diana Lee",
        "email": "diana@company.com",
        "role": UserRole.DEVELOPER,
        "manager_id": "alice_manager",
        "team": "Engineering",
        "slack_user_id": "U004",
        "expertise_tags": ["docker", "kubernetes", "devops", "ci/cd"]
    },
    {
        "id": "eve_intern",
        "name": "Eve Martinez",
        "email": "eve@company.com",
        "role": UserRole.INTERN,
        "manager_id": "bob_senior",
        "team": "Engineering",
        "slack_user_id": "U005",
        "expertise_tags": ["learning", "documentation"]
    }
]

DEMO_TASKS = [
    {
        "title": "Implement OAuth 2.0 Authentication",
        "description": "Add OAuth 2.0 support for user authentication",
        "assignee_id": "bob_senior",
        "status": TaskStatus.IN_PROGRESS,
        "priority": "high",
        "progress_percentage": 70
    },
    {
        "title": "Design User Dashboard UI",
        "description": "Create mockups and implement dashboard interface",
        "assignee_id": "charlie_dev",
        "status": TaskStatus.IN_PROGRESS,
        "priority": "high",
        "progress_percentage": 45
    },
    {
        "title": "Set up Docker CI/CD Pipeline",
        "description": "Configure Docker builds and automated deployments",
        "assignee_id": "diana_dev",
        "status": TaskStatus.COMPLETED,
        "priority": "medium",
        "progress_percentage": 100
    },
    {
        "title": "Write API Documentation",
        "description": "Document all REST API endpoints with examples",
        "assignee_id": "eve_intern",
        "status": TaskStatus.IN_PROGRESS,
        "priority": "medium",
        "progress_percentage": 30
    },
    {
        "title": "Implement Redis Caching Layer",
        "description": "Add Redis caching for frequently accessed data",
        "assignee_id": "bob_senior",
        "status": TaskStatus.NOT_STARTED,
        "priority": "medium",
        "progress_percentage": 0
    },
    {
        "title": "Fix Login Page Mobile Responsiveness",
        "description": "Login page doesn't display correctly on mobile devices",
        "assignee_id": "charlie_dev",
        "status": TaskStatus.BLOCKED,
        "priority": "high",
        "progress_percentage": 20
    },
    {
        "title": "Database Migration for User Profiles",
        "description": "Add new fields to user profile schema",
        "assignee_id": "diana_dev",
        "status": TaskStatus.IN_PROGRESS,
        "priority": "low",
        "progress_percentage": 60
    }
]

DEMO_STANDUPS = [
    # Bob's standups (last 3 days)
    {
        "user_id": "bob_senior",
        "days_ago": 0,
        "message": """Yesterday: Made good progress on OAuth integration, implemented the token refresh flow.
Today: Working on OAuth callback handling and error scenarios. Need help with session management - not sure about the best approach for token storage.
Blockers: Waiting on security review from InfoSec team before deploying.
Progress on OAuth: 70% complete"""
    },
    {
        "user_id": "bob_senior",
        "days_ago": 1,
        "message": """Yesterday: Started OAuth 2.0 implementation, got the basic flow working.
Today: Implementing token refresh and expiration handling.
No blockers, making steady progress."""
    },

    # Charlie's standups
    {
        "user_id": "charlie_dev",
        "days_ago": 0,
        "message": """Yesterday: Finished dashboard charts component.
Today: Working on the dashboard layout, hitting some React hooks issues.
Blockers: Login page is broken on mobile - design team hasn't sent updated mockups yet. This is blocking the dashboard work.
Need help: Could use React expert advice on state management"""
    },
    {
        "user_id": "charlie_dev",
        "days_ago": 1,
        "message": """Yesterday: Working on dashboard UI components.
Today: Building chart visualizations with Recharts.
No major blockers."""
    },

    # Diana's standups
    {
        "user_id": "diana_dev",
        "days_ago": 0,
        "message": """Yesterday: Completed Docker CI/CD pipeline setup! All tests passing.
Today: Starting database migration work, also helping Eve with documentation.
No blockers, smooth sailing."""
    },
    {
        "user_id": "diana_dev",
        "days_ago": 1,
        "message": """Yesterday: Debugging CI/CD pipeline issues.
Today: Finalizing Docker configuration and testing automated deployments.
Almost done!"""
    },

    # Eve's standups
    {
        "user_id": "eve_intern",
        "days_ago": 0,
        "message": """Yesterday: Worked on API documentation for authentication endpoints.
Today: Documenting the user management APIs. Learning a lot!
Could use some help understanding the OAuth flow for the docs - maybe Bob can explain?"""
    },
    {
        "user_id": "eve_intern",
        "days_ago": 1,
        "message": """Yesterday: Started API documentation project.
Today: Writing docs for auth endpoints.
No blockers."""
    }
]


async def seed_demo_data():
    """Seed the database with demo data"""

    print("\n🌱 Seeding MCP Demo Data...\n")

    # Initialize services
    print("Initializing services...")
    vector_db = VectorDBService(settings.QDRANT_URL)
    database = DatabaseService(settings.DATABASE_URL)

    await vector_db.initialize()
    await database.initialize()

    print("✅ Services initialized\n")

    # Initialize MCP Core
    print("Initializing MCP Core...")
    mcp = MCPCore(
        vector_db=vector_db,
        database=database,
        gemini_api_key=settings.GEMINI_API_KEY
    )
    await mcp.initialize()
    print("✅ MCP Core initialized\n")

    # 1. Create Users
    print("👥 Creating demo users...")
    for user_data in DEMO_USERS:
        try:
            await database.create_user(user_data)
            print(f"  ✅ Created user: {user_data['name']} ({user_data['role'].value})")
        except Exception as e:
            print(f"  ⚠️  User {user_data['name']} might already exist")
    print()

    # 2. Create Tasks
    print("📋 Creating demo tasks...")
    for task_data in DEMO_TASKS:
        try:
            task_id = await database.create_task(task_data)
            print(f"  ✅ Created task: {task_data['title']} (assigned to {task_data['assignee_id']})")
        except Exception as e:
            print(f"  ⚠️  Error creating task: {e}")
    print()

    # 3. Create Standups and Process Through MCP
    print("💬 Creating demo standups...")
    for standup_data in DEMO_STANDUPS:
        try:
            # Calculate timestamp
            timestamp = datetime.utcnow() - timedelta(days=standup_data['days_ago'])

            # Process through MCP (this adds to vector DB and parses with Gemini)
            result = await mcp.process_standup(
                user_id=standup_data['user_id'],
                message=standup_data['message'],
                timestamp=timestamp
            )

            # Also save to database
            user = await database.get_user(standup_data['user_id'])
            await database.save_standup(
                user_id=standup_data['user_id'],
                message=standup_data['message'],
                parsed_data=result.get('parsed_data', {})
            )

            print(f"  ✅ Standup from {user['name']} ({standup_data['days_ago']} days ago)")

            # Print what MCP extracted
            parsed = result.get('parsed_data', {})
            if parsed.get('blockers'):
                print(f"     🚨 Blockers: {len(parsed['blockers'])}")
            if parsed.get('help_requests'):
                print(f"     🤝 Help requests: {len(parsed['help_requests'])}")

        except Exception as e:
            print(f"  ⚠️  Error processing standup: {e}")
    print()

    # 4. Create Some Help Requests
    print("🤝 Creating demo help requests...")
    help_requests = [
        {
            "from_user": "bob_senior",
            "to_user": "diana_dev",
            "topic": "Session management best practices",
            "context": "Need advice on secure token storage for OAuth",
            "urgency": "medium"
        },
        {
            "from_user": "charlie_dev",
            "to_user": "bob_senior",
            "topic": "React state management",
            "context": "Dealing with complex state in dashboard component",
            "urgency": "low"
        },
        {
            "from_user": "eve_intern",
            "to_user": "bob_senior",
            "topic": "OAuth 2.0 flow explanation",
            "context": "Need to understand OAuth for documentation",
            "urgency": "low"
        }
    ]

    for req in help_requests:
        try:
            req_id = await database.create_help_request(**req)
            from_user = await database.get_user(req['from_user'])
            to_user = await database.get_user(req['to_user'])
            print(f"  ✅ Help request: {from_user['name']} → {to_user['name']} ({req['topic']})")
        except Exception as e:
            print(f"  ⚠️  Error creating help request: {e}")
    print()

    # 5. Create Some Blocker Alerts
    print("🚨 Creating blocker alerts...")
    blockers = [
        {
            "user_id": "charlie_dev",
            "manager_id": "alice_manager",
            "blocker_description": "Login page mobile responsiveness - waiting on design mockups",
            "severity": "high"
        }
    ]

    for blocker in blockers:
        try:
            await database.create_blocker_alert(**blocker)
            user = await database.get_user(blocker['user_id'])
            print(f"  ✅ Blocker alert: {user['name']} - {blocker['blocker_description']}")
        except Exception as e:
            print(f"  ⚠️  Error creating blocker: {e}")
    print()

    # 6. Generate Summary
    print("📊 Generating team summary...\n")
    summary = await mcp.generate_summary(days=3)
    print("="*60)
    print("TEAM SUMMARY (Last 3 Days)")
    print("="*60)
    print(summary)
    print("="*60)
    print()

    # Cleanup
    await mcp.cleanup()

    print("\n✅ Demo data seeded successfully!\n")
    print("Next steps:")
    print("  1. Start services: docker-compose up -d")
    print("  2. Visit dashboard: http://localhost:3000")
    print("  3. Check API docs: http://localhost:8000/docs")
    print("  4. Test in Slack!\n")


if __name__ == "__main__":
    # Run the seed script
    asyncio.run(seed_demo_data())
