# Stock Auto Trader - Service Management

This guide explains how to manage your Stock Auto Trader services.

## Quick Start

### Start Services
```bash
./start-services.sh
```

### Check Services Status
```bash
./check-services.sh
```

### Stop Services
```bash
./stop-services.sh
```

## Service Details

### Backend (FastAPI)
- **Port**: 8000
- **URL**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Location**: `stock-auto-trader/backend/`
- **Log**: `logs/backend.log`

### Frontend (React/Vite)
- **Port**: 5173 (or 5174, 3000)
- **URL**: http://localhost:5173
- **Location**: `stock-auto-trader/frontend/`
- **Log**: `logs/frontend.log`

## Monitoring Logs

### View Backend Logs
```bash
tail -f logs/backend.log
```

### View Frontend Logs
```bash
tail -f logs/frontend.log
```

### View Both Logs
```bash
tail -f logs/*.log
```

## Troubleshooting

### Issue: CORS Errors in Browser Console

**Symptoms:**
```
Access to XMLHttpRequest at 'http://localhost:8000/...' from origin 'http://localhost:5173'
has been blocked by CORS policy
```

**Solution:**
1. Make sure the backend is running: `./check-services.sh`
2. Restart services: `./stop-services.sh && ./start-services.sh`

### Issue: Database Enum Errors

**Symptoms:**
```
invalid input value for enum timeframe: "M15"
invalid input value for enum strategytype: "MTF_EMA"
```

**Solution:**
```bash
cd stock-auto-trader/backend
source venv/bin/activate
python fix_database_enum.py
python fix_all_enums.py
```

Then restart services:
```bash
cd ../..
./stop-services.sh
./start-services.sh
```

### Issue: Port Already in Use

**Solution:**
```bash
./stop-services.sh
sleep 2
./start-services.sh
```

### Issue: Services Won't Start

**Check Prerequisites:**

1. **Python virtual environment** (backend):
   ```bash
   cd stock-auto-trader/backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Node modules** (frontend):
   ```bash
   cd stock-auto-trader/frontend
   npm install
   ```

3. **PostgreSQL** database:
   ```bash
   # Check if PostgreSQL is running
   pg_isready

   # If not, start it (macOS with Homebrew):
   brew services start postgresql
   ```

4. **Environment variables**:
   - Check `stock-auto-trader/backend/.env` exists
   - Verify DATABASE_URL is correct

## Database Management

### Check Database Connection
```bash
cd stock-auto-trader/backend
source venv/bin/activate
python -c "from database import engine; print(engine.url)"
```

### Fix Database Enums (if needed)
```bash
cd stock-auto-trader/backend
source venv/bin/activate
python fix_database_enum.py
python fix_all_enums.py
```

## Service Management Scripts

### start-services.sh
- Checks if services are already running
- Offers to restart if needed
- Creates virtual environment if missing
- Installs dependencies if missing
- Starts backend and frontend
- Saves logs to `logs/` directory

### check-services.sh
- Shows which services are running
- Displays process IDs and ports
- Lists related processes (uvicorn, vite, python)
- Exit codes:
  - `0`: All services running
  - `1`: Some services running
  - `2`: No services running

### stop-services.sh
- Stops backend (port 8000)
- Stops frontend (ports 3000, 5173, 5174)
- Kills remaining uvicorn and vite processes

## Advanced Usage

### Manual Service Start

**Backend:**
```bash
cd stock-auto-trader/backend
source venv/bin/activate
python main.py
```

**Frontend:**
```bash
cd stock-auto-trader/frontend
npm run dev
```

### Check Specific Ports
```bash
lsof -ti:8000  # Backend
lsof -ti:5173  # Frontend
```

### Kill Specific Process
```bash
kill -9 <PID>
```

## API Endpoints

Once services are running, access:

- **Health Check**: http://localhost:8000/
- **API Documentation**: http://localhost:8000/docs
- **Stocks**: http://localhost:8000/stocks
- **Signals**: http://localhost:8000/signals/{symbol}?timeframe=1d
- **Portfolio**: http://localhost:8000/portfolio
- **Frontend**: http://localhost:5173

## Notes

- Logs are automatically created in `logs/` directory
- Services run in the background (nohup)
- Virtual environment is auto-created if missing
- Dependencies are auto-installed if missing
- CORS is configured for localhost:3000, 5173, and 5174
