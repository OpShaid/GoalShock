
import os
import asyncio
import httpx
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class KalshiClient:
    
    #We convert cents to decimal (42 → 0.42) but NO/0! implied probability math
    

    def __init__(self):
        self.api_key = os.getenv("KALSHI_API_KEY", "")  
        self.api_secret = os.getenv("KALSHI_API_SECRET", "")  
        self.base_url = "https://trading-api.kalshi.com/trade-api/v2"
        self.client = httpx.AsyncClient(timeout=10.0)
        self.auth_token = None

        logger.info("📊 Kalshi client initialized")

    async def login(self) -> bool:
        try:
            response = await self.client.post(
                f"{self.base_url}/login",
                json={"email": self.api_key, "password": self.api_secret}
            )

            if response.status_code == 200:
                self.auth_token = response.json().get("token")
                logger.info("✅ Kalshi authenticated successfully")
                return True
            else:
                logger.error(f"❌ Kalshi auth failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Kalshi login error: {e}")
            return False

    async def get_markets(self, event_ticker: str = None, status: str = "active") -> List[Dict]:
      
        if not self.auth_token:
            await self.login()

        try:
            params = {"status": status, "limit": 100}
            if event_ticker:
                params["event_ticker"] = event_ticker

            response = await self.client.get(
                f"{self.base_url}/markets",
                params=params,
                headers={"Authorization": f"Bearer {self.auth_token}"}
            )

            if response.status_code != 200:
                logger.error(f"Kalshi markets API error: {response.status_code}")
                return []

            markets = response.json().get("markets", [])
            logger.info(f"Found {len(markets)} Kalshi markets")

            return markets

        except Exception as e:
            logger.error(f"Error fetching Kalshi markets: {e}")
            return []

    async def get_orderbook(self, ticker: str) -> Optional[Dict]:
       
        if not self.auth_token:
            await self.login()

        try:
            response = await self.client.get(
                f"{self.base_url}/markets/{ticker}/orderbook",
                headers={"Authorization": f"Bearer {self.auth_token}"}
            )

            if response.status_code != 200:
                logger.error(f"Orderbook API error: {response.status_code}")
                return None

            data = response.json()
            orderbook = data.get("orderbook", {})

            yes_bids = orderbook.get("yes", [])
            no_bids = orderbook.get("no", [])

            if not yes_bids:
                logger.warning(f"Empty orderbook for {ticker}")
                return None

           
            yes_bid = yes_bids[0][0] if yes_bids else 0 
            yes_ask = no_bids[0][0] if no_bids else 100  

          
            yes_bid_decimal = yes_bid / 100
            yes_ask_decimal = yes_ask / 100
            mid_price = (yes_bid_decimal + yes_ask_decimal) / 2

            logger.debug(f"Orderbook for {ticker}:")
            logger.debug(f"  YES Bid: {yes_bid}¢ ({yes_bid_decimal:.2f})")
            logger.debug(f"  YES Ask: {yes_ask}¢ ({yes_ask_decimal:.2f})")
            logger.debug(f"  Mid: {mid_price:.4f} ({mid_price*100:.1f}%)")

            return {
                "ticker": ticker,
                "yes_bid": yes_bid_decimal,
                "yes_ask": yes_ask_decimal,
                "mid_price": mid_price,
                "spread": yes_ask_decimal - yes_bid_decimal,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return None

    async def get_yes_price(self, ticker: str) -> Optional[float]:
       
        orderbook = await self.get_orderbook(ticker)

        if not orderbook:
            return None

        
        yes_price = orderbook["yes_ask"]

        logger.info(f"YES price for {ticker}: {yes_price:.4f} ({yes_price*100:.1f}%)")

        return yes_price

    async def place_order(
        self,
        ticker: str,
        side: str, 
        action: str,  
        count: int,  
        price: int  
    ) -> Optional[Dict]:
       
        if not self.auth_token:
            await self.login()

        try:
            order_payload = {
                "ticker": ticker,
                "side": side.lower(),
                "action": action.lower(),
                "count": count,
                "type": "limit",
                "yes_price": price if side == "yes" else None,
                "no_price": price if side == "no" else None
            }

            response = await self.client.post(
                f"{self.base_url}/portfolio/orders",
                json=order_payload,
                headers={"Authorization": f"Bearer {self.auth_token}"}
            )

            if response.status_code == 200:
                order = response.json().get("order", {})
                order_id = order.get("order_id")
                logger.info(f"✅ Kalshi order placed: {order_id}")
                return order
            else:
                logger.error(f"❌ Kalshi order failed: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error placing Kalshi order: {e}")
            return None

    async def close(self):
        await self.client.aclose()
