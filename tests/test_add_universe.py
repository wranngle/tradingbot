"""Tests for universe registration."""

from unittest.mock import MagicMock
from types import SimpleNamespace


def test_static_universe_accepts_ticker_strings(reset_variables, fake_symbol, monkeypatch):
    import config as c
    import variables as v
    from AddUniverse import AddUniverseHandler

    algo = MagicMock()
    algo.AddEquity.return_value = MagicMock(Symbol=fake_symbol)
    algo.onSecuritiesChangedHandler = MagicMock()

    monkeypatch.setattr(c, "symbol_filter_condition_static_universe", True)
    monkeypatch.setattr(c, "symbol_filter_parameter_static_universe", ["TSLA"])

    AddUniverseHandler(algo).AddUniverse()

    algo.AddEquity.assert_called_once_with("TSLA", c.finest_resolution)
    algo.onSecuritiesChangedHandler.ensureSymbolInitialized.assert_called_once_with(fake_symbol)
    assert fake_symbol in v.active_symbols


def _fundamental(symbol, *, price=10, pe_ratio=10, revenue_growth=0.1, market_cap=100, dollar_volume=1000):
    return SimpleNamespace(
        Symbol=symbol,
        HasFundamentalData=True,
        Price=price,
        MarketCap=market_cap,
        DollarVolume=dollar_volume,
        ValuationRatios=SimpleNamespace(PERatio=pe_ratio),
        OperationRatios=SimpleNamespace(
            RevenueGrowth=SimpleNamespace(OneYear=revenue_growth),
        ),
    )


def test_dynamic_filter_skips_bad_fundamentals_without_emptying_universe(reset_variables):
    from AlgorithmImports import Symbol
    from AddUniverse import AddUniverseHandler

    valid = Symbol("GOOD")
    invalid = Symbol("BAD")
    algo = MagicMock()
    algo.Portfolio.TotalPortfolioValue = 1000

    result = AddUniverseHandler(algo).filterAndSortUniverse([
        SimpleNamespace(Symbol=Symbol("BROKEN")),
        _fundamental(invalid, pe_ratio=None),
        _fundamental(valid, market_cap=50),
    ])

    assert result == [valid]
