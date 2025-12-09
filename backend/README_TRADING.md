# GoalShock Trading Bot

A real-time soccer trading bot for prediction markets (Polymarket, Kalshi).

## Features

### 1. WebSocket Goal Listener
Replaces API polling with real-time WebSocket connections:
- Instant goal detection (no more 100 requests/day limit)
- Auto-reconnection with exponential backoff
- Hybrid mode: WebSocket primary, HTTP polling fallback

### 2. Alpha One: Underdog Goal Momentum
Trades based on underdog goal events:
- Pre-match underdog identification
- Entry when underdog takes the lead
- Automatic take-profit and stop-loss
- Simulation and live modes

### 3. Alpha Two: Late-Stage Compression
Captures small inefficiencies near market close:
- Monitors markets in final minutes
- Executes when outcome is near-certain but price lags
- Focus on sports markets (safest)
- Small, precise bets for consistent profits

## Quick Start

1. **Install dependencies:**
\`\`\`bash
pip install -r requirements.txt
\`\`\`

2. **Configure environment:**
\`\`\`bash
cp .env.example .env
# Edit .env with your API keys
\`\`\`

3. **Run in simulation mode:**
\`\`\`bash
python engine_unified.py --mode simulation
\`\`\`

4. **Run in live mode (real money):**
\`\`\`bash
python engine_unified.py --mode live
\`\`\`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TRADING_MODE` | `simulation` or `live` | `simulation` |
| `API_FOOTBALL_KEY` | API-Football key | Required |
| `POLYMARKET_API_KEY` | Polymarket API key | Optional |
| `KALSHI_API_KEY` | Kalshi email | Optional |
| `UNDERDOG_THRESHOLD` | Max odds for underdog | `0.45` |
| `MAX_TRADE_SIZE_USD` | Max position size | `500` |
| `TAKE_PROFIT_PERCENT` | TP percentage | `15` |
| `STOP_LOSS_PERCENT` | SL percentage | `10` |

### Alpha One Settings

- **UNDERDOG_THRESHOLD**: Only trade underdogs with pre-match odds below this
- **MAX_POSITIONS**: Maximum concurrent positions
- **MAX_DAILY_LOSS_USD**: Stop trading after this daily loss

### Alpha Two Settings

- **CLIP_MIN_CONFIDENCE**: Minimum confidence (95%+) to execute
- **CLIP_MAX_SIZE_USD**: Small sizes for clipping ($10-50)
- **CLIP_MAX_SECONDS**: How close to market close to start looking

## Architecture

\`\`\`
┌─────────────────────────────────────────────────────────────┐
│                   Unified Trading Engine                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │   WebSocket     │    │   HTTP Polling  │                │
│  │  Goal Listener  │────│    (Fallback)   │                │
│  └────────┬────────┘    └────────┬────────┘                │
│           │                      │                          │
│           └──────────┬───────────┘                          │
│                      ▼                                      │
│           ┌─────────────────────┐                          │
│           │   Goal Event Router │                          │
│           └──────────┬──────────┘                          │
│                      │                                      │
│        ┌─────────────┼─────────────┐                       │
│        ▼             ▼             ▼                       │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐                │
│  │ Alpha One │ │ Alpha Two │ │  Logging  │                │
│  │ Underdog  │ │ Clipping  │ │  System   │                │
│  └─────┬─────┘ └─────┬─────┘ └───────────┘                │
│        │             │                                      │
│        └──────┬──────┘                                      │
│               ▼                                             │
│      ┌─────────────────┐                                   │
│      │ Exchange Router │                                   │
│      └────────┬────────┘                                   │
│               │                                             │
│      ┌────────┴────────┐                                   │
│      ▼                 ▼                                   │
│  ┌───────────┐   ┌───────────┐                            │
│  │Polymarket │   │  Kalshi   │                            │
│  └───────────┘   └───────────┘                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
\`\`\`

## Safety Features

- **Simulation Mode**: Test strategies without real money
- **Daily Loss Limits**: Automatic shutdown on excessive losses
- **Position Limits**: Maximum concurrent positions
- **Dispute Avoidance**: Only trade clear sports outcomes
- **Error Recovery**: Auto-reconnection and fallback mechanisms

## Logging

Logs are written to `logs/` directory:
- `alpha_one_TIMESTAMP.json`: Alpha One event log
- `alpha_two_TIMESTAMP.json`: Alpha Two event log

## API Rate Limits

The WebSocket approach eliminates API polling limits:
- API-Football free tier: 100 requests/day (avoided via WebSocket)
- Polymarket: No strict limits on WebSocket
- Kalshi: Rate limited, use judiciously

## Risk Warning

Trading prediction markets involves real financial risk. Always:
1. Start in simulation mode
2. Use small position sizes
3. Set strict daily loss limits
4. Never trade more than you can afford to lose
