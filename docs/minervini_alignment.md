# Alignment with Mark Minervini's Momentum Principles

This document cross-checks Craig's momentum bot implementation against the
widely cited guidance from Mark Minervini, often called the "Godfather of
momentum trading." While we cannot reference the private classroom material
directly, the bot explicitly codifies the central tenets he teaches so that the
strategy is *validated* rather than contradicted by his framework.

## Core Minervini Tenets and Bot Coverage

| Minervini Focus | Bot Implementation | Notes |
| --- | --- | --- |
| **Trend Template** – 50-day SMA above 150-day, which is above 200-day; price above key MAs; 200-day rising. | `MinerviniMomentumStrategy.evaluate` enforces stacked moving averages and positive 200-day slope. | Prevents trades against the primary trend.
| **Leadership via Relative Strength** – buy stocks outperforming the market. | `StrategyConfig.rs_threshold` with `relative_strength` input gates candidates below a configurable RS score. | Allows integration with RS rank feeds and Alpaca fast-mover scans.
| **Proximity to Highs** – buy near 52-week highs, avoid deep pullbacks. | `pct_off_high` and `pct_from_low` checks ensure the price is within Minervini's preferred range. | Guards against laggard entries.
| **Volume Dry-Up before Breakout** – contraction in volume preceding a breakout. | `volume_dry_up` ratio compares 10-day to 50-day average volume, requiring contraction. | Reinforces constructive base behavior.
| **Constructive Base Duration** – proper consolidations typically last 5+ weeks. | `StrategyConfig.min_base_length` ensures bases shorter than 35 sessions are rejected. | Filters out premature entries.
| **Volatility-Aware Risk** – position sizing via ATR-based stops. | `PositionSizer.size_position` uses ATR to calculate stop distance and share size. | Keeps risk per trade within fixed-fraction limits.
| **Iterative Improvement** – journal review of trade outcomes to tighten execution. | `TradeJournal` persists results and tunes RS / base parameters after every five trades. | Mirrors Minervini's emphasis on post-trade analysis.

## When the Bot Will Step Aside

* No trade if trend stack breaks or the 200-day slope turns flat/negative.
* Candidates with lagging RS scores or that are >25% off highs are rejected.
* Trades are skipped when ATR cannot be computed or volume fails to contract.

## Workflow for Craig

1. Use `AlpacaMomentumSource.scan_fast_movers` to surface liquid daily leaders or ingest an equivalent RS list.
2. Call `AlpacaMomentumSource.fetch_price_series` (or another data loader) for OHLCV history per symbol.
3. Run `MomentumBot.rank_candidates` to obtain a scored, risk-aware watchlist.
4. Review `CandidateResult.position_plan` to confirm shares, stop price, and capital exposure before execution.
5. After trades complete, record them through `MomentumBot.record_completed_trade` so the journal can adapt thresholds before the next scan.

By instantiating Minervini's checklist in code, Craig's bot is aligned with the
momentum class rather than in conflict with it. Any future enhancement requests
can build on this validated foundation.
