#!/bin/bash

# Script to seed demo data into MCP

echo "🌱 Seeding MCP Demo Data..."
echo ""

# Check if backend container is running
if ! docker ps | grep -q mcp-backend; then
    echo "❌ Backend container not running!"
    echo "Please start services first: docker-compose up -d"
    exit 1
fi

# Run seed script inside backend container
docker-compose exec mcp-backend python seed_demo_data.py

echo ""
echo "✅ Done! Check the dashboard at http://localhost:3000"
