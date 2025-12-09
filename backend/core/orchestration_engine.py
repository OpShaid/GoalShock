
from .data_pipeline import DataAcquisitionLayer
from .stream_processor import StreamProcessor
from .market_synthesizer import MarketMicrostructure
from typing import Dict, List

class OrchestrationEngine:
    def __init__(self):
        self._dal = DataAcquisitionLayer()
        self._sp = StreamProcessor()
        self._mm = MarketMicrostructure()

    async def get_live_feed(self) -> Dict:
       
        raw_events = await self._dal.fetch_live_goals()

        market_data = await self._dal.fetch_market_data()

        enriched_events = await self._sp.enrich_events(raw_events, market_data)

        stats = await self._sp.aggregate_statistics(enriched_events)

        return {
            "events": enriched_events,
            "markets": market_data.get("markets", []),
            "statistics": stats,
            "timestamp": enriched_events[0]["timestamp"] if enriched_events else None
        }

    async def get_market_details(self, market_id: str) -> Dict:
        orderbook = self._mm.synthesize_orderbook(market_id)
        trade_history = self._mm.generate_trade_history(market_id)

        return {
            "market_id": market_id,
            "orderbook": orderbook,
            "recent_trades": trade_history,
            "timestamp": trade_history[0]["timestamp"] if trade_history else None
        }

    async def get_portfolio_status(self) -> Dict:
        pnl_history = self._mm.generate_pnl_path()

        # Current positions (synthetic for demo)
        positions = [
            {
                "market_id": "market_0",
                "question": "Will Manchester City win?",
                "side": "yes",
                "entry_price": 0.68,
                "current_price": 0.72,
                "size": 100,
                "pnl": 4.0
            },
            {
                "market_id": "market_2",
                "question": "Will Haaland score 30+ goals?",
                "side": "yes",
                "entry_price": 0.63,
                "current_price": 0.65,
                "size": 150,
                "pnl": 3.0
            }
        ]

        return {
            "pnl_history": pnl_history,
            "current_pnl": pnl_history[-1]["pnl"] if pnl_history else 1000,
            "positions": positions,
            "total_positions": len(positions)
        }

    async def cleanup(self):
        await self._dal.close()
