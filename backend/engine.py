
import os
import sys
import asyncio
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv


from data.api_football import APIFootballClient, Goal, LiveFixture
from exchanges.polymarket import PolymarketClient
from exchanges.kalshi import KalshiClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


load_dotenv()


@dataclass
class Position:
    
    id: str
    market_id: str
    side: str  
    entry_price: float
    entry_time: datetime
    size: float
    current_price: float = 0.0

    @property
    def pnl_percent(self) -> float:
       
        if self.entry_price == 0:
            return 0.0
        return ((self.current_price - self.entry_price) / self.entry_price) * 100

    @property
    def pnl_usd(self) -> float:
   
        return (self.current_price - self.entry_price) * self.size


@dataclass
class GoalEvent:
    
    fixture_id: int
    minute: int
    team: str
    player: str
    home_score: int
    away_score: int
    timestamp: datetime


class TradingEngine:
  

    def __init__(self):
        # Initialize API clients
        self.api_football = APIFootballClient()
        self.polymarket = PolymarketClient()
        self.kalshi = KalshiClient()

        # Configuration from environment
        self.api_football_key = os.getenv("API_FOOTBALL_KEY", "")
        self.polymarket_key = os.getenv("POLYMARKET_API_KEY", "")
        self.kalshi_key = os.getenv("KALSHI_API_KEY", "")

        # Risk management parameters
        self.max_trade_size = float(os.getenv("MAX_TRADE_SIZE_USD", "1000"))
        self.max_positions = int(os.getenv("MAX_POSITIONS", "10"))
        self.underdog_threshold = float(os.getenv("UNDERDOG_THRESHOLD", "0.50"))

        # NEW: Take-profit and stop-loss
        self.take_profit_percent = float(os.getenv("TAKE_PROFIT_PERCENT", "15"))
        self.stop_loss_percent = float(os.getenv("STOP_LOSS_PERCENT", "10"))

        # Active positions
        self.positions: Dict[str, Position] = {}

        self.underdog_cache: Dict[int, str] = {}

       
        self.running = False

        logger.info("🤖 GoalShock Trading Engine Initialized")
        logger.info(f"   Max Trade Size: ${self.max_trade_size}")
        logger.info(f"   Max Positions: {self.max_positions}")
        logger.info(f"   Take-Profit: {self.take_profit_percent}%")
        logger.info(f"   Stop-Loss: {self.stop_loss_percent}%")

    async def start(self):
    
        logger.info("🚀 Starting Headless Trading Engine...")
        self.running = True

        
        tasks = [
            asyncio.create_task(self.goal_detection_loop()),
            asyncio.create_task(self.position_monitoring_loop()),
        ]

        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("⏹️  Received shutdown signal")
            self.running = False
        except Exception as e:
            logger.error(f"❌ Engine error: {e}")
            self.running = False

    async def goal_detection_loop(self):
      
        logger.info("👁️  Goal detection loop started")

        while self.running:
            try:
              
                fixtures = await self.fetch_live_fixtures()

                if not fixtures:
                    logger.debug("No live fixtures currently")
                    await asyncio.sleep(10)
                    continue

                
                goals = await self.detect_goal_events(fixtures)

                for goal in goals:
                    logger.info(f"⚽ GOAL DETECTED: {goal.player} ({goal.team}) - {goal.minute}'")
                    logger.info(f"   Score: {goal.home_score}-{goal.away_score}")

                   
                    goal_event = GoalEvent(
                        fixture_id=goal.fixture_id,
                        minute=goal.minute,
                        team=goal.team,
                        player=goal.player,
                        home_score=goal.home_score,
                        away_score=goal.away_score,
                        timestamp=datetime.now()
                    )

            
                    await self.process_goal_event(goal_event)

               
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Error in goal detection: {e}")
                await asyncio.sleep(10)

    async def process_goal_event(self, goal: GoalEvent):
       


        underdog_team = await self.identify_pre_match_underdog(goal.fixture_id)

        if not underdog_team:
            logger.debug(f"No underdog data for fixture {goal.fixture_id}")
            return

        
        if goal.team != underdog_team:
            logger.debug(f"Goal by favorite ({goal.team}), not underdog ({underdog_team})")
            return

        logger.info(f"🎯 Underdog {underdog_team} scored!")
       
        if not await self.is_underdog_leading(goal, underdog_team):
            logger.warning(f"⚠️  {underdog_team} scored but NOT LEADING - NO TRADE")
            logger.info(f"   Score: {goal.home_score} - {goal.away_score}")
            return

        logger.info(f"✅ {underdog_team} is NOW LEADING - EXECUTING TRADE")

     
        market_price = await self.get_market_price(goal.fixture_id, underdog_team)

        if not market_price:
            logger.error(f"❌ No market price available for {underdog_team}")
            return

    
        await self.execute_trade(goal, underdog_team, market_price)

    async def is_underdog_leading(self, goal: GoalEvent, underdog_team: str) -> bool:
    
        fixture_details = await self.api_football.get_fixture_details(goal.fixture_id)

        if not fixture_details:
            logger.error(f"Could not fetch fixture details for {goal.fixture_id}")
            return False

        home_team = fixture_details["teams"]["home"]["name"]
        away_team = fixture_details["teams"]["away"]["name"]

      
        if underdog_team == home_team:
            underdog_score = goal.home_score
            favorite_score = goal.away_score
        elif underdog_team == away_team:
            underdog_score = goal.away_score
            favorite_score = goal.home_score
        else:
            logger.error(f"Underdog team {underdog_team} not in fixture {home_team} vs {away_team}")
            return False

        is_leading = underdog_score > favorite_score

        if is_leading:
            logger.info(f"   ✅ LEADING: {underdog_team} {underdog_score} - {favorite_score}")
        elif underdog_score == favorite_score:
            logger.info(f"   ⚖️  TIED: {underdog_team} {underdog_score} - {favorite_score}")
        else:
            logger.info(f"   ❌ LOSING: {underdog_team} {underdog_score} - {favorite_score}")

        return is_leading

    async def identify_pre_match_underdog(self, fixture_id: int) -> Optional[str]:
      
        if fixture_id in self.underdog_cache:
            return self.underdog_cache[fixture_id]

        try:
            
            odds = await self.fetch_pre_match_odds(fixture_id)

            if not odds:
                return None

            # Find team with lower odds (underdog)
            underdog = min(odds.items(), key=lambda x: x[1])[0]

          
            self.underdog_cache[fixture_id] = underdog

            logger.info(f"📊 Pre-match underdog for fixture {fixture_id}: {underdog}")
            return underdog

        except Exception as e:
            logger.error(f"Error identifying underdog: {e}")
            return None

    async def execute_trade(self, goal: GoalEvent, team: str, market_price: float):
       

        # Check position limits
        if len(self.positions) >= self.max_positions:
            logger.warning(f"⚠️  Max positions reached ({self.max_positions}), skipping trade")
            return

        # Create position
        position_id = f"{goal.fixture_id}_{team}_{int(datetime.now().timestamp())}"

        position = Position(
            id=position_id,
            market_id=f"fixture_{goal.fixture_id}_{team}",
            side="YES",  # Betting on underdog to win
            entry_price=market_price,
            entry_time=datetime.now(),
            size=self.max_trade_size,
            current_price=market_price
        )

        # Store position
        self.positions[position_id] = position

        logger.info(f"💰 TRADE EXECUTED:")
        logger.info(f"   Position ID: {position_id}")
        logger.info(f"   Team: {team}")
        logger.info(f"   Side: YES")
        logger.info(f"   Entry Price: {market_price:.2f} ({market_price*100:.1f}%)")
        logger.info(f"   Size: ${self.max_trade_size:.2f}")
        logger.info(f"   Active Positions: {len(self.positions)}")

       
        await self.submit_order_to_exchange(position)

    async def position_monitoring_loop(self):
      
        logger.info("📈 Position monitoring loop started")

        while self.running:
            try:
                if not self.positions:
                    await asyncio.sleep(10)
                    continue

                for position_id, position in list(self.positions.items()):
                    # Fetch current market price
                    current_price = await self.get_current_price(position.market_id)

                    if current_price:
                        position.current_price = current_price

                        # Check take-profit
                        if position.pnl_percent >= self.take_profit_percent:
                            logger.info(f"🎯 TAKE-PROFIT HIT:")
                            logger.info(f"   Position: {position_id}")
                            logger.info(f"   Entry: {position.entry_price:.2f}")
                            logger.info(f"   Exit: {current_price:.2f}")
                            logger.info(f"   P&L: +{position.pnl_percent:.2f}% (${position.pnl_usd:.2f})")

                            await self.close_position(position_id, "TAKE_PROFIT")

                        # Check stop-loss
                        elif position.pnl_percent <= -self.stop_loss_percent:
                            logger.warning(f"🛑 STOP-LOSS HIT:")
                            logger.warning(f"   Position: {position_id}")
                            logger.warning(f"   Entry: {position.entry_price:.2f}")
                            logger.warning(f"   Exit: {current_price:.2f}")
                            logger.warning(f"   P&L: {position.pnl_percent:.2f}% (${position.pnl_usd:.2f})")

                            await self.close_position(position_id, "STOP_LOSS")

               
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Error in position monitoring: {e}")
                await asyncio.sleep(10)

    async def close_position(self, position_id: str, reason: str):

        position = self.positions.get(position_id)

        if not position:
            return

     
        await self.submit_exit_order(position)

      
        del self.positions[position_id]

        logger.info(f"✅ Position closed: {position_id} (Reason: {reason})")
        logger.info(f"   Remaining positions: {len(self.positions)}")

   

    async def fetch_live_fixtures(self) -> List[LiveFixture]:
        
        return await self.api_football.get_live_fixtures()

    async def detect_goal_events(self, fixtures: List[LiveFixture]) -> List[Goal]:
        
        return await self.api_football.detect_goals(fixtures)

    async def fetch_pre_match_odds(self, fixture_id: int) -> Optional[Dict[str, float]]:
       
        try:
         
            markets = await self.polymarket.get_markets_by_event(f"fixture_{fixture_id}")

            if markets:
                odds = {}
                for market in markets:
                    team_name = market.get("title", "").split("to win")[0].strip()
                 
                    token_id = market.get("clobTokenIds", [None])[0]
                    if token_id:
                        yes_price = await self.polymarket.get_yes_price(token_id)
                        if yes_price:
                            odds[team_name] = yes_price

                if odds:
                    return odds

            
            #for production we would have a mapping of fixture_id to market ticker
            logger.debug(f"No Polymarket odds found for fixture {fixture_id}")
            return None

        except Exception as e:
            logger.error(f"Error fetching pre-match odds: {e}")
            return None

    async def get_market_price(self, fixture_id: int, team: str) -> Optional[float]:
       
        try:
         
            markets = await self.polymarket.get_markets_by_event(f"{team} to win")

            if markets:
                market = markets[0]
                token_id = market.get("clobTokenIds", [None])[0]

                if token_id:
                 
                    yes_price = await self.polymarket.get_yes_price(token_id)
                    return yes_price

            logger.warning(f"No market found for {team}")
            return None

        except Exception as e:
            logger.error(f"Error fetching market price: {e}")
            return None

    async def get_current_price(self, market_id: str) -> Optional[float]:
      
        try:
          
            parts = market_id.split("_")
            if len(parts) >= 3:
                team_name = "_".join(parts[2:])
                return await self.get_market_price(int(parts[1]), team_name)

            return None

        except Exception as e:
            logger.error(f"Error fetching current price: {e}")
            return None


async def run_headless():
   
    logger.info("=" * 60)
    logger.info("🤖 GOALSHOCK HEADLESS TRADING ENGINE")
    logger.info("=" * 60)

    engine = TradingEngine()
    await engine.start()


async def run_with_dashboard():
   
    logger.info("=" * 60)
    logger.info("🤖 GOALSHOCK ENGINE + DASHBOARD")
    logger.info("=" * 60)


    engine = TradingEngine()
    engine_task = asyncio.create_task(engine.start())

  
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)


def main():
  
    parser = argparse.ArgumentParser(
        description="GoalShock - Autonomous Soccer Trading Engine"
    )
    parser.add_argument(
        "--mode",
        choices=["headless", "dashboard"],
        default="headless",
        help="Run in headless mode (default) or with dashboard"
    )

    args = parser.parse_args()

    if args.mode == "headless":
        asyncio.run(run_headless())
    else:
        asyncio.run(run_with_dashboard())


if __name__ == "__main__":
    main()
