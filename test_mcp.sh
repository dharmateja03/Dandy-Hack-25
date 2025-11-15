#!/bin/bash

# 🧪 MCP Quick Test Script
# Run this on your local machine to test the MCP system

set -e  # Exit on error

echo "🧪 MCP Testing Script"
echo "===================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check prerequisites
echo "📋 Step 1: Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker Desktop.${NC}"
    exit 1
fi
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found. Please install Docker Compose.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker and Docker Compose found${NC}"
echo ""

# Step 2: Check .env file
echo "📋 Step 2: Checking environment configuration..."
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${RED}❌ Please edit .env and add your API keys:${NC}"
    echo "   - GEMINI_API_KEY (required)"
    echo "   - SLACK_BOT_TOKEN (optional for testing)"
    echo "   - SLACK_APP_TOKEN (optional for testing)"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Check if GEMINI_API_KEY is set
if grep -q "your_gemini_api_key_here" .env; then
    echo -e "${RED}❌ Please add your Gemini API key to .env${NC}"
    echo "   Get one here: https://makersuite.google.com/app/apikey"
    exit 1
fi
echo -e "${GREEN}✅ Environment configured${NC}"
echo ""

# Step 3: Start services
echo "🚀 Step 3: Starting MCP services..."
docker-compose down -v  # Clean start
docker-compose up -d
echo -e "${GREEN}✅ Services starting...${NC}"
echo ""

# Step 4: Wait for services to be ready
echo "⏳ Step 4: Waiting for services to be ready..."
echo "   This may take 30-60 seconds..."
sleep 10

# Check if backend is ready
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Backend didn't start. Check logs with: docker-compose logs mcp-backend${NC}"
        exit 1
    fi
    echo "   Still waiting... ($i/30)"
    sleep 2
done
echo ""

# Step 5: Seed demo data
echo "🌱 Step 5: Seeding demo data..."
./seed_data.sh
echo ""

# Step 6: Run tests
echo "🧪 Step 6: Running API tests..."

# Test 1: Health check
echo "Test 1: Health check..."
HEALTH=$(curl -s http://localhost:8000/health)
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
    echo "$HEALTH"
fi

# Test 2: Get recent standups
echo "Test 2: Get recent standups..."
STANDUPS=$(curl -s http://localhost:8000/api/standups/recent?days=7)
if echo "$STANDUPS" | grep -q "standups"; then
    STANDUP_COUNT=$(echo "$STANDUPS" | grep -o '"user_id"' | wc -l)
    echo -e "${GREEN}✅ Found $STANDUP_COUNT standups${NC}"
else
    echo -e "${RED}❌ Failed to get standups${NC}"
fi

# Test 3: Query MCP
echo "Test 3: Query MCP (semantic search)..."
QUERY_RESULT=$(curl -s "http://localhost:8000/api/mcp/query?query=who%20knows%20OAuth&user_id=alice_manager")
if echo "$QUERY_RESULT" | grep -q "answer"; then
    echo -e "${GREEN}✅ MCP query successful${NC}"
    echo "   Answer: $(echo "$QUERY_RESULT" | grep -o '"answer":"[^"]*"' | cut -d'"' -f4 | head -c 100)..."
else
    echo -e "${RED}❌ MCP query failed${NC}"
fi

# Test 4: Check dashboard
echo "Test 4: Check dashboard..."
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Dashboard is accessible${NC}"
else
    echo -e "${RED}❌ Dashboard not accessible${NC}"
fi

echo ""
echo "================================"
echo "🎉 Testing Complete!"
echo "================================"
echo ""
echo "📊 Access Points:"
echo "   • Dashboard:    http://localhost:3000"
echo "   • API Docs:     http://localhost:8000/docs"
echo "   • Health:       http://localhost:8000/health"
echo ""
echo "📝 Useful Commands:"
echo "   • View logs:    docker-compose logs -f"
echo "   • Stop:         docker-compose down"
echo "   • Restart:      docker-compose restart"
echo ""
echo "🧪 Manual Tests:"
echo "   • Open dashboard in browser"
echo "   • Check Overview tab for charts"
echo "   • Check Standups tab for recent updates"
echo "   • Check Analytics tab for graphs"
echo "   • Check Dependencies tab for task graph"
echo ""
