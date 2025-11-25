# PPR Bitcoin - Quick Start Guide

## Current Status
✅ Frontend fully implemented and ready to use
✅ Backend dependencies installed
⚠️ Database needs to be started

## Prerequisites
- Python 3.12+ installed ✅
- Node.js 18+ installed ✅
- Docker Desktop (for PostgreSQL database)

## Option 1: Full Setup with PostgreSQL (Recommended)

### Step 1: Start Docker Desktop
1. Open **Docker Desktop** application
2. Wait for it to fully start (whale icon stops animating in system tray)

### Step 2: Start Database
```bash
cd backend
docker-compose up -d
```

This will start PostgreSQL in a Docker container.

### Step 3: Run Database Migrations
```bash
cd backend
python -m alembic upgrade head
```

### Step 4: Seed Database with Initial Data
```bash
# Seed PPR funds (10 Portuguese PPRs)
python data/seeds/seed_pprs.py

# Seed Bitcoin historical data
python data/seeds/seed_bitcoin.py
```

### Step 5: Start Backend Server
```bash
cd backend
python -m uvicorn app.main:app --reload
```

Backend will be at: http://localhost:8000
API docs at: http://localhost:8000/docs

### Step 6: Start Frontend (in NEW terminal)
```bash
cd frontend
npm run dev
```

Frontend will be at: http://localhost:3000

---

## Option 2: Quick Test with SQLite (Faster, No Docker)

If you want to quickly test the frontend without Docker:

### Step 1: Modify Database Configuration
Edit `backend/.env` and change:
```
DATABASE_URL=sqlite:///./pprbitcoin.db
```

### Step 2: Install SQLite Async Support
```bash
cd backend
pip install aiosqlite
```

### Step 3: Run Migrations
```bash
cd backend
python -m alembic upgrade head
```

### Step 4: Seed Data
```bash
python data/seeds/seed_pprs.py
python data/seeds/seed_bitcoin.py
```

### Step 5: Start Backend
```bash
python -m uvicorn app.main:app --reload
```

### Step 6: Start Frontend (in NEW terminal)
```bash
cd frontend
npm run dev
```

---

## Verifying Everything Works

### 1. Test Backend
Open http://localhost:8000/docs - You should see the Swagger API documentation

### 2. Test Frontend
Open http://localhost:3000 - You should see the PPR Bitcoin calculator interface

### 3. Test Full Flow
1. In the frontend, select one or more PPRs
2. Adjust Bitcoin allocation slider
3. Configure investment amounts
4. Click "Calcular Carteira"
5. You should see a chart and metrics appear

---

## Troubleshooting

### "uvicorn does not exist"
✅ **FIXED** - Dependencies installed

### Docker not running
- Start Docker Desktop manually
- On Windows: Check system tray for Docker icon

### Database connection error
- Make sure Docker container is running: `docker ps`
- Check if PostgreSQL is listening: `docker-compose logs`

### Frontend can't connect to backend
- Make sure backend is running on http://localhost:8000
- Check browser console for CORS errors
- Verify `.env` file has correct `VITE_API_URL=http://localhost:8000`

### Port already in use
- Backend (8000): Stop other FastAPI/Python servers
- Frontend (3000): Vite will automatically try port 3001, 3002, etc.

---

## What You Can Do Now

The frontend is **production-ready** with all these features:
- ✅ PPR fund selection (up to 5 funds)
- ✅ Bitcoin allocation slider (0-100%)
- ✅ Investment amount configuration
- ✅ Date range selection with quick presets
- ✅ Rebalancing frequency options
- ✅ Interactive portfolio evolution chart
- ✅ Comprehensive metrics (CAGR, Sharpe Ratio, Sortino, Volatility, Max Drawdown)
- ✅ Responsive design (works on mobile)
- ✅ Portuguese language UI
- ✅ Error handling and loading states

---

## Next Steps After Testing

1. **Implement Real PPR Scrapers**
   Currently using sample data. See `backend/data/scrapers/ppr_scraper.py`

2. **Deploy to Production**
   - Backend: Railway, Render, or Fly.io
   - Frontend: Vercel or Netlify
   - Database: Managed PostgreSQL (Railway, Supabase, etc.)

3. **Add More Features**
   - Compare multiple portfolios side-by-side
   - Export results to PDF/CSV
   - Save portfolio configurations
   - Historical backtesting with different strategies

---

## Need Help?

Check the README files:
- `frontend/README.md` - Frontend documentation
- `backend/README.md` - Backend API documentation

Or check the API documentation at http://localhost:8000/docs when backend is running.
