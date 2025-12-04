# GoalShock v1.1 - Real-Time Soccer Goal Trading Platform

A high-speed trading bot that detects underdog goals in real-time and executes trades on Kalshi/Polymarket with sub-second latency. Features a production-grade React dashboard with smooth water ripple effects, custom cursor, and real-time data visualization.

---

## 🎯 Overview

GoalShock is a **full-stack real-time trading platform** for soccer prediction markets:

- **Real-time goal detection** from live API-Football data
- **Automated trading** on Kalshi and Polymarket
- **WebSocket streaming** for instant updates
- **Advanced market analysis** using Geometric Brownian Motion & GARCH volatility modeling

### Key Features

✅ **Real-time goal detection** from live soccer matches
✅ **Automated underdog trading** with sophisticated risk management
✅ **Sub-second latency** from goal event to order execution
✅ **Production-ready** React dashboard with smooth animations
✅ **WebSocket streaming** for real-time updates
✅ **Auto-fill settings** from environment variables
✅ **Advanced market simulation** for backtesting and analysis

### Headless mode (NEW) 
🎓 Key Concepts
1. Headless-First
Engine runs via CLI
No frontend dependency
Dashboard is optional (monitoring only)
2. No Probability Calculations
Orderbook prices ARE probabilities
0.42 = 42%, period
No conversion formulas
3. Underdog Leading Validation
Must be LEADING, not just tied
underdog_score > favorite_score
Critical validation before every trade
4. Continuous Risk Management
Real-time position monitoring
Auto-exit on TP/SL thresholds
Position limits enforced


Architecture Real APIs No Calculations

🎯 What It Does
Monitors live soccer matches via API-Football
Detects goals in real-time by comparing scores
Identifies underdog from pre-match orderbook odds
Validates underdog is LEADING (not just tied)
Executes trade on Polymarket/Kalshi using raw orderbook prices
Monitors positions continuously for take-profit / stop-loss
Zero frontend dependency. The engine runs autonomously.

---

## 🚀 Quick Start Headless

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Configure API keys
cp .env.example .env
nano .env  # Add your API keys

# 3. Run headless engine
python engine.py --mode headless
```

**That's it.** The engine is now running autonomously.
 

## 🚀 Quick Start Guide

### Prerequisites

- **Python 3.10+** (for backend)
- **Node.js 16+** (for frontend)
- **API Keys** (see Configuration section)

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Backend starts at**: http://localhost:8000
**API Docs**: http://localhost:8000/docs

### 2. Frontend Setup

```bash
cd app
npm install
npm run dev
```

**Frontend starts at**: http://localhost:5173

### 3. Start Trading

1. Open http://localhost:5173
2. Navigate to **Settings** page
3. Enter your API keys (auto-fills from `.env`)
4. Click **Dashboard**
5. Click **Start Bot**
6. Watch real-time goal events and trades!

---




---

## ⚙️ Configuration

### Environment Variables (`backend/.env`)

```env
# API Keys (required for live trading)
API_FOOTBALL_KEY=your-api-football-key
KALSHI_API_KEY=your-kalshi-email
KALSHI_API_SECRET=your-kalshi-password
POLYMARKET_API_KEY=your-polymarket-wallet-address
POLYMARKET_WALLET_KEY=your-polymarket-private-key

# Risk Management
MAX_TRADE_SIZE_USD=1000
MAX_DAILY_LOSS_USD=5000
MAX_DRAWDOWN_PERCENT=15
UNDERDOG_THRESHOLD=0.50
MAX_POSITIONS=10

