
import os
import asyncio
import httpx
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PolymarketClient:
    
    #Polymarket clob client so 
    #Prices are ALREADY probabilities
   

    def __init__(self):
        self.api_key = os.getenv("POLYMARKET_API_KEY", "")
        self.base_url = "https://clob.polymarket.com"
        self.gamma_url = "https://gamma-api.polymarket.com"
        self.client = httpx.AsyncClient(timeout=10.0)

        logger.info("📊 Polymarket client initialized")

    async def get_markets_by_event(self, event_name: str) -> List[Dict]:
       
        try:
            response = await self.client.get(
                f"{self.gamma_url}/markets",
                params={"search": event_name, "active": True}
            )

            if response.status_code != 200:
                logger.error(f"Polymarket API error: {response.status_code}")
                return []

            markets = response.json()
            logger.info(f"Found {len(markets)} markets for: {event_name}")

            return markets

        except Exception as e:
            logger.error(f"Error fetching Polymarket markets: {e}")
            return []

    async def get_orderbook(self, token_id: str) -> Optional[Dict]:
       
        try:
            response = await self.client.get(
                f"{self.base_url}/book",
                params={"token_id": token_id}
            )

            if response.status_code != 200:
                logger.error(f"Orderbook API error: {response.status_code}")
                return None

            orderbook = response.json()

         
            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])

            if not bids or not asks:
                logger.warning(f"Empty orderbook for token {token_id}")
                return None

            best_bid = float(bids[0]["price"])  
            best_ask = float(asks[0]["price"]) 
            mid_price = (best_bid + best_ask) / 2

            logger.debug(f"Orderbook for {token_id}:")
            logger.debug(f"  Best Bid: {best_bid:.4f} ({best_bid*100:.2f}%)")
            logger.debug(f"  Best Ask: {best_ask:.4f} ({best_ask*100:.2f}%)")
            logger.debug(f"  Mid: {mid_price:.4f} ({mid_price*100:.2f}%)")

            return {
                "token_id": token_id,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "mid_price": mid_price,
                "spread": best_ask - best_bid,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return None

    async def get_yes_price(self, token_id: str) -> Optional[float]:
       
        orderbook = await self.get_orderbook(token_id)

        if not orderbook:
            return None

        yes_price = orderbook["best_ask"]

        logger.info(f"YES price for {token_id}: {yes_price:.4f} ({yes_price*100:.1f}%)")

        return yes_price

    async def place_order(
        self,
        token_id: str,
        side: str,  
        price: float,
        size: float
    ) -> Optional[Dict]:
        
        try:
          
            order_payload = {
                "token_id": token_id,
                "side": side.upper(),
                "price": str(price),
                "size": str(size),
                "timestamp": int(datetime.now().timestamp())
            }

            #daniel in production we would need A PRIVATE KEY
            signature = sign_order(order_payload, private_key) 

            response = await self.client.post(
                f"{self.base_url}/order",
                json=order_payload,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )

            if response.status_code == 200:
                order_id = response.json().get("order_id")
                logger.info(f"✅ Order placed: {order_id}")
                return response.json()
            else:
                logger.error(f"❌ Order failed: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    async def close(self):
        await self.client.aclose()
