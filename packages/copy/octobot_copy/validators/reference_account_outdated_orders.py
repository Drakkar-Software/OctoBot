import decimal

import octobot_protocol.models as protocol_models
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data as trading_personal_data

import octobot_copy.constants as copy_constants
import octobot_copy.errors as copy_errors
import octobot_copy.exchange as copy_exchange


def resolve_order_trigger_above(order: protocol_models.Order) -> bool:
    if order.trigger_above is not None:
        return bool(order.trigger_above)
    if order.side is protocol_models.Side.SELL:
        return True
    return False


def get_replicable_reference_orders(
    reference_account: protocol_models.CopiedAccount,
) -> list[protocol_models.Order]:
    replicable: list[protocol_models.Order] = []
    for order in reference_account.orders or []:
        if order.status != protocol_models.OrderStatus.OPEN:
            continue
        if not order.is_active:
            continue
        raw = trading_personal_data.exchange_columns_dict_from_protocol_order(order)
        _side, trader_order_type = trading_personal_data.parse_order_type(raw)
        if trader_order_type in (
            trading_enums.TraderOrderType.BUY_MARKET,
            trading_enums.TraderOrderType.SELL_MARKET,
        ):
            continue
        replicable.append(order)
    return replicable


def is_order_impossible_at_market_price(
    order: protocol_models.Order,
    market_price: decimal.Decimal,
    threshold: decimal.Decimal,
) -> bool:
    if market_price <= trading_constants.ZERO:
        raise ValueError(
            f"Market price must be positive to validate order {order.id!r} on {order.symbol!r}, got {market_price}"
        )
    order_price = decimal.Decimal(str(order.price))
    if order_price <= trading_constants.ZERO:
        return False
    trigger_above = resolve_order_trigger_above(order)
    if trigger_above:
        return order_price <= market_price * (trading_constants.ONE - threshold)
    return order_price >= market_price * (trading_constants.ONE + threshold)


def _order_price_gap_ratio(
    order: protocol_models.Order,
    market_price: decimal.Decimal,
) -> decimal.Decimal:
    order_price = decimal.Decimal(str(order.price))
    trigger_above = resolve_order_trigger_above(order)
    if trigger_above:
        return (market_price - order_price) / market_price
    return (order_price - market_price) / market_price


async def ensure_reference_account_not_outdated(
    reference_account: protocol_models.CopiedAccount,
    exchange_interface: copy_exchange.ExchangeInterface,
) -> None:
    replicable_orders = get_replicable_reference_orders(reference_account)
    if not replicable_orders:
        return
    threshold = decimal.Decimal(str(copy_constants.OUTDATED_ORDER_PRICE_MAX_THRESHOLD))
    market_price_by_symbol: dict[str, decimal.Decimal] = {}
    for order in replicable_orders:
        symbol = order.symbol
        if symbol not in market_price_by_symbol:
            market_price, _is_outdated = exchange_interface.market.get_potentially_outdated_price(symbol)
            if market_price <= trading_constants.ZERO:
                raise ValueError(
                    f"Missing market price for {symbol!r} while validating reference account outdated orders"
                )
            market_price_by_symbol[symbol] = market_price
        market_price = market_price_by_symbol[symbol]
        if is_order_impossible_at_market_price(order, market_price, threshold):
            gap_ratio = _order_price_gap_ratio(order, market_price)
            gap_percent = float(gap_ratio * trading_constants.ONE_HUNDRED)
            trigger_above = resolve_order_trigger_above(order)
            raise copy_errors.OutdatedReferenceAccountError(
                f"Reference account updated_at={reference_account.updated_at} is outdated: "
                f"order {order.id!r} on {order.symbol!r} "
                f"(trigger_above={trigger_above}, price={order.price}, market={market_price}) "
                f"would instantly fill by {gap_percent:.2f}% "
                f"(threshold={float(threshold * trading_constants.ONE_HUNDRED):.2f}%)"
            )
