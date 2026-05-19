from AlgorithmImports import *
from shouldBuy import shouldBuy
from shouldSell import shouldSell
import config as c
import variables as v
import json
import os
import charts

EQUITY_LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "equity.jsonl")


def emit_equity_bar(algorithm, path=EQUITY_LOG_PATH):
    """Append one JSON line per bar with timestamp + portfolio equity.

    Failures are swallowed: the equity ledger is observational; a write hiccup
    must not interrupt the trading loop.
    """
    try:
        equity = float(getattr(algorithm.Portfolio, "TotalPortfolioValue", 0.0))
        cash = float(getattr(algorithm.Portfolio, "Cash", 0.0))
        time = getattr(algorithm, "Time", None)
        record = {
            "time": time.isoformat() if hasattr(time, "isoformat") else str(time),
            "equity": equity,
            "cash": cash,
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception:
        return


class OnDataHandler:
    def __init__(self, algorithm):
        self.algorithm = algorithm

    def OnData(self, data):
        try:
            if self.algorithm.IsWarmingUp:
                return

            else:
                emit_equity_bar(self.algorithm)
                self.CancelOldOrders()
                for symbol in v.active_symbols:
                    if symbol in data:
                        bar = data[symbol]
                        if bar is not None and isinstance(bar, (TradeBar, QuoteBar)):

                            indicators = v.indicators.get(symbol, None)
                            if indicators is not None:
                                all_ready = all(indicator.IsReady for indicator in indicators.values())
                                if all_ready:

                                    v.symbol_sector[symbol] = (
                                        self.algorithm.Securities[symbol]
                                        .Fundamentals
                                        .AssetClassification
                                        .MorningstarSectorCode
                                    )
                                    v.current_price[symbol] = data[symbol].Price
                                    v.current_close_price[symbol] = data[symbol].Close

                                    has_open_orders = bool(self.algorithm.Transactions.GetOpenOrders(symbol))
                                    invested = self.algorithm.Portfolio[symbol].Invested
                                    latest_order_ticket = None

                                    if not invested and not has_open_orders:
                                        should_buy, order_tag = shouldBuy(self.algorithm, symbol, data)
                                        if should_buy and v.position_size_share_qty_to_buy.get(symbol, 0) > 0:
                                            latest_order_ticket = self.algorithm.LimitOrder(
                                                symbol,
                                                v.position_size_share_qty_to_buy[symbol],
                                                v.buy_limit_price[symbol],
                                                order_tag,
                                            )
                                            v.latest_order_ticket[symbol] = latest_order_ticket
                                            v.open_order_tickets[symbol] = latest_order_ticket
                                            has_open_orders = True

                                    if invested and not has_open_orders:
                                        should_sell, order_tag = shouldSell(self.algorithm, symbol, data)
                                    else:
                                        should_sell = False

                                    if should_sell:

                                        shares_qty_held = self.algorithm.Portfolio[symbol].Quantity

                                        if v.take_profit_max_price[symbol] == v.take_profit_percent_price[symbol]:
                                            shares_qty_to_sell = max(
                                                1,
                                                round(
                                                    abs(shares_qty_held)
                                                    * c.sell_parameter_take_profit_percent_to_sell
                                                ),
                                            )
                                            latest_order_ticket = self.algorithm.LimitOrder(
                                                symbol,
                                                -shares_qty_to_sell,
                                                v.take_profit_max_price[symbol],
                                                order_tag,
                                            )
                                            v.latest_order_ticket[symbol] = latest_order_ticket
                                            v.open_order_tickets[symbol] = latest_order_ticket
                                        else:
                                            latest_order_ticket = self.algorithm.Liquidate(symbol, order_tag)
                                            v.latest_order_ticket[symbol] = latest_order_ticket
                                            v.open_order_tickets[symbol] = latest_order_ticket

                                    if latest_order_ticket is not None:
                                        debug_message = {
                                            "Type": latest_order_ticket.OrderDirection,
                                            "ID": latest_order_ticket.OrderId,
                                            "Symbol": str(latest_order_ticket.Symbol),
                                            "Quantity": latest_order_ticket.Quantity,
                                            "Status": latest_order_ticket.Status,
                                            "Price": latest_order_ticket.AverageFillPrice,
                                            "Time": str(latest_order_ticket.Time),
                                            "Tag": latest_order_ticket.Tag
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
                                            self.algorithm.Debug(
                                                f"{self.algorithm.Time} - {indicator_name} "
                                                f"not ready for {symbol}. Skipping OnData slice..."
                                            )
                                            continue
                            else:
                                self.algorithm.Error(f"{self.algorithm.Time} - indicators not initialized for {symbol}")
                        else:
                            self.algorithm.Error(f"Received unexpected data type for {symbol}: {type(bar)}. Skipping.")

        except Exception as e:
            self.algorithm.Error(f"Error on OnData: {str(e)}")

    def CancelOldOrders(self):
        try:
            for symbol, order_ticket in list(v.open_order_tickets.items()):

                if order_ticket is not None and not order_ticket.OrderClosed:
                    order_time = self.algorithm.Time  # Current algorithm time
                    order_age = (order_time - order_ticket.Time).total_seconds() / 60  # Age in minutes
                    order_age_minutes = int(order_age)

                    if order_age >= c.max_pending_order_age_minutes:
                        order_ticket.Cancel("Order too old")
                        v.open_order_tickets.pop(symbol, None)
                        self.algorithm.Debug(f"Order {order_ticket.OrderId} for {symbol} cancelled due to timeout")

                    elif order_age_minutes > 0 and order_age_minutes % 15 == 0:
                        self.algorithm.Debug(
                            f"Order still pending: {order_ticket.Symbol}, "
                            f"Order Age: {order_age_minutes} minutes, "
                            "Canceling in "
                            f"{c.max_pending_order_age_minutes - order_age_minutes} minutes..."
                        )

        except Exception as e:
            self.algorithm.Error(f"Error on CancelOldOrders: {str(e)}")
            return False
