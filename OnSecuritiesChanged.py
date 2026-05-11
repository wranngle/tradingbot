from AlgorithmImports import *
import config as c
import variables as v

class OnSecuritiesChangedHandler:
    def __init__(self, algorithm):
        self.algorithm = algorithm

    def OnSecuritiesChanged(self, changes):
        try:
            for x in changes.AddedSecurities:
                self.ensureSymbolInitialized(x.Symbol)

            for x in changes.RemovedSecurities:
                v.active_symbols.discard(x.Symbol)
                self.removeConsolidators(x.Symbol)

        except Exception as e:
            self.algorithm.Error(f"Error on OnSecuritiesChanged: {str(e)}")

    def updateIndicator(self, bar, indicator, indicator_key):
        try:
            if bar is None:
                self.algorithm.Debug(f"Skipping {indicator_key} update due to missing data.")
                return

            try:
                if indicator_key in ("atr", "sto"):
                    indicator.Update(bar)
                else:
                    dataPoint = IndicatorDataPoint(bar.EndTime, bar.Close)
                    indicator.Update(dataPoint)
            except Exception as e:
                self.algorithm.Error(f"Error updating {indicator_key}: {str(e)}")
                return

            counter_key = (bar.Symbol, indicator_key)
            v.indicator_warmup_counter[counter_key] = (
                v.indicator_warmup_counter.get(counter_key, 0) + 1
            )

            if self.algorithm.IsWarmingUp:
                self.algorithm.Debug(
                    f"{bar.EndTime} - {bar.Symbol} - Warming up {indicator_key}: "
                    f"{indicator.Current.Value} - Received "
                    f"{v.indicator_warmup_counter[counter_key]} / {c.warmup_period} data points..."
                )
            else:
                self.algorithm.Debug(
                    f"{bar.EndTime} - {bar.Symbol} - Updated {indicator_key}: "
                    f"{indicator.Current.Value}"
                )

        except Exception as e:
            self.algorithm.Error(f"Error on OnSecuritiesChanged: {str(e)}")

    def ensureSymbolInitialized(self, symbol):
        v.active_symbols.add(symbol)
        if symbol not in v.indicators:
            self.initializeIndicators(symbol)

        if symbol not in v.consolidators:
            self.registerConsolidator(symbol, c.finest_resolution)

    def updateIndicators(self, symbol, bar):
        for indicator_key, indicator in v.indicators.get(symbol, {}).items():
            self.updateIndicator(bar, indicator, indicator_key)

    def initializeIndicators(self, symbol):
        self.algorithm.Debug(f"Initializing indicators for {symbol}...")
        atr_min = Minimum(c.buy_parameter_atr_low_period)
        atr = AverageTrueRange(c.buy_parameter_atr_periods, MovingAverageType.Wilders)
        emaShort = ExponentialMovingAverage(c.buy_parameter_ema_short_periods)
        emaLong = ExponentialMovingAverage(c.buy_parameter_ema_long_periods)
        macd = MovingAverageConvergenceDivergence(12, 26, 9, MovingAverageType.Wilders)
        rsi = RelativeStrengthIndex(c.buy_parameter_rsi_periods)
        sto = Stochastic(c.buy_parameter_stochastic_rsi_periods, 3, 3)

        v.indicators[symbol] = {
            'atr_min': atr_min,
            'atr': atr,
            'emaShort': emaShort,
            'emaLong': emaLong,
            'macd': macd,
            'rsi': rsi,
            'sto': sto
        }

    def registerConsolidator(self, symbol, resolution):
        consolidator = self.algorithm.ResolveConsolidator(symbol, resolution)
        consolidator.DataConsolidated += lambda sender, bar: self.updateIndicators(symbol, bar)
        self.algorithm.SubscriptionManager.AddConsolidator(symbol, consolidator)
        v.consolidators[symbol] = [consolidator]

    def removeConsolidators(self, symbol):
        if symbol in v.consolidators:
            for consolidator in v.consolidators[symbol]:
                self.algorithm.SubscriptionManager.RemoveConsolidator(symbol, consolidator)
            del v.consolidators[symbol]
