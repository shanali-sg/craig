from types import SimpleNamespace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from craig_bot.data_sources import AlpacaMomentumSource


class DummyClient:
    def __init__(self) -> None:
        self.snapshots_payload = {}
        self.bars_payload = {}

    def get_snapshots(self, symbols):
        return {symbol: self.snapshots_payload.get(symbol) for symbol in symbols}

    def get_bars(self, symbol, timeframe, start, end, adjustment="raw"):
        return self.bars_payload.get(symbol, [])


def make_bar(o: float, h: float, l: float, c: float, v: float) -> SimpleNamespace:
    return SimpleNamespace(o=o, h=h, l=l, c=c, v=v)


def test_scan_fast_movers_ranks_by_percent_change():
    client = DummyClient()
    client.snapshots_payload = {
        "A": SimpleNamespace(daily_bar=SimpleNamespace(o=10.0, c=10.5, v=500_000)),
        "B": SimpleNamespace(daily_bar=SimpleNamespace(o=20.0, c=22.0, v=800_000)),
        "C": SimpleNamespace(daily_bar=SimpleNamespace(o=5.0, c=4.0, v=900_000)),
    }

    source = AlpacaMomentumSource(client)
    movers = source.scan_fast_movers(["A", "B", "C"], top_n=2)
    assert [snapshot.symbol for snapshot in movers] == ["B", "A"]


def test_fetch_price_series_shapes_payload():
    client = DummyClient()
    client.bars_payload = {
        "A": [
            make_bar(10.0, 10.5, 9.5, 10.2, 1_000_000),
            make_bar(10.2, 10.8, 10.0, 10.6, 900_000),
        ]
    }

    source = AlpacaMomentumSource(client)
    data = source.fetch_price_series(["A"], lookback_days=1)
    assert "A" in data
    payload = data["A"]
    assert payload["close"] == [10.6]
    assert payload["high"] == [10.8]
    assert payload["low"] == [10.0]
    assert payload["volume"] == [900000.0]
