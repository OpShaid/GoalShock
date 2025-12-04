
import os
import asyncio
import httpx
import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LiveFixture:
    """Live soccer fixture data"""
    fixture_id: int
    league_id: int
    league_name: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    minute: int
    status: str 
    timestamp: datetime


@dataclass
class Goal:
    fixture_id: int
    team: str
    player: str
    minute: int
    home_score: int
    away_score: int
    extra_time: Optional[int] = None


class APIFootballClient:

    def __init__(self):
        self.api_key = os.getenv("API_FOOTBALL_KEY", "")
        self.base_url = "https://api-football-v1.p.rapidapi.com/v3"
        self.client = httpx.AsyncClient(timeout=10.0)

        
        self.previous_scores: Dict[int, tuple] = {}  

      
        self.supported_leagues = [
            39,   
            140,  
            78,   
            135,  
            61,   
            2,    
        ]

        logger.info("⚽ API-Football client initialized")
        logger.info(f"   Monitoring {len(self.supported_leagues)} leagues")

    async def get_live_fixtures(self) -> List[LiveFixture]:
        
        try:
            response = await self.client.get(
                f"{self.base_url}/fixtures",
                params={"live": "all"},
                headers={
                    "x-rapidapi-key": self.api_key,
                    "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
                }
            )

            if response.status_code != 200:
                logger.error(f"API-Football error: {response.status_code}")
                return []

            data = response.json()
            fixtures_data = data.get("response", [])

            fixtures = []
            for f in fixtures_data:
                league_id = f["league"]["id"]

                if league_id not in self.supported_leagues:
                    continue

                fixture = LiveFixture(
                    fixture_id=f["fixture"]["id"],
                    league_id=league_id,
                    league_name=f["league"]["name"],
                    home_team=f["teams"]["home"]["name"],
                    away_team=f["teams"]["away"]["name"],
                    home_score=f["goals"]["home"] or 0,
                    away_score=f["goals"]["away"] or 0,
                    minute=f["fixture"]["status"]["elapsed"] or 0,
                    status=f["fixture"]["status"]["short"],
                    timestamp=datetime.now()
                )

                fixtures.append(fixture)

            if fixtures:
                logger.info(f"📡 {len(fixtures)} live fixtures found")

            return fixtures

        except Exception as e:
            logger.error(f"Error fetching live fixtures: {e}")
            return []

    async def detect_goals(self, fixtures: List[LiveFixture]) -> List[Goal]:
        
        new_goals = []

        for fixture in fixtures:
            fixture_id = fixture.fixture_id
            current_score = (fixture.home_score, fixture.away_score)

           
            if fixture_id not in self.previous_scores:
                self.previous_scores[fixture_id] = current_score
                continue

            previous_score = self.previous_scores[fixture_id]

            if current_score[0] > previous_score[0]:
                goal = Goal(
                    fixture_id=fixture_id,
                    team=fixture.home_team,
                    player="Unknown", 
                    minute=fixture.minute,
                    home_score=current_score[0],
                    away_score=current_score[1]
                )
                new_goals.append(goal)

                logger.info(f"⚽ GOAL! {fixture.home_team} {current_score[0]}-{current_score[1]} {fixture.away_team} ({fixture.minute}')")

            if current_score[1] > previous_score[1]:
                goal = Goal(
                    fixture_id=fixture_id,
                    team=fixture.away_team,
                    player="Unknown",
                    minute=fixture.minute,
                    home_score=current_score[0],
                    away_score=current_score[1]
                )
                new_goals.append(goal)

                logger.info(f"⚽ GOAL! {fixture.home_team} {current_score[0]}-{current_score[1]} {fixture.away_team} ({fixture.minute}')")

            self.previous_scores[fixture_id] = current_score

        return new_goals

    async def get_pre_match_odds(self, fixture_id: int) -> Optional[Dict[str, float]]:
      

        #Daniel Note: These are bookmaker odds, NOT market prices For actual trading, we use Polymarket/Kalshi odds
        
        try:
            response = await self.client.get(
                f"{self.base_url}/odds",
                params={"fixture": fixture_id, "bookmaker": 1},  
                headers={
                    "x-rapidapi-key": self.api_key,
                    "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
                }
            )

            if response.status_code != 200:
                logger.error(f"Odds API error: {response.status_code}")
                return None

            data = response.json()
            response_data = data.get("response", [])

            if not response_data:
                return None

            bookmaker = response_data[0]
            bets = bookmaker.get("bookmakers", [{}])[0].get("bets", [])

            for bet in bets:
                if bet["name"] == "Match Winner":
                    values = bet["values"]

                    odds_dict = {}
                    for v in values:
                       
                        decimal_odds = float(v["odd"])
                        probability = 1 / decimal_odds

                        odds_dict[v["value"]] = probability

                    return odds_dict

            return None

        except Exception as e:
            logger.error(f"Error fetching odds: {e}")
            return None

    async def get_fixture_details(self, fixture_id: int) -> Optional[Dict]:
        try:
            response = await self.client.get(
                f"{self.base_url}/fixtures",
                params={"id": fixture_id},
                headers={
                    "x-rapidapi-key": self.api_key,
                    "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
                }
            )

            if response.status_code != 200:
                return None

            data = response.json()
            fixtures = data.get("response", [])

            return fixtures[0] if fixtures else None

        except Exception as e:
            logger.error(f"Error fetching fixture details: {e}")
            return None

    async def close(self):
        await self.client.aclose()
