from __future__ import annotations

import os
from pathlib import Path

import pytest

from craig_bot.runtime import (
    _parse_dotenv,
    build_bot,
    compute_relative_strengths,
    estimate_base_lengths,
    load_alpaca_credentials,
)


def test_parse_dotenv_reads_key_values(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("ALPACA_API_KEY=abc\n# comment\nALPACA_SECRET_KEY='xyz'\n")

    values = _parse_dotenv(dotenv)
    assert values["ALPACA_API_KEY"] == "abc"
    assert values["ALPACA_SECRET_KEY"] == "xyz"


def test_load_alpaca_credentials_prefers_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "ALPACA_API_KEY=file_key\nALPACA_SECRET_KEY=file_secret\nALPACA_BASE_URL=https://paper.alpaca.markets\n"
    )

    monkeypatch.setenv("ALPACA_API_KEY", "env_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "env_secret")
    monkeypatch.setenv("ALPACA_BASE_URL", "https://live.alpaca.markets")

    credentials = load_alpaca_credentials(str(dotenv))
    assert credentials["ALPACA_API_KEY"] == "env_key"
    assert credentials["ALPACA_SECRET_KEY"] == "env_secret"
    assert credentials["ALPACA_BASE_URL"] == "https://live.alpaca.markets"


def test_load_alpaca_credentials_raises_when_missing(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("ALPACA_API_KEY=only_key\n")

    with pytest.raises(RuntimeError):
        load_alpaca_credentials(str(dotenv))


def test_compute_relative_strengths_orders_by_return() -> None:
    payload = {
        "AAA": {"close": [10, 11, 12, 13]},
        "BBB": {"close": [10, 9, 9.5, 9.7]},
        "CCC": {"close": [10, 10.5, 11, 11.5]},
    }

    strengths = compute_relative_strengths(payload, window=3)

    assert strengths["AAA"] > strengths["CCC"] > strengths["BBB"]
    assert 0.0 <= strengths["AAA"] <= 100.0


def test_estimate_base_lengths_defaults_to_minimum() -> None:
    payload = {
        "AAA": {
            "high": [10, 10.5, 10.2, 10.8, 10.9, 11.0],
        }
    }

    lengths = estimate_base_lengths(payload, lookback=10)
    assert lengths["AAA"] >= 35


def test_build_bot_creates_components(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    journal_path = tmp_path / "journal.json"
    bot = build_bot(journal_path=str(journal_path), account_equity=50_000, risk_fraction=0.02)

    assert bot.journal is not None
    assert bot.position_sizer.config.account_equity == 50_000
    assert bot.position_sizer.config.risk_fraction == 0.02

