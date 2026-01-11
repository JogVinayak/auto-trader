#!/bin/bash

echo "🚀 Starting Stock Auto Trader Services..."
echo "=========================================="

# Color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directories
BACKEND_DIR="/Users/Vinayak/stock-trader/auto-trader/stock-auto-trader/backend"
FRONTEND_DIR="/Users/Vinayak/stock-trader/auto-trader/stock-auto-trader/frontend"
LOG_DIR="/Users/Vinayak/stock-trader/auto-trader/logs"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Log files
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

# Function to check if a port is already in use
check_port() {
  local port=$1
  local service=$2
  if lsof -ti:$port >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Port $port is already in use by $service${NC}"
    echo "   Run './stop-services.sh' first to stop existing services"
    return 1
  fi
  return 0
}

# Check if services are already running
echo ""
echo "Checking for existing services..."
if lsof -ti:8000 >/dev/null 2>&1 || lsof -ti:3000 >/dev/null 2>&1 || lsof -ti:5173 >/dev/null 2>&1 || lsof -ti:5174 >/dev/null 2>&1; then
  echo -e "${YELLOW}⚠️  Some services are already running!${NC}"
  echo ""
  echo "Current status:"
  ./check-services.sh
  echo ""
  read -p "Do you want to restart services? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Stopping existing services..."
    ./stop-services.sh
    sleep 2
  else
    echo "Aborted."
    exit 1
  fi
fi

# Start Backend
echo ""
echo "Starting Backend (FastAPI)..."
echo "------------------------------"

if [ ! -d "$BACKEND_DIR" ]; then
  echo -e "${RED}❌ Backend directory not found: $BACKEND_DIR${NC}"
  exit 1
fi

cd "$BACKEND_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
  echo -e "${YELLOW}⚠️  Virtual environment not found. Creating one...${NC}"
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
else
  source venv/bin/activate
fi

# Start backend in background
echo "Starting uvicorn server on port 8000..."
nohup python main.py > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

# Wait a moment and check if it started successfully
sleep 2
if ps -p $BACKEND_PID > /dev/null; then
  echo -e "${GREEN}✅ Backend started successfully (PID: $BACKEND_PID)${NC}"
  echo "   Log: $BACKEND_LOG"
  echo "   URL: http://localhost:8000"
else
  echo -e "${RED}❌ Failed to start backend. Check logs: $BACKEND_LOG${NC}"
  tail -20 "$BACKEND_LOG"
  exit 1
fi

# Start Frontend
echo ""
echo "Starting Frontend (React/Vite)..."
echo "----------------------------------"

if [ ! -d "$FRONTEND_DIR" ]; then
  echo -e "${RED}❌ Frontend directory not found: $FRONTEND_DIR${NC}"
  exit 1
fi

cd "$FRONTEND_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
  echo -e "${YELLOW}⚠️  node_modules not found. Installing dependencies...${NC}"
  npm install
fi

# Start frontend in background
echo "Starting Vite dev server..."
nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

# Wait a moment and check if it started successfully
sleep 3
if ps -p $FRONTEND_PID > /dev/null; then
  # Try to detect which port Vite is using
  VITE_PORT=""
  for port in 5173 5174 3000; do
    if lsof -ti:$port >/dev/null 2>&1; then
      VITE_PORT=$port
      break
    fi
  done

  echo -e "${GREEN}✅ Frontend started successfully (PID: $FRONTEND_PID)${NC}"
  echo "   Log: $FRONTEND_LOG"
  if [ -n "$VITE_PORT" ]; then
    echo "   URL: http://localhost:$VITE_PORT"
  else
    echo "   URL: Check logs for the actual port"
  fi
else
  echo -e "${RED}❌ Failed to start frontend. Check logs: $FRONTEND_LOG${NC}"
  tail -20 "$FRONTEND_LOG"
  exit 1
fi

# Final status check
echo ""
echo "=========================================="
echo "🎉 All services started!"
echo ""
echo "Service URLs:"
echo "  Backend API:  http://localhost:8000"
echo "  API Docs:     http://localhost:8000/docs"
if [ -n "$VITE_PORT" ]; then
  echo "  Frontend:     http://localhost:$VITE_PORT"
fi
echo ""
echo "Logs are being written to:"
echo "  Backend:  $BACKEND_LOG"
echo "  Frontend: $FRONTEND_LOG"
echo ""
echo "To view logs in real-time:"
echo "  Backend:  tail -f $BACKEND_LOG"
echo "  Frontend: tail -f $FRONTEND_LOG"
echo ""
echo "To check status: ./check-services.sh"
echo "To stop services: ./stop-services.sh"
echo "=========================================="
