# GoalShock - Complete Setup & Run Guide

## 🚀 Quick Start (5 Minutes)

### Step 1: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 httpx-0.25.1 ...
```

### Step 2: Configure API Keys

```bash
# Copy example config
cp .env.example .env

# Edit with your API keys
nano .env  # or use any text editor
```

**Minimum required:**
```bash
API_FOOTBALL_KEY=your-rapidapi-key-here
```

**For live trading, also add:**
```bash
POLYMARKET_API_KEY=your-polymarket-wallet
POLYMARKET_WALLET_KEY=your-private-key
KALSHI_API_KEY=your-kalshi-email
KALSHI_API_SECRET=your-kalshi-password
```

### Step 3: Run Headless Engine

```bash
python engine.py --mode headless
```

**You should see:**
```
============================================================
🤖 GOALSHOCK HEADLESS TRADING ENGINE
============================================================
2025-12-03 23:30:00 | INFO | 🤖 GoalShock Trading Engine Initialized
2025-12-03 23:30:00 | INFO |    Max Trade Size: $1000.0
2025-12-03 23:30:00 | INFO |    Max Positions: 10
2025-12-03 23:30:00 | INFO |    Take-Profit: 15.0%
2025-12-03 23:30:00 | INFO |    Stop-Loss: 10.0%
2025-12-03 23:30:01 | INFO | 🚀 Starting Headless Trading Engine...
2025-12-03 23:30:01 | INFO | 👁️  Goal detection loop started
2025-12-03 23:30:01 | INFO | 📈 Position monitoring loop started
```

**✅ Engine is running!**

---

## 🧪 Testing Without Live API Keys

If you don't have API keys yet, you can still test the engine structure:

```bash
# Set dummy values in .env
API_FOOTBALL_KEY=test-key
POLYMARKET_API_KEY=test-wallet
KALSHI_API_KEY=test@email.com
KALSHI_API_SECRET=test-password

# Run engine
python engine.py --mode headless
```

Engine will start but won't fetch real data (expected behavior without valid keys).

---

## 📋 Getting API Keys

### 1. API-Football (Required)

1. Go to https://rapidapi.com/api-sports/api/api-football
2. Sign up for free account
3. Subscribe to "API-Football" (100 requests/day free)
4. Copy your RapidAPI key from dashboard
5. Paste into `.env` as `API_FOOTBALL_KEY`

**Test it works:**
```bash
curl --request GET \
  --url 'https://api-football-v1.p.rapidapi.com/v3/fixtures?live=all' \
  --header 'x-rapidapi-key: YOUR-KEY-HERE'
```

### 2. Polymarket (For Live Trading)

1. Create account at https://polymarket.com
2. Set up wallet (MetaMask or built-in)
3. Get your wallet address (0x...)
4. Export private key (⚠️ KEEP SECURE)
5. Add to `.env`:
   ```bash
   POLYMARKET_API_KEY=0xYourWalletAddress
   POLYMARKET_WALLET_KEY=0xYourPrivateKey
   ```

### 3. Kalshi (For Live Trading)

1. Create account at https://kalshi.com
2. Verify identity (required for trading)
3. Use your email + password in `.env`:
   ```bash
   KALSHI_API_KEY=your-email@example.com
   KALSHI_API_SECRET=your-password
   ```

---

## ⚙️ Configuration Options

All settings in `backend/.env`:

### Risk Management
```bash
MAX_TRADE_SIZE_USD=1000      # Max dollars per trade
MAX_POSITIONS=10             # Max concurrent positions
MAX_DAILY_LOSS_USD=5000      # Stop trading if daily loss hits this
```

### Trading Criteria
```bash
UNDERDOG_THRESHOLD=0.50      # Team with <50% odds = underdog
```

### Exit Rules
```bash
TAKE_PROFIT_PERCENT=15       # Auto-exit at +15% profit
STOP_LOSS_PERCENT=10         # Auto-exit at -10% loss
```

---

## 🎯 What Happens When Engine Runs

### 1. Goal Detection Loop (Every 10 seconds)
```
Fetch live fixtures from API-Football
    ↓
