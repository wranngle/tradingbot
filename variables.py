# This module stores dynamic, non-configurable variables used across the algorithm.

import collections

# Algorithm Initialization
day_trade_counter = 0  # Counts day trades
day_trade_dates = collections.deque(maxlen=5)  # Dates of last 5 day trades
last_increment_day = None  # Last day warmup counter was incremented
indicator_warmup_counter = {}  # Tracks warmup progress
daily_transactions = {}  # Track daily buys and sells for each security
current_date = {}

current_price = {}
current_close_price = {}
indicators = {}
consolidators = {}
position_size_chart = {}

# Buy Conditions
buy_limit_price = {} # Updated with each OnData slice through shouldBuy.

# Sell Conditions
max_loss_risk_per_share = {}
max_profit_reward_per_share = {}
stop_loss_atr_price = {}
stop_loss_fib_atr_price = {}
stop_loss_fibonacci_prices = {}
stop_loss_max_price = {}
stop_loss_percent_price = {}
stop_loss_trailing_price = {}
take_profit_atr_price = {}
take_profit_fib_atr_price = {}
take_profit_fibonacci_prices = {}
take_profit_max_price = {}
take_profit_percent_price = {}
take_profit_trailing_price = {}

# Symbols
unique_portfolio_symbols = set()
unique_portfolio_sectors = set()
symbol_history = {}
sector_portfolio_value = {}
symbol_counts_per_sector = {}
symbol_sector = {}
portfolio_percent_per_sector = {}
biggest_portfolio_sector = {}
max_symbol_price = 0
active_symbols = set()

# Orders
order_ticket = None
open_order_tickets = {}
position_size_share_qty_to_buy = {}
latest_order_ticket = {}

# Profit/Loss Sell Results
average_buy_price = {}
trade_win_count = 0
trade_loss_count = 0
total_profit = 0
total_loss = 0
kelly_criterion = 0
win_probability = 0
win_loss_ratio = 0
