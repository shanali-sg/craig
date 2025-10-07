# Momentum Strategy Implementation Review

This document summarizes how the current Craig bot implementation aligns with a Minervini-style momentum approach, highlighting notable strengths, observed weaknesses, and improvement opportunities.

## Strengths
- **Comprehensive indicator stack** – The strategy derives 50/150/200-day SMAs, a 21-day EMA, 52-week highs/lows, volume dry-up ratios, and ATR, providing the core technical context for Minervini-inspired screening.【F:craig_bot/strategy.py†L58-L138】
- **Rule-based qualification** – Candidates must satisfy stacked moving averages, a rising 200-day, proximity to highs, sufficient lift off lows, RS thresholds, volume contraction, and base duration checks before qualifying, mirroring the template's checklist discipline.【F:craig_bot/strategy.py†L148-L209】
- **Risk-aware execution** – Qualified setups automatically translate into position sizing with ATR-based stops and fixed-fractional risk, preserving capital in line with Minervini's emphasis on risk management.【F:craig_bot/strategy.py†L214-L232】【F:craig_bot/risk.py†L7-L41】
- **Adaptive feedback loop** – A persistent trade journal nudges RS and breakout distance tolerances based on recent win rate and returns, creating a feedback mechanism that reflects post-trade review practices from the Minervini framework.【F:craig_bot/journal.py†L38-L107】
- **Market data integration** – The Alpaca data source surfaces fast movers and rolls up OHLCV history so the strategy can be applied to timely candidates without additional glue code.【F:craig_bot/data_sources.py†L19-L113】

## Weaknesses
- **External RS dependency** – The bot expects pre-computed relative strength inputs, but Minervini typically derives RS internally (e.g., versus the S&P 500). Relying on external numbers risks inconsistencies if the upstream calculation diverges from the intended methodology.【F:craig_bot/bot.py†L35-L59】【F:craig_bot/strategy.py†L194-L232】
- **Simplistic base validation** – `base_length` is supplied as metadata rather than inferred from price structure, leaving a gap in automatically verifying proper bases, pivot tightening, or volatility contraction patterns emphasized in the SEPA process.【F:craig_bot/bot.py†L45-L63】【F:craig_bot/strategy.py†L202-L209】
- **Limited volume diagnostics** – Volume dry-up is approximated by a 10/50-day average ratio, but Minervini's playbook often inspects sequential volume trends, up/down ratios, and accumulation days that are not yet captured.【F:craig_bot/strategy.py†L107-L138】【F:craig_bot/strategy.py†L214-L232】
- **No general market filter** – The strategy lacks an integrated market trend overlay (e.g., checking leading indexes or market breadth) that Minervini uses to stay aligned with M conditions, which may lead to taking trades during hostile markets.【F:craig_bot/strategy.py†L148-L232】【F:craig_bot/bot.py†L20-L81】
- **Alpaca scan simplicity** – Fast-mover selection is purely percent-change driven and ignores other Minervini cues such as proximity to 52-week highs, relative strength rankings, or volume thrusts, reducing the fidelity of the upstream universe.【F:craig_bot/data_sources.py†L34-L87】

## Improvement Opportunities
- **Embed RS computation** – Incorporate internal RS line calculations (e.g., dividing by a benchmark index ETF) so the workflow is self-contained and consistent with Minervini's RS interpretation.【F:craig_bot/strategy.py†L58-L232】
- **Automate base diagnostics** – Extend indicator logic to detect consolidations, handle pivot points, and confirm volatility contraction instead of relying on manually supplied base metadata.【F:craig_bot/strategy.py†L90-L209】
- **Enrich volume analytics** – Track recent up/down volume ratios, pocket pivot signatures, and distribution day counts to better approximate the qualitative volume review from the class.【F:craig_bot/strategy.py†L107-L214】
- **Add market health gate** – Layer in a market trend model (e.g., follow-through day logic using major indexes) so the bot only activates when the overall market passes Minervini's M criteria.【F:craig_bot/bot.py†L20-L81】
- **Upgrade Alpaca screening** – Combine percent change with RS percentile, new-high proximity, and liquidity filters during fast-mover scans to surface higher-quality Minervini candidates before expensive indicator evaluation.【F:craig_bot/data_sources.py†L34-L113】
- **Refine journal heuristics** – Expand adaptive tuning to learn from expectancy (average win/loss) and risk-adjusted returns, enabling more nuanced adjustments than binary win-rate thresholds.【F:craig_bot/journal.py†L68-L107】

