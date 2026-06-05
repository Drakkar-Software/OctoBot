import dataclasses
import decimal
import typing

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums


@dataclasses.dataclass(frozen=True)
class MirroredQuantityComputeResult:
    ideal_quantity: decimal.Decimal
    resolved_trader_order_type: trading_enums.TraderOrderType
    limit_price: decimal.Decimal
    current_price: decimal.Decimal
    zero_short_reason: typing.Optional[str] = None
    scaled_quantity: decimal.Decimal = trading_constants.ZERO
    available_market_holding: typing.Optional[decimal.Decimal] = None
    available_symbol_holding: typing.Optional[decimal.Decimal] = None
    total_symbol_holding: typing.Optional[decimal.Decimal] = None
    quote_for_cap: typing.Optional[decimal.Decimal] = None
