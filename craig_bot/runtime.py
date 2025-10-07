"""Runtime helpers for wiring Craig's bot into real data workflows."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from .bot import MomentumBot
from .data_sources import AlpacaMomentumSource, PriceSeriesPayload
from .journal import TradeJournal
from .risk import PositionSizer, PositionSizerConfig
from .strategy import MinerviniMomentumStrategy


REQUIRED_ENV_VARS = {
    "ALPACA_API_KEY",
    "ALPACA_SECRET_KEY",
    "ALPACA_BASE_URL",
}


def _parse_dotenv(dotenv_path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not dotenv_path.exists():
        return values

    for raw_line in dotenv_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        value = raw_value.strip().strip("'\"")
        values[key.strip()] = value
    return values


def load_alpaca_credentials(dotenv_path: str = ".env") -> Dict[str, str]:
    """Load Alpaca credentials from environment variables and optional .env."""

    dotenv_values = _parse_dotenv(Path(dotenv_path))

    credentials: Dict[str, str] = {}
    missing: set[str] = set()
    for key in REQUIRED_ENV_VARS:
        value = os.environ.get(key) or dotenv_values.get(key)
        if not value:
            missing.add(key)
        else:
            credentials[key] = value

    if missing:
        joined = ", ".join(sorted(missing))
        raise RuntimeError(
            f"Missing required Alpaca credentials: {joined}. "
            "Set them in the environment or your .env file."
        )

    return credentials


def make_alpaca_client(credentials: Dict[str, str]):  # pragma: no cover - external dependency
    """Instantiate an Alpaca REST client using the provided credentials."""

    from alpaca_trade_api import REST

    return REST(
        credentials["ALPACA_API_KEY"],
        credentials["ALPACA_SECRET_KEY"],
        base_url=credentials["ALPACA_BASE_URL"],
    )


def build_bot(
    *,
    journal_path: str = "journal.json",
    account_equity: float = 100_000.0,
    risk_fraction: float = 0.01,
) -> MomentumBot:
    """Create a :class:`MomentumBot` with standard defaults."""

    strategy = MinerviniMomentumStrategy()
    position_sizer = PositionSizer(
        PositionSizerConfig(
            account_equity=account_equity,
            risk_fraction=risk_fraction,
        )
    )
    journal = TradeJournal(journal_path)
    return MomentumBot(strategy=strategy, position_sizer=position_sizer, journal=journal)


def compute_relative_strengths(
    price_series: PriceSeriesPayload, window: int = 125
) -> Dict[str, float]:
    """Convert trailing returns into percentile-based relative strength scores."""

    if window < 1:
        raise ValueError("window must be positive")

    trailing_returns: Dict[str, float] = {}
    for symbol, payload in price_series.items():
        closes = payload.get("close", [])
        if len(closes) < 2:
            continue
        lookback = min(window, len(closes) - 1)
        baseline = closes[-lookback - 1]
        latest = closes[-1]
        if baseline <= 0:
            continue
        trailing_returns[symbol] = (latest / baseline) - 1.0

    if not trailing_returns:
        raise ValueError("No trailing returns could be computed for relative strength")

    sorted_items = sorted(trailing_returns.items(), key=lambda item: item[1])
    denominator = max(len(sorted_items) - 1, 1)

    strengths: Dict[str, float] = {}
    for index, (symbol, _) in enumerate(sorted_items):
        percentile = 100.0 if denominator == 0 else index / denominator * 100.0
        strengths[symbol] = percentile
    return strengths


def estimate_base_lengths(
    price_series: PriceSeriesPayload, lookback: int = 90
) -> Dict[str, int]:
    """Estimate base lengths using the distance from the latest 3-month high."""

    if lookback < 1:
        raise ValueError("lookback must be positive")

    base_lengths: Dict[str, int] = {}
    for symbol, payload in price_series.items():
        highs = payload.get("high", [])
        if not highs:
            continue
        window = min(len(highs), lookback)
        recent_slice = list(highs[-window:])
        pivot = max(recent_slice)
        pivot_index = recent_slice.index(pivot)
        absolute_index = len(highs) - window + pivot_index
        base_length = len(highs) - absolute_index
        base_lengths[symbol] = max(int(base_length), 35)

    if not base_lengths:
        raise ValueError("Unable to derive base lengths from the provided data")

    return base_lengths


def prepare_data_source(credentials: Dict[str, str]) -> AlpacaMomentumSource:
    """Construct an :class:`AlpacaMomentumSource` from credentials."""

    client = make_alpaca_client(credentials)
    return AlpacaMomentumSource(client)

