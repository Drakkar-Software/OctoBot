import typing

import octobot_commons.constants as common_constants

import octobot_trading.enums as trading_enums
import octobot_trading.util.test_tools.exchange_data_util as exchange_data_util

if typing.TYPE_CHECKING:
    import octobot_trading.util.test_tools.exchange_data as exchange_data_import


def create_market_filter(
    exchange_data: typing.Optional["exchange_data_import.ExchangeData"],
    to_keep_quote: typing.Optional[str],
    to_keep_symbols: typing.Optional[typing.Iterable[str]] = None,
    to_keep_quotes: typing.Optional[typing.Iterable[str]] = None,
    force_usd_like_markets: bool = True,
) -> typing.Callable[[dict], bool]:
    relevant_symbols_to_keep = set(to_keep_symbols or [])   # forced symbols
    if exchange_data:
        relevant_symbols_to_keep.update(exchange_data_util.get_orders_and_positions_symbols(exchange_data))    # orders/positions symbols
        relevant_symbols_to_keep.update(market.symbol for market in exchange_data.markets)  # always in symbols in markets
    merged_to_keep_quotes = set(to_keep_quotes or [])
    if to_keep_quote:
        merged_to_keep_quotes.add(to_keep_quote)

    def market_filter(market: dict) -> bool:
        if market[trading_enums.ExchangeConstantsMarketStatusColumns.SYMBOL.value] in relevant_symbols_to_keep:
            return True
        base = market[trading_enums.ExchangeConstantsMarketStatusColumns.CURRENCY.value]
        quote = market[trading_enums.ExchangeConstantsMarketStatusColumns.MARKET.value]
        return (
            (
                # 1. all "X/to_keep_quote" markets
                # => always required to run the strategy
                quote in merged_to_keep_quotes or
                # 2. all "to_keep_quote/X" markets
                # => used in portfolio optimization. Ex: to buy BTC from USDT when BTC is the "to_keep_quote",
                #    BTC/USD-like market is required
                base in merged_to_keep_quotes or
                # 3. all USD-like/X markets
                # => used in portfolio optimization. Ex: to be able to convert USD like currencies into the
                #    same USD-like currency
                (force_usd_like_markets and base in common_constants.USD_LIKE_COINS)
            )
            and (
                market[trading_enums.ExchangeConstantsMarketStatusColumns.TYPE.value] ==
                trading_enums.ExchangeTypes.SPOT.value
            )
        )

    return market_filter
