# Fast-Mover Playground

The Alpaca fast-mover scan inside `AlpacaMomentumSource` is intentionally
real-time. Because intraday gainers shift quickly, replaying the scan over raw
historical bars rarely mirrors the live order book. Instead of attempting a
full backtest, the bot is designed so you can **record snapshots** and then
**replay them locally** to iterate on the workflow.

## 1. Record live snapshots

When you run a live scan, persist the payload that Alpaca returns:

```python
snapshots = client.get_snapshots(universe)
with open("2024-05-21-snapshots.json", "w") as fp:
    json.dump({symbol: snapshot._raw for symbol, snapshot in snapshots.items()}, fp)
```

Most Alpaca SDKs expose a `_raw` dictionary; otherwise you can build the dict by
hand. Capture the same universe every day so your comparisons remain apples to
apples.

## 2. Rehydrate snapshots with a fake client

The unit tests (`tests/test_data_sources.py`) already show how to stub the
client. You can copy that idea into a small playground script:

```python
import json
from types import SimpleNamespace

from craig_bot.data_sources import AlpacaMomentumSource

class ReplayClient:
    def __init__(self, snapshot_path, bars_path):
        with open(snapshot_path) as fp:
            raw_snapshots = json.load(fp)
        self.snapshots_payload = {
            symbol: SimpleNamespace(daily_bar=SimpleNamespace(**payload["daily_bar"]))
            for symbol, payload in raw_snapshots.items()
        }
        with open(bars_path) as fp:
            self.bars_payload = json.load(fp)

    def get_snapshots(self, symbols):
        return {symbol: self.snapshots_payload.get(symbol) for symbol in symbols}

    def get_bars(self, symbol, timeframe, start, end, adjustment="raw"):
        bars = self.bars_payload.get(symbol, [])
        return [SimpleNamespace(**bar) for bar in bars]

source = AlpacaMomentumSource(ReplayClient("2024-05-21-snapshots.json", "2024-05-21-bars.json"))
fast_movers = source.scan_fast_movers(["AAPL", "NVDA", "TSLA"])
```

Pair the snapshot file with a bar history export for the same session. The
`ReplayClient` returns exactly what the production data source expects, so you
can pipe the results into `MomentumBot` for a full dry run.

## 3. Drive the bot end to end

Once you have replay assets, you can execute the full pipeline without touching
Alpaca:

```python
from craig_bot.bot import MomentumBot
from craig_bot.journal import TradeJournal
from craig_bot.strategy import MomentumStrategy

journal = TradeJournal.load_or_create("journal.json")
strategy = MomentumStrategy()
source = AlpacaMomentumSource(ReplayClient(...))

bot = MomentumBot(strategy=strategy, data_source=source, journal=journal)
report = bot.build_watchlist(["AAPL", "NVDA", "TSLA"])
```

Because the journal persists to disk you can still grade hypothetical trades and
let the adaptive thresholds react.

## 4. Create what-if scenarios

To explore edge cases, edit the snapshot JSON by hand. For example, bump the
volume of a symbol to see when it clears the liquidity gate or tweak the daily
bar close to emulate a failed breakout. By replaying multiple variants of the
same day you can probe the sensitivity of each checklist item.

## 5. Paper trade the outputs

The fastest feedback loop is to paper trade from the replayed watchlists. Pick a
subset of signals, track them in the journal, and compare how the tuned
thresholds evolve versus the raw defaults. Even though the fast-mover scan isn’t
fully backtestable, this approach gives you a repeatable sandbox that reflects
real Alpaca data while preserving Minervini-style discipline.
