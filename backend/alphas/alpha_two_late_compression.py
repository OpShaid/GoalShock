"""
ALPHA TWO: Late-Stage Compression / Clipping Strategy

Strategy Overview:
- Monitor markets approaching resolution (last few minutes)
- Identify small price inefficiencies (fractions left on the table)
- Execute small, precise bets to capture near-certain profits
- Focus on sports markets with clear resolution times

Key Features:
- High-frequency market scanning near close
- Sub-second execution when opportunities detected
- Minimal risk (only bet when outcome is near-certain)
- Automated dispute avoidance
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class MarketStatus(Enum):
    ACTIVE = "active"
    CLOSING_SOON = "closing_soon"  # < 5 minutes to resolution
    FINAL_SECONDS = "final_seconds"  # < 60 seconds to resolution
    RESOLVED = "resolved"


@dataclass
class ClippingOpportunity:
    """Opportunity for late-stage clipping"""
    opportunity_id: str
    market_id: str
    market_question: str
    fixture_id: int
    
    # Current state
    yes_price: float
    no_price: float
    spread: float
    
    # Opportunity details
    expected_outcome: str  # "YES" or "NO"
    confidence: float  # 0.9+ required for clipping
    expected_profit_pct: float
    
    # Timing
    seconds_to_resolution: int
    detected_at: datetime = field(default_factory=datetime.now)
    
    # Execution
    recommended_side: str
    recommended_price: float
    recommended_size: float
    
    def to_dict(self) -> Dict:
        return {
            "opportunity_id": self.opportunity_id,
            "market_id": self.market_id,
            "market_question": self.market_question,
            "yes_price": self.yes_price,
            "no_price": self.no_price,
            "expected_outcome": self.expected_outcome,
            "confidence": self.confidence,
            "expected_profit_pct": self.expected_profit_pct,
            "seconds_to_resolution": self.seconds_to_resolution,
            "recommended_side": self.recommended_side,
            "recommended_price": self.recommended_price,
            "recommended_size": self.recommended_size
        }


@dataclass
class ClippingTrade:
    """Executed clipping trade"""
    trade_id: str
    opportunity: ClippingOpportunity
    entry_time: datetime
    entry_price: float
    size_usd: float
    
    # Resolution
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    actual_outcome: Optional[str] = None
    pnl: float = 0.0


@dataclass
class AlphaTwoStats:
    """Performance statistics for Alpha Two"""
    opportunities_detected: int = 0
    trades_executed: int = 0
    trades_won: int = 0
    trades_lost: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    avg_profit_per_trade: float = 0.0
    false_positives: int = 0  # Opportunities that didn't resolve as expected


class AlphaTwoLateCompression:
    """
    Alpha Two: Late-Stage Compression Strategy
    
    Concept:
    - Near market close, prices should approach 0 or 100 (certainty)
    - Sometimes prices lag behind reality (e.g., YES at 95 when outcome is certain)
    - Clip these small inefficiencies for near-risk-free profit
    
    Entry Conditions:
    1. Market closing within 5 minutes (for sports: match ending)
    2. Current score/state makes outcome near-certain (>95% confidence)
    3. Market price doesn't fully reflect certainty (e.g., YES at 90 when should be 98)
    4. Sufficient liquidity to execute
    
    Risk Management:
    - Only trade when confidence > 95%
    - Small position sizes ($10-50)
    - Avoid disputed markets
    - Focus on clear sports outcomes
    
    Example:
    - Match: Man City 3 - 0 Liverpool, 89th minute
    - Market: "Will Man City win?" YES @ 0.92
    - Expected value: 0.99 (virtually certain)
    - Trade: Buy YES @ 0.92, expect to sell/resolve at 1.00
    - Profit: 8% on position size
    """
    
    # Markets to avoid (high dispute risk)
    AVOIDED_MARKET_TYPES = [
        "political",
        "crypto",
        "weather",
        "entertainment"
    ]
    
    def __init__(
        self,
        polymarket_client=None,
        kalshi_client=None,
        simulation_mode: bool = True
    ):
        self.polymarket = polymarket_client
        self.kalshi = kalshi_client
        self.simulation_mode = simulation_mode
        
        # Configuration
        self.min_confidence = float(os.getenv("CLIP_MIN_CONFIDENCE", "0.95"))
        self.max_trade_size = float(os.getenv("CLIP_MAX_SIZE_USD", "50"))
        self.min_profit_threshold = float(os.getenv("CLIP_MIN_PROFIT_PCT", "3"))  # 3% minimum
        self.max_seconds_to_close = int(os.getenv("CLIP_MAX_SECONDS", "300"))  # 5 minutes
        
        # State
        self.monitored_markets: Dict[str, Dict] = {}  # Markets approaching close
        self.active_opportunities: Dict[str, ClippingOpportunity] = {}
        self.trades: Dict[str, ClippingTrade] = {}
        self.closed_trades: List[ClippingTrade] = []
        self.stats = AlphaTwoStats()
        
        # Event log
        self.event_log: List[Dict] = []
        
        # Running state
        self.running = False
        
        logger.info(f"Alpha Two initialized (simulation={simulation_mode})")
        logger.info(f"  Min confidence: {self.min_confidence}")
        logger.info(f"  Max trade size: ${self.max_trade_size}")
        logger.info(f"  Min profit threshold: {self.min_profit_threshold}%")

    async def start(self):
        """Start the late compression strategy"""
        self.running = True
        logger.info("Starting Alpha Two - Late Compression Strategy")
        
        # Start concurrent tasks
        tasks = [
            asyncio.create_task(self._market_scanner_loop()),
            asyncio.create_task(self._opportunity_detector_loop()),
            asyncio.create_task(self._execution_loop()),
            asyncio.create_task(self._resolution_monitor_loop())
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self):
        """Stop the strategy"""
        self.running = False
        logger.info("Alpha Two stopped")

    async def _market_scanner_loop(self):
        """Scan for markets approaching resolution"""
        while self.running:
            try:
                # Fetch markets closing soon
                closing_markets = await self._fetch_closing_markets()
                
                for market in closing_markets:
                    market_id = market.get("market_id")
                    seconds_to_close = market.get("seconds_to_close", 999999)
                    
                    if seconds_to_close <= self.max_seconds_to_close:
                        self.monitored_markets[market_id] = market
                        logger.debug(f"Monitoring market {market_id}: {seconds_to_close}s to close")
                
                # Clean up resolved markets
                resolved = [
                    mid for mid, m in self.monitored_markets.items()
                    if m.get("status") == "resolved"
                ]
                for mid in resolved:
                    del self.monitored_markets[mid]
                
                await asyncio.sleep(10)  # Scan every 10 seconds
                
            except Exception as e:
                logger.error(f"Market scanner error: {e}")
                await asyncio.sleep(10)

    async def _opportunity_detector_loop(self):
        """Detect clipping opportunities in closing markets"""
        while self.running:
            try:
                for market_id, market in list(self.monitored_markets.items()):
                    opportunity = await self._analyze_market_for_clipping(market)
                    
                    if opportunity:
                        self.active_opportunities[opportunity.opportunity_id] = opportunity
                        self.stats.opportunities_detected += 1
                        
                        self._log_event("opportunity_detected", opportunity.to_dict())
                        
                        logger.info(f"CLIPPING OPPORTUNITY: {opportunity.opportunity_id}")
                        logger.info(f"  Market: {opportunity.market_question}")
                        logger.info(f"  Expected: {opportunity.expected_outcome}")
                        logger.info(f"  Current price: {opportunity.yes_price:.4f}")
                        logger.info(f"  Confidence: {opportunity.confidence:.2f}")
                        logger.info(f"  Expected profit: {opportunity.expected_profit_pct:.1f}%")
                        logger.info(f"  Seconds to resolution: {opportunity.seconds_to_resolution}")
                
                await asyncio.sleep(2)  # Check every 2 seconds (high frequency near close)
                
            except Exception as e:
                logger.error(f"Opportunity detector error: {e}")
                await asyncio.sleep(2)

    async def _execution_loop(self):
        """Execute trades on detected opportunities"""
        while self.running:
            try:
                for opp_id, opportunity in list(self.active_opportunities.items()):
                    # Only execute if conditions still valid
                    if opportunity.confidence < self.min_confidence:
                        continue
                    
                    if opportunity.expected_profit_pct < self.min_profit_threshold:
                        continue
                    
                    # Check if already traded this opportunity
                    if opp_id in self.trades:
                        continue
                    
                    # Execute trade
                    await self._execute_clipping_trade(opportunity)
                    
                    # Remove from active opportunities
                    del self.active_opportunities[opp_id]
                
                await asyncio.sleep(0.5)  # Execute every 500ms (fast execution)
                
            except Exception as e:
                logger.error(f"Execution loop error: {e}")
                await asyncio.sleep(1)

    async def _resolution_monitor_loop(self):
        """Monitor trades for resolution"""
        while self.running:
            try:
                for trade_id, trade in list(self.trades.items()):
                    if trade.resolved:
                        continue
                    
                    # Check if market resolved
                    resolution = await self._check_market_resolution(
                        trade.opportunity.market_id
                    )
                    
                    if resolution:
                        await self._process_trade_resolution(trade, resolution)
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Resolution monitor error: {e}")
                await asyncio.sleep(5)

    async def _fetch_closing_markets(self) -> List[Dict]:
        """Fetch markets that are closing soon"""
        markets = []
        
        # In production: Query Polymarket/Kalshi for markets closing soon
        if self.polymarket:
            try:
                # Search for sports markets
                poly_markets = await self._fetch_polymarket_closing_markets()
                markets.extend(poly_markets)
            except Exception as e:
                logger.error(f"Polymarket fetch error: {e}")
        
        if self.kalshi:
            try:
                kalshi_markets = await self._fetch_kalshi_closing_markets()
                markets.extend(kalshi_markets)
            except Exception as e:
                logger.error(f"Kalshi fetch error: {e}")
        
        return markets

    async def _fetch_polymarket_closing_markets(self) -> List[Dict]:
        """Fetch Polymarket markets closing soon"""
        # This would query Polymarket API for markets with close_time approaching
        # For now, return empty (implement with actual API)
        return []

    async def _fetch_kalshi_closing_markets(self) -> List[Dict]:
        """Fetch Kalshi markets closing soon"""
        # This would query Kalshi API for markets with close_time approaching
        return []

    async def _analyze_market_for_clipping(self, market: Dict) -> Optional[ClippingOpportunity]:
        """
        Analyze market for clipping opportunity
        
        Returns opportunity if:
        1. High confidence in outcome (>95%)
        2. Current price doesn't reflect confidence
        3. Profit potential exceeds threshold
        """
        market_id = market.get("market_id")
        question = market.get("question", "")
        fixture_id = market.get("fixture_id", 0)
        
        # Get current prices
        yes_price = market.get("yes_price", 0.5)
        no_price = market.get("no_price", 0.5)
        spread = abs(yes_price - no_price)
        
        seconds_to_close = market.get("seconds_to_close", 999999)
        
        # Determine expected outcome based on current state
        outcome_analysis = await self._predict_outcome(market)
        
        if not outcome_analysis:
            return None
        
        expected_outcome = outcome_analysis["outcome"]  # "YES" or "NO"
        confidence = outcome_analysis["confidence"]
        
        # Check confidence threshold
        if confidence < self.min_confidence:
            return None
        
        # Calculate expected profit
        if expected_outcome == "YES":
            current_price = yes_price
            target_price = 1.0
        else:
            current_price = no_price
            target_price = 1.0
        
        expected_profit_pct = ((target_price - current_price) / current_price) * 100
        
        # Check profit threshold
        if expected_profit_pct < self.min_profit_threshold:
            return None
        
        # Create opportunity
        return ClippingOpportunity(
            opportunity_id=f"clip_{market_id}_{int(datetime.now().timestamp())}",
            market_id=market_id,
            market_question=question,
            fixture_id=fixture_id,
            yes_price=yes_price,
            no_price=no_price,
            spread=spread,
            expected_outcome=expected_outcome,
            confidence=confidence,
            expected_profit_pct=expected_profit_pct,
            seconds_to_resolution=seconds_to_close,
            recommended_side=expected_outcome,
            recommended_price=current_price,
            recommended_size=min(
                self.max_trade_size,
                self.max_trade_size * confidence  # Scale by confidence
            )
        )

    async def _predict_outcome(self, market: Dict) -> Optional[Dict]:
        """
        Predict market outcome based on current state
        
        For sports markets:
        - Check current score
        - Check time remaining
        - Calculate probability of outcome change
        
        Returns: {"outcome": "YES"|"NO", "confidence": 0.0-1.0}
        """
        market_type = market.get("type", "unknown")
        
        # Only handle sports markets for now (safest)
        if market_type not in ["soccer", "football", "basketball", "baseball"]:
            return None
        
        # Get current state
        current_score = market.get("current_score", {})
        time_remaining = market.get("seconds_to_close", 999999)
        
        home_score = current_score.get("home", 0)
        away_score = current_score.get("away", 0)
        
        # Determine what the market is asking
        question = market.get("question", "").lower()
        
        if "win" in question:
            # Predict winner based on current score and time
            if home_score > away_score:
                # Home leading
                if "home" in question or market.get("home_team", "").lower() in question:
                    # Market asks if home wins, they're leading
                    confidence = self._calculate_lead_confidence(
                        home_score - away_score,
                        time_remaining,
                        market_type
                    )
                    return {"outcome": "YES", "confidence": confidence}
                else:
                    # Market asks if away wins, they're losing
                    confidence = self._calculate_lead_confidence(
                        home_score - away_score,
                        time_remaining,
                        market_type
                    )
                    return {"outcome": "NO", "confidence": confidence}
            
            elif away_score > home_score:
                # Away leading
                if "away" in question or market.get("away_team", "").lower() in question:
                    confidence = self._calculate_lead_confidence(
                        away_score - home_score,
                        time_remaining,
                        market_type
                    )
                    return {"outcome": "YES", "confidence": confidence}
                else:
                    confidence = self._calculate_lead_confidence(
                        away_score - home_score,
                        time_remaining,
                        market_type
                    )
                    return {"outcome": "NO", "confidence": confidence}
        
        return None

    def _calculate_lead_confidence(
        self,
        lead_margin: int,
        seconds_remaining: int,
        sport: str
    ) -> float:
        """
        Calculate confidence that current leader will win
        
        Based on:
        - Lead margin
        - Time remaining
        - Sport-specific comeback rates
        """
        # Sport-specific parameters
        if sport == "soccer":
            # Soccer: goals are rare, leads are relatively safe
            # Average goals per 90 min: ~2.7 total
            # Expected goals in remaining time
            expected_goals = (seconds_remaining / 5400) * 2.7  # 90 min = 5400 sec
            
            # Probability of overcoming lead
            # Simplified: use Poisson approximation
            if lead_margin >= 3:
                confidence = 0.99
            elif lead_margin == 2:
                if seconds_remaining < 300:  # < 5 min
                    confidence = 0.98
                elif seconds_remaining < 600:  # < 10 min
                    confidence = 0.95
                else:
                    confidence = 0.90
            elif lead_margin == 1:
                if seconds_remaining < 120:  # < 2 min
                    confidence = 0.95
                elif seconds_remaining < 300:  # < 5 min
                    confidence = 0.85
                else:
                    confidence = 0.70
            else:
                confidence = 0.50  # Tied, no edge
        
        elif sport in ["basketball", "baseball"]:
            # Higher scoring, need larger margins
            if sport == "basketball":
                points_per_second = 0.04  # ~100 points per 48 min
            else:
                points_per_second = 0.003  # ~9 runs per game
            
            expected_swing = points_per_second * seconds_remaining * 2
            
            if lead_margin > expected_swing * 1.5:
                confidence = 0.98
            elif lead_margin > expected_swing:
                confidence = 0.90
            else:
                confidence = 0.60
        
        else:
            confidence = 0.50  # Unknown sport
        
        return min(0.99, confidence)

    async def _execute_clipping_trade(self, opportunity: ClippingOpportunity):
        """Execute clipping trade"""
        trade = ClippingTrade(
            trade_id=opportunity.opportunity_id,
            opportunity=opportunity,
            entry_time=datetime.now(),
            entry_price=opportunity.recommended_price,
            size_usd=opportunity.recommended_size
        )
        
        if self.simulation_mode:
            # Simulation: just record the trade
            self.trades[trade.trade_id] = trade
            self.stats.trades_executed += 1
            
            self._log_event("trade_executed_simulation", {
                "trade_id": trade.trade_id,
                "entry_price": trade.entry_price,
                "size_usd": trade.size_usd,
                "expected_profit": opportunity.expected_profit_pct
            })
            
            logger.info(f"[SIMULATION] Clipping trade executed: {trade.trade_id}")
            logger.info(f"  Entry: {trade.entry_price:.4f}")
            logger.info(f"  Size: ${trade.size_usd:.2f}")
            logger.info(f"  Expected profit: {opportunity.expected_profit_pct:.1f}%")
        
        else:
            # Live execution
            success = await self._place_exchange_order(opportunity)
            
            if success:
                self.trades[trade.trade_id] = trade
                self.stats.trades_executed += 1
                logger.info(f"[LIVE] Clipping trade executed: {trade.trade_id}")
            else:
                logger.error(f"Failed to execute clipping trade: {trade.trade_id}")

    async def _place_exchange_order(self, opportunity: ClippingOpportunity) -> bool:
        """Place order on exchange"""
        if self.polymarket:
            try:
                # Would need to implement actual order placement
                # result = await self.polymarket.place_order(...)
                return False  # Placeholder
            except Exception as e:
                logger.error(f"Polymarket order error: {e}")
        
        if self.kalshi:
            try:
                # result = await self.kalshi.place_order(...)
                return False  # Placeholder
            except Exception as e:
                logger.error(f"Kalshi order error: {e}")
        
        return False

    async def _check_market_resolution(self, market_id: str) -> Optional[Dict]:
        """Check if market has resolved"""
        # In production: Query exchange for resolution status
        # Return {"outcome": "YES"|"NO", "resolution_time": datetime}
        return None

    async def _process_trade_resolution(self, trade: ClippingTrade, resolution: Dict):
        """Process trade resolution and calculate P&L"""
        trade.resolved = True
        trade.resolution_time = resolution.get("resolution_time", datetime.now())
        trade.actual_outcome = resolution.get("outcome")
        
        # Calculate P&L
        if trade.actual_outcome == trade.opportunity.expected_outcome:
            # Won: get full contract value (1.00) minus entry price
            trade.pnl = (1.0 - trade.entry_price) * trade.size_usd / trade.entry_price
            self.stats.trades_won += 1
        else:
            # Lost: lose entire position
            trade.pnl = -trade.size_usd
            self.stats.trades_lost += 1
            self.stats.false_positives += 1
        
        self.stats.total_pnl += trade.pnl
        
        # Update win rate
        total = self.stats.trades_won + self.stats.trades_lost
        self.stats.win_rate = self.stats.trades_won / total if total > 0 else 0
        self.stats.avg_profit_per_trade = self.stats.total_pnl / total if total > 0 else 0
        
        # Move to closed trades
        del self.trades[trade.trade_id]
        self.closed_trades.append(trade)
        
        self._log_event("trade_resolved", {
            "trade_id": trade.trade_id,
            "expected_outcome": trade.opportunity.expected_outcome,
            "actual_outcome": trade.actual_outcome,
            "pnl": trade.pnl
        })
        
        logger.info(f"Trade resolved: {trade.trade_id}")
        logger.info(f"  Expected: {trade.opportunity.expected_outcome}")
        logger.info(f"  Actual: {trade.actual_outcome}")
        logger.info(f"  P&L: ${trade.pnl:.2f}")

    # ==========================================================================
    # Manual Market Feeding (for integration with live fixtures)
    # ==========================================================================
    
    async def feed_live_fixture_update(self, fixture_data: Dict):
        """
        Feed live fixture update for clipping analysis
        
        Call this from the main event loop when fixture updates arrive.
        
        Args:
            fixture_data: {
                "fixture_id": 12345,
                "market_id": "polymarket_abc123",
                "question": "Will Man City win?",
                "home_team": "Manchester City",
                "away_team": "Liverpool",
                "home_score": 3,
                "away_score": 0,
                "minute": 88,
                "status": "2H",
                "yes_price": 0.92,
                "no_price": 0.08
            }
        """
        # Convert fixture minute to seconds remaining
        minute = fixture_data.get("minute", 0)
        status = fixture_data.get("status", "")
        
        if status in ["FT", "AET", "PEN"]:
            return  # Match finished
        
        # Estimate seconds remaining (90 min match + injury time)
        total_minutes = 90
        if status == "HT":
            seconds_remaining = (total_minutes - 45) * 60
        elif status == "ET":
            seconds_remaining = 30 * 60  # Extra time
        else:
            seconds_remaining = max(0, (total_minutes - minute) * 60)
        
        # Build market dict for analysis
        market = {
            "market_id": fixture_data.get("market_id", f"fixture_{fixture_data['fixture_id']}"),
            "question": fixture_data.get("question", ""),
            "fixture_id": fixture_data.get("fixture_id"),
            "type": "soccer",
            "home_team": fixture_data.get("home_team"),
            "away_team": fixture_data.get("away_team"),
            "current_score": {
                "home": fixture_data.get("home_score", 0),
                "away": fixture_data.get("away_score", 0)
            },
            "seconds_to_close": seconds_remaining,
            "yes_price": fixture_data.get("yes_price", 0.5),
            "no_price": fixture_data.get("no_price", 0.5),
            "status": "active" if seconds_remaining > 0 else "resolved"
        }
        
        # Add to monitored markets
        self.monitored_markets[market["market_id"]] = market
        
        # Check for immediate clipping opportunity
        if seconds_remaining <= self.max_seconds_to_close:
            opportunity = await self._analyze_market_for_clipping(market)
            
            if opportunity:
                logger.info(f"Clipping opportunity from live fixture: {opportunity.opportunity_id}")
                self.active_opportunities[opportunity.opportunity_id] = opportunity
                self.stats.opportunities_detected += 1

    def _log_event(self, event_type: str, data: Dict):
        """Log event for analysis"""
        self.event_log.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        })

    def get_stats(self) -> AlphaTwoStats:
        """Get current performance statistics"""
        return self.stats

    def export_event_log(self, filepath: str):
        """Export event log to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.event_log, f, indent=2, default=str)
        logger.info(f"Event log exported to {filepath}")
