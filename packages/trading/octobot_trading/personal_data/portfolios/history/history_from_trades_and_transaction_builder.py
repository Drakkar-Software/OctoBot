import copy
import decimal
import math

import octobot_commons.constants as commons_constants
import octobot_commons.logging as logging_module
import octobot_protocol.models as protocol_models


_SUPPORTED_PROTOCOL_TRANSACTION_TYPES = frozenset({
    protocol_models.TransactionType.BLOCKCHAIN_DEPOSIT,
    protocol_models.TransactionType.BLOCKCHAIN_WITHDRAWAL,
    protocol_models.TransactionType.FUNDING_FEE,
    protocol_models.TransactionType.TRADING_FEE,
})


def build_historical_holdings(
    latest_portfolio: dict[str, dict[str, decimal.Decimal]],
    trades: list[protocol_models.Trade],
    transactions: list[protocol_models.Transaction],
) -> dict[float, dict[str, dict[str, decimal.Decimal]]]:
    """
    Compute daily portfolio snapshots by reverse-applying trades and transactions
    to the latest portfolio in antichronological order.

    Returns a dict keyed by UTC day-start timestamp (00:00:00) mapping to the
    portfolio content at the end of that day.
    """
    # Build unified event list sorted descending by timestamp.
    events = _build_sorted_events(trades, transactions)
    if not events:
        return {}

    portfolio = copy.deepcopy(latest_portfolio)
    snapshots_by_day: dict[float, dict[str, dict[str, decimal.Decimal]]] = {}

    for event_timestamp, event in events:
        try:
            day_start = _utc_day_start(event_timestamp)
            # Record snapshot for the day before applying the reverse delta,
            # so we capture the portfolio state after this event was originally applied.
            if day_start not in snapshots_by_day:
                snapshots_by_day[day_start] = copy.deepcopy(portfolio)

            # Compute reverse delta and apply it.
            reverse_deltas = _compute_reverse_delta(event)
            _apply_deltas(portfolio, reverse_deltas)
        except Exception as e:
            logging_module.get_logger("HistoryFromTradesAndTransactionBuilder").exception(
                e,
                True,
                f"Unexpected error when computing reverse delta for event: {event} ({e} {e.__class__.__name__})",
            )

    # Record the final state (before the oldest event) at its day boundary.
    if events:
        oldest_day = _utc_day_start(events[-1][0])
        prior_day = oldest_day - commons_constants.DAYS_TO_SECONDS
        if prior_day not in snapshots_by_day:
            snapshots_by_day[prior_day] = copy.deepcopy(portfolio)

    return snapshots_by_day


def _build_sorted_events(
    trades: list[protocol_models.Trade],
    transactions: list[protocol_models.Transaction],
) -> list[tuple[float, protocol_models.Trade | protocol_models.Transaction]]:
    """Merge trades and transactions into a single list sorted by timestamp descending."""
    events: list[tuple[float, protocol_models.Trade | protocol_models.Transaction]] = []
    for trade in trades:
        events.append((trade.executed_at.timestamp(), trade))
    for transaction in transactions:
        if transaction.type not in _SUPPORTED_PROTOCOL_TRANSACTION_TYPES:
            continue
        events.append((transaction.timestamp.timestamp(), transaction))
    events.sort(key=lambda event_tuple: event_tuple[0], reverse=True)
    return events


def _compute_reverse_delta(
    event: protocol_models.Trade | protocol_models.Transaction,
) -> dict[str, dict[str, decimal.Decimal]]:
    """
    Compute the portfolio delta that reverses the effect of the given event.
    For a trade that added +X to base, the reverse is -X (and vice versa).
    """
    if isinstance(event, protocol_models.Trade):
        return _reverse_protocol_trade_delta(event)
    if isinstance(event, protocol_models.Transaction):
        return _reverse_protocol_transaction_delta(event)
    raise ValueError(f"Unexpected event type: {type(event)}: {event}")


def _protocol_trade_fee_by_currency(
    trade: protocol_models.Trade,
) -> dict[str, decimal.Decimal]:
    if trade.fee is None:
        return {}
    return {trade.fee.currency: decimal.Decimal(str(trade.fee.amount))}


def _reverse_protocol_trade_delta(
    trade: protocol_models.Trade,
) -> dict[str, dict[str, decimal.Decimal]]:
    """
    Reverse the portfolio effect of a spot trade.
    Forward: BUY  → base +qty, quote -(qty*price)
    Forward: SELL → base -qty, quote +(qty*price)
    Fees are subtracted from the receiving side in the forward direction,
    so they are added back in the reverse direction.
    """
    deltas: dict[str, dict[str, decimal.Decimal]] = {}
    if "/" not in trade.symbol:
        return deltas
    base, quote = trade.symbol.split("/", 1)
    quantity = decimal.Decimal(str(trade.quantity))
    cost = quantity * decimal.Decimal(str(trade.price))
    fee_by_currency = _protocol_trade_fee_by_currency(trade)

    if trade.side is protocol_models.Side.BUY:
        base_delta = -(quantity - fee_by_currency.get(base, decimal.Decimal(0)))
        quote_delta = cost + fee_by_currency.get(quote, decimal.Decimal(0))
    else:
        base_delta = quantity + fee_by_currency.get(base, decimal.Decimal(0))
        quote_delta = -(cost - fee_by_currency.get(quote, decimal.Decimal(0)))

    deltas[base] = _portfolio_delta(base_delta)
    deltas[quote] = _portfolio_delta(quote_delta)
    return deltas


def _reverse_protocol_transaction_delta(
    transaction: protocol_models.Transaction,
) -> dict[str, dict[str, decimal.Decimal]]:
    amount = decimal.Decimal(str(transaction.amount))
    if transaction.type is protocol_models.TransactionType.BLOCKCHAIN_DEPOSIT:
        delta = -amount
    elif transaction.type is protocol_models.TransactionType.BLOCKCHAIN_WITHDRAWAL:
        delta = amount
    elif transaction.type in (
        protocol_models.TransactionType.FUNDING_FEE,
        protocol_models.TransactionType.TRADING_FEE,
    ):
        delta = amount
    else:
        return {}
    return {transaction.asset: _portfolio_delta(delta)}


def _portfolio_delta(value: decimal.Decimal) -> dict[str, decimal.Decimal]:
    return {
        commons_constants.PORTFOLIO_TOTAL: value,
        commons_constants.PORTFOLIO_AVAILABLE: value,
    }


def _apply_deltas(
    portfolio: dict[str, dict[str, decimal.Decimal]],
    deltas: dict[str, dict[str, decimal.Decimal]],
) -> None:
    """Apply deltas in-place to the portfolio."""
    for asset, delta_values in deltas.items():
        if asset in portfolio:
            portfolio[asset][commons_constants.PORTFOLIO_TOTAL] += delta_values[commons_constants.PORTFOLIO_TOTAL]
            portfolio[asset][commons_constants.PORTFOLIO_AVAILABLE] += delta_values[commons_constants.PORTFOLIO_AVAILABLE]
        else:
            portfolio[asset] = {
                commons_constants.PORTFOLIO_TOTAL: delta_values[commons_constants.PORTFOLIO_TOTAL],
                commons_constants.PORTFOLIO_AVAILABLE: delta_values[commons_constants.PORTFOLIO_AVAILABLE],
            }


def _utc_day_start(timestamp: float) -> float:
    """Return the UTC day-start (00:00:00) for the given unix timestamp."""
    return float(math.floor(
        timestamp / commons_constants.DAYS_TO_SECONDS
    ) * commons_constants.DAYS_TO_SECONDS)
