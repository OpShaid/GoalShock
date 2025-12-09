
import logging
from typing import List, Dict
from ..models.schemas import GoalEvent, MarketPrice, LiveMatch
from .market_fetcher import MarketFetcher

logger = logging.getLogger(__name__)

class MarketMapper:
 
    def __init__(self, market_fetcher: MarketFetcher):
        self.market_fetcher = market_fetcher
        self.fixture_market_map: Dict[int, List[str]] = {}

    async def map_goal_to_markets(self, goal: GoalEvent) -> List[MarketPrice]:
      
        markets = []

     
        if goal.fixture_id in self.fixture_market_map:
            market_ids = self.fixture_market_map[goal.fixture_id]
            for market_id in market_ids:
                market = self.market_fetcher.get_market(market_id)
                if market and not market.is_stale:
                    markets.append(market)

        
        if not markets:
            markets = await self.market_fetcher.fetch_markets_for_fixture(
                goal.fixture_id,
                goal.home_team,
                goal.away_team
            )

           
            self.fixture_market_map[goal.fixture_id] = [m.market_id for m in markets]

      
        relevant_markets = self._filter_relevant_markets(goal, markets)

        logger.info(f"Mapped goal to {len(relevant_markets)} markets for {goal.home_team} vs {goal.away_team}")
        return relevant_markets

    def _filter_relevant_markets(self, goal: GoalEvent, markets: List[MarketPrice]) -> List[MarketPrice]:
        #This Filters markets to those relevant to the goal event
        #E.g., if Liverpool scores, show Liverpool win markets
        relevant = []

        for market in markets:
            question = market.question.lower()

            if any(keyword in question for keyword in ["win", "victory", "winner", "result"]):
                if goal.team.lower() in question:
                    relevant.append(market)
                elif goal.home_team.lower() in question or goal.away_team.lower() in question:
                    relevant.append(market)

            elif any(keyword in question for keyword in ["goals", "score", "total"]):
                relevant.append(market)

            elif goal.player.lower() in question:
                relevant.append(market)

        return relevant or markets  # Return all if no specific matches

    async def get_markets_for_match(self, match: LiveMatch) -> List[MarketPrice]:
        """Get all markets for a live match"""
        if match.fixture_id in self.fixture_market_map:
            market_ids = self.fixture_market_map[match.fixture_id]
            markets = []
            for market_id in market_ids:
                market = self.market_fetcher.get_market(market_id)
                if market:
                    markets.append(market)

            if markets:
                return markets

        markets = await self.market_fetcher.fetch_markets_for_fixture(
            match.fixture_id,
            match.home_team,
            match.away_team
        )

        self.fixture_market_map[match.fixture_id] = [m.market_id for m in markets]

        return markets

    def update_market_mapping(self, fixture_id: int, market_ids: List[str]):
        self.fixture_market_map[fixture_id] = market_ids

    def clear_stale_mappings(self):
        stale_fixtures = []

        for fixture_id, market_ids in self.fixture_market_map.items():
            markets = [self.market_fetcher.get_market(m_id) for m_id in market_ids]
            markets = [m for m in markets if m]  

            if markets and all(m.is_stale for m in markets):
                stale_fixtures.append(fixture_id)

        for fixture_id in stale_fixtures:
            del self.fixture_market_map[fixture_id]

        if stale_fixtures:
            logger.info(f"Cleared {len(stale_fixtures)} stale fixture mappings")