Compare current scores with previous
    ↓
Detect new goals
    ↓
Process each goal event
```

### 2. Trade Decision
```
Goal scored by underdog?
    ├─ NO → Skip
    └─ YES → Check if underdog is LEADING
        ├─ Tied (1-1) → Skip ❌
        ├─ Losing (1-2) → Skip ❌
        └─ LEADING (2-1) → Execute Trade ✅
```

### 3. Position Monitoring (Every 10 seconds)
```
For each open position:
    Fetch current market price
    Calculate P&L percentage
    ├─ P&L >= +15% → Close (Take-Profit)
    └─ P&L <= -10% → Close (Stop-Loss)
```

---

## 📊 Example Logs (What You'll See)

### Engine Starting
```
2025-12-03 23:30:00 | INFO | 🤖 GoalShock Trading Engine Initialized
2025-12-03 23:30:00 | INFO |    Max Trade Size: $1000.0
2025-12-03 23:30:00 | INFO |    Take-Profit: 15.0%
2025-12-03 23:30:01 | INFO | 👁️  Goal detection loop started
2025-12-03 23:30:01 | INFO | 📈 Position monitoring loop started
```

### Live Fixtures Detected
```
2025-12-03 23:32:10 | INFO | 📡 3 live fixtures found
```

### Goal Detected
```
2025-12-03 23:35:22 | INFO | ⚽ GOAL DETECTED: Salah (Liverpool) - 67'
2025-12-03 23:35:22 | INFO |    Score: 2-1
2025-12-03 23:35:22 | INFO | 🎯 Underdog Liverpool scored!
```

### Leading Validation (CRITICAL)
```
2025-12-03 23:35:22 | INFO |    ✅ LEADING: Liverpool 2 - 1
2025-12-03 23:35:22 | INFO | ✅ Liverpool is NOW LEADING - EXECUTING TRADE
```

### Trade Executed
```
2025-12-03 23:35:23 | INFO | 💰 TRADE EXECUTED:
2025-12-03 23:35:23 | INFO |    Position ID: 12345_Liverpool_1701234523
2025-12-03 23:35:23 | INFO |    Team: Liverpool
2025-12-03 23:35:23 | INFO |    Side: YES
2025-12-03 23:35:23 | INFO |    Entry Price: 0.48 (48.0%)
2025-12-03 23:35:23 | INFO |    Size: $1000.00
2025-12-03 23:35:23 | INFO |    Active Positions: 1
```

### Take-Profit Hit
```
2025-12-03 23:42:10 | INFO | 🎯 TAKE-PROFIT HIT:
2025-12-03 23:42:10 | INFO |    Position: 12345_Liverpool_1701234523
2025-12-03 23:42:10 | INFO |    Entry: 0.48
2025-12-03 23:42:10 | INFO |    Exit: 0.56
2025-12-03 23:42:10 | INFO |    P&L: +16.67% ($167.00)
2025-12-03 23:42:10 | INFO | ✅ Position closed: 12345_Liverpool_1701234523 (Reason: TAKE_PROFIT)
```

---

## 🔍 Troubleshooting

### Issue: "No module named 'data'"
**Solution:**
```bash
# Make sure you're in backend directory
cd backend

