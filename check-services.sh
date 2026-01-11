#!/bin/bash

echo "🔍 Checking Stock Auto Trader Services Status..."
echo "================================================"

# Function to check if a port is in use
check_port() {
  local port=$1
  local service_name=$2
  local pid=$(lsof -ti:$port 2>/dev/null)

  if [ -n "$pid" ]; then
    local process_name=$(ps -p $pid -o comm= 2>/dev/null)
    local cmd=$(ps -p $pid -o args= 2>/dev/null | head -c 80)
    echo "✅ $service_name is RUNNING"
    echo "   Port: $port"
    echo "   PID: $pid"
    echo "   Process: $process_name"
    echo "   Command: $cmd"
    return 0
  else
    echo "❌ $service_name is NOT RUNNING"
    echo "   Expected port: $port"
    return 1
  fi
}

# Check Backend (FastAPI/uvicorn on port 8000)
echo ""
echo "Backend (FastAPI):"
echo "-------------------"
check_port 8000 "Backend API"
BACKEND_STATUS=$?

# Check Frontend (Vite on ports 3000, 5173, or 5174)
echo ""
echo "Frontend (React/Vite):"
echo "----------------------"
FRONTEND_STATUS=1
for PORT in 3000 5173 5174; do
  pid=$(lsof -ti:$PORT 2>/dev/null)
  if [ -n "$pid" ]; then
    check_port $PORT "Frontend Dev Server"
    FRONTEND_STATUS=0
    break
  fi
done

if [ $FRONTEND_STATUS -eq 1 ]; then
  echo "❌ Frontend is NOT RUNNING"
  echo "   Expected ports: 3000, 5173, or 5174"
fi

# Additional process checks
echo ""
echo "Related Processes:"
echo "-------------------"

# Check for uvicorn processes
UVICORN_PIDS=$(pgrep -f "uvicorn" 2>/dev/null)
if [ -n "$UVICORN_PIDS" ]; then
  echo "📦 Uvicorn processes found:"
  ps -p $UVICORN_PIDS -o pid,ppid,cmd | grep -v "PID"
else
  echo "   No uvicorn processes running"
fi

# Check for Vite processes
VITE_PIDS=$(pgrep -f "vite" 2>/dev/null)
if [ -n "$VITE_PIDS" ]; then
  echo "📦 Vite processes found:"
  ps -p $VITE_PIDS -o pid,ppid,cmd | grep -v "PID"
else
  echo "   No vite processes running"
fi

# Check for Python processes related to the project
PYTHON_PIDS=$(pgrep -f "main.py" 2>/dev/null)
if [ -n "$PYTHON_PIDS" ]; then
  echo "🐍 Python main.py processes:"
  ps -p $PYTHON_PIDS -o pid,ppid,cmd | grep -v "PID"
fi

# Summary
echo ""
echo "================================================"
echo "Summary:"
if [ $BACKEND_STATUS -eq 0 ] && [ $FRONTEND_STATUS -eq 0 ]; then
  echo "✅ All services are running"
  exit 0
elif [ $BACKEND_STATUS -eq 0 ] || [ $FRONTEND_STATUS -eq 0 ]; then
  echo "⚠️  Some services are running"
  exit 1
else
  echo "❌ No services are running"
  exit 2
fi