# System
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000
```

### Getting API Keys

**1. API-Football (Required for live goals)**
- Sign up at https://rapidapi.com
- Subscribe to "API-Football" (100 requests/day free)
- Copy your RapidAPI key
- Paste into `API_FOOTBALL_KEY`

**2. Kalshi (Required for live trading)**
- Create account at https://kalshi.com
- Generate API key in account settings
- Add email to `KALSHI_API_KEY` and password to `KALSHI_API_SECRET`

**3. Polymarket (Required for live trading)**
- Create account at https://polymarket.com
- Get your wallet private key
- Add to `POLYMARKET_API_KEY` and `POLYMARKET_WALLET_KEY`

**Settings Auto-Fill**: All values in `.env` automatically populate in the dashboard Settings page!

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend (Vite)                    │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │ Dashboard  │  │  Markets   │  │  Settings  │           │
│  │  - P&L     │  │  - Live    │  │  - Auto-   │           │
│  │  - Trades  │  │    Odds    │  │    Fill    │           │
│  └────────────┘  └────────────┘  └────────────┘           │
│         │                │                 │                │
│         └────────────────┴─────────────────┘                │
│                     WebSocket + REST API                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              FastAPI Backend (Python 3.10+)                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         OrchestrationEngine (Data Router)            │  │
│  │  • Routes real-time data from APIs                  │  │
│  │  • Manages WebSocket connections                    │  │
│  └──────────┬───────────────────────────┬────────────────┘  │
│             │                           │                    │
│  ┌──────────▼────────────┐   ┌─────────▼──────────────┐    │
│  │ DataAcquisitionLayer  │   │  MarketMicrostructure  │    │
│  │  • API-Football calls │   │  • Brownian Motion     │    │
│  │  • Kalshi/Polymarket  │   │  • GARCH volatility    │    │
│  └───────────────────────┘   │  • Order flow analysis │    │
│                               └────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Risk Management Engine                  │   │
│  │  • Position limits  • Stop-loss  • P&L tracking    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                  External APIs                              │
│  ┌──────────────┐  ┌────────────┐  ┌──────────────┐       │
│  │ API-Football │  │   Kalshi   │  │  Polymarket  │       │
│  │ (Live Goals) │  │  (Trading) │  │  (Trading)   │       │
│  └──────────────┘  └────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

**Primary Flow (Real APIs)**:
- API-Football webhooks trigger goal events
- System fetches current odds from Kalshi/Polymarket
- Risk engine validates trade parameters
- Order executor submits trade
- WebSocket broadcasts update to frontend
- Frontend displays live trade with P&L

---





## 🔧 API Endpoints

### Bot Control
- `POST /api/bot/start` - Start trading bot
- `POST /api/bot/stop` - Stop trading bot
- `GET /api/status` - Get bot status & metrics

### Data Access
- `GET /api/markets` - Get prediction markets
- `GET /api/markets/live` - Get live soccer matches
- `GET /api/performance` - Get performance metrics

### Configuration
- `GET /api/settings/load` - Load settings from .env
- `POST /api/settings/save` - Save settings to .env

### WebSocket
- `ws://localhost:8000/ws` - Real-time event stream
  - Goal events
  - Trade executions
  - P&L updates
  - Market price updates

---

## ⚡ How It Works

### Trading Pipeline (< 1 second)

```
1. GOAL DETECTED
   ↓ (50-100ms)
   → API-Football webhook or polling

2. MARKET LOOKUP
   ↓ (100-200ms)
   → Fetch current odds from Kalshi/Polymarket
   → Calculate implied probabilities

3. UNDERDOG CHECK
   ↓ (< 10ms)
   → Is scoring team < 50% implied probability?
   → Check recent momentum & context

4. RISK VALIDATION
   ↓ (< 10ms)
   → Max position limits (10 concurrent)
   → Daily loss cap ($5,000)
   → Trade size limits ($1,000)

5. EXECUTE ORDER
   ↓ (200-400ms)
   → Submit limit order (IOC)
   → Await fill confirmation

6. TRACK P&L
   ↓ (continuous)
   → Monitor position
   → Apply stop-loss rules
   → Track realized/unrealized P&L
```

---

## 📊 Known Issues & Limitations

### Current Limitations

1. **API Rate Limits**
   - API-Football free tier: 100 requests/day
   - Polymarket: Rate limited per IP
   - Solution: Upgrade to paid tier for production

2. **Market Data Latency**
   - Real-time odds can lag 500ms-2s behind actual markets
   - Mitigation: Use WebSocket feeds when available
   - Impact: May miss fastest-moving opportunities

3. **No Authentication**
   - Frontend and backend have no auth layer
   - Risk: Anyone can access dashboard if deployed publicly
   - Solution: Add JWT/OAuth before production deployment

4. **Single Server Architecture**
   - No horizontal scaling or load balancing
   - Mitigation: Docker containerization ready
   - Solution: Deploy with Kubernetes for high availability

### Troubleshooting

**Backend won't start**:
```bash
# Check Python version (need 3.10+)
python --version

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check port availability
netstat -ano | findstr :8000
```

**Frontend WebSocket connection fails**:
```bash
# Verify backend health
curl http://localhost:8000/

# Check CORS configuration in backend/main.py
# Should include: http://localhost:5173
```

**No trades executing**:
```bash
# Start the bot
curl -X POST http://localhost:8000/api/bot/start

# Check status
curl http://localhost:8000/api/status
```

---

## 🛡️ Security & Risk

### Risk Management

**Position Limits**:
- Max 10 concurrent positions
- $1,000 max trade size
- $5,000 daily loss limit
- 15% stop-loss per trade

**Underdog Criteria**:
- Scoring team implied prob < 50%
- Minimum liquidity check
- No duplicate trades per match

### Security Considerations

⚠️ **IMPORTANT**: Before live trading:

1. **Add Authentication**
   - Implement JWT tokens
   - Add user management
   - Secure API endpoints

2. **Secure API Keys**
   - Use secrets manager (AWS Secrets, HashiCorp Vault)
   - Never commit `.env` to version control
   - Rotate keys regularly

3. **Enable HTTPS**
   - Use SSL/TLS certificates
   - Secure WebSocket connections (WSS)

4. **Rate Limiting**
   - Prevent API abuse
   - Throttle requests per IP

5. **Monitoring & Alerts**
   - Set up error tracking (Sentry)
   - Monitor trading activity
   - Alert on unusual patterns

---




## 📄 License

MIT License - GoalShock Trading Systems

---

