"""Tests for `calculateTakeProfitPrice`.

The prior implementation subtracted ATR for a take-profit target and then
dropped the ATR candidate from the final max selection. That made "profit"
targets behave like stop losses.
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def take_profit_setup(reset_variables, fake_symbol, monkeypatch):
    import variables as v
    import config as c

    v.current_price[fake_symbol] = 100.0
    v.indicators[fake_symbol] = {
        "atr": MagicMock(Current=MagicMock(Value=2.0), IsReady=True),
    }

    monkeypatch.setattr(c, "sell_condition_take_profit_atr_price", True)
    monkeypatch.setattr(c, "sell_parameter_take_profit_price_atr_multiplier", 2)
    monkeypatch.setattr(c, "sell_condition_take_profit_fibonacci_atr_price", True)
    monkeypatch.setattr(
        c,
        "sell_parameter_take_profit_fibonacci_retracement_levels",
        [0.236, 0.382, 0.618],
    )
    monkeypatch.setattr(c, "sell_condition_take_profit_trailing_percent", True)
    monkeypatch.setattr(c, "sell_parameter_take_profit_trailing_percent", 0.10)
    monkeypatch.setattr(c, "sell_condition_take_profit_percent", True)
    monkeypatch.setattr(c, "sell_parameter_take_profit_percent", 0.20)
    return fake_symbol


def _data_slice(symbol, price=100.0):
    return {symbol: MagicMock(Price=price)}


def test_returns_max_enabled_take_profit_price(take_profit_setup):
    import variables as v
    from calculateTakeProfitPrice import calculateTakeProfitPrice

    result = calculateTakeProfitPrice(
        MagicMock(),
        take_profit_setup,
        _data_slice(take_profit_setup),
    )

    assert v.take_profit_atr_price[take_profit_setup] == pytest.approx(104.0)
    assert result == pytest.approx(125.6)


def test_disabled_methods_do_not_add_zero_targets(take_profit_setup, monkeypatch):
    import config as c
    from calculateTakeProfitPrice import calculateTakeProfitPrice

    monkeypatch.setattr(c, "sell_condition_take_profit_fibonacci_atr_price", False)
    monkeypatch.setattr(c, "sell_condition_take_profit_trailing_percent", False)
    monkeypatch.setattr(c, "sell_condition_take_profit_percent", False)

    result = calculateTakeProfitPrice(
        MagicMock(),
        take_profit_setup,
        _data_slice(take_profit_setup),
    )
    assert result == pytest.approx(104.0)
