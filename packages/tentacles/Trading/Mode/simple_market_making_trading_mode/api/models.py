import enum
import dataclasses
import decimal
import typing

import octobot_commons.dataclasses

import octobot_trading.exchanges.util.exchange_data as exchange_data_import


class OrderBookFetchPolicy(enum.Enum):
    GIVEN_SYMBOLS = None    # default
    ALL_SYMBOLS = "all_symbols"


@dataclasses.dataclass
class MarketMakingData:
    exchange: str
    pair: str
    pair_alias: typing.Optional[str]
    price: decimal.Decimal
    base_volume: decimal.Decimal
    quote_volume: decimal.Decimal
    market_status: typing.Union[dict, None]
    market_details: list[exchange_data_import.MarketDetails] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class LiquidityScore(octobot_commons.dataclasses.FlexibleDataclass):
    timestamp: float
    exchange_id: str
    symbol: str
    score: float
    bid_ask_spread : typing.Optional[float]
    bids_ob_depth: typing.Optional[float]
    asks_ob_depth: typing.Optional[float]
