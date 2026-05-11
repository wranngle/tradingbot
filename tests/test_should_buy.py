"""Tests for `shouldBuy`.

This function used to be a wall of flags where disabled conditions became the
literal string `"Disabled"` and then still had to compare equal to `True`.
That made the default config mostly theatrical: it looked configurable while
blocking buys.
"""

from unittest.mock import MagicMock

import pytest


def _indicator(value, previous=None, ready=True):
    return MagicMock(
        Current=MagicMock(Value=value),
        Previous=MagicMock(Value=value if previous is None else previous),
        IsReady=ready,
    )


@pytest.fixture
def buy_setup(reset_variables, fake_symbol, fake_algorithm, monkeypatch):
    import config as c
    import variables as v

    sym = fake_symbol
    v.current_price[sym] = 100.0
    v.current_close_price[sym] = 100.0
    v.kelly_criterion = 0

    macd = _indicator(1.0)
    macd.Signal = MagicMock(Current=MagicMock(Value=0.5))
    v.indicators[sym] = {
        "atr_min": _indicator(95.0),
        "atr": _indicator(2.0),
        "emaShort": _indicator(12.0, previous=11.0),
        "emaLong": _indicator(10.0, previous=10.0),
        "macd": macd,
        "rsi": _indicator(55.0),
        "sto": _indicator(60.0),
    }

    fake_algorithm.Portfolio.Cash = 1000
    fake_algorithm.Portfolio.TotalPortfolioValue = 1000
    fake_algorithm.Portfolio.TotalHoldingsValue = 0

    monkeypatch.setattr(c, "buy_condition_limit_order_percent", True)
    monkeypatch.setattr(c, "buy_condition_kelly_criterion_position_size", True)
    monkeypatch.setattr(c, "buy_condition_ema_crossover", True)
    monkeypatch.setattr(c, "buy_condition_atr_breakout_level_reached", False)
    monkeypatch.setattr(c, "buy_condition_ema_distance_widening", False)
    monkeypatch.setattr(c, "buy_condition_macd_cross_above_signal", False)
    monkeypatch.setattr(c, "buy_condition_reward_risk_ratio", False)
    monkeypatch.setattr(c, "buy_condition_rsi_strong", False)
    monkeypatch.setattr(c, "buy_condition_short_ema_rising", False)
    monkeypatch.setattr(c, "buy_condition_stochastic_rsi_strong", False)
    monkeypatch.setattr(c, "buy_condition_max_total_portfolio_invested_percent", False)
    monkeypatch.setattr(c, "buy_condition_max_portfolio_percent_per_trade", False)
    monkeypatch.setattr(c, "buy_condition_min_symbols_invested", False)
    monkeypatch.setattr(c, "buy_condition_max_sector_invested_percent", False)
    monkeypatch.setattr(c, "buy_condition_pdt_rule", False)

    monkeypatch.setattr(c, "sell_condition_stop_loss_atr_price", True)
    monkeypatch.setattr(c, "sell_parameter_stop_loss_price_atr_multiplier", 2)
    monkeypatch.setattr(c, "sell_condition_stop_loss_fibonacci_atr_price", True)
    monkeypatch.setattr(c, "sell_parameter_stop_loss_fibonacci_retracement_levels", [0.236, 0.382, 0.618])
    monkeypatch.setattr(c, "sell_condition_stop_loss_trailing_percent", True)
    monkeypatch.setattr(c, "sell_parameter_stop_loss_trailing_percent", 0.10)
    monkeypatch.setattr(c, "sell_condition_stop_loss_percent", True)
    monkeypatch.setattr(c, "sell_parameter_stop_loss_percent", 0.20)

    monkeypatch.setattr(c, "sell_condition_take_profit_atr_price", True)
    monkeypatch.setattr(c, "sell_parameter_take_profit_price_atr_multiplier", 2)
    monkeypatch.setattr(c, "sell_condition_take_profit_fibonacci_atr_price", True)
    monkeypatch.setattr(c, "sell_parameter_take_profit_fibonacci_retracement_levels", [0.236, 0.382, 0.618])
    monkeypatch.setattr(c, "sell_condition_take_profit_trailing_percent", True)
    monkeypatch.setattr(c, "sell_parameter_take_profit_trailing_percent", 0.10)
    monkeypatch.setattr(c, "sell_condition_take_profit_percent", True)
    monkeypatch.setattr(c, "sell_parameter_take_profit_percent", 0.20)

    return sym


def _data_slice(symbol):
    return {symbol: MagicMock(Price=100.0, Close=100.0)}


def test_disabled_conditions_do_not_block_buy(buy_setup, fake_algorithm):
    import variables as v
    from shouldBuy import shouldBuy

    decision, tag = shouldBuy(fake_algorithm, buy_setup, _data_slice(buy_setup))

    assert decision is True
    assert tag is not None
    assert v.position_size_share_qty_to_buy[buy_setup] == 10


def test_pdt_condition_blocks_buy_when_enabled(buy_setup, fake_algorithm, monkeypatch):
    import config as c
    import variables as v
    from shouldBuy import shouldBuy

    monkeypatch.setattr(c, "buy_condition_pdt_rule", True)
    v.day_trade_dates.extend(["2024-01-01", "2024-01-02", "2024-01-03"])

    decision, tag = shouldBuy(fake_algorithm, buy_setup, _data_slice(buy_setup))

    assert decision is False
    assert tag is not None


def test_buy_floor_blocks_when_portfolio_is_too_small(buy_setup, fake_algorithm, monkeypatch):
    import config as c
    from shouldBuy import shouldBuy

    fake_algorithm.Portfolio.Cash = 25
    fake_algorithm.Portfolio.TotalPortfolioValue = 25
    fake_algorithm.Portfolio.TotalHoldingsValue = 0
    monkeypatch.setattr(c, "buy_parameter_lost_it_all", 50)

    decision, tag = shouldBuy(fake_algorithm, buy_setup, _data_slice(buy_setup))

    assert decision is False
    assert tag is None
