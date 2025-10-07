"""End-to-end orchestration for Craig's momentum trading bot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Tuple

from .journal import TradeJournal, TradeRecord
from .risk import PositionSizer
from .strategy import MinerviniMomentumStrategy, PriceSeries, StrategyEvaluation


@dataclass
class CandidateResult:
    symbol: str
    evaluation: StrategyEvaluation
    position_plan: Dict[str, float]


class MomentumBot:
    """Aggregate strategy evaluation, risk sizing, and portfolio ranking."""

    def __init__(
        self,
        strategy: MinerviniMomentumStrategy,
        position_sizer: PositionSizer,
        *,
        journal: TradeJournal | None = None,
    ) -> None:
        self.strategy = strategy
        self.position_sizer = position_sizer
        self.journal = journal

    def rank_candidates(
        self,
        price_series: Mapping[str, PriceSeries],
        *,
        relative_strengths: Mapping[str, float],
        base_lengths: Mapping[str, int],
    ) -> List[CandidateResult]:
        if self.journal is not None:
            tuned_config = self.journal.apply_adaptive_tuning(self.strategy.config)
            if tuned_config != self.strategy.config:
                self.strategy = MinerviniMomentumStrategy(tuned_config)

        results: List[CandidateResult] = []
        for symbol, series in price_series.items():
            if symbol not in relative_strengths:
                raise KeyError(f"Relative strength not provided for {symbol}")
            if symbol not in base_lengths:
                raise KeyError(f"Base length not provided for {symbol}")

            evaluation = self.strategy.evaluate(
                series,
                relative_strength=relative_strengths[symbol],
                base_length=base_lengths[symbol],
            )
            if not evaluation.qualifies:
                continue

            position_plan = self.position_sizer.size_position(
                evaluation.entry_price, evaluation.metrics["atr_14"]
            )
            results.append(CandidateResult(symbol, evaluation, position_plan))

        results.sort(key=lambda result: result.evaluation.score, reverse=True)
        return results

    def summary(self, candidates: Iterable[CandidateResult]) -> List[Tuple[str, float, float, int]]:
        table: List[Tuple[str, float, float, int]] = []
        for result in candidates:
            plan = result.position_plan
            table.append(
                (
                    result.symbol,
                    result.evaluation.score,
                    plan.get("stop_price", float("nan")),
                    plan.get("shares", 0),
                )
            )
        return table

    # ------------------------------------------------------------------
    # Journal integration
    # ------------------------------------------------------------------
    def record_completed_trade(self, record: TradeRecord) -> None:
        """Persist an executed trade outcome for adaptive learning."""

        if self.journal is None:
            raise RuntimeError("No journal configured for this bot instance")
        self.journal.record_trade(record)
