"""Tests for order-fill accounting."""

from unittest.mock import MagicMock


class _Portfolio(dict):
    """Dict portfolio stub with attachable QuantConnect-like attributes."""


def _security(sector):
    return MagicMock(
        Fundamentals=MagicMock(
            AssetClassification=MagicMock(MorningstarSectorCode=sector),
        ),
    )


def _filled_event(symbol, direction, price, quantity):
    from AlgorithmImports import OrderStatus

    return MagicMock(
        Symbol=symbol,
        Direction=direction,
        Status=OrderStatus.Filled,
        FillPrice=price,
        FillQuantity=quantity,
        OrderId=1,
    )


def test_sell_fill_profit_uses_absolute_sell_quantity(reset_variables, fake_symbol):
    from AlgorithmImports import OrderDirection
    import variables as v
    from OnOrderEvent import OnOrderEventHandler

    holding = MagicMock(
        Invested=True,
        AveragePrice=10.0,
        HoldingsValue=100.0,
    )
    portfolio = _Portfolio({fake_symbol: holding})
    portfolio.TotalPortfolioValue = 1000.0

    algo = MagicMock()
    algo.Portfolio = portfolio
    algo.Securities = {fake_symbol: _security(101)}
    algo.Time.date.return_value = "2024-01-02"

    handler = OnOrderEventHandler(algo)
    handler.OnOrderEvent(_filled_event(fake_symbol, OrderDirection.Buy, 10.0, 10))
    handler.OnOrderEvent(_filled_event(fake_symbol, OrderDirection.Sell, 12.0, -10))

    assert v.trade_win_count == 1
    assert v.total_profit == 20
    assert v.trade_loss_count == 0
    assert v.kelly_criterion == 1


def test_terminal_order_status_clears_open_ticket(reset_variables, fake_symbol):
    from AlgorithmImports import OrderDirection, OrderStatus
    import variables as v
    from OnOrderEvent import OnOrderEventHandler

    ticket = MagicMock()
    v.open_order_tickets[fake_symbol] = ticket

    algo = MagicMock()
    handler = OnOrderEventHandler(algo)
    handler.OnOrderEvent(
        MagicMock(
            Symbol=fake_symbol,
            Direction=OrderDirection.Buy,
            Status=OrderStatus.Canceled,
            FillPrice=0,
            FillQuantity=0,
            OrderId=2,
        )
    )

    assert fake_symbol not in v.open_order_tickets
