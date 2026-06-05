import decimal
import typing

import octobot_commons.logging as logging
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_protocol.models as protocol_models
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums

import octobot_copy.entities as copy_entities
import octobot_copy.exchange as copy_exchange
import octobot_copy.orders_mirroring.mirrored_order_replication_failure as mirrored_order_replication_failure

REPLICATION_FAILURES_SUMMARY_LIMIT = 20


def replication_failure_from_order(
    order: protocol_models.Order,
    short_reason: str,
) -> mirrored_order_replication_failure.MirroredOrderReplicationFailure:
    order_price = order.price
    price = (
        decimal.Decimal(str(order_price))
        if order_price not in (None, "")
        else trading_constants.ZERO
    )
    order_side = order.side
    if order_side in (None, ""):
        side = "unknown"
    else:
        side_value = getattr(order_side, "value", order_side)
        side = str(side_value)
    return mirrored_order_replication_failure.MirroredOrderReplicationFailure(
        symbol=order.symbol,
        side=side,
        price=price,
        reference_order_id=str(order.id),
        short_reason=short_reason,
    )


def format_replication_failure_entry(
    failure: mirrored_order_replication_failure.MirroredOrderReplicationFailure,
) -> str:
    return (
        f"{failure.side} {failure.symbol} @ {failure.price} "
        f"[{failure.reference_order_id}] ({failure.short_reason})"
    )


def format_replication_failures_summary(
    replication_failures: list[mirrored_order_replication_failure.MirroredOrderReplicationFailure],
) -> str:
    if not replication_failures:
        return ""
    displayed_failures = replication_failures[:REPLICATION_FAILURES_SUMMARY_LIMIT]
    entries = ", ".join(
        format_replication_failure_entry(failure) for failure in displayed_failures
    )
    remaining_count = len(replication_failures) - len(displayed_failures)
    summary = f"Failed to replicate {len(replication_failures)} order(s): {entries}."
    if remaining_count > 0:
        summary = f"{summary[:-1]} … and {remaining_count} more."
    return summary


def log_skipped_mirror_action(
    logger: logging.BotLogger,
    failure: mirrored_order_replication_failure.MirroredOrderReplicationFailure,
    *,
    trader_order_type: trading_enums.TraderOrderType,
    **context: typing.Any,
) -> None:
    context_parts = ", ".join(f"{key}={value}" for key, value in context.items())
    message = (
        f"Skipping mirrored order creation ({failure.short_reason}): "
        f"{format_replication_failure_entry(failure)} type={trader_order_type}"
    )
    if context_parts:
        message = f"{message}, {context_parts}"
    logger.warning(message)


def upsert_failure_return(
    logger: logging.BotLogger,
    order: protocol_models.Order,
    short_reason: str,
    trader_order_type: trading_enums.TraderOrderType,
    **context: typing.Any,
) -> tuple[list, int, int, mirrored_order_replication_failure.MirroredOrderReplicationFailure]:
    failure = replication_failure_from_order(order, short_reason)
    log_skipped_mirror_action(logger, failure, trader_order_type=trader_order_type, **context)
    return [], 0, 0, failure


def mirror_scale_failure_context(
    order: protocol_models.Order,
    symbol: str,
    side: trading_enums.TradeOrderSide,
    scaled_quantity: typing.Optional[decimal.Decimal],
    reference_account: protocol_models.CopiedAccount,
    exchange_interface: copy_exchange.ExchangeInterface,
) -> dict[str, typing.Any]:
    parsed = symbol_util.parse_symbol(symbol)
    scale_currency = parsed.quote if side is trading_enums.TradeOrderSide.BUY else parsed.base
    values = copy_entities.copied_asset_total_by_name(reference_account)
    reference_total = values.get(scale_currency, trading_constants.ZERO)
    copier_total = exchange_interface.portfolio.get_currency_portfolio_total(scale_currency)
    reference_order_quantity = decimal.Decimal(str(order.quantity))
    return {
        "scale_currency": scale_currency,
        "reference_total": reference_total,
        "copier_total": copier_total,
        "reference_order_quantity": reference_order_quantity,
        "scaled_quantity": scaled_quantity,
    }
