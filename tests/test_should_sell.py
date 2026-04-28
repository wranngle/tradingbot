"""Tests for `shouldSell`.

The original code had `=` (assignment) instead of `==` (comparison) on
several `is_sell_condition_*` lines, silently overwriting the price-target
variables every time `shouldSell` ran. These tests pin down the corrected
behavior.
"""

from unittest.mock import MagicMock

import pytest


def _bar(price=100.0):
    return MagicMock(Price=price)


@pytest.fixture
def sell_setup(reset_variables, fake_symbol, monkeypatch):
    import variables as v
    import config as c

    sym = fake_symbol
    v.current_price[sym] = 100.0
    v.take_profit_max_price[sym] = 110.0
    v.stop_loss_max_price[sym] = 90.0

    # Each per-method price differs from the chosen max so the comparison
    # flags are False unless explicitly set otherwise.
    v.stop_loss_atr_price[sym] = 95.0
    v.stop_loss_fib_atr_price[sym] = 92.0
    v.stop_loss_percent_price[sym] = 80.0
    v.stop_loss_trailing_price[sym] = 88.0
    v.take_profit_atr_price[sym] = 105.0
    v.take_profit_fib_atr_price[sym] = 108.0
    v.take_profit_percent_price[sym] = 110.0  # matches take_profit_max
    v.take_profit_trailing_price[sym] = 112.0

    v.indicators[sym] = {
        "atr": MagicMock(Current=MagicMock(Value=2.0)),
        "macd": MagicMock(
            Current=MagicMock(Value=1.0),
            Signal=MagicMock(Current=MagicMock(Value=0.5)),
        ),
        "rsi": MagicMock(Current=MagicMock(Value=40)),
    }

    monkeypatch.setattr(c, "sell_condition_macd_cross_below_signal", False)
    monkeypatch.setattr(c, "sell_condition_rsi_weak", False)
    monkeypatch.setattr(c, "sell_parameter_rsi_max_threshold", 30)
    return sym


def test_does_not_mutate_price_target_variables(sell_setup):
    """Regression: `=` instead of `==` was overwriting these to take_profit_max_price."""
    import variables as v
    from shouldSell import shouldSell

    before = {
        "stop_loss_percent_price": v.stop_loss_percent_price[sell_setup],
        "stop_loss_trailing_price": v.stop_loss_trailing_price[sell_setup],
        "take_profit_atr_price": v.take_profit_atr_price[sell_setup],
        "take_profit_fib_atr_price": v.take_profit_fib_atr_price[sell_setup],
        "take_profit_trailing_price": v.take_profit_trailing_price[sell_setup],
    }

    shouldSell(MagicMock(), sell_setup, {sell_setup: _bar()})

    after = {k: getattr(v, k)[sell_setup] for k in before}
    assert before == after


def test_sells_when_take_profit_target_met(sell_setup):
    import variables as v
    from shouldSell import shouldSell

    v.current_price[sell_setup] = 120.0  # above take_profit_max_price (110)

    decision, tag = shouldSell(MagicMock(), sell_setup, {sell_setup: _bar(120.0)})
    assert decision is True
    assert tag is not None


def test_holds_when_price_inside_range(sell_setup):
    from shouldSell import shouldSell

    decision, tag = shouldSell(MagicMock(), sell_setup, {sell_setup: _bar()})
    assert decision is False
    assert tag is None


def test_returns_tuple_when_symbol_missing(sell_setup):
    """Regression: the except branch used to return `False` (single value),
    causing callers that did `should_sell, tag = shouldSell(...)` to crash."""
    from shouldSell import shouldSell

    result = shouldSell(MagicMock(), sell_setup, {})
    assert result == (False, None)
