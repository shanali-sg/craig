from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from craig_bot.journal import TradeJournal, TradeRecord
from craig_bot.strategy import StrategyConfig


def make_record(return_pct: float) -> TradeRecord:
    entry = 100.0
    exit_price = entry * (1 + return_pct)
    return TradeRecord(
        symbol="TEST",
        entry_price=entry,
        exit_price=exit_price,
        shares=10,
        entry_date="2023-01-01",
        exit_date="2023-01-02",
    )


def test_adaptive_config_raises_threshold(tmp_path: Path) -> None:
    journal = TradeJournal(tmp_path / "journal.json", min_samples=5)
    for _ in range(5):
        journal.record_trade(make_record(0.1))

    config = StrategyConfig(rs_threshold=70.0, max_pct_off_high=0.25)
    tuned = journal.apply_adaptive_tuning(config)
    assert tuned.rs_threshold > config.rs_threshold
    assert tuned.max_pct_off_high < config.max_pct_off_high


def test_adaptive_config_softens_threshold_on_losses(tmp_path: Path) -> None:
    journal = TradeJournal(tmp_path / "journal.json", min_samples=5)
    for _ in range(5):
        journal.record_trade(make_record(-0.1))

    config = StrategyConfig(rs_threshold=70.0, min_pct_from_low=0.3)
    tuned = journal.apply_adaptive_tuning(config)
    assert tuned.rs_threshold < config.rs_threshold
    assert tuned.min_pct_from_low <= config.min_pct_from_low
