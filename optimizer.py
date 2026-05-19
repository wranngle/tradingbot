"""Capital allocation optimizer.

Given N candidate strategies and a historical worst-case constraint, output
recommended portfolio weights that maximize risk-adjusted return (Sharpe).

The optimizer is intentionally dependency-free: it uses a coarse simplex grid
search over the N-dimensional weight space so it composes cleanly with the
existing gauntlet (round-1 #4) and black-swan replay (round-1 #5). The replay
worst-case is consulted via a pluggable callable so heavy backtests can be
mocked in tests and supplied by the real harness in production.

Public surface:
    Strategy            — input dataclass (name, sharpe, expected_return, vol)
    OptimizerResult     — output dataclass (weights, sharpe, worst_case_dd)
    optimize_weights()  — main entry point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Callable, Dict, Iterable, List, Sequence


@dataclass(frozen=True)
class Strategy:
    name: str
    sharpe: float
    expected_return: float
    volatility: float


@dataclass(frozen=True)
class OptimizerResult:
    weights: Dict[str, float]
    portfolio_sharpe: float
    worst_case_drawdown_pct: float
    grid_step: float = field(default=0.0)


WorstCaseFn = Callable[[Sequence[Strategy], Sequence[float]], float]


def _default_worst_case(strategies: Sequence[Strategy], weights: Sequence[float]) -> float:
    """Cheap analytic stand-in for the black-swan replay harness.

    Real callers should pass the black-swan replay function (round-1 #5);
    tests mock this. The default assumes worst-case drawdown scales with the
    weighted volatility — strictly a placeholder, never used in production.
    """
    return sum(w * s.volatility * 3.0 for w, s in zip(weights, strategies)) * 100.0


def _portfolio_sharpe(strategies: Sequence[Strategy], weights: Sequence[float]) -> float:
    expected = sum(w * s.expected_return for w, s in zip(weights, strategies))
    variance = sum((w * s.volatility) ** 2 for w, s in zip(weights, strategies))
    if variance <= 0:
        return float("-inf")
    return expected / (variance ** 0.5)


def _simplex_grid(n: int, step: float) -> Iterable[List[float]]:
    """Enumerate weight vectors on the n-simplex with the given step size."""
    if n <= 0:
        return
    ticks = round(1.0 / step)
    for combo in product(range(ticks + 1), repeat=n):
        if sum(combo) != ticks:
            continue
        yield [c / ticks for c in combo]


def optimize_weights(
    strategies: Sequence[Strategy],
    max_drawdown_pct: float = 40.0,
    worst_case_fn: WorstCaseFn = _default_worst_case,
    grid_step: float = 0.05,
) -> OptimizerResult:
    """Find weights that maximize Sharpe under a historical drawdown cap.

    Args:
        strategies: candidate strategies (≥1).
        max_drawdown_pct: hard cap; any allocation whose worst-case replay
            exceeds this is rejected. Cited from round-1 #5 black-swan replay.
        worst_case_fn: callable returning worst-case drawdown % for a given
            (strategies, weights). Mock in tests; pass black-swan replay in prod.
        grid_step: simplex resolution (smaller = finer, slower). Default 0.05
            gives 5% allocation buckets which is sane for live trading.

    Returns:
        OptimizerResult with weights summing to 1.0. Falls back to an
        equal-weight allocation if no grid point satisfies the constraint.
    """
    if not strategies:
        raise ValueError("optimize_weights requires at least one strategy")
    if not 0 < grid_step <= 1:
        raise ValueError("grid_step must be in (0, 1]")

    n = len(strategies)
    best: OptimizerResult | None = None

    for weights in _simplex_grid(n, grid_step):
        worst_case = worst_case_fn(strategies, weights)
        if worst_case > max_drawdown_pct:
            continue
        sharpe = _portfolio_sharpe(strategies, weights)
        if best is None or sharpe > best.portfolio_sharpe:
            best = OptimizerResult(
                weights={s.name: w for s, w in zip(strategies, weights)},
                portfolio_sharpe=sharpe,
                worst_case_drawdown_pct=worst_case,
                grid_step=grid_step,
            )

    if best is None:
        equal = 1.0 / n
        weights = [equal] * n
        return OptimizerResult(
            weights={s.name: equal for s in strategies},
            portfolio_sharpe=_portfolio_sharpe(strategies, weights),
            worst_case_drawdown_pct=worst_case_fn(strategies, weights),
            grid_step=grid_step,
        )
    return best
