
import random
import math
from typing import Dict, List
from datetime import datetime, timedelta

class MarketMicrostructure:
    def __init__(self):
        self._vol_state = {}
        self._flow_imbalance = {}

    def _brownian_drift(self, current: float, volatility: float, dt: float = 1.0) -> float:
        mu = 0.0 
        sigma = volatility
        dW = random.gauss(0, math.sqrt(dt))
        return current * math.exp((mu - 0.5 * sigma**2) * dt + sigma * dW)

    def _order_flow_imbalance(self) -> float:
        """Simulate order flow imbalance (-1 to 1)"""
        return random.gauss(0, 0.3)

    def _microstructure_noise(self) -> float:
        """High-frequency tick noise"""
        return random.gauss(0, 0.0005)

    def synthesize_orderbook(self, market_id: str, base_price: float = None) -> Dict:
        """Generate realistic limit order book"""
        if base_price is None:
            base_price = random.uniform(0.3, 0.7)

        if market_id not in self._vol_state:
            self._vol_state[market_id] = random.uniform(0.02, 0.08)

        current_vol = self._vol_state[market_id]
        vol_shock = random.gauss(0, 0.01)
        self._vol_state[market_id] = max(0.01, current_vol * 0.9 + abs(vol_shock) * 0.1)

        mid_price = self._brownian_drift(base_price, current_vol, 0.1)
        mid_price = max(0.01, min(0.99, mid_price))

        mid_price += self._microstructure_noise()

        base_spread = 0.02
        spread = base_spread * (1 + abs(self._order_flow_imbalance()))

        bids = []
        asks = []

        for i in range(5):
            bid_price = mid_price - spread / 2 - i * 0.01
            bid_size = random.randint(100, 5000) * (1 + random.random())
            bids.append({"price": round(bid_price, 4), "size": int(bid_size)})

            ask_price = mid_price + spread / 2 + i * 0.01
            ask_size = random.randint(100, 5000) * (1 + random.random())
            asks.append({"price": round(ask_price, 4), "size": int(ask_size)})

        total_volume = random.randint(50000, 500000)

        return {
            "mid_price": round(mid_price, 4),
            "spread": round(spread, 4),
            "bids": sorted(bids, key=lambda x: x["price"], reverse=True),
            "asks": sorted(asks, key=lambda x: x["price"]),
            "total_volume": total_volume,
            "volatility": round(current_vol, 4)
        }

    def generate_trade_history(self, market_id: str, num_trades: int = 20) -> List[Dict]:
        """Generate realistic trade history"""
        trades = []
        current_time = datetime.now()

        orderbook = self.synthesize_orderbook(market_id)
        current_price = orderbook["mid_price"]

        for i in range(num_trades):
            is_buy = random.random() > 0.5
            if is_buy:
                price = random.choice(orderbook["asks"])["price"]
                price += random.gauss(0, 0.001)
            else:
                price = random.choice(orderbook["bids"])["price"]
                price -= random.gauss(0, 0.001)

            size = random.randint(10, 1000)
            timestamp = current_time - timedelta(minutes=i * random.randint(1, 5))

            trades.append({
                "price": round(price, 4),
                "size": size,
                "side": "buy" if is_buy else "sell",
                "timestamp": timestamp.isoformat()
            })

        return sorted(trades, key=lambda x: x["timestamp"], reverse=True)

    def generate_pnl_path(self, initial_value: float = 1000, num_points: int = 100) -> List[Dict]:
        """Generate realistic P&L path with proper risk characteristics"""
        pnl_history = []
        current_pnl = initial_value

        win_rate = 0.58
        avg_win = 0.02
        avg_loss = -0.015

        for i in range(num_points):
            if random.random() < win_rate:
                change_pct = random.gauss(avg_win, 0.01)
            else:
                change_pct = random.gauss(avg_loss, 0.008)

            current_pnl *= (1 + change_pct)

            timestamp = datetime.now() - timedelta(hours=num_points - i)
            pnl_history.append({
                "timestamp": timestamp.isoformat(),
                "pnl": round(current_pnl, 2),
                "change_pct": round(change_pct * 100, 2)
            })

        return pnl_history
