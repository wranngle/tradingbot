from AlgorithmImports import *
import config as c
import variables as v

DISABLED = "Disabled"


def calculateStopLossPrice(self, symbol, data):
    try:
        if symbol in data and data[symbol] is not None and hasattr(data[symbol], 'Price'):

            indicators = v.indicators[symbol]

            v.stop_loss_atr_price[symbol] = (
                v.current_price[symbol]
                - (
                    indicators["atr"].Current.Value
                    * c.sell_parameter_stop_loss_price_atr_multiplier
                )
                if c.sell_condition_stop_loss_atr_price else DISABLED
            )

            v.stop_loss_fibonacci_prices[symbol] = [
                v.current_price[symbol] * (1 - abs(level))
                for level in c.sell_parameter_stop_loss_fibonacci_retracement_levels
            ]
            v.stop_loss_fib_atr_price[symbol] = (
                max(v.stop_loss_fibonacci_prices[symbol]) - indicators["atr"].Current.Value
                if c.sell_condition_stop_loss_fibonacci_atr_price else DISABLED
            )

            v.stop_loss_trailing_price[symbol] = (
                v.current_price[symbol] * (1 - c.sell_parameter_stop_loss_trailing_percent)
                if c.sell_condition_stop_loss_trailing_percent else DISABLED
            )

            v.stop_loss_percent_price[symbol] = (
                v.current_price[symbol] * (1 - c.sell_parameter_stop_loss_percent)
                if c.sell_condition_stop_loss_percent else DISABLED
            )

            candidate_prices = [
                p for p in (
                    v.stop_loss_atr_price[symbol],
                    v.stop_loss_fib_atr_price[symbol],
                    v.stop_loss_trailing_price[symbol],
                    v.stop_loss_percent_price[symbol],
                )
                if p != DISABLED and p < v.current_price[symbol]
            ]
            v.stop_loss_max_price[symbol] = max(candidate_prices) if candidate_prices else None
            return v.stop_loss_max_price[symbol]

        else:
            return None

    except Exception as e:
        self.Error(f"Error on calculateStopLossPrice for {symbol}: {str(e)}")
        return None
