from AlgorithmImports import *


def SetStartDate(algorithm_instance):
    algorithm_instance.SetStartDate(2023, 10, 1)


def SetEndDate(algorithm_instance):
    algorithm_instance.SetEndDate(2024, 3, 23)


starting_cash = 1000


def SetCash(algorithm_instance):
    algorithm_instance.SetCash(starting_cash)


finest_resolution = Resolution.Daily
warmup_period = 30
max_pending_order_age_minutes = 15


def SetWarmUp(algorithm_instance):
    algorithm_instance.SetWarmUp(warmup_period, finest_resolution)


def SetBrokerageModel(algorithm_instance):
    algorithm_instance.SetBrokerageModel(BrokerageName.TradierBrokerage, AccountType.Cash)


symbol_filter_condition_extended_market_hours = False
symbol_filter_condition_min_price = True
symbol_filter_condition_max_symbol_price_portfolio_percent = True
symbol_filter_condition_min_pe_ratio = True
symbol_filter_condition_max_pe_ratio = True
symbol_filter_condition_min_revenue_growth_percent = True
symbol_filter_condition_blacklist = False
symbol_filter_condition_static_universe = True

symbol_filter_parameter_min_price = 3.00
symbol_filter_parameter_max_symbol_price_portfolio_percent = 0.10
symbol_filter_parameter_min_pe_ratio = 0
symbol_filter_parameter_max_pe_ratio = 20
symbol_filter_parameter_min_revenue_growth_percent = 0
symbol_filter_parameter_blacklist = [
    "CMCSA",
    "VZ",
    "NSRGY",
    "BAC",
    "SIVB",
    "SBNY",
    "FRC",
    "CS",
    "BTI",
    "NWG",
    "ILMN",
    "GS",
    "DB",
    "TMUS",
]
symbol_filter_parameter_static_universe = ["TSLA"]

buy_condition_limit_order_percent = True
buy_condition_atr_breakout_level_reached = False
buy_condition_ema_crossover = True
buy_condition_ema_distance_widening = False
buy_condition_macd_cross_above_signal = False
buy_condition_reward_risk_ratio = False
buy_condition_rsi_strong = False
buy_condition_short_ema_rising = False
buy_condition_stochastic_rsi_strong = False
buy_condition_max_portfolio_percent_per_trade = False
buy_condition_max_total_portfolio_invested_percent = False
buy_condition_min_symbols_invested = False
buy_condition_max_sector_invested_percent = False
buy_condition_kelly_criterion_position_size = True
buy_condition_pdt_rule = False

buy_parameter_limit_order_percent = 0.98
buy_parameter_atr_breakout_level_multiplier = 1.5
buy_parameter_atr_low_period = 24
buy_parameter_atr_periods = 14
buy_parameter_ema_short_periods = 9
buy_parameter_ema_long_periods = 14
buy_parameter_reward_risk_ratio = 2
buy_parameter_rsi_periods = 14
buy_parameter_rsi_min_threshold = 50
buy_parameter_stochastic_rsi_periods = 14
buy_parameter_stochastic_rsi_min_threshold = 0.5
buy_parameter_max_total_portfolio_invested_percent = 0.95
buy_parameter_max_portfolio_percent_per_trade = 0.50
buy_parameter_min_symbols_invested = 5
buy_parameter_max_sector_invested_percent = 0.65
buy_parameter_lost_it_all = 50

sell_condition_stop_loss_atr_price = True
sell_condition_stop_loss_fibonacci_atr_price = True
sell_condition_stop_loss_percent = True
sell_condition_stop_loss_trailing_percent = True
sell_condition_take_profit_atr_price = True
sell_condition_take_profit_fibonacci_atr_price = True
sell_condition_take_profit_percent = True
sell_condition_take_profit_trailing_percent = True
sell_condition_macd_cross_below_signal = False
sell_condition_rsi_weak = False

sell_parameter_stop_loss_fibonacci_retracement_levels = [0.236, 0.382, 0.618]
sell_parameter_stop_loss_percent = 0.20
sell_parameter_stop_loss_price_atr_multiplier = 2
sell_parameter_stop_loss_trailing_percent = 0.10
sell_parameter_take_profit_fibonacci_retracement_levels = [0.236, 0.382, 0.618]
sell_parameter_take_profit_percent = 0.20
sell_parameter_take_profit_percent_to_sell = 0.50
sell_parameter_take_profit_price_atr_multiplier = 2
sell_parameter_take_profit_trailing_percent = 0.10
sell_parameter_rsi_max_threshold = 30
