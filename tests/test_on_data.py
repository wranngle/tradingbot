"""Tests for `OnData` event-flow behavior."""

from unittest.mock import MagicMock
from datetime import datetime, timedelta


class _Portfolio(dict):
    """Dict portfolio stub with attachable QuantConnect-like attributes."""


def _indicator(value=1.0):
    return MagicMock(Current=MagicMock(Value=value), IsReady=True)


def _ready_indicators():
    macd = _indicator()
    macd.Signal = MagicMock(Current=MagicMock(Value=0.5))
    return {
        "atr_min": _indicator(),
        "atr": _indicator(),
        "emaShort": _indicator(),
        "emaLong": _indicator(),
        "macd": macd,
        "rsi": _indicator(),
        "sto": _indicator(),
    }


def test_on_data_does_not_recalculate_buy_targets_for_invested_symbol(
    reset_variables,
    fake_symbol,
    monkeypatch,
):
    from AlgorithmImports import TradeBar
    import variables as v
    import OnData as on_data_module
    from OnData import OnDataHandler

    holding = MagicMock(Invested=True, Quantity=10)
    portfolio = _Portfolio({fake_symbol: holding})
    portfolio.Cash = 1000
    portfolio.TotalPortfolioValue = 1000

    algo = MagicMock()
    algo.IsWarmingUp = False
    algo.Portfolio = portfolio
    algo.Transactions.GetOpenOrders.return_value = []
    algo.Securities = {
        fake_symbol: MagicMock(
            Fundamentals=MagicMock(
                AssetClassification=MagicMock(MorningstarSectorCode=101),
            ),
        ),
    }

    v.active_symbols.add(fake_symbol)
    v.indicators[fake_symbol] = _ready_indicators()

    should_buy = MagicMock(return_value=(True, "buy-tag"))
    should_sell = MagicMock(return_value=(False, None))
    monkeypatch.setattr(on_data_module, "shouldBuy", should_buy)
    monkeypatch.setattr(on_data_module, "shouldSell", should_sell)

    bar = TradeBar()
    bar.Price = 100.0
    bar.Close = 100.0

    OnDataHandler(algo).OnData({fake_symbol: bar})

    should_buy.assert_not_called()
    should_sell.assert_called_once()


def test_cancel_old_orders_removes_stale_ticket(reset_variables, fake_symbol, monkeypatch):
    import config as c
    import variables as v
    from OnData import OnDataHandler

    now = datetime(2024, 1, 1, 10, 0)
    ticket = MagicMock(
        OrderClosed=False,
        Time=now - timedelta(minutes=16),
        OrderId=123,
    )
    v.open_order_tickets[fake_symbol] = ticket

    algo = MagicMock()
    algo.Time = now
    monkeypatch.setattr(c, "max_pending_order_age_minutes", 15)

    OnDataHandler(algo).CancelOldOrders()

    ticket.Cancel.assert_called_once_with("Order too old")
    assert fake_symbol not in v.open_order_tickets
