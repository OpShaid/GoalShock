
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable
import websockets
import httpx
from ..models.schemas import MarketPrice, MarketUpdate
from ..config.settings import settings

logger = logging.getLogger(__name__)

class MarketFetcher:
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=settings.WS_TIMEOUT)
        self.market_cache: Dict[str, MarketPrice] = {}
        self.update_callbacks: List[Callable] = []
        self.running = False

        self.polymarket_ws: Optional[websockets.WebSocketClientProtocol] = None
        self.kalshi_ws: Optional[websockets.WebSocketClientProtocol] = None

    def register_update_callback(self, callback: Callable):
        self.update_callbacks.append(callback)
        logger.info(f"Registered market callback: {callback.__name__}")

    async def start(self):
        if not settings.has_market_access():
            logger.warning("No market API keys configured - prices unavailable")
            return

        self.running = True
        logger.info("Starting real-time market price fetching")

        if settings.POLYMARKET_API_KEY:
            asyncio.create_task(self._connect_polymarket_ws())

        if settings.KALSHI_API_KEY:
            asyncio.create_task(self._connect_kalshi_ws())

    async def stop(self):
        self.running = False

        if self.polymarket_ws:
            await self.polymarket_ws.close()

        if self.kalshi_ws:
            await self.kalshi_ws.close()

        await self.client.aclose()
        logger.info("Stopped market fetching")

    async def _connect_polymarket_ws(self):
        while self.running:
            try:
                async with websockets.connect(
                    settings.POLYMARKET_WS,
                    extra_headers={"Authorization": f"Bearer {settings.POLYMARKET_API_KEY}"}
                ) as ws:
                    self.polymarket_ws = ws
                    logger.info("✅ Connected to Polymarket WebSocket")

                    await ws.send(json.dumps({
                        "type": "subscribe",
                        "channel": "markets",
                        "filter": {"tags": ["soccer", "football"]}
                    }))

                    async for message in ws:
                        if not self.running:
                            break

                        data = json.loads(message)
                        await self._process_polymarket_update(data)

            except Exception as e:
                logger.error(f"Polymarket WebSocket error: {e}")
                await asyncio.sleep(settings.WS_RECONNECT_DELAY)

    async def _connect_kalshi_ws(self):
        while self.running:
            try:
                async with websockets.connect(
                    settings.KALSHI_WS,
                    extra_headers={"Authorization": f"Bearer {settings.KALSHI_API_KEY}"}
                ) as ws:
                    self.kalshi_ws = ws
                    logger.info("✅ Connected to Kalshi WebSocket")

                    await ws.send(json.dumps({
                        "type": "subscribe",
                        "market_type": "sports",
                        "sport": "soccer"
                    }))

                    async for message in ws:
                        if not self.running:
                            break

                        data = json.loads(message)
                        await self._process_kalshi_update(data)

            except Exception as e:
                logger.error(f"Kalshi WebSocket error: {e}")
                await asyncio.sleep(settings.WS_RECONNECT_DELAY)

    async def _process_polymarket_update(self, data: Dict):
        try:
            if data.get("type") != "price_update":
                return

            market_id = data.get("market_id")
            yes_price = data.get("yes_price")
            no_price = data.get("no_price")

            if not all([market_id, yes_price, no_price]):
                return

            if market_id in self.market_cache:
                self.market_cache[market_id].yes_price = yes_price
                self.market_cache[market_id].no_price = no_price
                self.market_cache[market_id].last_updated = datetime.now()

            update = MarketUpdate(
                market_id=market_id,
                yes_price=yes_price,
                no_price=no_price
            )
            await self._notify_update(update)

            logger.debug(f"📊 Polymarket update: {market_id} YES={yes_price:.2f} NO={no_price:.2f}")

        except Exception as e:
            logger.error(f"Failed to process Polymarket update: {e}")

    async def _process_kalshi_update(self, data: Dict):
        try:
            if data.get("type") != "market_snapshot":
                return

            market_id = data.get("market_ticker")
            yes_price = data.get("yes_bid") or data.get("yes_ask")
            no_price = data.get("no_bid") or data.get("no_ask")

            if not all([market_id, yes_price, no_price]):
                return

            yes_price = yes_price / 100.0
            no_price = no_price / 100.0

            if market_id in self.market_cache:
                self.market_cache[market_id].yes_price = yes_price
                self.market_cache[market_id].no_price = no_price
                self.market_cache[market_id].last_updated = datetime.now()

            update = MarketUpdate(
                market_id=market_id,
                yes_price=yes_price,
                no_price=no_price
            )
            await self._notify_update(update)

            logger.debug(f"📊 Kalshi update: {market_id} YES={yes_price:.2f} NO={no_price:.2f}")

        except Exception as e:
            logger.error(f"Failed to process Kalshi update: {e}")

    async def _notify_update(self, update: MarketUpdate):
        for callback in self.update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(update)
                else:
                    callback(update)
            except Exception as e:
                logger.error(f"Market callback error: {e}")

    async def fetch_markets_for_fixture(self, fixture_id: int, home_team: str, away_team: str) -> List[MarketPrice]:
        
        markets = []

        # Try Polymarket
        if settings.POLYMARKET_API_KEY:
            poly_markets = await self._fetch_polymarket_markets(home_team, away_team)
            markets.extend(poly_markets)

        # Try Kalshi
        if settings.KALSHI_API_KEY:
            kalshi_markets = await self._fetch_kalshi_markets(home_team, away_team)
            markets.extend(kalshi_markets)

        for market in markets:
            self.market_cache[market.market_id] = market

        return markets

    async def _fetch_polymarket_markets(self, home_team: str, away_team: str) -> List[MarketPrice]:
        try:
            response = await self.client.get(
                "https://api.polymarket.com/markets",
                headers={"Authorization": f"Bearer {settings.POLYMARKET_API_KEY}"},
                params={
                    "tag": "soccer",
                    "query": f"{home_team} {away_team}"
                }
            )

            if response.status_code != 200:
                return []

            data = response.json()
            markets = []

            for m in data.get("markets", []):
                markets.append(MarketPrice(
                    market_id=m["id"],
                    fixture_id=0,  #THis Should maybe Will be set by mapper
                    question=m["question"],
                    yes_price=m["yes_price"],
                    no_price=m["no_price"],
                    source="polymarket",
                    home_team=home_team,
                    away_team=away_team,
                    volume_24h=m.get("volume_24h"),
                    liquidity=m.get("liquidity")
                ))

            return markets

        except Exception as e:
            logger.error(f"Failed to fetch Polymarket markets: {e}")
            return []

    async def _fetch_kalshi_markets(self, home_team: str, away_team: str) -> List[MarketPrice]:
        try:
            response = await self.client.get(
                "https://api.kalshi.com/v1/markets",
                headers={"Authorization": f"Bearer {settings.KALSHI_API_KEY}"},
                params={
                    "category": "sports",
                    "sport": "soccer",
                    "query": f"{home_team} {away_team}"
                }
            )

            if response.status_code != 200:
                return []

            data = response.json()
            markets = []

            for m in data.get("markets", []):
                markets.append(MarketPrice(
                    market_id=m["ticker"],
                    fixture_id=0,  #same thing
                    question=m["title"],
                    yes_price=m["yes_price"] / 100.0,
                    no_price=m["no_price"] / 100.0,
                    source="kalshi",
                    home_team=home_team,
                    away_team=away_team,
                    volume_24h=m.get("volume"),
                    liquidity=m.get("open_interest")
                ))

            return markets

        except Exception as e:
            logger.error(f"Failed to fetch Kalshi markets: {e}")
            return []

    def get_market(self, market_id: str) -> Optional[MarketPrice]:
        return self.market_cache.get(market_id)

    def get_all_markets(self) -> List[MarketPrice]:
        return list(self.market_cache.values())
