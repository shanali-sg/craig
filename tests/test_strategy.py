import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from craig_bot.strategy import MinerviniMomentumStrategy, StrategyConfig
from craig_bot.risk import PositionSizer, PositionSizerConfig
from craig_bot.bot import MomentumBot


def build_trending_data(periods: int = 400) -> dict[str, list[float]]:
    close = []
    for idx in range(periods):
        base = 50 + 70 * idx / (periods - 1)
        noise = 0.2 * math.sin(idx / 7)
        close.append(base + noise)
    high = [price + 1 for price in close]
    low = [price - 1 for price in close]
    volume = [500_000 - 400 * idx for idx in range(periods)]
    return {"close": close, "high": high, "low": low, "volume": volume}


def test_strategy_flags_qualifying_candidate():
    data = build_trending_data()
    strategy = MinerviniMomentumStrategy(StrategyConfig(rs_threshold=65))
    evaluation = strategy.evaluate(data, relative_strength=85, base_length=60)
    assert evaluation.qualifies
    assert not evaluation.reasons
    assert evaluation.score > 0


def test_strategy_rejects_when_trend_is_missing():
    data = build_trending_data()
    data["close"] = list(reversed(data["close"]))
    data["high"] = [price + 1 for price in data["close"]]
    data["low"] = [price - 1 for price in data["close"]]
    strategy = MinerviniMomentumStrategy()
    evaluation = strategy.evaluate(data, relative_strength=85, base_length=60)
    assert not evaluation.qualifies
    assert "200-day trend is not rising" in evaluation.reasons


def test_bot_ranks_candidates_by_score():
    data_a = build_trending_data()
    data_b = build_trending_data()
    data_b["close"] = [price * 0.9 for price in data_b["close"]]
    data_b["high"] = [price + 1 for price in data_b["close"]]
    data_b["low"] = [price - 1 for price in data_b["close"]]

    strategy = MinerviniMomentumStrategy()
    position_sizer = PositionSizer(PositionSizerConfig(account_equity=50_000))
    bot = MomentumBot(strategy, position_sizer)

    price_series = {"AAA": data_a, "BBB": data_b}
    relative_strengths = {"AAA": 90, "BBB": 75}
    base_lengths = {"AAA": 60, "BBB": 60}

    ranked = bot.rank_candidates(
        price_series,
        relative_strengths=relative_strengths,
        base_lengths=base_lengths,
    )
    assert [result.symbol for result in ranked] == ["AAA", "BBB"]
    plan = ranked[0].position_plan
    assert plan["shares"] > 0
