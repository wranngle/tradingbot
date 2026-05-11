from AlgorithmImports import *
import config as c
import variables as v
from sectorAnalysis import sectorAnalysis

class OnOrderEventHandler:
    def __init__(self, algorithm):
        self.algorithm = algorithm

    def _clearClosedTicket(self, symbol, status):
        terminal_statuses = {OrderStatus.Filled, OrderStatus.Canceled}
        invalid_status = getattr(OrderStatus, "Invalid", None)
        if invalid_status is not None:
            terminal_statuses.add(invalid_status)

        if status in terminal_statuses:
            v.open_order_tickets.pop(symbol, None)

    def OnOrderEvent(self, orderEvent):
        try:
            symbol = orderEvent.Symbol
            fill_price = orderEvent.FillPrice
            fill_qty = orderEvent.FillQuantity
            v.current_date = self.algorithm.Time.date()
            direction = 'buy' if orderEvent.Direction == OrderDirection.Buy else 'sell'

            if orderEvent.Status == OrderStatus.Submitted:
                self.algorithm.Debug(
                    f"Order Submitted: {symbol} - ID: {orderEvent.OrderId} - "
                    f"Qty: {fill_qty} * ${fill_price} = ${fill_qty * fill_price}"
                )

            self._clearClosedTicket(symbol, orderEvent.Status)

            if orderEvent.Status == OrderStatus.Filled:
                v.unique_portfolio_sectors = sectorAnalysis.getUniquePortfolioSectors(self.algorithm)

                sector = (
                    self.algorithm.Securities[symbol]
                    .Fundamentals
                    .AssetClassification
                    .MorningstarSectorCode
                )
                v.sector_portfolio_value[sector] = (
                    sectorAnalysis.calculatePortfolioValueForSector(self.algorithm, sector)
                )

                v.portfolio_percent_per_sector = {}
                for portfolio_sector in v.unique_portfolio_sectors:
                    sector_value = sectorAnalysis.calculatePortfolioValueForSector(
                        self.algorithm,
                        portfolio_sector,
                    )
                    v.portfolio_percent_per_sector[portfolio_sector] = (
                        sector_value
                        / self.algorithm.Portfolio.TotalPortfolioValue
                        if self.algorithm.Portfolio.TotalPortfolioValue > 0
                        else 0
                    )

                v.biggest_portfolio_sector = (
                    max(v.portfolio_percent_per_sector, key=v.portfolio_percent_per_sector.get)
                    if v.portfolio_percent_per_sector else None
                )

                if hasattr(self.algorithm.Portfolio, "items"):
                    portfolio_items = self.algorithm.Portfolio.items()
                else:
                    portfolio_items = (
                        (s, self.algorithm.Portfolio[s])
                        for s in self.algorithm.Portfolio.Keys
                    )
                v.unique_portfolio_symbols = {
                    s for s, holding in portfolio_items if holding.Invested
                }
                self.algorithm.Debug(f"Updated unique portfolio symbols: str({v.unique_portfolio_symbols})")

                if v.current_date != v.last_increment_day:
                    v.daily_transactions.clear()
                    v.last_increment_day = v.current_date

                if symbol not in v.daily_transactions:
                    v.daily_transactions[symbol] = {'buy': 0, 'sell': 0}

                v.daily_transactions[symbol][direction] += 1

                if v.daily_transactions[symbol]['buy'] > 0 and v.daily_transactions[symbol]['sell'] > 0:
                    if not v.daily_transactions[symbol].get('day_trade_counted'):
                        v.day_trade_counter += 1
                        v.day_trade_dates.append(v.current_date)
                        v.daily_transactions[symbol]['day_trade_counted'] = True

                v.max_symbol_price = (
                    self.algorithm.Portfolio.TotalPortfolioValue
                    * c.symbol_filter_parameter_max_symbol_price_portfolio_percent
                    if c.symbol_filter_condition_max_symbol_price_portfolio_percent
                    else 0.95 * self.algorithm.Portfolio.TotalPortfolioValue
                )

                if orderEvent.Direction == OrderDirection.Buy:
                    v.average_buy_price[symbol] = self.algorithm.Portfolio[orderEvent.Symbol].AveragePrice
                    self.algorithm.Debug(
                        f"---- BUY Order Filled: {symbol} - ID: {orderEvent.OrderId} - "
                        f"Qty: {fill_qty} * ${fill_price} = ${fill_qty * fill_price}"
                    )

                elif orderEvent.Direction == OrderDirection.Sell:
                    self.algorithm.Debug(
                        f"---- SELL Order Filled: {symbol} - ID: {orderEvent.OrderId} - "
                        f"Qty: {fill_qty} * ${fill_price} = ${fill_qty * fill_price}"
                    )

                    average_buy_price = v.average_buy_price.get(
                        symbol,
                        self.algorithm.Portfolio[orderEvent.Symbol].AveragePrice,
                    )
                    profit = (orderEvent.FillPrice - average_buy_price) * abs(orderEvent.FillQuantity)
                    if profit > 0:
                        v.trade_win_count += 1
                        v.total_profit += profit
                    else:
                        v.trade_loss_count += 1
                        v.total_loss += abs(profit)

                    total_trades = v.trade_win_count + v.trade_loss_count
                    if total_trades > 0:
                        v.win_probability = v.trade_win_count / total_trades
                        v.win_loss_ratio = v.total_profit / v.total_loss if v.total_loss != 0 else float('inf')
                        v.kelly_criterion = v.win_probability - ((1 - v.win_probability) / v.win_loss_ratio)
                        self.algorithm.Debug(
                            f"Updated Win Probability: {v.win_probability:.2f}, "
                            f"Win/Loss Ratio: {v.win_loss_ratio:.2f}, "
                            f"Kelly Criterion: {v.kelly_criterion:.2f}"
                        )

        except Exception as e:
            self.algorithm.Error(f"Error in OnOrderEvent for {orderEvent.OrderId}: {str(e)}")
