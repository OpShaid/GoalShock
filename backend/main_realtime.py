
import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv


from bot.realtime_ingestor import RealtimeIngestor
from bot.market_fetcher import MarketFetcher
from bot.market_mapper import MarketMapper
from models.schemas import GoalEvent, MarketPrice, GoalAlert, MarketUpdate
from config.settings import settings

load_dotenv()


app = FastAPI(title="GoalShock Real-Time API", version="3.0.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealtimeSystem:
    def __init__(self):
        self.websocket_clients: Set[WebSocket] = set()

        self.ingestor = RealtimeIngestor()
        self.market_fetcher = MarketFetcher()
        self.market_mapper = MarketMapper(self.market_fetcher)

       
        self.ingestor.register_goal_callback(self.on_goal_detected)
        self.market_fetcher.register_update_callback(self.on_market_update)

    async def start(self):
       
        logger.info("🚀 Starting GoalShock real-time system")

        
        await self.ingestor.start()
        await self.market_fetcher.start()

        logger.info("✅ Real-time system online")

    async def stop(self):
        
        logger.info("Stopping real-time system")
        await self.ingestor.stop()
        await self.market_fetcher.stop()

    async def on_goal_detected(self, goal: GoalEvent):
       
        logger.info(f"⚽ GOAL DETECTED: {goal.player} ({goal.team}) - {goal.minute}'")

        # Map goal to relevant markets
        markets = await self.market_mapper.map_goal_to_markets(goal)

        # Create alert with updated market prices
        alert = GoalAlert(
            type="goal",
            goal=goal,
            markets=markets
        )

        # Broadcast to all connected clients
        await self.broadcast(alert.dict())

        logger.info(f"📡 Broadcast goal alert to {len(self.websocket_clients)} clients")

    async def on_market_update(self, update: MarketUpdate):
        
        # Broadcast price update
        await self.broadcast(update.dict())

    async def broadcast(self, message: dict):
        "
        if not self.websocket_clients:
            return

        disconnected = set()
        for client in self.websocket_clients:
            try:
                await client.send_json(message)
            except:
                disconnected.add(client)

        self.websocket_clients -= disconnected

realtime_system = RealtimeSystem()

@app.on_event("startup")
async def startup():
   
    await realtime_system.start()

@app.on_event("shutdown")
async def shutdown():
  
    await realtime_system.stop()

# API Endpoints

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "goalshock-realtime",
        "version": "3.0.0",
        "api_configured": settings.is_configured(),
        "market_access": settings.has_market_access()
    }

@app.get("/api/health")
async def health_check():
   
    return {
        "status": "healthy",
        "api_football_configured": settings.is_configured(),
        "market_apis_configured": settings.has_market_access(),
        "active_matches": len(realtime_system.ingestor.active_fixtures),
        "cached_markets": len(realtime_system.market_fetcher.market_cache),
        "connected_clients": len(realtime_system.websocket_clients)
    }

@app.get("/api/matches/live")
async def get_live_matches():
    
    try:
        matches = realtime_system.ingestor.get_active_matches()

        enriched = []
        for match in matches:
            markets = await realtime_system.market_mapper.get_markets_for_match(match)
            match_dict = match.dict()
            match_dict["markets"] = [m.dict() for m in markets]
            enriched.append(match_dict)

        return {
            "matches": enriched,
            "total": len(enriched),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to fetch live matches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/markets/{fixture_id}")
async def get_markets_for_fixture(fixture_id: int):
    
    try:
     
        matches = realtime_system.ingestor.get_active_matches()
        match = next((m for m in matches if m.fixture_id == fixture_id), None)

        if not match:
            raise HTTPException(status_code=404, detail="Match not found")

        markets = await realtime_system.market_mapper.get_markets_for_match(match)

        return {
            "fixture_id": fixture_id,
            "match": match.dict(),
            "markets": [m.dict() for m in markets],
            "total_markets": len(markets)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch markets for fixture {fixture_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/markets/all")
async def get_all_markets():
 
    markets = realtime_system.market_fetcher.get_all_markets()

  
    fresh_markets = [m for m in markets if not m.is_stale]

    return {
        "markets": [m.dict() for m in fresh_markets],
        "total": len(fresh_markets),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/settings/load")
async def load_settings():
  
    try:
        return {
            "api_football_key": "***" + settings.API_FOOTBALL_KEY[-4:] if settings.API_FOOTBALL_KEY else "",
            "polymarket_api_key": "***" + settings.POLYMARKET_API_KEY[-4:] if settings.POLYMARKET_API_KEY else "",
            "kalshi_api_key": "***" + settings.KALSHI_API_KEY[-4:] if settings.KALSHI_API_KEY else "",
            "api_configured": settings.is_configured(),
            "market_access": settings.has_market_access()
        }
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/live")
async def websocket_live_feed(websocket: WebSocket):
   
    await websocket.accept()
    realtime_system.websocket_clients.add(websocket)
    logger.info(f"✅ WebSocket client connected ({len(realtime_system.websocket_clients)} total)")

    try:
        # Send initial state
        await websocket.send_json({
            "type": "connected",
            "timestamp": datetime.now().isoformat(),
            "active_matches": len(realtime_system.ingestor.active_fixtures),
            "message": "Connected to GoalShock real-time feed"
        })

        # Send current live matches
        matches = realtime_system.ingestor.get_active_matches()
        if matches:
            await websocket.send_json({
                "type": "matches",
                "matches": [m.dict() for m in matches]
            })

        # Keep connection alive and handle incoming messages
        while True:
            try:
               
                data = await websocket.receive_text()
            
                if data == "ping":
                    await websocket.send_text("pong")

            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        realtime_system.websocket_clients.discard(websocket)
        logger.info(f"WebSocket client disconnected ({len(realtime_system.websocket_clients)} remaining)")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
