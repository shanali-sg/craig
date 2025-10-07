"""Persistent trade journal and adaptive tuning for Craig's trader bot."""

from __future__ import annotations

from dataclasses import dataclass, asdict, replace
from pathlib import Path
from statistics import mean
from typing import Iterable, List, Sequence

from .strategy import StrategyConfig


@dataclass(frozen=True)
class TradeRecord:
    """Representation of an executed trade captured in the journal."""

    symbol: str
    entry_price: float
    exit_price: float
    shares: int
    entry_date: str
    exit_date: str

    @property
    def pnl(self) -> float:
        """Absolute profit and loss for the trade."""

        return (self.exit_price - self.entry_price) * self.shares

    @property
    def return_pct(self) -> float:
        """Percent return based on entry capital."""

        if self.entry_price == 0:
            return 0.0
        return (self.exit_price - self.entry_price) / self.entry_price


class TradeJournal:
    """Persist trade outcomes and adapt strategy configuration heuristically."""

    def __init__(self, path: str | Path, *, min_samples: int = 5) -> None:
        self.path = Path(path)
        self.min_samples = min_samples
        self._records: List[TradeRecord] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.path.exists():
            return
        data = self.path.read_text().strip()
        if not data:
            return
        import json

        raw = json.loads(data)
        self._records = [TradeRecord(**item) for item in raw]

    def _persist(self) -> None:
        import json

        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(record) for record in self._records]
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def record_trade(self, record: TradeRecord) -> None:
        """Append a trade outcome and persist to storage."""

        self._records.append(record)
        self._persist()

    def records(self) -> Sequence[TradeRecord]:
        return tuple(self._records)

    # ------------------------------------------------------------------
    # Adaptive tuning
    # ------------------------------------------------------------------
    def adapt_config(self, config: StrategyConfig) -> StrategyConfig:
        """Adjust configuration thresholds based on recent performance."""

        recent = self._records[-self.min_samples :]
        if len(recent) < self.min_samples:
            return config

        returns = [record.return_pct for record in recent]
        wins = [value for value in returns if value > 0]
        win_rate = len(wins) / len(recent)
        avg_return = mean(returns)

        rs_threshold = config.rs_threshold
        max_pct_off_high = config.max_pct_off_high
        min_pct_from_low = config.min_pct_from_low

        if win_rate > 0.6 and avg_return > 0:
            rs_threshold = min(rs_threshold + 5.0, 95.0)
            max_pct_off_high = max(max_pct_off_high - 0.02, 0.15)
        elif win_rate < 0.4:
            rs_threshold = max(rs_threshold - 5.0, 60.0)
            min_pct_from_low = max(min_pct_from_low - 0.05, 0.10)

        return replace(
            config,
            rs_threshold=rs_threshold,
            max_pct_off_high=max_pct_off_high,
            min_pct_from_low=min_pct_from_low,
        )

    def apply_adaptive_tuning(
        self, strategy_config: StrategyConfig
    ) -> StrategyConfig:
        """Public entry point that wraps :meth:`adapt_config`."""

        return self.adapt_config(strategy_config)


def bootstrap_journal(path: str | Path, records: Iterable[TradeRecord]) -> TradeJournal:
    """Create a journal and seed it with records (mainly for tests)."""

    journal = TradeJournal(path)
    for record in records:
        journal.record_trade(record)
    return journal

