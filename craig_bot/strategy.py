"""Core momentum strategy logic used by Craig's trader bot."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence

PriceSeries = Mapping[str, Sequence[float]]


@dataclass(frozen=True)
class StrategyConfig:
    """Configuration options for the Minervini inspired momentum template."""

    rs_threshold: float = 70.0
    max_pct_off_high: float = 0.25
    min_pct_from_low: float = 0.30
    min_volume_dry_up_ratio: float = 0.5
    trend_lookback: int = 10
    min_base_length: int = 35


@dataclass(frozen=True)
class StrategyEvaluation:
    """Outcome of evaluating a single asset against the strategy rules."""

    qualifies: bool
    score: float
    reasons: List[str]
    metrics: Dict[str, float]
    entry_price: float
    stop_price: float


def _to_float_list(values: Sequence[float]) -> List[float]:
    return [float(value) for value in values]


def _validate_inputs(price_data: PriceSeries) -> None:
    required = {"close", "high", "low", "volume"}
    missing = required.difference(price_data.keys())
    if missing:
        raise ValueError(f"Price data missing required series: {sorted(missing)}")

    lengths = {len(series) for series in price_data.values()}
    if len(lengths) != 1:
        raise ValueError("All price series must share the same length")


def _rolling_mean(values: Sequence[float], window: int) -> List[float]:
    length = len(values)
    result = [math.nan] * length
    if length < window or window <= 0:
        return result

    window_sum = sum(values[:window])
    result[window - 1] = window_sum / window
    for idx in range(window, length):
        window_sum += values[idx] - values[idx - window]
        result[idx] = window_sum / window
    return result


def _rolling_max(values: Sequence[float], window: int) -> List[float]:
    length = len(values)
    result = [math.nan] * length
    if length < window or window <= 0:
        return result

    for idx in range(window - 1, length):
        window_slice = values[idx - window + 1 : idx + 1]
        result[idx] = max(window_slice)
    return result


def _rolling_min(values: Sequence[float], window: int) -> List[float]:
    length = len(values)
    result = [math.nan] * length
    if length < window or window <= 0:
        return result

    for idx in range(window - 1, length):
        window_slice = values[idx - window + 1 : idx + 1]
        result[idx] = min(window_slice)
    return result


def _ema(values: Sequence[float], span: int) -> List[float]:
    length = len(values)
    result = [math.nan] * length
    if length < span or span <= 0:
        return result

    alpha = 2.0 / (span + 1.0)
    initial = sum(values[:span]) / span
    result[span - 1] = initial
    for idx in range(span, length):
        result[idx] = alpha * values[idx] + (1.0 - alpha) * result[idx - 1]
    return result


def _atr(high: Sequence[float], low: Sequence[float], close: Sequence[float], window: int) -> List[float]:
    length = len(close)
    true_range = [0.0] * length
    true_range[0] = high[0] - low[0]
    for idx in range(1, length):
        high_low = high[idx] - low[idx]
        high_close = abs(high[idx] - close[idx - 1])
        low_close = abs(low[idx] - close[idx - 1])
        true_range[idx] = max(high_low, high_close, low_close)
    return _rolling_mean(true_range, window)


def calculate_indicators(price_data: PriceSeries) -> Dict[str, List[float]]:
    """Calculate rolling indicators used by the momentum template."""

    _validate_inputs(price_data)
    close = _to_float_list(price_data["close"])
    high = _to_float_list(price_data["high"])
    low = _to_float_list(price_data["low"])
    volume = _to_float_list(price_data["volume"])

    sma_50 = _rolling_mean(close, 50)
    sma_150 = _rolling_mean(close, 150)
    sma_200 = _rolling_mean(close, 200)
    ema_21 = _ema(close, 21)
    avg_volume_50 = _rolling_mean(volume, 50)
    avg_volume_10 = _rolling_mean(volume, 10)
    high_52 = _rolling_max(high, 252)
    low_52 = _rolling_min(low, 252)
    atr_14 = _atr(high, low, close, 14)

    pct_off_high = [math.nan] * len(close)
    pct_from_low = [math.nan] * len(close)
    volume_dry_up = [math.nan] * len(close)
    for idx, price in enumerate(close):
        high_val = high_52[idx]
        low_val = low_52[idx]
        avg_10 = avg_volume_10[idx]
        avg_50 = avg_volume_50[idx]

        if math.isfinite(high_val) and high_val != 0:
            pct_off_high[idx] = (high_val - price) / high_val
        if math.isfinite(low_val) and low_val != 0:
            pct_from_low[idx] = (price - low_val) / low_val
        if math.isfinite(avg_10) and math.isfinite(avg_50) and avg_50 > 0:
            volume_dry_up[idx] = avg_10 / avg_50

    return {
        "close": close,
        "sma_50": sma_50,
        "sma_150": sma_150,
        "sma_200": sma_200,
        "ema_21": ema_21,
        "avg_volume_50": avg_volume_50,
        "avg_volume_10": avg_volume_10,
        "high_52": high_52,
        "low_52": low_52,
        "atr_14": atr_14,
        "pct_off_high": pct_off_high,
        "pct_from_low": pct_from_low,
        "volume_dry_up": volume_dry_up,
    }


class MinerviniMomentumStrategy:
    """Implementation of Mark Minervini's momentum template customized for Craig."""

    def __init__(self, config: StrategyConfig | None = None) -> None:
        self.config = config or StrategyConfig()

    def evaluate(
        self,
        price_data: PriceSeries,
        *,
        relative_strength: float,
        base_length: int,
    ) -> StrategyEvaluation:
        indicators = calculate_indicators(price_data)
        latest_idx = -1

        reasons: List[str] = []
        qualifies = True

        def fail(reason: str) -> None:
            nonlocal qualifies
            qualifies = False
            reasons.append(reason)

        latest_ma = [
            indicators["sma_50"][latest_idx],
            indicators["sma_150"][latest_idx],
            indicators["sma_200"][latest_idx],
        ]
        if any(math.isnan(value) for value in latest_ma):
            fail("Not enough data to compute moving averages")
            close_price = indicators["close"][latest_idx]
            return StrategyEvaluation(
                qualifies=False,
                score=0.0,
                reasons=reasons,
                metrics={"relative_strength": relative_strength},
                entry_price=float(close_price),
                stop_price=float(close_price),
            )

        if not (latest_ma[0] > latest_ma[1] > latest_ma[2]):
            fail("Moving averages are not stacked in bullish order")

        sma_200 = indicators["sma_200"]
        if len(sma_200) > self.config.trend_lookback:
            earlier = sma_200[latest_idx - self.config.trend_lookback]
            latest_200 = sma_200[latest_idx]
            if math.isnan(earlier) or math.isnan(latest_200) or latest_200 <= earlier:
                fail("200-day trend is not rising")
        else:
            fail("Not enough data to assess 200-day trend")

        close_price = indicators["close"][latest_idx]
        if close_price <= latest_ma[0] or close_price <= latest_ma[1]:
            fail("Price is not above key moving averages")

        pct_off_high = indicators["pct_off_high"][latest_idx]
        if not math.isfinite(pct_off_high) or pct_off_high > self.config.max_pct_off_high:
            fail("Price is extended too far below 52-week high")

        pct_from_low = indicators["pct_from_low"][latest_idx]
        if not math.isfinite(pct_from_low) or pct_from_low < self.config.min_pct_from_low:
            fail("Price is not sufficiently off the 52-week low")

        if relative_strength < self.config.rs_threshold:
            fail("Relative strength is below threshold")

        volume_dry_up = indicators["volume_dry_up"][latest_idx]
        if not math.isfinite(volume_dry_up) or volume_dry_up < self.config.min_volume_dry_up_ratio:
            fail("Volume has not dried up during base")

        if base_length < self.config.min_base_length:
            fail("Base duration is too short")

        atr = indicators["atr_14"][latest_idx]
        if not math.isfinite(atr) or atr <= 0:
            fail("ATR is not available")

        score_components = [
            min(relative_strength / 100.0, 1.0),
            min(1.0 - pct_off_high, 1.0),
            min(pct_from_low, 1.0),
            min(volume_dry_up / 1.5, 1.0),
        ]
        score = sum(score_components) / len(score_components)
        stop_price = float(close_price - 2.0 * atr)

        metrics = {
            "sma_50": float(latest_ma[0]),
            "sma_150": float(latest_ma[1]),
            "sma_200": float(latest_ma[2]),
            "atr_14": float(atr) if math.isfinite(atr) else float("nan"),
            "pct_off_high": float(pct_off_high) if math.isfinite(pct_off_high) else float("nan"),
            "pct_from_low": float(pct_from_low) if math.isfinite(pct_from_low) else float("nan"),
            "volume_dry_up": float(volume_dry_up) if math.isfinite(volume_dry_up) else float("nan"),
            "relative_strength": float(relative_strength),
        }

        return StrategyEvaluation(
            qualifies=qualifies,
            score=score if qualifies else 0.0,
            reasons=reasons,
            metrics=metrics,
            entry_price=float(close_price),
            stop_price=stop_price,
        )
