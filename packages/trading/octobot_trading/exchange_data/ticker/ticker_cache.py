import typing
import cachetools

import octobot_commons.constants
import octobot_commons.symbols
import octobot_commons.logging


class TickerCache:

    def __init__(self, ttl: float, maxsize: int):
        # direct cache
        self._ALL_TICKERS_BY_EXCHANGE_KEY: cachetools.TTLCache[str, dict[str, dict[str, float]]] = cachetools.TTLCache(
            maxsize=maxsize, ttl=ttl
        )

        # indirect caches:
        # - synchronized with _ALL_TICKERS_BY_EXCHANGE_KEY
        # BTCUSDT => BTC/USDT
        self._ALL_PARSED_SYMBOLS_BY_MERGED_SYMBOLS_BY_EXCHANGE_KEY: dict[str, dict[str, octobot_commons.symbols.Symbol]] = {}
        # BTCUSDT => BTC/USDT + BTCUSDT => BTC/USDT:USDT
        self._ALL_PARSED_SYMBOLS_BY_FUTURE_MERGED_SYMBOLS_BY_EXCHANGE_KEY: dict[str, dict[str, octobot_commons.symbols.Symbol]] = {}

    def is_valid_symbol(self, exchange_name: str, exchange_type: str, sandboxed: bool, symbol: str) -> bool:
        try:
            # will raise if symbol is missing (therefore invalid)
            self._ALL_TICKERS_BY_EXCHANGE_KEY[ # pylint: disable=expression-not-assigned
                self.get_exchange_key(exchange_name, exchange_type, sandboxed)
            ][symbol]
            return True
        except KeyError:
            return False

    def get_all_tickers(
        self, exchange_name: str, exchange_type: str, sandboxed: bool, 
        default: typing.Optional[dict[str, dict[str, float]]] = None
    ) -> typing.Optional[dict[str, dict[str, float]]]:
        return self._ALL_TICKERS_BY_EXCHANGE_KEY.get(self.get_exchange_key(exchange_name, exchange_type, sandboxed), default)

    def has_ticker_data(self, exchange_name: str, exchange_type: str, sandboxed: bool) -> bool:
        return self.get_exchange_key(exchange_name, exchange_type, sandboxed) in self._ALL_TICKERS_BY_EXCHANGE_KEY

    def get_all_parsed_symbols_by_merged_symbols(
        self, exchange_name: str, exchange_type: str, sandboxed: bool, default=None
    ) -> typing.Optional[dict[str, octobot_commons.symbols.Symbol]]:
        # populated by set_all_tickers
        # WARNING: does not expire when tickers expire: use has_ticker_data to check if cache is up-to-date
        if exchange_type == octobot_commons.constants.CONFIG_EXCHANGE_FUTURE:
            return self._ALL_PARSED_SYMBOLS_BY_FUTURE_MERGED_SYMBOLS_BY_EXCHANGE_KEY.get(
                    self.get_exchange_key(exchange_name, exchange_type, sandboxed), default
                )
        return self._ALL_PARSED_SYMBOLS_BY_MERGED_SYMBOLS_BY_EXCHANGE_KEY.get(
            self.get_exchange_key(exchange_name, exchange_type, sandboxed), default
        )

    def set_all_tickers(
        self, exchange_name: str, exchange_type: str, sandboxed: bool, tickers: dict, replace_all: bool = True
    ):
        sandbox = " sandbox" if sandboxed else ""
        key = self.get_exchange_key(exchange_name, exchange_type, sandboxed)
        merged_tickers = tickers if replace_all else {
            **self._ALL_TICKERS_BY_EXCHANGE_KEY.get(key, {}), **tickers
        }
        octobot_commons.logging.get_logger(self.__class__.__name__).info(
            f"Refreshed {len(tickers)} ({len(tickers)})/{len(merged_tickers)}) tickers cache for {exchange_name} {exchange_type}{sandbox}"
        )
        self._ALL_TICKERS_BY_EXCHANGE_KEY[key] = merged_tickers
        self._ALL_PARSED_SYMBOLS_BY_MERGED_SYMBOLS_BY_EXCHANGE_KEY[key] = {
            octobot_commons.symbols.parse_symbol(symbol).merged_str_symbol(market_separator=""):
                octobot_commons.symbols.parse_symbol(symbol)
            for symbol in merged_tickers
        }
        if exchange_type == octobot_commons.constants.CONFIG_EXCHANGE_FUTURE:
            self._ALL_PARSED_SYMBOLS_BY_FUTURE_MERGED_SYMBOLS_BY_EXCHANGE_KEY[key] = {
                **self._ALL_PARSED_SYMBOLS_BY_MERGED_SYMBOLS_BY_EXCHANGE_KEY[key],
                **{
                    octobot_commons.symbols.parse_symbol(symbol).merged_str_base_and_quote_only_symbol(market_separator=""):
                        octobot_commons.symbols.parse_symbol(symbol)
                    for symbol in merged_tickers
                }
            }

    def reset_all_tickers_cache(self):
        self._ALL_TICKERS_BY_EXCHANGE_KEY.clear()
        self._ALL_PARSED_SYMBOLS_BY_MERGED_SYMBOLS_BY_EXCHANGE_KEY.clear()
        self._ALL_PARSED_SYMBOLS_BY_FUTURE_MERGED_SYMBOLS_BY_EXCHANGE_KEY.clear()

    @staticmethod
    def get_exchange_key(exchange_name: str, exchange_type: str, sandboxed: bool) -> str:
        return f"{exchange_name}_{exchange_type or octobot_commons.constants.CONFIG_EXCHANGE_SPOT}_{sandboxed}"
