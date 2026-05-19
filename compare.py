"""Strategy comparison harness.

Given two strategy YAML files, runs each through the pre-flight risk
gauntlet (round-1 PR #4) and the black-swan replay harness
(round-1 PR #5), then emits a `{a, b, delta}` dict so two candidates can
be diffed side-by-side before promotion.

The gauntlet + replay round-1 modules are open PRs at the time this
landed; this harness recreates the same contracts in self-contained
form (same field names, same veto semantics, same replay window set)
so the comparison is meaningful on `main` alone and re-aligns
trivially once those PRs merge.

Stdlib + pyyaml only.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import yaml


GAUNTLET_CAPS: dict[str, dict[str, Any]] = {
    "max_leverage": {"limit": 2.0, "field": "leverage"},
    "max_drawdown_cap": {"limit": 25.0, "field": "max_drawdown_pct"},
    "max_concentration": {"limit": 0.25, "field": "max_position_weight"},
    "max_risk_per_trade": {"limit": 1.0, "field": "risk_per_trade_pct"},
    "min_universe_size": {"limit": 5, "field": "universe_size", "direction": "min"},
}


BLACK_SWAN_WINDOWS: list[dict[str, Any]] = [
    {
        "name": "2008-gfc",
        "start": "2008-09-01",
        "end": "2009-03-31",
        "shock_pct": -56.8,
        "vol_multiplier": 3.2,
    },
    {
        "name": "2020-covid",
        "start": "2020-02-19",
        "end": "2020-04-07",
        "shock_pct": -33.9,
        "vol_multiplier": 4.7,
    },
    {
        "name": "2022-rates",
        "start": "2022-01-03",
        "end": "2022-10-12",
        "shock_pct": -25.4,
        "vol_multiplier": 1.9,
    },
]


def load_strategy(path: str | Path) -> dict[str, Any]:
    """Load and minimally normalize a strategy YAML."""
    raw = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ValueError(f"strategy file must be a mapping: {path}")
    return data


def run_gauntlet(strategy: dict[str, Any]) -> dict[str, Any]:
    """Pre-flight risk gauntlet — same contract as round-1 PR #4.

    Returns `{passed, vetoes, checked}` where vetoes is a list of
    `{cap, value, limit}` for every breach.
    """
    vetoes: list[dict[str, Any]] = []
    checked: list[str] = []
    for cap_name, spec in GAUNTLET_CAPS.items():
        checked.append(cap_name)
        value = strategy.get(spec["field"])
        if value is None:
            vetoes.append(
                {"cap": cap_name, "value": None, "limit": spec["limit"], "reason": "missing"}
            )
            continue
        limit = spec["limit"]
        direction = spec.get("direction", "max")
        breached = value < limit if direction == "min" else value > limit
        if breached:
            vetoes.append({"cap": cap_name, "value": value, "limit": limit, "reason": "breach"})
    return {"passed": not vetoes, "vetoes": sorted(vetoes, key=lambda v: v["cap"]), "checked": sorted(checked)}


def _drawdown_under_shock(
    strategy: dict[str, Any], shock_pct: float, vol_multiplier: float
) -> float:
    """Closed-form drawdown estimate for a window.

    Realized drawdown is modelled as a damped fraction of the shock,
    proportional to net exposure and amplified by leverage:

        dd_pct = |shock_pct| * net_exposure * dampening

    where `net_exposure = (1 - cash_weight) * leverage` and `dampening`
    is a tanh-bounded function of risk_per_trade and the window's
    vol_multiplier, ensuring `dd_pct` stays within [0, 95]. Deterministic
    by construction (no RNG) so test comparison is byte-stable.
    """
    leverage = float(strategy.get("leverage", 1.0))
    cash_weight = float(strategy.get("cash_weight", 0.0))
    risk_per_trade = float(strategy.get("risk_per_trade_pct", 1.0))
    net_exposure = max(0.0, 1.0 - cash_weight) * leverage
    risk_amp = math.tanh(risk_per_trade * math.log1p(max(vol_multiplier, 1.0) - 1.0) / 4.0)
    dampening = 0.45 + 0.45 * risk_amp
    dd = abs(shock_pct) * net_exposure * dampening
    return round(min(dd, 95.0), 2)


def run_black_swan_replay(strategy: dict[str, Any]) -> dict[str, Any]:
    """Black-swan replay harness — same window set as round-1 PR #5."""
    windows: list[dict[str, Any]] = []
    for w in BLACK_SWAN_WINDOWS:
        dd = _drawdown_under_shock(strategy, w["shock_pct"], w["vol_multiplier"])
        windows.append(
            {
                "name": w["name"],
                "start": w["start"],
                "end": w["end"],
                "max_drawdown_pct": dd,
                "shock_pct": w["shock_pct"],
            }
        )
    windows.sort(key=lambda x: x["name"])
    return {
        "windows": windows,
        "worst_window": max(windows, key=lambda x: x["max_drawdown_pct"])["name"] if windows else None,
        "max_drawdown_pct": max((w["max_drawdown_pct"] for w in windows), default=0.0),
    }


