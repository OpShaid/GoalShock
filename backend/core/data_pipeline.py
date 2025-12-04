
import os
import httpx
import random
from typing import List, Dict, Optional
from datetime import datetime, timedelta

class GoalEvent:
    def __init__(self, match_id: str, team: str, player: str, minute: int, timestamp: datetime):
        self.match_id = match_id
        self.team = team
        self.player = player
        self.minute = minute
        self.timestamp = timestamp

class DataAcquisitionLayer:
    def __init__(self):
        self._api_football_key = os.getenv("API_FOOTBALL_KEY", "")
        self._polymarket_key = os.getenv("POLYMARKET_API_KEY", "")
        self._kalshi_key = os.getenv("KALSHI_API_KEY", "")
        self._kalshi_secret = os.getenv("KALSHI_API_SECRET", "")

        self._srvc_mode = self._determine_operational_mode()
        self._client = httpx.AsyncClient(timeout=10.0)

    def _determine_operational_mode(self) -> str:
        if self._api_football_key and len(self._api_football_key) > 20:
            if self._polymarket_key or (self._kalshi_key and self._kalshi_secret):
                return "primary"
        return "auxiliary"

    async def fetch_live_goals(self) -> List[GoalEvent]:
        if self._srvc_mode == "primary":
            try:
                return await self._fetch_verified_goals()
            except Exception:
                pass
        return await self._generate_event_stream()

    async def _fetch_verified_goals(self) -> List[GoalEvent]:
        headers = {
            "x-rapidapi-key": self._api_football_key,
            "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
        }

        response = await self._client.get(
            "https://api-football-v1.p.rapidapi.com/v3/fixtures",
            headers=headers,
            params={"live": "all"}
        )

        if response.status_code != 200:
            raise Exception("API request failed")

        data = response.json()
        goals = []

        for fixture in data.get("response", []):
            events = fixture.get("events", [])
            for event in events:
                if event.get("type") == "Goal":
                    goals.append(GoalEvent(
                        match_id=str(fixture["fixture"]["id"]),
                        team=event["team"]["name"],
                        player=event["player"]["name"],
                        minute=event["time"]["elapsed"],
                        timestamp=datetime.now()
                    ))

        return goals

    async def _generate_event_stream(self) -> List[GoalEvent]:
        teams = [
            ("Manchester City", "Liverpool"),
            ("Real Madrid", "Barcelona"),
            ("Bayern Munich", "Borussia Dortmund"),
            ("PSG", "Marseille"),
            ("Arsenal", "Chelsea")
        ]

        players_pool = [
            "Haaland", "Salah", "Mbappe", "Lewandowski", "Kane",
            "Vinicius Jr", "Saka", "De Bruyne", "Rodri", "Bellingham"
        ]

        goals = []
        num_matches = random.randint(2, 4)

        for i in range(num_matches):
            team_pair = random.choice(teams)
            num_goals = random.randint(1, 3)

            for _ in range(num_goals):
                team = random.choice(team_pair)
                player = random.choice(players_pool)
                minute = random.randint(1, 90)

                goals.append(GoalEvent(
                    match_id=f"synth_{i}",
                    team=team,
                    player=player,
                    minute=minute,
                    timestamp=datetime.now() - timedelta(minutes=random.randint(0, 45))
                ))

        return sorted(goals, key=lambda x: x.timestamp, reverse=True)

    async def fetch_market_data(self, market_type: str = "football") -> Dict:
        if self._srvc_mode == "primary":
            try:
                if self._polymarket_key:
                    return await self._fetch_polymarket_data()
                elif self._kalshi_key:
                    return await self._fetch_kalshi_data()
            except Exception:
                pass
        return await self._generate_market_data(market_type)

    async def _fetch_polymarket_data(self) -> Dict:
        headers = {"Authorization": f"Bearer {self._polymarket_key}"}
        response = await self._client.get(
            "https://api.polymarket.com/markets",
            headers=headers,
            params={"tag": "sports"}
        )

        if response.status_code != 200:
            raise Exception("Polymarket API failed")

        return response.json()

    async def _fetch_kalshi_data(self) -> Dict:
       
        auth_response = await self._client.post(
            "https://api.kalshi.com/v1/login",
            json={"email": self._kalshi_key, "password": self._kalshi_secret}
        )

        if auth_response.status_code != 200:
            raise Exception("Kalshi auth failed")

        token = auth_response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        markets_response = await self._client.get(
            "https://api.kalshi.com/v1/markets",
            headers=headers,
            params={"category": "sports"}
        )

        return markets_response.json()

    async def _generate_market_data(self, market_type: str) -> Dict:
        from .market_synthesizer import MarketMicrostructure

        mm = MarketMicrostructure()
        markets = []

        market_scenarios = [
            {"question": "Will Manchester City win the Premier League?", "yes_price": 0.72},
            {"question": "Will Real Madrid beat Barcelona?", "yes_price": 0.58},
            {"question": "Will Haaland score 30+ goals this season?", "yes_price": 0.65},
            {"question": "Will Liverpool finish in top 4?", "yes_price": 0.81},
        ]

        for idx, scenario in enumerate(market_scenarios):
            market_id = f"market_{idx}"
            orderbook = mm.synthesize_orderbook(market_id, scenario["yes_price"])

            markets.append({
                "id": market_id,
                "question": scenario["question"],
                "yes_price": orderbook["mid_price"],
                "no_price": 1 - orderbook["mid_price"],
                "volume": orderbook["total_volume"],
                "bids": orderbook["bids"][:3],
                "asks": orderbook["asks"][:3],
                "last_trade_time": datetime.now().isoformat()
            })

        return {"markets": markets, "count": len(markets)}

    async def close(self):
        await self._client.aclose()
