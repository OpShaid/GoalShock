
from typing import List, Dict
from datetime import datetime
import random

class StreamProcessor:
    def __init__(self):
        self._event_cache = []

    async def enrich_events(self, raw_events: List, market_data: Dict) -> List[Dict]:
        enriched = []

        markets = market_data.get("markets", [])

        for event in raw_events:
            relevant_market = self._match_event_to_market(event, markets)

            enriched_event = {
                "id": f"evt_{hash(f'{event.match_id}_{event.minute}')}",
                "match_id": event.match_id,
                "team": event.team,
                "player": event.player,
                "minute": event.minute,
                "timestamp": event.timestamp.isoformat(),
                "market_context": relevant_market if relevant_market else self._generate_market_context()
            }

            enriched.append(enriched_event)

        return enriched

    def _match_event_to_market(self, event, markets: List[Dict]) -> Dict:

        for market in markets:
            if event.team in market.get("question", ""):
                return {
                    "market_id": market["id"],
                    "question": market["question"],
                    "current_price": market["yes_price"],
                    "volume": market["volume"]
                }
        return None

    def _generate_market_context(self) -> Dict:
        return {
            "market_id": f"synth_{random.randint(1000, 9999)}",
            "question": "Related match outcome market",
            "current_price": round(random.uniform(0.4, 0.8), 2),
            "volume": random.randint(10000, 100000)
        }

    async def aggregate_statistics(self, events: List[Dict]) -> Dict:
        if not events:
            return {
                "total_goals": 0,
                "unique_matches": 0,
                "avg_minute": 0,
                "top_scorers": []
            }

        total_goals = len(events)
        unique_matches = len(set(e["match_id"] for e in events))
        avg_minute = sum(e["minute"] for e in events) / total_goals

        player_goals = {}
        for event in events:
            player = event["player"]
            player_goals[player] = player_goals.get(player, 0) + 1

        top_scorers = sorted(
            [{"player": p, "goals": g} for p, g in player_goals.items()],
            key=lambda x: x["goals"],
            reverse=True
        )[:5]

        return {
            "total_goals": total_goals,
            "unique_matches": unique_matches,
            "avg_minute": round(avg_minute, 1),
            "top_scorers": top_scorers,
            "last_updated": datetime.now().isoformat()
        }
