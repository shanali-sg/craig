"""Momentum trading bot package aligned with Craig's strategy principles."""

from .bot import CandidateResult, MomentumBot
from .journal import TradeJournal, TradeRecord
from .risk import PositionSizer, PositionSizerConfig
from .strategy import MinerviniMomentumStrategy, StrategyConfig, StrategyEvaluation

__all__ = [
    "CandidateResult",
    "MomentumBot",
    "PositionSizer",
    "PositionSizerConfig",
    "MinerviniMomentumStrategy",
    "StrategyConfig",
    "StrategyEvaluation",
    "TradeJournal",
    "TradeRecord",
]