def evaluate_strategy(path: str | Path) -> dict[str, Any]:
    """Run gauntlet + replay for one strategy."""
    strat = load_strategy(path)
    gauntlet = run_gauntlet(strat)
    replay = run_black_swan_replay(strat)
    return {
        "name": strat.get("name", Path(path).stem),
        "path": str(path),
        "gauntlet": gauntlet,
        "replay": replay,
        "max_drawdown_pct": replay["max_drawdown_pct"],
    }


def _delta(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Field-by-field b-minus-a delta with rounded floats."""
    return {
        "max_drawdown_pct": round(b["max_drawdown_pct"] - a["max_drawdown_pct"], 2),
        "gauntlet_veto_count": len(b["gauntlet"]["vetoes"]) - len(a["gauntlet"]["vetoes"]),
        "gauntlet_passed_change": int(b["gauntlet"]["passed"]) - int(a["gauntlet"]["passed"]),
        "worst_window": {
            "a": a["replay"]["worst_window"],
            "b": b["replay"]["worst_window"],
        },
        "per_window_drawdown_delta": _per_window_delta(a["replay"]["windows"], b["replay"]["windows"]),
    }


def _per_window_delta(
    a_windows: list[dict[str, Any]], b_windows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    a_map = {w["name"]: w["max_drawdown_pct"] for w in a_windows}
    b_map = {w["name"]: w["max_drawdown_pct"] for w in b_windows}
    out: list[dict[str, Any]] = []
    for name in sorted(set(a_map) | set(b_map)):
        out.append(
            {
                "window": name,
                "a": a_map.get(name),
                "b": b_map.get(name),
                "delta": round((b_map.get(name) or 0.0) - (a_map.get(name) or 0.0), 2),
            }
        )
    return out


def compare(path_a: str | Path, path_b: str | Path) -> dict[str, Any]:
    """Return `{a, b, delta}` for two strategy YAML files."""
    a = evaluate_strategy(path_a)
    b = evaluate_strategy(path_b)
    return {"a": a, "b": b, "delta": _delta(a, b)}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="compare",
        description="Compare two trading strategies through gauntlet + black-swan replay.",
    )
    p.add_argument("a", help="path to baseline strategy YAML")
    p.add_argument("b", help="path to candidate strategy YAML")
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="optional output JSON path (default: stdout)",
    )
    p.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indent (default: 2)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(argv) if argv is not None else sys.argv[1:])
    try:
        result = compare(args.a, args.b)
    except FileNotFoundError as e:
        print(f"compare: file not found: {e.filename}", file=sys.stderr)
        return 2
    payload = json.dumps(result, indent=args.indent, sort_keys=True) + "\n"
    if args.out is None:
        sys.stdout.write(payload)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
