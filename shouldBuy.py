from AlgorithmImports import *
import config as c
import variables as v
from calculateStopLossPrice import calculateStopLossPrice
from calculateTakeProfitPrice import calculateTakeProfitPrice
import json
import charts

def shouldBuy(algorithm, symbol, data):
    try:
        if symbol in data and data[symbol] is not None and hasattr(data[symbol], 'Price'): # Confirm this is a valid data point

            indicators = v.indicators.get(symbol, None)

            # Risk/Reward Analysis
            v.take_profit_max_price[symbol] = calculateTakeProfitPrice(algorithm, symbol, data)
                # Calculate optimal Take Profit share price for this buy. 
            
            v.stop_loss_max_price[symbol] = calculateStopLossPrice(algorithm, symbol, data)
                # Calculate optimal Stop Loss share price for this buy.

            v.max_profit_reward_per_share[symbol] = v.take_profit_max_price[symbol] - v.current_price[symbol]
                # Calculate max potential profit per share for this buy.

            v.max_loss_risk_per_share[symbol] = v.current_price[symbol] - v.stop_loss_max_price[symbol]
                # Calculate max potential loss per share for this buy.

            if (
                v.max_loss_risk_per_share[symbol] is None 
                or v.max_loss_risk_per_share[symbol] <= 0 
                or v.max_profit_reward_per_share[symbol] is None 
                or v.max_profit_reward_per_share[symbol] <= 0
            ):    
                algorithm.Error(f"Risk/Reward per share is non-positive or invalid (max_loss_risk_per_share: {str(v.max_loss_risk_per_share[symbol])}, max_profit_reward_per_share: {str(v.max_profit_reward_per_share[symbol])}). Skipping position size calculation.")                
                return False
                # Throw error if risk/reward calculation problem.
            
            # Position Size Analysis
            v.buy_limit_price[symbol] = (
                v.current_close_price[symbol]
                * c.buy_parameter_limit_order_percent
                if c.buy_condition_limit_order_percent else v.current_price[symbol]
            ) # Calulate desired limit price for this buy if enabled, otherwise use market price.

            position_size_cash_available_share_qty = (
                algorithm.Portfolio.Cash
                / v.buy_limit_price[symbol]
            ) # Calculate potential position size for this buy based on available cash.
              # Simplest method, always enabled.

            position_size_kelly_criterion_share_qty = (
                (algorithm.Portfolio.Cash * v.kelly_criterion)
                / v.max_loss_risk_per_share[symbol] 
                if c.buy_condition_kelly_criterion_position_size else 0
            ) # Uses the win probability and win/loss ratio to determine
              # the optimal fraction of capital to be used for each trade.

            position_size_max_portfolio_percent_per_trade_share_qty = (
                (algorithm.Portfolio.TotalPortfolioValue * c.buy_parameter_max_portfolio_percent_per_trade)
                / v.max_loss_risk_per_share[symbol] 
                if c.buy_condition_max_portfolio_percent_per_trade else 0
            ) # Calculate potential position size for this buy based on max portfolio percent of a single trade.
            
            position_size_max_total_portfolio_invested_percent_share_qty = (
                (algorithm.Portfolio.TotalPortfolioValue * c.buy_parameter_max_total_portfolio_invested_percent) 
                / v.max_loss_risk_per_share[symbol] 
                if c.buy_condition_max_total_portfolio_invested_percent else 0
            ) # Calculate potential position size for this buy based on
              # percent of total invested portfolio value.

            v.position_size_share_qty_to_buy[symbol] = round(min(
                position_size_max_portfolio_percent_per_trade_share_qty,
                position_size_max_total_portfolio_invested_percent_share_qty,
                position_size_cash_available_share_qty,
                position_size_kelly_criterion_share_qty
            )) # Use the lesser of the 4 potential position sizes.
            
            charts.plotPositionSizes(algorithm, symbol)

            max_loss_risk_per_trade = (
                v.max_loss_risk_per_share[symbol] * v.position_size_share_qty_to_buy[symbol]
            ) # Calculate max potential loss for this trade.

            is_buy_condition_limit_order_percent = (
                True if c.buy_condition_limit_order_percent else "Disabled"
            )

            is_buy_condition_kelly_criterion_position_size = (
                position_size_kelly_criterion_share_qty == v.position_size_share_qty_to_buy[symbol]
                if c.buy_condition_kelly_criterion_position_size else "Disabled"
            )         
            
            is_buy_condition_max_total_portfolio_invested_percent = (
                max_loss_risk_per_trade < c.buy_parameter_max_total_portfolio_invested_percent 
                * algorithm.Portfolio.TotalPortfolioValue 
                if c.buy_condition_max_total_portfolio_invested_percent else "Disabled"
            )

            is_buy_condition_max_portfolio_percent_per_trade = (
                max_loss_risk_per_trade < c.buy_parameter_max_portfolio_percent_per_trade 
                * algorithm.Portfolio.TotalPortfolioValue 
                if c.buy_condition_max_portfolio_percent_per_trade else "Disabled"
            )

            is_buy_condition_min_symbols_invested = (
                len(v.unique_portfolio_symbols) < c.buy_parameter_min_symbols_invested 
                if c.buy_condition_min_symbols_invested else "Disabled"
            )

            is_buy_condition_max_sector_invested_percent = (
                v.portfolio_percent_per_sector[symbol] 
                < c.buy_parameter_max_sector_invested_percent 
                if symbol in v.portfolio_percent_per_sector 
                and c.buy_condition_max_sector_invested_percent else "Disabled"
            )

            is_buy_condition_pdt_rule = (
                len(v.day_trade_dates) >= 3 
                and algorithm.Portfolio.Cash < 25000 
                if c.buy_condition_pdt_rule else "Disabled"
            )

            is_buy_condition_max_sector_invested_percent = (
                v.portfolio_percent_per_sector[symbol] < c.buy_parameter_max_sector_invested_percent 
                if symbol in v.portfolio_percent_per_sector
                and c.buy_condition_max_sector_invested_percent else "Disabled"
            ) # Check if the symbol's sector is the max sector 
              # and if its percentage is less than the parameter.
            
            is_buy_condition_atr_breakout_level_reached = (
                v.current_price[symbol] > (
                    indicators["atr_min"].Current.Value + 
                    (indicators["atr"].Current.Value * c.buy_parameter_atr_breakout_level_multiplier)
                ) if c.buy_condition_atr_breakout_level_reached else "Disabled"
            )

            is_buy_condition_ema_crossover = (
                indicators["emaShort"].Current.Value > indicators["emaLong"].Current.Value 
                if c.buy_condition_ema_crossover else "Disabled"
            )

            is_buy_condition_ema_distance_widening = (
                (indicators["emaShort"].Current.Value - indicators["emaLong"].Current.Value) > 
                (indicators["emaShort"].Previous.Value - indicators["emaLong"].Previous.Value)
                if c.buy_condition_ema_distance_widening else "Disabled"
            )

            is_buy_condition_macd_cross_above_signal = (
                indicators["macd"].Current.Value > indicators["macd"].Signal.Current.Value
                if c.buy_condition_macd_cross_above_signal else "Disabled"
            )

            is_buy_condition_reward_risk_ratio = (
                (v.max_profit_reward_per_share[symbol] / v.max_loss_risk_per_share[symbol]) >= c.buy_parameter_reward_risk_ratio 
                if c.buy_condition_reward_risk_ratio else "Disabled"
            )

            is_buy_condition_rsi_strong = (
                v.rsi.get(symbol, 0) > c.buy_parameter_rsi_min_threshold 
                if c.buy_condition_rsi_strong else "Disabled"
            )

            is_buy_condition_short_ema_rising = (
                indicators["emaShort"].Current.Value > indicators["emaShort"].Previous.Value
                if c.buy_condition_short_ema_rising else "Disabled"
            )

            is_buy_condition_stochastic_rsi_strong = (
                indicators["sto"].Current.Value > c.buy_parameter_stochastic_rsi_min_threshold 
                if c.buy_condition_stochastic_rsi_strong else "Disabled"
            )

            # Diversification Parameters
            
            condition_details = {
                "Conditions": {
                    "ATRBreakoutLevelReached": is_buy_condition_atr_breakout_level_reached,
                    "EMACrossover": is_buy_condition_ema_crossover,
                    "EMADistanceWidening": is_buy_condition_ema_distance_widening,
                    "MACDCrossAboveSignal": is_buy_condition_macd_cross_above_signal,
                    "RewardRiskRatio": is_buy_condition_reward_risk_ratio,
                    "RSIStrong": is_buy_condition_rsi_strong,
                    "ShortEMARising": is_buy_condition_short_ema_rising,
                    "StochasticRSIStrong": is_buy_condition_stochastic_rsi_strong,
                    "MaxTotalPortfolioInvestedPercent": is_buy_condition_max_total_portfolio_invested_percent,
                    "MaxPortfolioPercentPerTrade": is_buy_condition_max_portfolio_percent_per_trade,
                    "MinSymbolsInvested": is_buy_condition_min_symbols_invested,
                    "MaxSectorInvestedPercent": is_buy_condition_max_sector_invested_percent,
                    "PDTRule": is_buy_condition_pdt_rule,
                    "BuyLimitOrderEnabled": is_buy_condition_limit_order_percent,
                    "KellyCriterionPositionSize": is_buy_condition_kelly_criterion_position_size
                },
                "UnderlyingValues": {
                    "CurrentPrice": v.current_price[symbol],
                    "TakeProfitPrice": v.take_profit_max_price[symbol],
                    "StopLossPrice": v.stop_loss_max_price[symbol],
                    "ShortEMACurrent": indicators["emaShort"].Current.Value,
                    "ShortEMAPrevious": indicators["emaShort"].Previous.Value,
                    "LongEMA": indicators["emaLong"].Current.Value,
                    "ATR": indicators["atr"].Current.Value,
                    "MACDValue": indicators["macd"].Current.Value,
                    "MACDSignal": indicators["macd"].Signal.Current.Value,
                    "RSI": indicators["rsi"].Current.Value,
                    "StochasticRSI": indicators["sto"].Current.Value
                },
                "Parameters": {
                    "LimitOrderPercent": c.buy_parameter_limit_order_percent,
                    "ATRBreakoutMultiplier": c.buy_parameter_atr_breakout_level_multiplier,
                    "MaxPortfolioPercentPerTrade": c.buy_parameter_max_portfolio_percent_per_trade,
                    "MaxTotalPortfolioInvestedPercent": c.buy_parameter_max_total_portfolio_invested_percent,
                    "RSIMinThreshold": c.buy_parameter_rsi_min_threshold,
                    "StochasticRSIMinThreshold": c.buy_parameter_stochastic_rsi_min_threshold,
                    "RewardRiskRatio": c.buy_parameter_reward_risk_ratio
                }
            }

            # Convert Symbol objects to string representation
            condition_details_json = {
                "Symbol": str(symbol),
                "Conditions": condition_details["Conditions"],
                "UnderlyingValues": {
                    key: value.to_dict() if isinstance(value, Symbol) else value
                    for key, value in condition_details["UnderlyingValues"].items()
                },
                "Parameters": condition_details["Parameters"]
            }

            order_tag = json.dumps(condition_details_json)

            # For a Buy to occur, all conditions must be True if they are enabled.
            if (
                # is_buy_condition_atr_breakout_level_reached
                is_buy_condition_ema_crossover == True
                and is_buy_condition_ema_distance_widening == True
                and is_buy_condition_macd_cross_above_signal == True
                and is_buy_condition_reward_risk_ratio == True
                and is_buy_condition_rsi_strong == True
                and is_buy_condition_short_ema_rising == True
                and is_buy_condition_stochastic_rsi_strong == True
                and is_buy_condition_max_total_portfolio_invested_percent == True
                and is_buy_condition_max_portfolio_percent_per_trade == True
                and is_buy_condition_min_symbols_invested == True
                and is_buy_condition_max_sector_invested_percent == True
                and is_buy_condition_pdt_rule == True
            ):  
                return True, order_tag

            else:
                return False, None
        else:
            return False, None  # Return None if symbol is not in data or data[symbol] is None

    except Exception as e:
        algorithm.Error(f"Error on shouldBuy: {str(e)}")
        return False, None
