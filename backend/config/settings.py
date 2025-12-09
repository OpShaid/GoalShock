"""
Configuration settings for GoalShock real-time soccer data
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # API Keys - REDACTED for security
    API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
    POLYMARKET_API_KEY = os.getenv("POLYMARKET_API_KEY", "")
    KALSHI_API_KEY = os.getenv("KALSHI_API_KEY", "")

    # API Endpoints
    API_FOOTBALL_BASE = "https://api-football-v1.p.rapidapi.com/v3"
    POLYMARKET_WS = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    KALSHI_WS = "wss://trading-api.kalshi.com/trade-api/ws/v2"

    # WebSocket endpoints for real-time goal detection (replaces polling)
    GOAL_WS_PRIMARY = "wss://api-football-v1.p.rapidapi.com/ws/live"
    GOAL_WS_SOFASCORE = "wss://ws.sofascore.com/live/events"
    GOAL_WS_BACKUP = "wss://sportdata.io/ws/soccer"

    # WebSocket settings
    WS_RECONNECT_DELAY = 5  # seconds
    WS_PING_INTERVAL = 30   # seconds
    WS_TIMEOUT = 10         # seconds
    WS_MAX_RECONNECT_ATTEMPTS = 10
    WS_RECONNECT_BACKOFF_BASE = 2  # seconds

    # Polling fallback (only if WebSocket fails)
    POLL_INTERVAL_SECONDS = 10
    MAX_POLL_RETRIES = 3

    # Rate limiting
    API_FOOTBALL_REQUESTS_PER_DAY = 100
    REQUEST_DELAY_MS = 1000

    # Data filtering
    SUPPORTED_LEAGUES = [
        39,   # Premier League
        140,  # La Liga
        78,   # Bundesliga
        135,  # Serie A
        61,   # Ligue 1
        2,    # Champions League
        3,    # Europa League
        848,  # Conference League
    ]

    # Market mapping
    MARKET_REFRESH_INTERVAL = 5  # seconds
    STALE_DATA_THRESHOLD = 60    # seconds

    # Alpha One - Underdog Strategy
    UNDERDOG_THRESHOLD = float(os.getenv("UNDERDOG_THRESHOLD", "0.45"))
    MAX_TRADE_SIZE_USD = float(os.getenv("MAX_TRADE_SIZE_USD", "500"))
    MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "5"))
    TAKE_PROFIT_PERCENT = float(os.getenv("TAKE_PROFIT_PERCENT", "15"))
    STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", "10"))
    MAX_DAILY_LOSS_USD = float(os.getenv("MAX_DAILY_LOSS_USD", "2000"))

    # Alpha Two - Late Compression Strategy
    CLIP_MIN_CONFIDENCE = float(os.getenv("CLIP_MIN_CONFIDENCE", "0.95"))
    CLIP_MAX_SIZE_USD = float(os.getenv("CLIP_MAX_SIZE_USD", "50"))
    CLIP_MIN_PROFIT_PCT = float(os.getenv("CLIP_MIN_PROFIT_PCT", "3"))
    CLIP_MAX_SECONDS = int(os.getenv("CLIP_MAX_SECONDS", "300"))

    # Trading mode
    TRADING_MODE = os.getenv("TRADING_MODE", "simulation")  # "simulation" or "live"

    @classmethod
    def is_configured(cls) -> bool:
        """Check if API keys are configured"""
        return bool(cls.API_FOOTBALL_KEY and len(cls.API_FOOTBALL_KEY) > 20)

    @classmethod
    def has_market_access(cls) -> bool:
        """Check if market API keys are configured"""
        return bool(cls.POLYMARKET_API_KEY or cls.KALSHI_API_KEY)

    @classmethod
    def is_live_mode(cls) -> bool:
        """Check if running in live trading mode"""
        return cls.TRADING_MODE.lower() == "live"

settings = Settings()
