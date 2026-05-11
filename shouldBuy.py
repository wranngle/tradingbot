from AlgorithmImports import *
import config as c
import variables as v
from calculateStopLossPrice import calculateStopLossPrice
from calculateTakeProfitPrice import calculateTakeProfitPrice
import charts
import json
import math


DISABLED = "Disabled"
UNAVAILABLE = "Unavailable"


def _condition(enabled, value):
    return value if enabled else DISABLED


def _condition_passed(value):
    return value == DISABLED or value is True


def _positive_number(value, default=0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def _total_holdings_value(portfolio):
    value = getattr(portfolio, "TotalHoldingsValue", None)
    if isinstance(value, (int, float)):
        return max(float(value), 0)

    total_value = _positive_number(getattr(portfolio, "TotalPortfolioValue", 0))
    cash = _positive_number(getattr(portfolio, "Cash", 0))
    return max(total_value - cash, 0)


def _symbol_sector(symbol):
    return v.symbol_sector.get(symbol)


def _sector_value(symbol):
    sector = _symbol_sector(symbol)
    if sector is None:
        return 0
    return _positive_number(v.sector_portfolio_value.get(sector, 0))


def _sector_percent(symbol):
    sector = _symbol_sector(symbol)
    if sector is None:
        return 0
    return _positive_number(v.portfolio_percent_per_sector.get(sector, 0))


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


def shouldBuy(algorithm, symbol, data):
    try:
        if symbol not in data or data[symbol] is None or not hasattr(data[symbol], "Price"):
            return False, None

        indicators = v.indicators.get(symbol)
        if indicators is None:
            algorithm.Error(f"Indicators not initialized for {symbol}. Skipping buy check.")
            return False, None

        v.take_profit_max_price[symbol] = calculateTakeProfitPrice(algorithm, symbol, data)
        v.stop_loss_max_price[symbol] = calculateStopLossPrice(algorithm, symbol, data)

        if v.take_profit_max_price[symbol] is None or v.stop_loss_max_price[symbol] is None:
            algorithm.Error(f"Missing price targets for {symbol}. Skipping buy check.")
            return False, None

        v.max_profit_reward_per_share[symbol] = (
            v.take_profit_max_price[symbol] - v.current_price[symbol]
        )
        v.max_loss_risk_per_share[symbol] = (
            v.current_price[symbol] - v.stop_loss_max_price[symbol]
        )

        if (
            v.max_loss_risk_per_share[symbol] <= 0
            or v.max_profit_reward_per_share[symbol] <= 0
        ):
            algorithm.Error(
                "Risk/reward per share is non-positive or invalid "
                f"(risk: {v.max_loss_risk_per_share[symbol]}, "
                f"reward: {v.max_profit_reward_per_share[symbol]}). "
                "Skipping buy check."
            )
            return False, None

        v.buy_limit_price[symbol] = (
            v.current_close_price[symbol] * c.buy_parameter_limit_order_percent
            if c.buy_condition_limit_order_percent
            else v.current_price[symbol]
        )
        buy_price = _positive_number(v.buy_limit_price[symbol])
        if buy_price <= 0:
            algorithm.Error(f"Buy price for {symbol} is invalid: {v.buy_limit_price[symbol]}")
            return False, None

        portfolio_value = _positive_number(algorithm.Portfolio.TotalPortfolioValue)
        cash = _positive_number(algorithm.Portfolio.Cash)
        total_holdings_value = _total_holdings_value(algorithm.Portfolio)
        if portfolio_value < c.buy_parameter_lost_it_all:
            algorithm.Debug(
                f"Portfolio value {portfolio_value} is below buy floor "
                f"{c.buy_parameter_lost_it_all}."
            )
            return False, None

        position_size_candidates = {
            "CashAvailable": cash / buy_price,
        }

        kelly_fraction = _positive_number(v.kelly_criterion)
        if c.buy_condition_kelly_criterion_position_size and kelly_fraction > 0:
            position_size_candidates["KellyCriterion"] = (
                cash * min(kelly_fraction, 1) / buy_price
            )

        if c.buy_condition_max_portfolio_percent_per_trade:
            position_size_candidates["MaxPortfolioPercentPerTrade"] = (
                portfolio_value * c.buy_parameter_max_portfolio_percent_per_trade / buy_price
            )

        if c.buy_condition_max_total_portfolio_invested_percent:
            max_invested_value = (
                portfolio_value * c.buy_parameter_max_total_portfolio_invested_percent
            )
            position_size_candidates["MaxTotalPortfolioInvestedPercent"] = (
                max(max_invested_value - total_holdings_value, 0) / buy_price
            )

        positive_candidates = [
            quantity for quantity in position_size_candidates.values() if quantity > 0
        ]
        if not positive_candidates:
            algorithm.Error(f"No positive position-size candidates for {symbol}.")
            return False, None

        v.position_size_share_qty_to_buy[symbol] = math.floor(min(positive_candidates))
        if v.position_size_share_qty_to_buy[symbol] < 1:
            algorithm.Debug(f"Calculated buy quantity for {symbol} is below 1 share.")
            return False, None

        charts.plotPositionSizes(algorithm, symbol, position_size_candidates)

        proposed_position_value = v.position_size_share_qty_to_buy[symbol] * buy_price
        proposed_sector_percent = (
            (_sector_value(symbol) + proposed_position_value) / portfolio_value
            if portfolio_value > 0
            else 0
        )

        is_buy_condition_limit_order_percent = (
            True if c.buy_condition_limit_order_percent else DISABLED
        )
        is_buy_condition_kelly_criterion_position_size = (
            kelly_fraction > 0
            if c.buy_condition_kelly_criterion_position_size
            else DISABLED
        )
        if is_buy_condition_kelly_criterion_position_size is False:
            is_buy_condition_kelly_criterion_position_size = UNAVAILABLE

        is_buy_condition_max_total_portfolio_invested_percent = _condition(
            c.buy_condition_max_total_portfolio_invested_percent,
            total_holdings_value + proposed_position_value
            <= c.buy_parameter_max_total_portfolio_invested_percent * portfolio_value,
        )

        is_buy_condition_max_portfolio_percent_per_trade = _condition(
            c.buy_condition_max_portfolio_percent_per_trade,
            proposed_position_value
            <= c.buy_parameter_max_portfolio_percent_per_trade * portfolio_value,
        )

        is_buy_condition_min_symbols_invested = _condition(
            c.buy_condition_min_symbols_invested,
            len(v.unique_portfolio_symbols) < c.buy_parameter_min_symbols_invested,
        )

        is_buy_condition_max_sector_invested_percent = _condition(
            c.buy_condition_max_sector_invested_percent,
            proposed_sector_percent <= c.buy_parameter_max_sector_invested_percent,
        )

        is_buy_condition_pdt_rule = _condition(
            c.buy_condition_pdt_rule,
            not (len(set(v.day_trade_dates)) >= 3 and cash < 25000),
        )

        is_buy_condition_atr_breakout_level_reached = _condition(
            c.buy_condition_atr_breakout_level_reached,
            v.current_price[symbol]
            > (
                indicators["atr_min"].Current.Value
                + (
                    indicators["atr"].Current.Value
                    * c.buy_parameter_atr_breakout_level_multiplier
                )
            ),
        )

        is_buy_condition_ema_crossover = _condition(
            c.buy_condition_ema_crossover,
            indicators["emaShort"].Current.Value > indicators["emaLong"].Current.Value,
        )

        is_buy_condition_ema_distance_widening = _condition(
            c.buy_condition_ema_distance_widening,
            (indicators["emaShort"].Current.Value - indicators["emaLong"].Current.Value)
            > (indicators["emaShort"].Previous.Value - indicators["emaLong"].Previous.Value),
        )

        is_buy_condition_macd_cross_above_signal = _condition(
            c.buy_condition_macd_cross_above_signal,
            indicators["macd"].Current.Value > indicators["macd"].Signal.Current.Value,
        )

        is_buy_condition_reward_risk_ratio = _condition(
            c.buy_condition_reward_risk_ratio,
            (
                v.max_profit_reward_per_share[symbol]
                / v.max_loss_risk_per_share[symbol]
            )
            >= c.buy_parameter_reward_risk_ratio,
        )

        is_buy_condition_rsi_strong = _condition(
            c.buy_condition_rsi_strong,
            indicators["rsi"].Current.Value > c.buy_parameter_rsi_min_threshold,
        )

        is_buy_condition_short_ema_rising = _condition(
            c.buy_condition_short_ema_rising,
            indicators["emaShort"].Current.Value > indicators["emaShort"].Previous.Value,
        )

        is_buy_condition_stochastic_rsi_strong = _condition(
            c.buy_condition_stochastic_rsi_strong,
            indicators["sto"].Current.Value > c.buy_parameter_stochastic_rsi_min_threshold,
        )

        conditions = {
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
            "KellyCriterionPositionSize": is_buy_condition_kelly_criterion_position_size,
        }

        underlying_values = {
            "CurrentPrice": v.current_price[symbol],
            "TakeProfitPrice": v.take_profit_max_price[symbol],
            "StopLossPrice": v.stop_loss_max_price[symbol],
            "BuyPrice": buy_price,
            "PositionSize": v.position_size_share_qty_to_buy[symbol],
            "PositionSizeCandidates": position_size_candidates,
            "ShortEMACurrent": indicators["emaShort"].Current.Value,
            "ShortEMAPrevious": indicators["emaShort"].Previous.Value,
            "LongEMA": indicators["emaLong"].Current.Value,
            "ATR": indicators["atr"].Current.Value,
            "MACDValue": indicators["macd"].Current.Value,
            "MACDSignal": indicators["macd"].Signal.Current.Value,
            "RSI": indicators["rsi"].Current.Value,
            "StochasticRSI": indicators["sto"].Current.Value,
            "CurrentSectorPercent": _sector_percent(symbol),
            "ProposedSectorPercent": proposed_sector_percent,
        }

        parameters = {
            "LimitOrderPercent": c.buy_parameter_limit_order_percent,
            "ATRBreakoutMultiplier": c.buy_parameter_atr_breakout_level_multiplier,
            "MaxPortfolioPercentPerTrade": c.buy_parameter_max_portfolio_percent_per_trade,
            "MaxTotalPortfolioInvestedPercent": c.buy_parameter_max_total_portfolio_invested_percent,
            "RSIMinThreshold": c.buy_parameter_rsi_min_threshold,
            "StochasticRSIMinThreshold": c.buy_parameter_stochastic_rsi_min_threshold,
            "RewardRiskRatio": c.buy_parameter_reward_risk_ratio,
        }

        order_tag = _build_order_tag(symbol, conditions, underlying_values, parameters)

        required_conditions = [
            is_buy_condition_atr_breakout_level_reached,
            is_buy_condition_ema_crossover,
            is_buy_condition_ema_distance_widening,
            is_buy_condition_macd_cross_above_signal,
            is_buy_condition_reward_risk_ratio,
            is_buy_condition_rsi_strong,
            is_buy_condition_short_ema_rising,
            is_buy_condition_stochastic_rsi_strong,
            is_buy_condition_max_total_portfolio_invested_percent,
            is_buy_condition_max_portfolio_percent_per_trade,
            is_buy_condition_min_symbols_invested,
            is_buy_condition_max_sector_invested_percent,
            is_buy_condition_pdt_rule,
        ]

        return all(_condition_passed(value) for value in required_conditions), order_tag

    except Exception as e:
        algorithm.Error(f"Error on shouldBuy: {str(e)}")
        return False, None