# Run from backend directory
python engine.py --mode headless
```

### Issue: "API-Football error: 401"
**Solution:**
- Check your `API_FOOTBALL_KEY` is correct
- Verify key is active on RapidAPI dashboard
- Check you haven't exceeded daily quota (100 requests/day free)

### Issue: "No live fixtures currently"
**Solution:**
- This is normal when no soccer matches are live
- Check https://api-football-v1.p.rapidapi.com/v3/fixtures?live=all manually
- Engine will find fixtures when games are live

### Issue: Engine starts but no trades execute
**Possible reasons:**
1. No live matches currently ✅ (Normal)
2. No goals being scored ✅ (Normal)
3. Goals by favorite, not underdog ✅ (Normal)
4. Underdog scored but tied/losing ✅ (Normal - working as designed)

**This is expected behavior!** Engine only trades when:
- ✅ Underdog scores
- ✅ AND underdog is now LEADING (not tied)

---

## 🚀 Running in Production

### With systemd (Linux)

Create `/etc/systemd/system/goalshock.service`:
```ini
[Unit]
Description=GoalShock Trading Engine
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/goalshock/backend
ExecStart=/usr/bin/python3 engine.py --mode headless
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable goalshock
sudo systemctl start goalshock
sudo systemctl status goalshock
```

### With screen (Any OS)

```bash
# Start screen session
screen -S goalshock

# Run engine
cd backend
python engine.py --mode headless

# Detach: Ctrl+A, then D
# Reattach: screen -r goalshock
```

### With Docker

```bash
# Build image
docker build -t goalshock .

# Run container
docker run -d \
  --name goalshock \
  --env-file backend/.env \
  --restart unless-stopped \
  goalshock
```

---

## 🎓 Understanding The Output

### ❌ Goal but NO TRADE (Tied)
```
⚽ GOAL DETECTED: Salah (Liverpool) - 45'
   Score: 1-1
🎯 Underdog Liverpool scored!
   ⚖️  TIED: Liverpool 1 - 1
⚠️  Liverpool scored but NOT LEADING - NO TRADE
```
**✅ Working correctly** - Underdog must be LEADING, not tied

### ❌ Goal but NO TRADE (Still Losing)
```
⚽ GOAL DETECTED: Salah (Liverpool) - 60'
   Score: 1-2
🎯 Underdog Liverpool scored!
   ❌ LOSING: Liverpool 1 - 2
⚠️  Liverpool scored but NOT LEADING - NO TRADE
```
**✅ Working correctly** - Underdog still behind

### ✅ Trade Executed (Leading)
```
⚽ GOAL DETECTED: Salah (Liverpool) - 75'
   Score: 2-1
🎯 Underdog Liverpool scored!
   ✅ LEADING: Liverpool 2 - 1
✅ Liverpool is NOW LEADING - EXECUTING TRADE
💰 TRADE EXECUTED: Entry Price: 0.48 (48.0%)
```
**✅ Perfect** - Underdog is ahead, trade executed

---

## 📞 Support & Documentation

- **Full Documentation**: See [HEADLESS-ENGINE.md](HEADLESS-ENGINE.md)
- **Quick Start**: See [README-HEADLESS.md](README-HEADLESS.md)
- **This Guide**: Complete setup instructions

---

## ✅ Verification Checklist

Before contacting support, verify:

- [ ] Running from `backend/` directory
- [ ] `requirements.txt` dependencies installed
- [ ] `.env` file exists with API keys
- [ ] API-Football key is valid (test with curl)
- [ ] Python 3.10+ installed
- [ ] Logs show "Goal detection loop started"
- [ ] Logs show "Position monitoring loop started"

**If all checked, engine is working correctly!**

---

## 🎯 Expected Behavior Summary

| Scenario | Expected Behavior |
|----------|-------------------|
| No live matches | "No live fixtures currently" (every 10s) |
| Live match, no goals | Fixture detected, no trades (normal) |
| Favorite scores | "Goal by favorite, not underdog" (skip) |
| Underdog scores, tied | "NOT LEADING - NO TRADE" (skip) |
| Underdog scores, losing | "NOT LEADING - NO TRADE" (skip) |
| Underdog scores, LEADING | "EXECUTING TRADE" (trade!) |
| Position profit >= 15% | "TAKE-PROFIT HIT" (auto-close) |
| Position loss >= 10% | "STOP-LOSS HIT" (auto-close) |

**All scenarios = Engine working flawlessly** ✅

---

**Ready to trade. Ready to win. 🚀**
