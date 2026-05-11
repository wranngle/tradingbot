import config as c
import variables as v


def _plot(self, chart, series, value):
    try:
        self.Plot(chart, series, value)
    except AttributeError:
        return


def plotIndicators(self, symbol, indicators):
    chart = f"{symbol} Indicators"
    _plot(self, chart, "EMA Short", indicators["emaShort"].Current.Value)
    _plot(self, chart, "EMA Long", indicators["emaLong"].Current.Value)
    _plot(self, chart, "MACD", indicators["macd"].Current.Value)
    _plot(self, chart, "MACD Signal", indicators["macd"].Signal.Current.Value)
    _plot(
        self,
        chart,
        "MACD Histogram",
        indicators["macd"].Current.Value - indicators["macd"].Signal.Current.Value,
    )
    _plot(self, chart, "RSI", indicators["rsi"].Current.Value)
    _plot(self, chart, "Stochastic", indicators["sto"].Current.Value)


def plotPositionSizes(self, symbol, position_size_candidates=None):
    if position_size_candidates is None:
        buy_price = v.buy_limit_price.get(symbol)
        risk_per_share = v.max_loss_risk_per_share.get(symbol)
        if not buy_price or not risk_per_share:
            return

        position_size_candidates = {
            "CashAvailable": self.Portfolio.Cash / buy_price,
            "KellyCriterion": (
                self.Portfolio.Cash * max(min(v.kelly_criterion, 1), 0) / buy_price
            ),
            "MaxPortfolioPercentPerTrade": (
                self.Portfolio.TotalPortfolioValue
                * c.buy_parameter_max_portfolio_percent_per_trade
                / buy_price
            ),
            "MaxTotalPortfolioInvestedPercent": (
                self.Portfolio.TotalPortfolioValue
                * c.buy_parameter_max_total_portfolio_invested_percent
                / buy_price
            ),
        }

    chart = f"{symbol} Position Size"
    for name, quantity in position_size_candidates.items():
        _plot(self, chart, name, quantity)
