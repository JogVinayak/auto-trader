#!/bin/bash

echo "🛑 Stopping Stock Auto Trader Services..."

# Stop FastAPI backend (running on port 8000)
echo ""
echo "Stopping backend (FastAPI on port 8000)..."
BACKEND_PID=$(lsof -ti:8000)
if [ -n "$BACKEND_PID" ]; then
  kill -9 $BACKEND_PID
  echo "✅ Backend stopped (PID: $BACKEND_PID)"
else
  echo "ℹ️  Backend not running on port 8000"
fi

# Stop frontend (Vite dev server on ports 3000, 5173, or 5174)
echo ""
echo "Stopping frontend (Vite)..."
for PORT in 3000 5173 5174; do
  FRONTEND_PID=$(lsof -ti:$PORT)
  if [ -n "$FRONTEND_PID" ]; then
    kill -9 $FRONTEND_PID
    echo "✅ Frontend stopped on port $PORT (PID: $FRONTEND_PID)"
  fi
done

# Check if any Vite processes are still running
VITE_PIDS=$(pgrep -f "vite")
if [ -n "$VITE_PIDS" ]; then
  echo ""
  echo "Stopping remaining Vite processes..."
  kill -9 $VITE_PIDS
  echo "✅ Vite processes stopped"
fi

# Check for uvicorn processes (FastAPI server)
UVICORN_PIDS=$(pgrep -f "uvicorn")
if [ -n "$UVICORN_PIDS" ]; then
  echo ""
  echo "Stopping remaining uvicorn processes..."
  kill -9 $UVICORN_PIDS
  echo "✅ Uvicorn processes stopped"
fi

echo ""
echo "✅ All services stopped successfully!"
