from AlgorithmImports import *
import config as c
from AddUniverse import AddUniverseHandler
from OnSecuritiesChanged import OnSecuritiesChangedHandler
from OnWarmupFinished import OnWarmupFinishedHandler
from OnData import OnDataHandler
from OnOrderEvent import OnOrderEventHandler
from risk_gauntlet import RiskGauntlet, RiskGauntletError
from regime import classify_regime_verbose

# Feature flag: when True, an SPY-derived regime label is logged each bar.
# Strategy decision logic is unchanged; this is observation-only until a
# downstream consumer opts in.
ENABLE_REGIME_DETECTION = False
REGIME_WINDOW = 60

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
        self._regime_prices: list[float] = []
        self._last_regime_label: str | None = None

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
        if ENABLE_REGIME_DETECTION:
            self._update_regime(data)

    def _update_regime(self, data):
        spy = self.Securities["SPY"] if "SPY" in self.Securities else None
        price = float(spy.Price) if spy and spy.Price else None
        if not price:
            return
        self._regime_prices.append(price)
        if len(self._regime_prices) > REGIME_WINDOW:
            self._regime_prices = self._regime_prices[-REGIME_WINDOW:]
        if len(self._regime_prices) < 2:
            return
        report = classify_regime_verbose(self._regime_prices)
        if report["label"] != self._last_regime_label:
            self._last_regime_label = report["label"]
            self.Log(f"regime={report['label']} vol={report['annualised_vol']:.3f} dd={report['max_drawdown']:.3f}")

    def OnOrderEvent(self, orderEvent):
        self.onOrderEventHandler.OnOrderEvent(orderEvent)

    def initializeIndicators(self, symbol):
        self.onSecuritiesChangedHandler.initializeIndicators(symbol)
