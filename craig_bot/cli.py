"""Command-line helpers for running Craig's momentum bot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List

from .bot import CandidateResult
from .runtime import (
    build_bot,
    compute_relative_strengths,
    estimate_base_lengths,
    load_alpaca_credentials,
    prepare_data_source,
)


def _print_summary(results: Iterable[CandidateResult]) -> None:
    rows = list(results)
    if not rows:
        print("No qualifying candidates found.")
        return

    header = f"{'Symbol':<8} {'Score':>7} {'Stop':>10} {'Shares':>8}"
    print(header)
    print("-" * len(header))
    for row in rows:
        plan = row.position_plan
        print(
            f"{row.symbol:<8} "
            f"{row.evaluation.score:>7.2f} "
            f"{plan.get('stop_price', float('nan')):>10.2f} "
            f"{plan.get('shares', 0):>8d}"
        )


def _save_results(results: Iterable[CandidateResult], path: Path) -> None:
    payload: List[dict] = []
    for result in results:
        payload.append(
            {
                "symbol": result.symbol,
                "score": result.evaluation.score,
                "reasons": result.evaluation.reasons,
                "entry_price": result.evaluation.entry_price,
                "stop_price": result.evaluation.stop_price,
                "position_plan": result.position_plan,
            }
        )
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"Saved detailed results to {path}")


def run_historical(args: argparse.Namespace) -> None:
    credentials = load_alpaca_credentials(args.dotenv)
    data_source = prepare_data_source(credentials)

    if not args.symbols:
        raise SystemExit("Provide --symbols when running in historical mode")

    price_series = data_source.fetch_price_series(
        args.symbols,
        lookback_days=args.lookback_days,
        timeframe=args.timeframe,
    )

    relative_strengths = compute_relative_strengths(price_series, window=args.rs_window)
    base_lengths = estimate_base_lengths(price_series, lookback=args.base_lookback)

    common_symbols = sorted(
        set(price_series) & set(relative_strengths) & set(base_lengths)
    )
    if not common_symbols:
        raise SystemExit("No overlap between price data, relative strength, and base lengths")

    bot = build_bot(
        journal_path=args.journal,
        account_equity=args.account_equity,
        risk_fraction=args.risk_fraction,
    )

    results = bot.rank_candidates(
        {symbol: price_series[symbol] for symbol in common_symbols},
        relative_strengths={symbol: relative_strengths[symbol] for symbol in common_symbols},
        base_lengths={symbol: base_lengths[symbol] for symbol in common_symbols},
    )

    _print_summary(results)
    if args.output:
        _save_results(results, Path(args.output))


def run_live(args: argparse.Namespace) -> None:
    credentials = load_alpaca_credentials(args.dotenv)
    data_source = prepare_data_source(credentials)

    universe = args.symbols or args.universe
    if not universe:
        raise SystemExit("Provide --symbols or --universe for live mode")

    fast_movers = data_source.scan_fast_movers(
        universe,
        min_price=args.min_price,
        min_volume=args.min_volume,
        top_n=args.top_n,
    )
    symbols = [snapshot.symbol for snapshot in fast_movers]
    if not symbols:
        print("No fast movers met the scan criteria today.")
        return

    price_series = data_source.fetch_price_series(
        symbols,
        lookback_days=args.lookback_days,
        timeframe=args.timeframe,
    )
    relative_strengths = compute_relative_strengths(price_series, window=args.rs_window)
    base_lengths = estimate_base_lengths(price_series, lookback=args.base_lookback)

    common_symbols = sorted(
        set(price_series) & set(relative_strengths) & set(base_lengths)
    )
    if not common_symbols:
        print("Fast movers lacked sufficient history for evaluation.")
        return

    bot = build_bot(
        journal_path=args.journal,
        account_equity=args.account_equity,
        risk_fraction=args.risk_fraction,
    )

    results = bot.rank_candidates(
        {symbol: price_series[symbol] for symbol in common_symbols},
        relative_strengths={symbol: relative_strengths[symbol] for symbol in common_symbols},
        base_lengths={symbol: base_lengths[symbol] for symbol in common_symbols},
    )

    _print_summary(results)
    if args.output:
        _save_results(results, Path(args.output))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Craig's momentum bot")
    parser.add_argument("mode", choices=["historical", "live"], help="Execution mode")
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="Symbols to evaluate (historical mode) or to seed the fast-mover scan",
    )
    parser.add_argument(
        "--universe",
        nargs="+",
        help="Fallback universe for the fast-mover scan when --symbols is omitted",
    )
    parser.add_argument("--lookback-days", type=int, default=365, help="Historical lookback window")
    parser.add_argument("--timeframe", default="1Day", help="Alpaca timeframe string")
    parser.add_argument("--rs-window", type=int, default=125, help="Relative strength lookback window")
    parser.add_argument("--base-lookback", type=int, default=90, help="Window for base length estimation")
    parser.add_argument("--journal", default="journal.json", help="Path to the trade journal file")
    parser.add_argument("--account-equity", type=float, default=100_000.0, help="Account equity for sizing")
    parser.add_argument("--risk-fraction", type=float, default=0.01, help="Fraction of equity risked per trade")
    parser.add_argument("--dotenv", default=".env", help="Path to a dotenv file with Alpaca credentials")
    parser.add_argument("--output", help="Optional JSON file for detailed results")
    parser.add_argument("--min-price", type=float, default=5.0, help="Minimum price for fast movers")
    parser.add_argument(
        "--min-volume", type=float, default=200_000, help="Minimum volume for fast movers"
    )
    parser.add_argument("--top-n", type=int, default=25, help="Number of fast movers to evaluate")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.mode == "historical":
        run_historical(args)
    else:
        run_live(args)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()

