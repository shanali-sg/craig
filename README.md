# Craig Momentum Bot

This repository contains a momentum trading bot aligned with Craig's strategy
and Mark Minervini's momentum principles.

## What's New

- **Persistent trade journal** – outcomes are written to disk and every five
  trades the journal automatically tightens or loosens the key momentum
  thresholds depending on performance.
- **Alpaca fast-mover scan** – a lightweight Alpaca data source fetches daily
  gainers that satisfy Minervini-inspired liquidity and price filters and
  shapes OHLCV history for the strategy to evaluate.
- **Adaptive orchestration** – the bot consults the journal before each
  ranking pass, ensuring fresh candidates leverage the tuned configuration.

## Components

- `craig_bot/strategy.py` – Minervini-inspired checklist for qualifying
  breakouts.
- `craig_bot/risk.py` – ATR-based position sizing using fixed-fractional risk.
- `craig_bot/bot.py` – Orchestrates screening results into a ranked watchlist.
- `docs/minervini_alignment.md` – Documentation showing the alignment between
  the bot and Minervini's class teachings.
- `tests/test_strategy.py` – Deterministic unit tests validating the workflow
  without third-party dependencies.
- `docs/fast_mover_playground.md` – A hands-on guide for experimenting with the
  fast-mover workflow using recorded Alpaca data and faked clients.

## Running Tests

```bash
pytest
```
