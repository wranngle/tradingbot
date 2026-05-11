from AlgorithmImports import *
import config as c
import variables as v

DISABLED = "Disabled"


def calculateTakeProfitPrice(self, symbol, data):
    try:
        if symbol in data and data[symbol] is not None and hasattr(data[symbol], 'Price'):

            indicators = v.indicators[symbol]

            v.take_profit_atr_price[symbol] = (
                v.current_price[symbol]
                + (
                    indicators["atr"].Current.Value
                    * c.sell_parameter_take_profit_price_atr_multiplier
                )
                if c.sell_condition_take_profit_atr_price and indicators["atr"].IsReady else DISABLED
            )

            v.take_profit_fibonacci_prices[symbol] = [
                v.current_price[symbol] * (1 + abs(level))
                for level in c.sell_parameter_take_profit_fibonacci_retracement_levels
            ]
            v.take_profit_fib_atr_price[symbol] = (
                min(v.take_profit_fibonacci_prices[symbol]) + indicators["atr"].Current.Value
                if c.sell_condition_take_profit_fibonacci_atr_price and indicators["atr"].IsReady else DISABLED
            )

            v.take_profit_trailing_price[symbol] = (
                v.current_price[symbol] * (1 + c.sell_parameter_take_profit_trailing_percent)
                if c.sell_condition_take_profit_trailing_percent else DISABLED
            )

            v.take_profit_percent_price[symbol] = (
                v.current_price[symbol] * (1 + c.sell_parameter_take_profit_percent)
                if c.sell_condition_take_profit_percent else DISABLED
            )

            candidate_prices = [
                p for p in (
                    v.take_profit_atr_price[symbol],
                    v.take_profit_fib_atr_price[symbol],
                    v.take_profit_trailing_price[symbol],
                    v.take_profit_percent_price[symbol],
                )
                if p != DISABLED and p > v.current_price[symbol]
            ]
            v.take_profit_max_price[symbol] = max(candidate_prices) if candidate_prices else None

            return v.take_profit_max_price[symbol]

        else:
            return None

    except Exception as e:
        self.Error(f"Error in calculateTakeProfitPrice for {symbol}: {str(e)}")
        return None
