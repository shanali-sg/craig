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
- `craig_bot/runtime.py` – Utilities for wiring credentials and heuristics.
- `craig_bot/cli.py` – Command line entry point for historical and live runs.
- `docs/minervini_alignment.md` – Documentation showing the alignment between
  the bot and Minervini's class teachings.
- `tests/test_strategy.py` – Deterministic unit tests validating the workflow
  without third-party dependencies.
- `docs/fast_mover_playground.md` – A hands-on guide for experimenting with the
  fast-mover workflow using recorded Alpaca data and faked clients.

## Set up credentials

Create a `.env` file (or export the variables in your shell) with your Alpaca
credentials:

```dotenv
ALPACA_API_KEY="xxxx"
ALPACA_SECRET_KEY="yyy"
ALPACA_BASE_URL="https://api.alpaca.markets"
```

Install dependencies and activate your environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip alpaca-trade-api
```

## Historical dry run

You can rehearse tomorrow's session on end-of-day data directly from Alpaca.

```bash
python -m craig_bot.cli historical \
  --symbols AAPL NVDA TSLA \
  --lookback-days 400 \
  --journal journal.json
```

The command downloads the requested history, estimates relative strength and
base lengths, and prints a ranked table. Add `--output watchlist.json` to
persist the full evaluation payload for further review.

## Live fast-mover run

When the market opens, use the same CLI to pull the day's fast movers and build
a trading plan:

```bash
python -m craig_bot.cli live \
  --universe AAPL NVDA TSLA MSFT AMD META GOOGL \
  --journal journal.json \
  --top-n 15
```

The bot records outcomes in `journal.json` so the adaptive tuning evolves as you
paper trade or execute real positions. Supply `--symbols` to seed the scan with
a custom watchlist, or `--universe` to rely on the default filters.

## Running Tests

```bash
pytest
```
