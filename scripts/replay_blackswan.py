#!/usr/bin/env python3
"""Black-swan replay harness.

Runs a strategy against canned crash-window price fixtures (2008-09, COVID-Mar-2020)
and reports peak drawdown, terminal equity, and a survival flag.

Run:
    python3 scripts/replay_blackswan.py --scenario 2008
    python3 scripts/replay_blackswan.py --scenario covid
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "blackswan"

STARTING_CASH = 1_000.0


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    fixture: Path
    survival_max_drawdown_pct: float  # if peak_dd ≤ this, survived=True


SCENARIOS: dict[str, ScenarioSpec] = {
    "2008": ScenarioSpec(
        name="2008",
        fixture=FIXTURES_DIR / "2008.csv",
        survival_max_drawdown_pct=0.60,
    ),
    "covid": ScenarioSpec(
        name="covid",
        fixture=FIXTURES_DIR / "covid.csv",
        survival_max_drawdown_pct=0.40,
    ),
}


@dataclass(frozen=True)
class Bar:
    date: str
    close: float


def load_fixture(path: Path) -> list[Bar]:
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        return [Bar(date=row["date"], close=float(row["close"])) for row in reader]


# A Strategy is a callable that takes the full bar series and returns a per-bar
# equity series (same length). Keeping it pure makes determinism trivial.
Strategy = Callable[[Sequence[Bar]], list[float]]


def buy_and_hold(bars: Sequence[Bar]) -> list[float]:
    """100% allocated to the asset at bar 0; ride it through the window."""
    if not bars:
        return []
    units = STARTING_CASH / bars[0].close
    return [units * bar.close for bar in bars]


def cash_heavy(bars: Sequence[Bar]) -> list[float]:
    """Known-good defensive fixture: 10% in equity, 90% cash. Always survives."""
    if not bars:
        return []
    equity_alloc = STARTING_CASH * 0.10
    cash_alloc = STARTING_CASH - equity_alloc
    units = equity_alloc / bars[0].close
    return [cash_alloc + units * bar.close for bar in bars]


STRATEGIES: dict[str, Strategy] = {
    "buy_and_hold": buy_and_hold,
    "cash_heavy": cash_heavy,
}


def peak_drawdown(equity: Sequence[float]) -> float:
    """Largest peak-to-trough decline as a positive fraction (0.0–1.0)."""
    peak = equity[0]
    worst = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak <= 0:
            continue
        dd = (peak - value) / peak
        worst = max(worst, dd)
    return worst


def replay(scenario_key: str, strategy_key: str = "cash_heavy") -> dict:
    if scenario_key not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario_key!r}; choices: {sorted(SCENARIOS)}")
    if strategy_key not in STRATEGIES:
        raise ValueError(f"unknown strategy: {strategy_key!r}; choices: {sorted(STRATEGIES)}")
    spec = SCENARIOS[scenario_key]
    bars = load_fixture(spec.fixture)
    equity = STRATEGIES[strategy_key](bars)
    dd = peak_drawdown(equity)
    return {
        "scenario": spec.name,
        "strategy": strategy_key,
        "bars": len(bars),
        "starting_equity": STARTING_CASH,
        "terminal_equity": round(equity[-1], 2),
        "peak_drawdown_pct": round(dd, 4),
        "survival_max_drawdown_pct": spec.survival_max_drawdown_pct,
        "survived": dd <= spec.survival_max_drawdown_pct,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay a strategy against a black-swan fixture.")
    parser.add_argument("--scenario", required=True, choices=sorted(SCENARIOS))
    parser.add_argument("--strategy", default="cash_heavy", choices=sorted(STRATEGIES))
    args = parser.parse_args(argv)
    report = replay(args.scenario, args.strategy)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
