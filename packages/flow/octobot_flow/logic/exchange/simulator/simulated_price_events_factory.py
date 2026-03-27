import decimal
import typing

import octobot_commons.enums as commons_enums
import octobot_commons.logging as commons_logging

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchange_data.recent_trades.recent_trades_manager as recent_trades_manager_import
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.exchanges.util.exchange_data as exchange_data_import

import octobot_flow.entities as entities_import


class SimulatedPriceEventsFactory:

    def __init__(
        self,
        simulated_exchange_manager: trading_exchanges.ExchangeManager,
    ) -> None:
        self._simulated_exchange_manager = simulated_exchange_manager

    def push_mark_price_and_recent_trades_updates(
        self,
        account_elements: entities_import.ReferenceExchangeAccountElements,
        fetched_exchange_data: entities_import.FetchedExchangeData,
    ) -> None:
        symbols = self._symbols_for_mark_price_updates(
            account_elements.orders.open_orders
        )
        markets = fetched_exchange_data.public_data.markets
        for symbol in symbols:
            if ticker := fetched_exchange_data.public_data.tickers.get(symbol):
                if close_price := ticker.get(
                    trading_enums.ExchangeConstantsTickersColumns.CLOSE.value
                ):
                    self._simulated_exchange_manager.get_symbol_data(symbol).handle_mark_price_update(
                        decimal.Decimal(str(close_price)),
                        trading_enums.MarkPriceSources.TICKER_CLOSE_PRICE.value,
                        reset_mark_price_from_other_sources=True,
                    )
                else:
                    self._logger().error(
                        "SimulatedPriceEventsResolver: ticker for %s has no close, skip mark price",
                        symbol,
                    )
            else:
                self._logger().error(
                    "SimulatedPriceEventsResolver: no ticker for %s, skip mark price "
                    "(simulated fills may miss)",
                    symbol,
                )

            if chosen_market := self._pick_shortest_timeframe_market(markets, symbol):
                if trades := self._synthetic_recent_trades_from_ohlcv_market(
                    chosen_market, symbol, self._simulated_exchange_manager.exchange
                ):
                    self._simulated_exchange_manager.get_symbol_data(symbol).handle_recent_trade_update(
                        trades, replace_all=False
                    )
            else:
                self._logger().info(
                    "No eligible OHLCV market for %s, skip synthetic recent trades",
                    symbol,
                )

    @staticmethod
    def _pick_shortest_timeframe_market(
        markets: list[exchange_data_import.MarketDetails],
        symbol: str,
    ) -> typing.Optional[exchange_data_import.MarketDetails]:
        eligible: list[tuple[int, str, exchange_data_import.MarketDetails]] = []
        for market in markets:
            if market.symbol != symbol:
                continue
            if not market.time_frame or not market.time or not market.close:
                continue
            if len(market.time) != len(market.close):
                continue
            try:
                time_frame_enum = commons_enums.TimeFrames(market.time_frame)
                timeframe_minutes = commons_enums.TimeFramesMinutes[time_frame_enum]
            except (ValueError, KeyError):
                continue
            eligible.append((timeframe_minutes, market.time_frame, market))
        if not eligible:
            return None
        eligible.sort(key=lambda eligible_entry: (eligible_entry[0], eligible_entry[1]))
        return eligible[0][2]

    @staticmethod
    def _synthetic_recent_trades_from_ohlcv_market(
        market: exchange_data_import.MarketDetails,
        symbol: str,
        exchange: trading_exchanges.AbstractExchange,
    ) -> list[dict]:
        recent_candles_window = min(
            len(market.time),
            recent_trades_manager_import.RecentTradesManager.MAX_RECENT_TRADES_COUNT,
        )
        recent_times = market.time[-recent_candles_window:]
        recent_closes = market.close[-recent_candles_window:]
        high_low_lists_aligned = (
            len(market.high) == len(market.close)
            and len(market.low) == len(market.close)
        )
        recent_highs = (
            market.high[-recent_candles_window:] if high_low_lists_aligned else ()
        )
        recent_lows = (
            market.low[-recent_candles_window:] if high_low_lists_aligned else ()
        )
        time_frame_enum = commons_enums.TimeFrames(market.time_frame)
        timeframe_seconds = commons_enums.TimeFramesMinutes[time_frame_enum] * 60
        order_columns = trading_enums.ExchangeConstantsOrderColumns
        trades: list[dict] = []
        for candle_index, candle_time in enumerate(recent_times):
            uniformized_open_timestamp = exchange.get_uniformized_timestamp(candle_time)
            trade_timestamp = int(uniformized_open_timestamp) + timeframe_seconds
            close_price = recent_closes[candle_index]
            if high_low_lists_aligned:
                high_price = recent_highs[candle_index]
                low_price = recent_lows[candle_index]
                if high_price != close_price or low_price != close_price:
                    for trade_role_suffix, price in (
                        ("low", low_price),
                        ("high", high_price),
                    ):
                        trades.append({
                            order_columns.PRICE.value: price,
                            order_columns.TIMESTAMP.value: trade_timestamp,
                            order_columns.SYMBOL.value: symbol,
                            order_columns.EXCHANGE_TRADE_ID.value: (
                                f"sim_ohlcv:{symbol}:{market.time_frame}:"
                                f"{candle_time}:{candle_index}:{trade_role_suffix}"
                            ),
                        })
                    continue
            trades.append({
                order_columns.PRICE.value: close_price,
                order_columns.TIMESTAMP.value: trade_timestamp,
                order_columns.SYMBOL.value: symbol,
                order_columns.EXCHANGE_TRADE_ID.value: (
                    f"sim_ohlcv:{symbol}:{market.time_frame}:{candle_time}:{candle_index}"
                ),
            })
        return trades

    @staticmethod
    def _symbols_for_mark_price_updates(open_orders: list[dict]) -> list[str]:
        symbols: set[str] = set()
        for order in open_orders:
            storage = order.get(trading_constants.STORAGE_ORIGIN_VALUE, order)
            order_symbol = storage.get(
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value
            )
            if order_symbol:
                symbols.add(order_symbol)
        return list(symbols)

    def _logger(self) -> commons_logging.BotLogger:
        return commons_logging.get_logger(self.__class__.__name__)
