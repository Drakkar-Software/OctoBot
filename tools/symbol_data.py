class SymbolCandles:
    def __init__(self, symbol, time_frame):
        self.symbol = symbol
        self.time_frame = time_frame


class SymbolOrderBook:
    def __init__(self, symbol):
        self.symbol = symbol

































    def add_price(self, symbol, time_frame, start_candle_time, candle_data):
        # add price only if candles have been initialized by rest exchange
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

    def initialize_candles_data(self, symbol, time_frame, symbol_candle_data, symbol_candle_data_frame):
        self._initialize_price_candles(self._adapt_symbol(symbol), time_frame.value,
                                       symbol_candle_data, symbol_candle_data_frame)

    def set_ticker(self, symbol, ticker_data):
        self.symbol_tickers[symbol] = ticker_data

    # select methods
    def candles_are_initialized(self, symbol, time_frame):
        adapted_symbol = self._adapt_symbol(symbol)
        return adapted_symbol in self.symbol_prices and time_frame.value in self.symbol_prices[adapted_symbol]

    def get_candles(self, symbol, time_frame, limit=None, data_frame=True):
        adapted_symbol = self._adapt_symbol(symbol)
        candles_data = self.symbol_prices[adapted_symbol][time_frame.value]
        wanted_candles = candles_data[self.CANDLE_DATAFRAME] if data_frame else candles_data[self.CANDLE_LIST]
        if limit is not None:
            actual_limit = min(limit, len(wanted_candles))
            return wanted_candles[-actual_limit:].reset_index(drop=True) if data_frame \
                else wanted_candles[-actual_limit:]
        return wanted_candles

    def _initialize_price_candles(self, symbol, time_frame, candle_data, candle_data_frame=None):
        if symbol not in self.symbol_prices:
            self.symbol_prices[symbol] = {}
        prices_per_time_frames = self.symbol_prices[symbol]

        # if no data from this timeframe => create new database
        if time_frame not in prices_per_time_frames:
            prices_per_time_frames[time_frame] = {
                self.CANDLE_LIST: candle_data,
                self.CANDLE_DATAFRAME:
                    candle_data_frame if candle_data_frame is not None else
                    DataFrameUtil.candles_array_to_data_frame(candle_data),
                self.TIME_FRAME_HAS_REACH_MAX_CANDLE_COUNT:
                    len(candle_data) >= self._MAX_STORED_CANDLE_COUNT
            }

    # TODO temporary method awaiting for symbol "/" reconstruction in ws
    @staticmethod
    def _adapt_symbol(symbol):
        return symbol.replace("/", "")