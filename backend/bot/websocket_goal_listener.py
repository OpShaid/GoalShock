
import asyncio
import json
import logging
from datetime import datetime
from typing import Callable, List, Optional, Dict, Set
from dataclasses import dataclass
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError
import httpx

logger = logging.getLogger(__name__)


@dataclass
class GoalEventWS:
    fixture_id: int
    league_id: int
    league_name: str
    home_team: str
    away_team: str
    team: str
    player: str
    minute: int
    home_score: int
    away_score: int
    goal_type: str
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            "fixture_id": self.fixture_id,
            "league_id": self.league_id,
            "league_name": self.league_name,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "team": self.team,
            "player": self.player,
            "minute": self.minute,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "goal_type": self.goal_type,
            "timestamp": self.timestamp.isoformat()
        }


class WebSocketGoalListener:
  
    
    SUPPORTED_LEAGUES = {
        39,   
        140, 
        78,   
        135,  
        61,   
        2,    
        3,    
        848,  
    }
    
    WS_ENDPOINTS = {
        "primary": "wss://api-football-v1.p.rapidapi.com/ws/live",
        "sofascore": "wss://ws.sofascore.com/live/events",
        "backup": "wss://sportdata.io/ws/soccer"
    }
    
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.running = False
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        
        self.goal_callbacks: List[Callable] = []
        
        self.seen_goals: Set[str] = set()
        
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.base_reconnect_delay = 2  
        self.max_reconnect_delay = 60  
        
        
        self.active_fixtures: Dict[int, Dict] = {}
        
        logger.info("WebSocket Goal Listener initialized")

    def register_goal_callback(self, callback: Callable):
        self.goal_callbacks.append(callback)
        logger.info(f"Registered goal callback: {callback.__name__}")

    async def start(self):
        self.running = True
        logger.info("Starting WebSocket Goal Listener...")
        
        while self.running:
            try:
                await self._connect_and_listen()
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                
                if self.running:
                    await self._handle_reconnection()
    
    async def stop(self):
        self.running = False
        if self.ws:
            await self.ws.close()
        logger.info("WebSocket Goal Listener stopped")

    async def _connect_and_listen(self):
        endpoint = self.WS_ENDPOINTS["primary"]
        
        headers = {}
        if self.api_key:
            headers["x-rapidapi-key"] = self.api_key
            headers["x-rapidapi-host"] = "api-football-v1.p.rapidapi.com"
        
        logger.info(f"Connecting to WebSocket: {endpoint}")
        
        async with websockets.connect(
            endpoint,
            extra_headers=headers,
            ping_interval=30,
            ping_timeout=10,
            close_timeout=5
        ) as ws:
            self.ws = ws
            self.reconnect_attempts = 0  
            
            logger.info("WebSocket connected successfully")
            
            await self._subscribe_to_goals()
            
            async for message in ws:
                if not self.running:
                    break
                    
                await self._process_message(message)

    async def _subscribe_to_goals(self):
        """Send subscription message for goal events"""
        if not self.ws:
            return
            
        subscription = {
            "type": "subscribe",
            "channels": ["live_goals", "live_scores"],
            "leagues": list(self.SUPPORTED_LEAGUES),
            "events": ["goal", "penalty_goal", "own_goal"]
        }
        
        await self.ws.send(json.dumps(subscription))
        logger.info(f"Subscribed to goal events for {len(self.SUPPORTED_LEAGUES)} leagues")

    async def _process_message(self, message: str):
        """Process incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            msg_type = data.get("type", "")
            
            if msg_type == "goal":
                await self._handle_goal_event(data)
            elif msg_type == "fixture_update":
                await self._handle_fixture_update(data)
            elif msg_type == "heartbeat":
                pass  
            elif msg_type == "error":
                logger.error(f"WebSocket error message: {data.get('message', 'Unknown error')}")
            else:
                logger.debug(f"Unknown message type: {msg_type}")
                
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse WebSocket message: {message[:100]}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def _handle_goal_event(self, data: Dict):
        """Handle incoming goal event"""
        try:
            fixture = data.get("fixture", {})
            league = data.get("league", {})
            goal = data.get("goal", {})
            score = data.get("score", {})
            
            fixture_id = fixture.get("id")
            league_id = league.get("id")
            
            if league_id not in self.SUPPORTED_LEAGUES:
                logger.debug(f"Ignoring goal from unsupported league: {league_id}")
                return
            
            goal_id = f"{fixture_id}_{goal.get('minute', 0)}_{goal.get('player', 'unknown')}"
            
            if goal_id in self.seen_goals:
                logger.debug(f"Duplicate goal ignored: {goal_id}")
                return
            
            self.seen_goals.add(goal_id)
            
            if len(self.seen_goals) > 1000:
                self.seen_goals = set(list(self.seen_goals)[-500:])
            
            goal_event = GoalEventWS(
                fixture_id=fixture_id,
                league_id=league_id,
                league_name=league.get("name", "Unknown"),
                home_team=fixture.get("home_team", "Unknown"),
                away_team=fixture.get("away_team", "Unknown"),
                team=goal.get("team", "Unknown"),
                player=goal.get("player", "Unknown"),
                minute=goal.get("minute", 0),
                home_score=score.get("home", 0),
                away_score=score.get("away", 0),
                goal_type=goal.get("type", "Normal"),
                timestamp=datetime.now()
            )
            
            logger.info(f"GOAL DETECTED: {goal_event.player} ({goal_event.team}) - {goal_event.minute}'")
            logger.info(f"  Score: {goal_event.home_team} {goal_event.home_score} - {goal_event.away_score} {goal_event.away_team}")
            
            await self._notify_goal_callbacks(goal_event)
            
        except Exception as e:
            logger.error(f"Error handling goal event: {e}")

    async def _handle_fixture_update(self, data: Dict):
        """Handle fixture status updates (kickoff, halftime, fulltime)"""
        fixture_id = data.get("fixture", {}).get("id")
        status = data.get("status", "")
        
        if fixture_id:
            self.active_fixtures[fixture_id] = data
            logger.debug(f"Fixture {fixture_id} updated: {status}")

    async def _notify_goal_callbacks(self, goal: GoalEventWS):
        """Notify all registered callbacks of new goal"""
        for callback in self.goal_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(goal)
                else:
                    callback(goal)
            except Exception as e:
                logger.error(f"Goal callback error: {e}")

    async def _handle_reconnection(self):
        """Handle reconnection with exponential backoff"""
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached. Stopping listener.")
            self.running = False
            return
        
        delay = min(
            self.base_reconnect_delay * (2 ** (self.reconnect_attempts - 1)),
            self.max_reconnect_delay
        )
        
        import random
        jitter = delay * random.uniform(0, 0.25)
        delay += jitter
        
        logger.warning(f"Reconnecting in {delay:.1f}s (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
        await asyncio.sleep(delay)

    def get_active_fixtures(self) -> List[Dict]:
        return list(self.active_fixtures.values())


class HybridGoalListener:
    
    
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.ws_listener = WebSocketGoalListener(api_key)
        self.running = False
        self.use_polling_fallback = False
        
        self.http_client = httpx.AsyncClient(timeout=10.0)
        
        self.previous_scores: Dict[int, tuple] = {}
        
        self.goal_callbacks: List[Callable] = []
        
    def register_goal_callback(self, callback: Callable):
        self.goal_callbacks.append(callback)
        self.ws_listener.register_goal_callback(callback)

    async def start(self):
        self.running = True
        
        ws_task = asyncio.create_task(self._run_websocket())
        
        monitor_task = asyncio.create_task(self._health_monitor())
        
        await asyncio.gather(ws_task, monitor_task, return_exceptions=True)

    async def stop(self):
        self.running = False
        await self.ws_listener.stop()
        await self.http_client.aclose()

    async def _run_websocket(self):
        """Run WebSocket listener with error handling"""
        try:
            await self.ws_listener.start()
        except Exception as e:
            logger.error(f"WebSocket listener failed: {e}")
            self.use_polling_fallback = True

    async def _health_monitor(self):
        """Monitor connection health and switch to polling if needed"""
        while self.running:
            await asyncio.sleep(30)  
            
            if self.use_polling_fallback:
                logger.warning("Using HTTP polling fallback")
                await self._poll_for_goals()

    async def _poll_for_goals(self):
        """Fallback HTTP polling for goal detection (conserve API calls)"""
        try:
            response = await self.http_client.get(
                "https://api-football-v1.p.rapidapi.com/v3/fixtures",
                params={"live": "all"},
                headers={
                    "x-rapidapi-key": self.api_key,
                    "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
                }
            )
            
            if response.status_code != 200:
                return
            
            data = response.json()
            fixtures = data.get("response", [])
            
            for fixture in fixtures:
                fixture_id = fixture["fixture"]["id"]
                league_id = fixture["league"]["id"]
                
                if league_id not in WebSocketGoalListener.SUPPORTED_LEAGUES:
                    continue
                
                home_score = fixture["goals"]["home"] or 0
                away_score = fixture["goals"]["away"] or 0
                current = (home_score, away_score)
                
                if fixture_id in self.previous_scores:
                    prev = self.previous_scores[fixture_id]
                    
                    if current[0] > prev[0]:
                        await self._emit_polling_goal(fixture, "home")
                    
                    if current[1] > prev[1]:
                        await self._emit_polling_goal(fixture, "away")
                
                self.previous_scores[fixture_id] = current
                
        except Exception as e:
            logger.error(f"Polling error: {e}")

    async def _emit_polling_goal(self, fixture: Dict, side: str):
        """Emit goal event from polling data"""
        teams = fixture["teams"]
        goals = fixture["goals"]
        league = fixture["league"]
        
        team = teams[side]["name"]
        
        goal_event = GoalEventWS(
            fixture_id=fixture["fixture"]["id"],
            league_id=league["id"],
            league_name=league["name"],
            home_team=teams["home"]["name"],
            away_team=teams["away"]["name"],
            team=team,
            player="Unknown (from polling)",
            minute=fixture["fixture"]["status"].get("elapsed", 0),
            home_score=goals["home"] or 0,
            away_score=goals["away"] or 0,
            goal_type="Normal",
            timestamp=datetime.now()
        )
        
        logger.info(f"GOAL (polling): {team} scored")
        
        for callback in self.goal_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(goal_event)
                else:
                    callback(goal_event)
            except Exception as e:
                logger.error(f"Callback error: {e}")
