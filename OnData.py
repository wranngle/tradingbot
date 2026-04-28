# Begin OnData.py

from AlgorithmImports import *
from shouldBuy import shouldBuy
from shouldSell import shouldSell
import config as c
import variables as v
import json
import charts

class OnDataHandler:
    def __init__(self, algorithm):
        self.algorithm = algorithm

    def OnData(self, data):
    # Runs upon receipt of every bar/candle for the filtered symbols
        try:
            # Log warm-up progress every 10 iterations
            if self.algorithm.IsWarmingUp:
                pass
                    
            else:               
                for symbol in v.active_symbols:
                    if symbol in data:                        
                        bar = data[symbol]
                        if bar is not None and isinstance(bar, (TradeBar, QuoteBar)):

                            # Check if the indicators for the symbol are ready
                            indicators = v.indicators.get(symbol, None)
                            if indicators is not None:
                                all_ready = all(indicator.IsReady for indicator in indicators.values())
                                if all_ready:

                                    v.symbol_sector[symbol] = self.algorithm.Securities[symbol].Fundamentals.AssetClassification.MorningstarSectorCode
                                    v.current_price[symbol] = data[symbol].Price
                                    v.current_close_price[symbol] = data[symbol].Close
                                
                                    # Check for Buy condition
                                    should_buy, order_tag = shouldBuy(self.algorithm, symbol, data)
                                    if should_buy:
                                        v.latest_order_ticket[symbol] = self.algorithm.LimitOrder(symbol, round(v.position_size_share_qty_to_buy[symbol]), v.buy_limit_price[symbol], order_tag)
                                        v.open_order_tickets[symbol] = v.latest_order_ticket[symbol]

                                    # Check for Sell condition
                                    should_sell, order_tag = shouldSell(self.algorithm, symbol, data)
                                    if self.algorithm.Portfolio[symbol].Invested and not self.algorithm.Transactions.GetOpenOrders(symbol) and not should_buy and should_sell:
                                        
                                        shares_qty_held = self.algorithm.Portfolio[symbol].Quantity
                                            # Get the total shares held for this symbol.
                                        
                                        if v.take_profit_max_price[symbol] == v.take_profit_percent_price[symbol]:
                                            shares_qty_to_sell = round(shares_qty_held * c.sell_parameter_take_profit_percent) 
                                            v.latest_order_ticket[symbol] = self.algorithm.LimitOrder(symbol, -round(shares_qty_to_sell), v.take_profit_max_price[symbol], order_tag)
                                                # In case the price target is the Fixed Take Profit %, only sell half.
                                            v.open_order_tickets[symbol]  = v.latest_order_ticket[symbol]
                                        else:
                                            v.latest_order_ticket[symbol] = self.algorithm.Liquidate(symbol, order_tag)
                                            v.open_order_tickets[symbol]  = v.latest_order_ticket[symbol]
                                                # Otherwise, sell the entire position.   

                                    if should_buy or should_sell:
                                        if symbol in v.latest_order_ticket and v.latest_order_ticket is not None:
                                            debug_message = {
                                                "Type": v.latest_order_ticket[symbol].OrderDirection,
                                                "ID": v.latest_order_ticket[symbol].OrderId,
                                                "Symbol": str(v.latest_order_ticket[symbol].Symbol),
                                                "Quantity": v.latest_order_ticket[symbol].Quantity,
                                                "Status": v.latest_order_ticket[symbol].Status,
                                                "Price": v.latest_order_ticket[symbol].AverageFillPrice,
                                                "Time": str(v.latest_order_ticket[symbol].Time),
                                                "Tag": v.latest_order_ticket[symbol].Tag
                                            }                     
                                            self.algorithm.Debug("ORDER SUBMITTED:")
                                            self.algorithm.Debug(json.dumps(debug_message))
                                    
                                    self.algorithm.Debug(f"Plotting indicators for {symbol}")
                                    try:
                                        charts.plotIndicators(self.algorithm, symbol, indicators)
                                    except Exception as e:
                                        self.algorithm.Error(f"Error in plotIndicators for {symbol}: {str(e)}")
                                    
                                else:
                                    for indicator_name, indicator in indicators.items():
                                        if not indicator.IsReady:
                                            self.algorithm.Debug(f"{self.algorithm.Time} - {indicator_name} not ready for {symbol}. Skipping OnData slice...")
                                            continue
                            else: 
                                self.algorithm.Error(f"{self.algorithm.Time} - {indicator_name} not initialized for {symbol}")
                        else:
                            self.algorithm.Error(f"Received unexpected data type for {symbol}: {type(bar)}. Skipping.")                            

        except Exception as e:
            self.algorithm.Error(f"Error on OnData: {str(e)}")  

    def CancelOldOrders(self):
        try:
            for symbol, order_ticket in v.open_order_tickets.items():
                
                if order_ticket is not None and not order_ticket.OrderClosed:
                    order_time = self.algorithm.Time  # Current algorithm time
                    order_age = (order_time - order_ticket.Time).total_seconds() / 60  # Age in minutes
                    order_age_minutes = int(order_age)

                    if order_age > c.max_pending_order_age_minutes:
                        order_ticket.Cancel("Order too old")
                        self.algorithm.Debug(f"Order {order_ticket.OrderId} for {symbol} cancelled due to timeout")

                    # Log unfilled orders periodically (every 15 minutes of age).
                    # Compare on the integer-minute bucket so float drift doesn't skip the check.
                    elif order_age_minutes > 0 and order_age_minutes % 15 == 0:
                        self.algorithm.Debug(f"Order still pending: {order_ticket.Symbol}, Order Age: {order_age_minutes} minutes, Canceling in {c.max_pending_order_age_minutes - order_age_minutes} minutes...")
        
        except Exception as e:
            self.algorithm.Error(f"Error on HandleTradeOutcome: {str(e)}") 
            return False
    


# End OnData.py