
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
 
    API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
    POLYMARKET_API_KEY = os.getenv("POLYMARKET_API_KEY", "")
    KALSHI_API_KEY = os.getenv("KALSHI_API_KEY", "")

    API_FOOTBALL_BASE = "https://api-football-v1.p.rapidapi.com/v3"
    POLYMARKET_WS = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    KALSHI_WS = "wss://trading-api.kalshi.com/trade-api/ws/v2"

  
    WS_RECONNECT_DELAY = 5 
    WS_PING_INTERVAL = 30   
    WS_TIMEOUT = 10        

    # Polling fallback if WebSocket fails
    POLL_INTERVAL_SECONDS = 10
    MAX_POLL_RETRIES = 3

    # Rate limiting
    API_FOOTBALL_REQUESTS_PER_DAY = 100
    REQUEST_DELAY_MS = 1000

    # Data filtering
    SUPPORTED_LEAGUES = [
        39,   
        140, 
        78, 
        135, 
        61,   
    ]

    MARKET_REFRESH_INTERVAL = 5  
    STALE_DATA_THRESHOLD = 60   

    @classmethod
    def is_configured(cls) -> bool:
        return bool(cls.API_FOOTBALL_KEY and len(cls.API_FOOTBALL_KEY) > 20)

    @classmethod
    def has_market_access(cls) -> bool:
        return bool(cls.POLYMARKET_API_KEY or cls.KALSHI_API_KEY)

settings = Settings()
