"""Monte-Carlo position-size sanity tester.

Stress-tests a fixed per-trade risk fraction against synthetic trade sequences
sampled from a win-rate / payoff-ratio assumption. Each simulation walks
`trades` Bernoulli draws and tracks peak-to-trough drawdown on the equity
curve; the script emits p50 / p95 / p99 of the drawdown distribution so the
operator can pick a risk fraction that survives the tail, not just the mean.

Sibling to the equity-curve plotter (#9): that hook plots a *single* realised
curve from `logs/equity.jsonl`, this tester explores the *distribution* of
curves a given configuration could produce before any capital is committed.

Stdlib only. Deterministic for a given `--seed`.

CLI:
    python monte_carlo.py --risk 0.02 --win-rate 0.55 --payoff 1.8 \
        --trades 250 --sims 100 --seed 42

Output: JSON to stdout with `p50_drawdown_pct`, `p95_drawdown_pct`,
`p99_drawdown_pct` (monotonically increasing), plus echoed inputs.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class SimConfig:
    risk: float
    win_rate: float
    payoff: float
    trades: int
    sims: int
    seed: int


@dataclass(frozen=True)
class SimResult:
    p50_drawdown_pct: float
    p95_drawdown_pct: float
    p99_drawdown_pct: float
    worst_drawdown_pct: float
    mean_final_equity_pct: float
    ruined_sim_count: int


def _validate(cfg: SimConfig) -> None:
    if not 0 < cfg.risk < 1:
        raise ValueError("--risk must be in (0, 1)")
    if not 0 < cfg.win_rate < 1:
        raise ValueError("--win-rate must be in (0, 1)")
    if cfg.payoff <= 0:
        raise ValueError("--payoff must be > 0")
    if cfg.trades <= 0:
        raise ValueError("--trades must be > 0")
    if cfg.sims <= 0:
        raise ValueError("--sims must be > 0")


def _max_drawdown_pct(curve: Iterable[float]) -> float:
    peak = float("-inf")
    worst = 0.0
    for equity in curve:
        if equity > peak:
            peak = equity
        if peak > 0:
            dd = (peak - equity) / peak
            if dd > worst:
                worst = dd
    return worst * 100.0


def _simulate_one(cfg: SimConfig, rng: random.Random) -> tuple[float, float]:
    """Return (max_drawdown_pct, final_equity_pct) for one simulated path."""
    equity = 1.0
    peak = 1.0
    worst = 0.0
    win_payoff = cfg.risk * cfg.payoff
    for _ in range(cfg.trades):
        if rng.random() < cfg.win_rate:
            equity *= 1.0 + win_payoff
        else:
            equity *= 1.0 - cfg.risk
        if equity > peak:
            peak = equity
        if peak > 0:
            dd = (peak - equity) / peak
            if dd > worst:
                worst = dd
        if equity <= 0:
            break
    return worst * 100.0, equity * 100.0


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Nearest-rank percentile on a pre-sorted list. pct in [0, 100]."""
    if not sorted_values:
        return 0.0
    rank = max(1, min(len(sorted_values), int(round(pct / 100.0 * len(sorted_values)))))
    return sorted_values[rank - 1]


def run(cfg: SimConfig) -> SimResult:
    _validate(cfg)
    rng = random.Random(cfg.seed)
    drawdowns: list[float] = []
    finals: list[float] = []
    ruined = 0
    for _ in range(cfg.sims):
        dd, final_eq = _simulate_one(cfg, rng)
        drawdowns.append(dd)
        finals.append(final_eq)
        if final_eq <= 1.0:
            ruined += 1
    drawdowns.sort()
    p50 = _percentile(drawdowns, 50)
    p95 = _percentile(drawdowns, 95)
    p99 = _percentile(drawdowns, 99)
    return SimResult(
        p50_drawdown_pct=round(p50, 4),
        p95_drawdown_pct=round(p95, 4),
        p99_drawdown_pct=round(p99, 4),
        worst_drawdown_pct=round(drawdowns[-1], 4),
        mean_final_equity_pct=round(sum(finals) / len(finals), 4),
        ruined_sim_count=ruined,
    )


def _parse_args(argv: list[str] | None = None) -> SimConfig:
    p = argparse.ArgumentParser(
        prog="monte_carlo",
        description="Monte-Carlo position-size sanity tester (drawdown percentiles).",
    )
    p.add_argument("--risk", type=float, default=0.02,
                   help="Fraction of equity risked per trade (default: 0.02)")
    p.add_argument("--win-rate", type=float, default=0.55,
                   help="Probability a trade wins (default: 0.55)")
    p.add_argument("--payoff", type=float, default=1.8,
                   help="Reward-to-risk ratio on winning trades (default: 1.8)")
    p.add_argument("--trades", type=int, default=250,
                   help="Trades per simulation (default: 250)")
    p.add_argument("--sims", type=int, default=100,
                   help="Number of simulated paths (default: 100)")
    p.add_argument("--seed", type=int, default=42,
                   help="RNG seed for reproducibility (default: 42)")
    args = p.parse_args(argv)
    return SimConfig(
        risk=args.risk,
        win_rate=args.win_rate,
        payoff=args.payoff,
        trades=args.trades,
        sims=args.sims,
        seed=args.seed,
    )


def main(argv: list[str] | None = None) -> int:
    cfg = _parse_args(argv)
    result = run(cfg)
    payload = {"config": asdict(cfg), **asdict(result)}
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
