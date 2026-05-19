from AlgorithmImports import *
import config as c
from AddUniverse import AddUniverseHandler
from OnSecuritiesChanged import OnSecuritiesChangedHandler
from OnWarmupFinished import OnWarmupFinishedHandler
from OnData import OnDataHandler
from OnOrderEvent import OnOrderEventHandler
from risk_gauntlet import RiskGauntlet, RiskGauntletError

class CodysAdvancedStrategy(QCAlgorithm):
    def Initialize(self):
        try:
            RiskGauntlet().validate(c.Config())
        except RiskGauntletError as err:
            self.Debug(f"[risk-gauntlet] blocked algorithm load: {err}")
            raise
        c.SetStartDate(self)
        c.SetEndDate(self)
        c.SetWarmUp(self)
        c.SetCash(self)
        c.SetBrokerageModel(self)

        self.SetBenchmark("SPY")

        self.Settings.FreePortfolioValuePercentage = (
            1 - c.buy_parameter_max_total_portfolio_invested_percent
            if c.buy_condition_max_total_portfolio_invested_percent
            else 0.03
        )

        self.onSecuritiesChangedHandler = OnSecuritiesChangedHandler(self)

        self.addUniverseHandler = AddUniverseHandler(self)
        self.addUniverseHandler.AddUniverse()

        self.onWarmupFinishedHandler = OnWarmupFinishedHandler(self)
        self.onDataHandler = OnDataHandler(self)
        self.onOrderEventHandler = OnOrderEventHandler(self)

    def OnSecuritiesChanged(self, changes):
        self.onSecuritiesChangedHandler.OnSecuritiesChanged(changes)

    def OnWarmupFinished(self):
        self.onWarmupFinishedHandler.OnWarmupFinished()

    def OnData(self, data):
        self.onDataHandler.OnData(data)

    def OnOrderEvent(self, orderEvent):
        self.onOrderEventHandler.OnOrderEvent(orderEvent)

    def initializeIndicators(self, symbol):
        self.onSecuritiesChangedHandler.initializeIndicators(symbol)
