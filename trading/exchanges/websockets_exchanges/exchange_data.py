import pandas

from config.cst import *
from tools.data_frame_util import DataFrameUtil


class ExchangeData:

    ORDERS_KEY = "orders"
    TIME_FRAME_CANDLE_TIME = "candle_time"
    CANDLE_LIST = "data_list"
    CANDLE_DATAFRAME = "dataframe"
    TIME_FRAME_HAS_REACH_MAX_CANDLE_COUNT = "reached_max_candle_count"

    _MAX_STORED_CANDLE_COUNT = 1000

    # note: symbol keys are without /
    def __init__(self):
        self.symbol_prices = {}
        self.symbol_tickers = {}
        self.portfolio = {}
        self.orders = {}
        self.is_initialized = {
            self.ORDERS_KEY: False
        }

    def _initialize_price_candles(self, symbol, time_frame, candle_data, candle_dataframe=None):
        if symbol not in self.symbol_prices:
            self.symbol_prices[symbol] = {}
        prices_per_time_frames = self.symbol_prices[symbol]

        # if no data from this timeframe => create new database
        if time_frame not in prices_per_time_frames:
            prices_per_time_frames[time_frame] = {
                self.CANDLE_LIST: candle_data,
                self.CANDLE_DATAFRAME:
                    candle_dataframe if candle_dataframe is not None else
                    DataFrameUtil.candles_array_to_data_frame(candle_data),
                self.TIME_FRAME_HAS_REACH_MAX_CANDLE_COUNT:
                    len(candle_data) >= self._MAX_STORED_CANDLE_COUNT
            }

    def add_price(self, symbol, time_frame, start_candle_time, candle_data):

        # add price only if candles have been initialized bu rest exchange
        if symbol in self.symbol_prices and time_frame in self.symbol_prices[symbol]:
            time_frame_data = self.symbol_prices[symbol][time_frame]

            # add new candle if previous candle is done
            if time_frame_data[self.CANDLE_LIST][-1][PriceIndexes.IND_PRICE_TIME.value] < start_candle_time:

                # remove most ancient candle if max candle count reached
                if time_frame_data[self.TIME_FRAME_HAS_REACH_MAX_CANDLE_COUNT]:
                    time_frame_data[self.CANDLE_LIST].pop(0)
                    time_frame_data[self.CANDLE_DATAFRAME].drop(0, inplace=True)
                    time_frame_data[self.CANDLE_DATAFRAME].reset_index(drop=True, inplace=True)
                elif len(time_frame_data[self.CANDLE_LIST])+1 >= self._MAX_STORED_CANDLE_COUNT:
                    time_frame_data[self.TIME_FRAME_HAS_REACH_MAX_CANDLE_COUNT] = True

                # add new candle
                time_frame_data[self.CANDLE_LIST].append(candle_data)

                # refresh dataframe
                time_frame_data[self.CANDLE_DATAFRAME] = pandas.concat(
                    [time_frame_data[self.CANDLE_DATAFRAME], DataFrameUtil.candles_array_to_data_frame([candle_data])],
                    ignore_index=True)

            # else update current candle
            else:
                time_frame_data[self.CANDLE_LIST][-1] = candle_data
                time_frame_data[self.CANDLE_DATAFRAME][PriceStrings.STR_PRICE_HIGH.value].iloc[-1] = \
                    candle_data[PriceIndexes.IND_PRICE_HIGH.value]
                time_frame_data[self.CANDLE_DATAFRAME][PriceStrings.STR_PRICE_LOW.value].iloc[-1] = \
                    candle_data[PriceIndexes.IND_PRICE_LOW.value]
                time_frame_data[self.CANDLE_DATAFRAME][PriceStrings.STR_PRICE_CLOSE.value].iloc[-1] = \
                    candle_data[PriceIndexes.IND_PRICE_CLOSE.value]
                time_frame_data[self.CANDLE_DATAFRAME][PriceStrings.STR_PRICE_VOL.value].iloc[-1] = \
                    candle_data[PriceIndexes.IND_PRICE_VOL.value]

    def update_portfolio(self, currency, total, available, in_order):
        self.portfolio[currency] = {
            CONFIG_PORTFOLIO_FREE: available,
            CONFIG_PORTFOLIO_USED: in_order,
            CONFIG_PORTFOLIO_TOTAL: total
        }

    def set_ticker(self, symbol, ticker_data):
        self.symbol_tickers[symbol] = ticker_data

    # maybe later add an order remover to free up memory ?
    def upsert_order(self, order_id, ccxt_order):
        self.orders[order_id] = ccxt_order

    def get_all_orders(self, symbol, since, limit):
        return self._select_orders(None, symbol, since, limit)

    def get_open_orders(self, symbol, since, limit):
        return self._select_orders("open", symbol, since, limit)

    def get_candles(self, symbol, time_frame, limit=None, data_frame=True):
        adapted_symbol = self._adapt_symbol(symbol)
        candles_data = self.symbol_prices[adapted_symbol][time_frame.value]
        wanted_candles = candles_data[self.CANDLE_DATAFRAME] if data_frame else candles_data[self.CANDLE_LIST]
        if limit is not None:
            actual_limit = min(limit, len(wanted_candles))
            return wanted_candles[-actual_limit:].reset_index(drop=True), candles_data[self.CANDLE_LIST][-actual_limit:]
        return wanted_candles, candles_data[self.CANDLE_LIST]

    def get_closed_orders(self, symbol, since, limit):
        return self._select_orders("closed", symbol, since, limit)

    def initialize_candles_data(self, symbol, time_frame, symbol_candle_data, symbol_candle_dataframe):
        self._initialize_price_candles(self._adapt_symbol(symbol), time_frame.value,
                                       symbol_candle_data, symbol_candle_dataframe)

    def candles_are_initialized(self, symbol, time_frame):
        adapted_symbol = self._adapt_symbol(symbol)
        return adapted_symbol in self.symbol_prices and time_frame.value in self.symbol_prices[adapted_symbol]

    # TODO temporary method awaiting for symbol "/" reconstruction in ws
    @staticmethod
    def _adapt_symbol(symbol):
        return symbol.replace("/", "")

    def _select_orders(self, state, symbol, since, limit):
        orders = [
            order
            for order in self.orders.values()
            if (
                    (state is None or order["status"] == state) and
                    (symbol is None or (symbol and order["symbol"] == symbol)) and
                    (since is None or (since and order['timestamp'] < since))
            )
        ]
        if limit is not None:
            return orders[0:limit]
        else:
            return orders
