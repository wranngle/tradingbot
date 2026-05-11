from AlgorithmImports import *
import config as c
import variables as v
import json


def _target_used(price_map, symbol, selected_price):
    return price_map.get(symbol) == selected_price


def _build_order_tag(symbol, conditions, underlying_values, parameters):
    return json.dumps(
        {
            "Symbol": str(symbol),
            "Conditions": conditions,
            "UnderlyingValues": {
                key: value.to_dict() if isinstance(value, Symbol) else value
                for key, value in underlying_values.items()
            },
            "Parameters": parameters,
        }
    )


def shouldSell(algorithm, symbol, data):
    try:
        if symbol not in data or data[symbol] is None or not hasattr(data[symbol], "Price"):
            return False, None

        take_profit_price = v.take_profit_max_price.get(symbol)
        stop_loss_price = v.stop_loss_max_price.get(symbol)
        if take_profit_price is None or stop_loss_price is None:
            return False, None

        indicators = v.indicators.get(symbol)
        if indicators is None:
            algorithm.Error(f"Indicators not initialized for {symbol}. Skipping sell check.")
            return False, None

        is_sell_condition_price_target_met = (
            v.current_price[symbol] >= take_profit_price
            or v.current_price[symbol] <= stop_loss_price
        )

        is_sell_condition_macd_cross_below_signal = (
            indicators["macd"].Current.Value < indicators["macd"].Signal.Current.Value
            if c.sell_condition_macd_cross_below_signal else True
        )

        is_sell_condition_rsi_weak = (
            indicators["rsi"].Current.Value < c.sell_parameter_rsi_max_threshold
            if c.sell_condition_rsi_weak else True
        )

        conditions = {
            "SellPriceTargetMet": is_sell_condition_price_target_met,
            "StopLossATRPriceUsed": _target_used(v.stop_loss_atr_price, symbol, stop_loss_price),
            "StopLossFibATRPriceUsed": _target_used(v.stop_loss_fib_atr_price, symbol, stop_loss_price),
            "StopLossPercentPriceUsed": _target_used(v.stop_loss_percent_price, symbol, stop_loss_price),
            "StopLossTrailingPriceUsed": _target_used(v.stop_loss_trailing_price, symbol, stop_loss_price),
            "TakeProfitATRPriceUsed": _target_used(v.take_profit_atr_price, symbol, take_profit_price),
            "TakeProfitFibATRPriceUsed": _target_used(v.take_profit_fib_atr_price, symbol, take_profit_price),
            "TakeProfitPercentPriceUsed": _target_used(v.take_profit_percent_price, symbol, take_profit_price),
            "TakeProfitTrailingPriceUsed": _target_used(v.take_profit_trailing_price, symbol, take_profit_price),
            "MACDCrossBelowSignal": is_sell_condition_macd_cross_below_signal,
            "RSIWeak": is_sell_condition_rsi_weak,
        }

        underlying_values = {
            "CurrentPrice": v.current_price[symbol],
            "TakeProfitPrice": take_profit_price,
            "StopLossPrice": stop_loss_price,
            "ATR": indicators["atr"].Current.Value,
            "MACDValue": indicators["macd"].Current.Value,
            "MACDSignal": indicators["macd"].Signal.Current.Value,
            "RSI": indicators["rsi"].Current.Value,
        }

        parameters = {
            "StopLossATRPriceEnabled": c.sell_condition_stop_loss_atr_price,
            "StopLossFibATRPriceEnabled": c.sell_condition_stop_loss_fibonacci_atr_price,
            "StopLossPercentPriceEnabled": c.sell_condition_stop_loss_percent,
            "StopLossTrailingPriceEnabled": c.sell_condition_stop_loss_trailing_percent,
            "TakeProfitATRPriceEnabled": c.sell_condition_take_profit_atr_price,
            "TakeProfitFibATRPriceEnabled": c.sell_condition_take_profit_fibonacci_atr_price,
            "TakeProfitPercentPriceEnabled": c.sell_condition_take_profit_percent,
            "TakeProfitTrailingPriceEnabled": c.sell_condition_take_profit_trailing_percent,
            "MACDCrossBelowSignalEnabled": c.sell_condition_macd_cross_below_signal,
            "RSIWeakEnabled": c.sell_condition_rsi_weak,
            "RSIMaxThreshold": c.sell_parameter_rsi_max_threshold,
        }

        order_tag = _build_order_tag(symbol, conditions, underlying_values, parameters)
        should_sell = (
            is_sell_condition_price_target_met
            and is_sell_condition_macd_cross_below_signal
            and is_sell_condition_rsi_weak
        )
        return should_sell, order_tag if should_sell else None

    except Exception as e:
        algorithm.Error(f"Error on shouldSell: {str(e)}")
        return False, None
