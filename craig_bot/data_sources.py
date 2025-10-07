"""Data access helpers that integrate Craig's bot with the Alpaca API."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List

PriceSeriesPayload = Dict[str, Dict[str, List[float]]]


def _extract_attr(obj: object, name: str, default: float | int | None = None) -> float | int | None:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


@dataclass
class AlpacaSnapshot:
    symbol: str
    percent_change: float
    volume: float
    close: float


class AlpacaMomentumSource:
    """Helper around Alpaca's REST client for Minervini-style scans."""

    def __init__(self, client) -> None:  # pragma: no cover - duck typed client
        self.client = client

    # ------------------------------------------------------------------
    # Fast mover scanning
    # ------------------------------------------------------------------
    def scan_fast_movers(
        self,
        universe: Iterable[str],
        *,
        min_price: float = 5.0,
        min_volume: float = 200_000,
        top_n: int = 25,
    ) -> List[AlpacaSnapshot]:
        """Select the fastest movers from the universe based on daily percent change."""

        symbols = list(universe)
        if not symbols:
            return []

        snapshots = self.client.get_snapshots(symbols)  # type: ignore[attr-defined]
        ranked: List[AlpacaSnapshot] = []
        for symbol in symbols:
            snapshot = snapshots.get(symbol)
            if snapshot is None:
                continue

            daily_bar = _extract_attr(snapshot, "daily_bar") or _extract_attr(snapshot, "dailyBar")
            if daily_bar is None:
                continue

            close = float(_extract_attr(daily_bar, "c", 0.0) or 0.0)
            open_price = float(_extract_attr(daily_bar, "o", 0.0) or 0.0)
            volume = float(_extract_attr(daily_bar, "v", 0.0) or 0.0)
            if open_price <= 0 or close < min_price or volume < min_volume:
                continue

            percent_change = (close - open_price) / open_price
            ranked.append(
                AlpacaSnapshot(
                    symbol=symbol,
                    percent_change=percent_change,
                    volume=volume,
                    close=close,
                )
            )

        ranked.sort(key=lambda snap: snap.percent_change, reverse=True)
        return ranked[:top_n]

    # ------------------------------------------------------------------
    # Historical price utilities
    # ------------------------------------------------------------------
    def fetch_price_series(
        self,
        symbols: Iterable[str],
        *,
        lookback_days: int = 365,
        timeframe: str = "1Day",
    ) -> PriceSeriesPayload:
        """Download OHLCV candles and shape them into Craig's price payload format."""

        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=lookback_days * 2)

        payload: PriceSeriesPayload = {}
        for symbol in symbols:
            bars = self.client.get_bars(  # type: ignore[attr-defined]
                symbol,
                timeframe,
                start.isoformat(),
                end.isoformat(),
                adjustment="raw",
            )

            close: List[float] = []
            high: List[float] = []
            low: List[float] = []
            volume: List[float] = []
            for bar in bars:
                close.append(float(_extract_attr(bar, "c", 0.0) or 0.0))
                high.append(float(_extract_attr(bar, "h", 0.0) or 0.0))
                low.append(float(_extract_attr(bar, "l", 0.0) or 0.0))
                volume.append(float(_extract_attr(bar, "v", 0.0) or 0.0))

            if not close:
                continue

            payload[symbol] = {
                "close": close[-lookback_days:],
                "high": high[-lookback_days:],
                "low": low[-lookback_days:],
                "volume": volume[-lookback_days:],
            }

        return payload
