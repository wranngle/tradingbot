# Begin OnOrderEvent.py

from AlgorithmImports import *
import config as c
import variables as v
from sectorAnalysis import sectorAnalysis

class OnOrderEventHandler:
    def __init__(self, algorithm):
        self.algorithm = algorithm

    def OnOrderEvent(self, orderEvent):# Runs for every order placed.
        try:
            symbol = orderEvent.Symbol
            fill_price = orderEvent.FillPrice
            fill_qty = orderEvent.FillQuantity
            v.current_date = self.algorithm.Time.date()
            direction = 'buy' if orderEvent.Direction == OrderDirection.Buy else 'sell'
            v.average_buy_price[symbol] = self.algorithm.Portfolio[orderEvent.Symbol].AveragePrice

            if orderEvent.Status == OrderStatus.Submitted:
                self.algorithm.Debug(f"Order Submitted: {symbol} - ID: {orderEvent.OrderId} - Qty: {fill_qty} * ${fill_price} = ${fill_qty * fill_price}")

            if orderEvent.Status == OrderStatus.Filled:

                # Update Sector Details
                v.unique_portfolio_sectors = sectorAnalysis.getUniquePortfolioSectors(self)
                    # Update list of unique sectors in portfolio.

                v.sector_portfolio_value[symbol] = sectorAnalysis.calculatePortfolioValueForSector(self, self.algorithm.Securities[symbol].Fundamentals.AssetClassification.MorningstarSectorCode)
                    # Update new portfolio value for this order's sector.
                
                for sector in v.unique_portfolio_sectors:
                    v.portfolio_percent_per_sector[sector] = v.sector_portfolio_value[sector] / self.algorithm.Portfolio.TotalPortfolioValue
                    # Update the portfolio percents for each sector.
                    
                v.biggest_portfolio_sector = max(v.portfolio_percent_per_sector, key=v.portfolio_percent_per_sector.get)
                    # Update sector with highest portfolio percentage.

                v.unique_portfolio_symbols.clear()        
                v.unique_portfolio_symbols = {s for s, holding in self.algorithm.Portfolio.items() if holding.Invested}
                self.algorithm.Debug(f"Updated unique portfolio symbols: str({v.unique_portfolio_symbols})")
                    # Update list of unique portfolio symbols.

                # Update Day Trade Counter
                if v.current_date != v.last_increment_day:
                    v.daily_transactions.clear()
                    v.last_increment_day = v.current_date
                    # Update list of all today's transactions for the symbol
                    
                if symbol not in v.daily_transactions:
                    v.daily_transactions[symbol] = {'buy': 0, 'sell': 0}
                    # If this symbol wasn't already traded today, set its buy/sell count to 0.

                v.daily_transactions[symbol][direction] += 1
                    # Increment this symbol's buy/sell count for today.

                if v.daily_transactions[symbol]['buy'] > 0 and v.daily_transactions[symbol]['sell'] > 0:
                    v.day_trade_counter += 1
                    v.day_trade_dates.append(v.current_date)
                    # If both a buy trade and a sell trade were both detected today, count today's date as a day trading date.

                v.max_symbol_price = (
                    self.algorithm.Portfolio.TotalPortfolioValue * c.symbol_filter_parameter_max_symbol_price_portfolio_percent
                    if c.symbol_filter_condition_max_symbol_price_portfolio_percent
                    else 0.95 * self.algorithm.Portfolio.TotalPortfolioValue
                ) # Set max price of symbols in the universe to what's defined in config.py, if not then 95%.

                if orderEvent.Direction == OrderDirection.Buy:
                    self.algorithm.Debug(f"---- BUY Order Filled: {symbol} - ID: {orderEvent.OrderId} - Qty: {fill_qty} * ${fill_price} = ${fill_qty * fill_price}")

                elif orderEvent.Direction == OrderDirection.Sell:
                    self.algorithm.Debug(f"---- SELL Order Filled: {symbol} - ID: {orderEvent.OrderId} - Qty: {fill_qty} * ${fill_price} = ${fill_qty * fill_price}")

                    # Update Kelly Criterion
                        # Calculate profit or loss
                    profit = (orderEvent.FillPrice - v.average_buy_price[symbol]) * orderEvent.FillQuantity
                    if profit > 0:
                        # Update profit
                        v.trade_win_count += 1
                        v.total_profit += profit
                    else:
                        # Update loss
                        v.trade_loss_count += 1
                        v.total_loss += abs(profit)

                        # Update win probability and ratio
                    total_trades = v.trade_win_count + v.trade_loss_count
                    if total_trades > 0:
                        v.win_probability = v.trade_win_count / total_trades
                        v.win_loss_ratio = v.total_profit / v.total_loss if v.total_loss != 0 else float('inf')  # 'inf' if no losses
                        v.kelly_criterion = v.win_probability - ((1 - v.win_probability) / v.win_loss_ratio)
                        self.algorithm.Debug(f"Updated Win Probability: {v.win_probability:.2f}, Win/Loss Ratio: {v.win_loss_ratio:.2f}, Kelly Criterion: {v.kelly_criterion:.2f}")
                            # Calculate Kelly Criterion
                        
        except Exception as e:
            self.algorithm.Error(f"Error in OnOrderEvent for {orderEvent.OrderId}: {str(e)}")

# End OnOrderEvent.py