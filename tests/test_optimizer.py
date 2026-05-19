"""Tests for capital allocation optimizer (round-2 #4).

Contract under test:
- Weights sum to 1.0 within float tolerance.
- The highest-Sharpe strategy gets the largest weight (no constraint binds).
- The drawdown cap from the black-swan replay (round-1 #5) is honored.
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest

from optimizer import OptimizerResult, Strategy, optimize_weights


@pytest.fixture
def three_strategies() -> list[Strategy]:
    return [
        Strategy(name="momentum",      sharpe=0.8, expected_return=0.10, volatility=0.20),
        Strategy(name="mean_reverter", sharpe=1.6, expected_return=0.12, volatility=0.10),
        Strategy(name="trend_follow",  sharpe=1.1, expected_return=0.09, volatility=0.15),
    ]


def test_weights_sum_to_one(three_strategies):
    result = optimize_weights(three_strategies, worst_case_fn=lambda *_: 5.0)
    assert math.isclose(sum(result.weights.values()), 1.0, abs_tol=1e-9)


def test_highest_sharpe_gets_largest_weight(three_strategies):
    result = optimize_weights(three_strategies, worst_case_fn=lambda *_: 5.0)
    largest = max(result.weights.items(), key=lambda kv: kv[1])
    assert largest[0] == "mean_reverter"


def test_worst_case_fn_is_mocked_not_called_for_real_replay(three_strategies):
    mock_replay = MagicMock(return_value=10.0)
    optimize_weights(three_strategies, worst_case_fn=mock_replay, grid_step=0.5)
    assert mock_replay.call_count > 0


def test_drawdown_cap_rejects_violating_allocations(three_strategies):
    def punishing_worst_case(strategies, weights):
        idx_high_vol = max(range(len(strategies)), key=lambda i: strategies[i].volatility)
        return 100.0 if weights[idx_high_vol] > 0.2 else 5.0

    result = optimize_weights(
        three_strategies,
        max_drawdown_pct=40.0,
        worst_case_fn=punishing_worst_case,
    )
    momentum_weight = result.weights["momentum"]
    assert momentum_weight <= 0.2 + 1e-9


def test_no_feasible_allocation_falls_back_to_equal_weight(three_strategies):
    result = optimize_weights(
        three_strategies,
        max_drawdown_pct=1.0,
        worst_case_fn=lambda *_: 999.0,
    )
    assert math.isclose(sum(result.weights.values()), 1.0, abs_tol=1e-9)
    assert all(math.isclose(w, 1 / 3, abs_tol=1e-9) for w in result.weights.values())


def test_single_strategy_gets_full_allocation():
    only = [Strategy(name="solo", sharpe=1.0, expected_return=0.1, volatility=0.1)]
    result = optimize_weights(only, worst_case_fn=lambda *_: 1.0)
    assert result.weights == {"solo": 1.0}


def test_empty_strategies_raises():
    with pytest.raises(ValueError):
        optimize_weights([], worst_case_fn=lambda *_: 0.0)


def test_invalid_grid_step_raises(three_strategies):
    with pytest.raises(ValueError):
        optimize_weights(three_strategies, grid_step=0.0)
    with pytest.raises(ValueError):
        optimize_weights(three_strategies, grid_step=1.5)


def test_result_shape(three_strategies):
    result = optimize_weights(three_strategies, worst_case_fn=lambda *_: 5.0)
    assert isinstance(result, OptimizerResult)
    assert set(result.weights.keys()) == {"momentum", "mean_reverter", "trend_follow"}
    assert result.portfolio_sharpe > 0
    assert result.worst_case_drawdown_pct <= 40.0
