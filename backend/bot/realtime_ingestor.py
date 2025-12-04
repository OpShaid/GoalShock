
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable
import httpx
from ..models.schemas import GoalEvent, LiveMatch
from ..config.settings import settings

logger = logging.getLogger(__name__)

class RealtimeIngestor:
  
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=settings.WS_TIMEOUT)
        self.active_fixtures: Dict[int, LiveMatch] = {}
        self.goal_callbacks: List[Callable] = []
        self.running = False
        self.last_request_time = datetime.now()

    def register_goal_callback(self, callback: Callable):
        self.goal_callbacks.append(callback)
        logger.info(f"Registered goal callback: {callback.__name__}")

    async def start(self):
        if not settings.is_configured():
            logger.warning("API-Football key not configured - using fallback mode")
            return

        self.running = True
        logger.info("Starting real-time soccer data ingestion")

      
        asyncio.create_task(self._poll_live_matches())

    async def stop(self):
        self.running = False
        await self.client.aclose()
        logger.info("Stopped real-time ingestion")

    async def _poll_live_matches(self):
       
        while self.running:
            try:
               
                await self._rate_limit()

               
                fixtures = await self._fetch_live_fixtures()

                if fixtures:
                    await self._process_fixtures(fixtures)

              
                await asyncio.sleep(settings.POLL_INTERVAL_SECONDS)

            except Exception as e:
                logger.error(f"Error polling live matches: {e}")
                await asyncio.sleep(settings.WS_RECONNECT_DELAY)

    async def _rate_limit(self):
        elapsed = (datetime.now() - self.last_request_time).total_seconds()
        if elapsed < (settings.REQUEST_DELAY_MS / 1000):
            await asyncio.sleep((settings.REQUEST_DELAY_MS / 1000) - elapsed)
        self.last_request_time = datetime.now()

    async def _fetch_live_fixtures(self) -> List[Dict]:
        try:
            headers = {
                "x-rapidapi-key": settings.API_FOOTBALL_KEY,
                "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
            }

            response = await self.client.get(
                f"{settings.API_FOOTBALL_BASE}/fixtures",
                headers=headers,
                params={"live": "all"}
            )

            if response.status_code != 200:
                logger.error(f"API-Football returned {response.status_code}")
                return []

            data = response.json()
            fixtures = data.get("response", [])

            filtered = [
                f for f in fixtures
                if f.get("league", {}).get("id") in settings.SUPPORTED_LEAGUES
            ]

            logger.info(f"Fetched {len(filtered)} live fixtures from {len(fixtures)} total")
            return filtered

        except Exception as e:
            logger.error(f"Failed to fetch live fixtures: {e}")
            return []

    async def _process_fixtures(self, fixtures: List[Dict]):
        for fixture_data in fixtures:
            fixture_id = fixture_data["fixture"]["id"]

            match = self._parse_live_match(fixture_data)

            if fixture_id in self.active_fixtures:
                old_match = self.active_fixtures[fixture_id]
                new_goals = self._detect_new_goals(old_match, match, fixture_data)

                for goal in new_goals:
                    await self._notify_goal(goal)

            self.active_fixtures[fixture_id] = match

    def _parse_live_match(self, fixture_data: Dict) -> LiveMatch:
        fixture = fixture_data["fixture"]
        league = fixture_data["league"]
        teams = fixture_data["teams"]
        goals = fixture_data["goals"]
        status = fixture_data["fixture"]["status"]

        return LiveMatch(
            fixture_id=fixture["id"],
            league_id=league["id"],
            league_name=league["name"],
            home_team=teams["home"]["name"],
            away_team=teams["away"]["name"],
            home_score=goals["home"] or 0,
            away_score=goals["away"] or 0,
            minute=status.get("elapsed", 0),
            status=status.get("short", "1H")
        )

    def _detect_new_goals(self, old: LiveMatch, new: LiveMatch, fixture_data: Dict) -> List[GoalEvent]:
        goals = []

        # Home team scored
        if new.home_score > old.home_score:
            goal = self._create_goal_event(fixture_data, new.home_team, "home")
            if goal:
                goals.append(goal)

        if new.away_score > old.away_score:
            goal = self._create_goal_event(fixture_data, new.away_team, "away")
            if goal:
                goals.append(goal)

        return goals

    def _create_goal_event(self, fixture_data: Dict, team: str, side: str) -> Optional[GoalEvent]:
        try:
            events = fixture_data.get("events", [])
            goal_events = [e for e in events if e.get("type") == "Goal" and e["team"]["name"] == team]

            if not goal_events:
                logger.warning(f"No goal event found for {team}")
                return None

            latest_goal = goal_events[-1]  

            fixture = fixture_data["fixture"]
            league = fixture_data["league"]
            teams = fixture_data["teams"]
            goals = fixture_data["goals"]

            return GoalEvent(
                id=f"goal_{fixture['id']}_{latest_goal['time']['elapsed']}_{team}",
                fixture_id=fixture["id"],
                league_id=league["id"],
                league_name=league["name"],
                home_team=teams["home"]["name"],
                away_team=teams["away"]["name"],
                team=team,
                player=latest_goal["player"]["name"],
                assist=latest_goal.get("assist", {}).get("name"),
                minute=latest_goal["time"]["elapsed"],
                extra_time=latest_goal["time"].get("extra"),
                goal_type=latest_goal["detail"],
                home_score=goals["home"] or 0,
                away_score=goals["away"] or 0,
                timestamp=datetime.now()
            )

        except Exception as e:
            logger.error(f"Failed to create goal event: {e}")
            return None

    async def _notify_goal(self, goal: GoalEvent):
        logger.info(f"⚽ GOAL! {goal.player} ({goal.team}) - {goal.minute}' - {goal.home_team} {goal.home_score}-{goal.away_score} {goal.away_team}")

        for callback in self.goal_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(goal)
                else:
                    callback(goal)
            except Exception as e:
                logger.error(f"Goal callback error: {e}")

    def get_active_matches(self) -> List[LiveMatch]:
        return list(self.active_fixtures.values())
