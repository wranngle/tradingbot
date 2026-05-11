from AlgorithmImports import *
import config as c
import variables as v
import numpy as np


def _symbolValue(symbol):
    return getattr(symbol, "Value", str(symbol))


def _isFiniteNumber(value):
    try:
        return value is not None and not np.isnan(value)
    except TypeError:
        return False


class AddUniverseHandler:
    def __init__(self, algorithm):
        self.algorithm = algorithm

    def AddUniverse(self):
        self.algorithm.Debug(f"Creating Universe...")
        self.algorithm.Debug(
            "---- Static Universe "
            f"(c.symbol_filter_condition_static_universe) = "
            f"{c.symbol_filter_condition_static_universe}"
        )
        if c.symbol_filter_condition_static_universe:
            for ticker in c.symbol_filter_parameter_static_universe:
                security = self.algorithm.AddEquity(ticker, c.finest_resolution)
                symbol = security.Symbol
                self._ensureSymbolInitialized(symbol)
                self.algorithm.Debug(f"-------- Static Universe Updated: +{symbol}")

        elif not c.symbol_filter_condition_static_universe:
            self.algorithm.Debug(
                "---- Extended Market Hours "
                f"(c.symbol_filter_condition_extended_market_hours) = "
                f"{c.symbol_filter_condition_extended_market_hours}"
            )
            self.algorithm.UniverseSettings.ExtendedMarketHours = (
                c.symbol_filter_condition_extended_market_hours
            ) # Enable or disable Extended Market Hours for the Universe.

            self.algorithm.Debug(f"---- Finest Resolution (c.finest_resolution) = {c.finest_resolution}")
            self.algorithm.UniverseSettings.Resolution = c.finest_resolution

            self.algorithm.AddUniverse(self.filterAndSortUniverse)

    def _ensureSymbolInitialized(self, symbol):
        v.active_symbols.add(symbol)
        handler = getattr(self.algorithm, "onSecuritiesChangedHandler", None)
        if handler is None:
            return

        ensure_symbol_initialized = getattr(handler, "ensureSymbolInitialized", None)
        if callable(ensure_symbol_initialized):
            ensure_symbol_initialized(symbol)
            return

        if symbol not in v.indicators:
            handler.initializeIndicators(symbol)

        if symbol not in v.consolidators:
            handler.registerConsolidator(symbol, c.finest_resolution)

    def filterAndSortUniverse(self, fundamental: List[Fundamental]) -> List[Symbol]:
        v.max_symbol_price = (
            self.algorithm.Portfolio.TotalPortfolioValue
            * c.symbol_filter_parameter_max_symbol_price_portfolio_percent
            if c.symbol_filter_condition_max_symbol_price_portfolio_percent
            else 0.95 * self.algorithm.Portfolio.TotalPortfolioValue
        )

        self.algorithm.Debug(
            f"---- Symbol Price Range: ${c.symbol_filter_parameter_min_price} - ${v.max_symbol_price}"
        )
        self.algorithm.Debug(
            f"---- P/E Ratio Range: {c.symbol_filter_parameter_min_pe_ratio} "
            f"to {c.symbol_filter_parameter_max_pe_ratio}"
        )
        self.algorithm.Debug(
            "---- Min Annual Revenue Growth %: "
            f"{c.symbol_filter_parameter_min_revenue_growth_percent}"
        )
        self.algorithm.Debug(
            f"---- Extended Market Hours Enabled: {c.symbol_filter_condition_extended_market_hours}"
        )

        try:
            blacklist = {_symbolValue(symbol) for symbol in c.symbol_filter_parameter_blacklist}

            filtered_symbols = []
            for f in fundamental:
                try:
                    pe_ratio = f.ValuationRatios.PERatio
                    revenue_growth = f.OperationRatios.RevenueGrowth.OneYear

                    if not f.HasFundamentalData:
                        continue
                    if not _isFiniteNumber(f.MarketCap) or f.MarketCap <= 0:
                        continue
                    if not _isFiniteNumber(f.DollarVolume) or f.DollarVolume <= 0:
                        continue
                    if not _isFiniteNumber(f.Price) or f.Price > v.max_symbol_price:
                        continue
                    if c.symbol_filter_condition_blacklist and _symbolValue(f.Symbol) in blacklist:
                        continue
                    if c.symbol_filter_condition_min_price and f.Price < c.symbol_filter_parameter_min_price:
                        continue
                    if c.symbol_filter_condition_min_pe_ratio and not (
                        _isFiniteNumber(pe_ratio)
                        and pe_ratio != 0
                        and c.symbol_filter_parameter_min_pe_ratio < pe_ratio
                    ):
                        continue
                    if c.symbol_filter_condition_max_pe_ratio and not (
                        _isFiniteNumber(pe_ratio)
                        and pe_ratio != 0
                        and c.symbol_filter_parameter_max_pe_ratio > pe_ratio
                    ):
                        continue
                    if c.symbol_filter_condition_min_revenue_growth_percent and not (
                        _isFiniteNumber(revenue_growth)
                        and revenue_growth != 0
                        and c.symbol_filter_parameter_min_revenue_growth_percent < revenue_growth
                    ):
                        continue
                except AttributeError:
                    continue

                filtered_symbols.append(f)

            symbols_sorted_by_dollar_volume = sorted(
                filtered_symbols,
                key=lambda f: f.DollarVolume,
                reverse=True)[:100]

            symbols_sorted_by_pe_ratio = sorted(
                symbols_sorted_by_dollar_volume,
                key=lambda f: f.ValuationRatios.PERatio,
                reverse=False)[:50]

            symbols_sorted_by_market_cap = sorted(
                symbols_sorted_by_pe_ratio,
                key=lambda f: f.MarketCap,
                reverse=False)[:10]
            return [f.Symbol for f in symbols_sorted_by_market_cap]

        except Exception as e:
            self.algorithm.Error(f"---- Error on filterAndSortUniverse: {str(e)}")
            return []
