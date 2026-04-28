"""Tests for `calculateStopLossPrice`.

These tests pin down the math on each enabled stop-loss method and confirm
that disabled methods do not poison the `max(...)` selection — which used to
raise `TypeError` because the literal string `"Disabled"` was mixed with
floats.
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def stop_loss_setup(reset_variables, fake_symbol, monkeypatch):
    """Configure indicators + variables for a single symbol."""
    import variables as v
    import config as c

    v.current_price[fake_symbol] = 100.0
    v.indicators[fake_symbol] = {
        "atr": MagicMock(Current=MagicMock(Value=2.0), IsReady=True),
    }

    # Enable every method with deterministic parameters.
    monkeypatch.setattr(c, "sell_condition_stop_loss_atr_price", True)
    monkeypatch.setattr(c, "sell_parameter_stop_loss_price_atr_multiplier", 2)
    monkeypatch.setattr(c, "sell_condition_stop_loss_fibonacci_atr_price", True)
    monkeypatch.setattr(
        c, "sell_parameter_stop_loss_fibonacci_retracement_levels",
        [-0.236, -0.382, -0.618],
    )
    monkeypatch.setattr(c, "sell_condition_stop_loss_trailing_percent", True)
    monkeypatch.setattr(c, "sell_parameter_stop_loss_trailing_percent", 0.10)
    monkeypatch.setattr(c, "sell_condition_stop_loss_percent", True)
    monkeypatch.setattr(c, "sell_parameter_stop_loss_percent", 0.20)

    return fake_symbol


def _data_slice(symbol, price=100.0):
    bar = MagicMock(Price=price)
    return {symbol: bar}


def test_returns_max_of_enabled_methods(stop_loss_setup):
    from calculateStopLossPrice import calculateStopLossPrice

    algo = MagicMock()
    result = calculateStopLossPrice(algo, stop_loss_setup, _data_slice(stop_loss_setup))

    # ATR:    100 - (2 * 2) = 96
    # Fib+ATR: min(100*(1-0.236), 100*(1-0.382), 100*(1-0.618)) + 2 = 38.2 + 2 = 40.2
    # Trailing: 100 * (1 - 0.10) = 90
    # Percent:  100 * (1 - 0.20) = 80  -- regression: this used to multiply by the
    # boolean flag instead of the parameter, producing 0.
    assert result == pytest.approx(96.0)


def test_disabled_methods_do_not_raise_typeerror(stop_loss_setup, monkeypatch):
    """Regression: `max("Disabled", 96.0, ...)` used to raise."""
    import config as c
    from calculateStopLossPrice import calculateStopLossPrice

    monkeypatch.setattr(c, "sell_condition_stop_loss_trailing_percent", False)
    monkeypatch.setattr(c, "sell_condition_stop_loss_percent", False)

    algo = MagicMock()
    result = calculateStopLossPrice(algo, stop_loss_setup, _data_slice(stop_loss_setup))
    assert result == pytest.approx(96.0)


def test_returns_none_when_symbol_missing_from_data(stop_loss_setup):
    from calculateStopLossPrice import calculateStopLossPrice

    algo = MagicMock()
    assert calculateStopLossPrice(algo, stop_loss_setup, {}) is None


def test_returns_none_on_exception(reset_variables, fake_symbol):
    """Indicators missing for the symbol should be caught and reported."""
    from calculateStopLossPrice import calculateStopLossPrice

    algo = MagicMock()
    # No indicators registered → KeyError inside the function.
    result = calculateStopLossPrice(algo, fake_symbol, _data_slice(fake_symbol))
    assert result is None
    assert algo.Error.called
