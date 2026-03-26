import decimal
import typing

import octobot_commons.constants as commons_constants
import octobot_commons.logging as logging
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_trading.constants as trading_constants
import octobot_trading.errors as trading_errors
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data as trading_personal_data

import octobot_copy.constants as copy_constants
import octobot_copy.entities as copy_entities
import octobot_copy.exchange as copy_exchange


class OrdersSynchronizer:
    """Synches reference account open orders onto the copier exchange (spot mirror rows)."""

    def __init__(
        self,
        reference_account: copy_entities.Account,
        exchange_interface: copy_exchange.ExchangeInterface,
    ) -> None:
        self._reference_account = reference_account
        self._exchange_interface = exchange_interface

    def _get_replicable_reference_orders(self) -> list[dict[str, typing.Any]]:
        replicable: list[dict[str, typing.Any]] = []
        for doc in self._reference_account.orders:
            if trading_constants.STORAGE_ORIGIN_VALUE not in doc:
                continue
            origin = doc[trading_constants.STORAGE_ORIGIN_VALUE]
            if (
                origin.get(trading_enums.ExchangeConstantsOrderColumns.STATUS.value)
                != trading_enums.OrderStatus.OPEN.value
            ):
                continue
            if origin.get(trading_enums.ExchangeConstantsOrderColumns.SELF_MANAGED.value, False):
                continue
            if origin.get(trading_enums.ExchangeConstantsOrderColumns.IS_ACTIVE.value, True) is False:
                continue
            replicable.append(doc)
        return replicable

    async def synchronize(self) -> list:
        """Align copier open orders with reference_account.orders (synched mirror rows)."""
        replicable = self._get_replicable_reference_orders()
        active_reference_ids = {
            str(
                doc[trading_constants.STORAGE_ORIGIN_VALUE][
                    trading_enums.ExchangeConstantsOrderColumns.ID.value
                ]
            )
            for doc in replicable
        }
        orphan_cancelled_count = await self._cancel_mirrored_orphan_orders(active_reference_ids)
        created: list = []
        replaced_cancelled_count = 0
        already_synchronized_count = 0
        for doc in replicable:
            try:
                batch, replace_count, already_count = await self._upsert_mirrored_reference_order(doc)
                created.extend(batch)
                replaced_cancelled_count += replace_count
                already_synchronized_count += already_count
            except (
                trading_errors.MissingMinimalExchangeTradeVolume,
                trading_errors.OrderCreationError,
            ) as err:
                self._get_logger().exception(
                    err,
                    True,
                    f"Skipping synched reference order mirror: {err} ({err.__class__.__name__})",
                )
        total_cancelled = orphan_cancelled_count + replaced_cancelled_count
        total_created = len(created)
        self._get_logger().info(
            f"Order mirror completed: {total_cancelled} cancelled "
            f"[{orphan_cancelled_count} orphan(s), {replaced_cancelled_count} replaced], "
            f"{total_created} created, "
            f"{already_synchronized_count} already synchronized orders."
        )
        return created

    async def _cancel_mirrored_orphan_orders(self, active_reference_ids: set) -> int:
        cancelled_count = 0
        for order in self._exchange_interface.orders.get_open_orders():
            if order.tag != copy_constants.MIRRORED_ORDER_TAG:
                continue
            if str(order.order_id) in active_reference_ids:
                continue
            try:
                await self._exchange_interface.orders.cancel_order(order)
                cancelled_count += 1
                self._get_logger().info(
                    f"Cancelled mirrored orphan order: symbol={order.symbol} "
                    f"order_id={order.order_id} side={order.side} type={order.order_type}"
                )
            except trading_errors.UnexpectedExchangeSideOrderStateError as err:
                self._get_logger().exception(
                    err,
                    True,
                    f"Skipped orphan cancel: {err}, order: {order}",
                )
        return cancelled_count

    def _scale_mirrored_order_quantity(
        self,
        origin: dict,
        symbol: str,
        side: trading_enums.TradeOrderSide,
    ) -> typing.Optional[decimal.Decimal]:
        # Spot: sells spend base, buys spend quote — scale the reference order amount by the same leg's
        # holdings ratio. This will need to be adapted for futures (margin/position sizing, not spot wallets).
        parsed = symbol_util.parse_symbol(symbol)
        scale_currency = parsed.quote if side is trading_enums.TradeOrderSide.BUY else parsed.base
        reference_holdings = self._reference_account.content.get(scale_currency, {})  # type: ignore
        reference_total = reference_holdings.get(
            commons_constants.PORTFOLIO_TOTAL, trading_constants.ZERO
        )
        if reference_total <= trading_constants.ZERO:
            return None
        copier_total = self._exchange_interface.portfolio.get_currency_portfolio_total(scale_currency)
        amount = decimal.Decimal(str(origin[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value]))
        if amount <= trading_constants.ZERO:
            return None
        scale = copier_total / reference_total
        return amount * scale

    def _find_open_order_by_bot_order_id(self, order_id: str) -> typing.Optional[trading_personal_data.Order]:
        for order in self._exchange_interface.orders.get_open_orders():
            if str(order.order_id) == str(order_id):
                return order
        return None

    def _mirrored_order_target_mismatch_reason(
        self,
        order: trading_personal_data.Order,
        symbol: str,
        side: trading_enums.TradeOrderSide,
        order_type: trading_enums.TraderOrderType,
        ideal_quantity: decimal.Decimal,
        order_target_price: decimal.Decimal,
        current_price: decimal.Decimal,
    ) -> typing.Optional[str]:
        if order.symbol != symbol:
            return f"symbol mismatch (open_order={order.symbol!r}, target={symbol!r})"
        if order.side != side:
            return f"side mismatch (open_order={order.side}, target={side})"
        if order.order_type != order_type:
            return f"order_type mismatch (open_order={order.order_type}, target={order_type})"
        quantity_tolerance = ideal_quantity * decimal.Decimal("0.002")
        quantity_threshold = max(quantity_tolerance, decimal.Decimal("1e-12"))
        if abs(order.origin_quantity - ideal_quantity) > quantity_threshold:
            return (
                f"quantity mismatch (open_order={order.origin_quantity}, target={ideal_quantity}, "
                f"threshold={quantity_threshold})"
            )
        if trading_personal_data.get_trade_order_type(order_type) is trading_enums.TradeOrderType.MARKET:
            return None
        price_tolerance = order_target_price * decimal.Decimal("0.0001")
        reference_price = (
            order_target_price if order_target_price > trading_constants.ZERO else current_price
        )
        price_threshold = max(price_tolerance, decimal.Decimal("1e-12"))
        if abs(order.origin_price - reference_price) > price_threshold:
            return (
                f"limit price mismatch (open_order={order.origin_price}, target={reference_price}, "
                f"threshold={price_threshold})"
            )
        return None

    async def _upsert_mirrored_reference_order(self, doc: dict) -> tuple[list, int, int]:
        origin = doc[trading_constants.STORAGE_ORIGIN_VALUE]
        symbol = origin[trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value]
        side, trader_order_type = trading_personal_data.parse_order_type(origin)
        if side is None or trader_order_type is None:
            self._get_logger().info(
                f"Skipping reference order mirror: unsupported type for {symbol} ({trader_order_type})"
            )
            return [], 0, 0
        reference_order_id = str(origin[trading_enums.ExchangeConstantsOrderColumns.ID.value])
        scaled_quantity = self._scale_mirrored_order_quantity(origin, symbol, side)
        if scaled_quantity is None or scaled_quantity <= trading_constants.ZERO:
            return [], 0, 0
        existing = self._find_open_order_by_bot_order_id(reference_order_id)
        current_price_val = origin[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]
        order_target_price = (
            decimal.Decimal(str(current_price_val))
            if current_price_val not in (None, "")
            else trading_constants.ZERO
        )
        (
            ideal_quantity,
            resolved_type,
            market_or_limit_price,
            current_price,
        ) = await self._compute_mirrored_quantity_type_and_price(
            symbol,
            side,
            scaled_quantity,
            order_target_price,
            trader_order_type,
        )
        if ideal_quantity <= trading_constants.ZERO:
            self._get_logger().error(
                f"Skipping mirrored order: target quantity is zero: symbol={symbol} "
                f"order_id={reference_order_id} side={side} type={trader_order_type} "
                f"origin_order: {origin}"
            )
            return [], 0, 0
        replace_reason: typing.Optional[str] = None
        if existing is not None:
            replace_reason = self._mirrored_order_target_mismatch_reason(
                existing,
                symbol,
                side,
                resolved_type,
                ideal_quantity,
                market_or_limit_price,
                current_price,
            )
            if replace_reason is None:
                self._get_logger().info(
                    f"Mirrored order already synchronized: symbol={existing.symbol} "
                    f"order_id={existing.order_id} side={existing.side} type={existing.order_type} "
                    f"(reference_id={reference_order_id})"
                )
                return [], 0, 1
        replaced_cancelled = 0
        if existing is not None:
            self._get_logger().info(
                f"Cancelling mirrored order for replace ({replace_reason}): symbol={existing.symbol} "
                f"order_id={existing.order_id} side={existing.side} type={existing.order_type} "
                f"(reference_id={reference_order_id})"
            )
            await self._exchange_interface.orders.cancel_order(existing)
            replaced_cancelled = 1
            self._get_logger().info(
                f"Cancelled mirrored order for replace ({replace_reason}): symbol={existing.symbol} "
                f"order_id={existing.order_id} side={existing.side} type={existing.order_type} "
                f"(reference_id={reference_order_id})"
            )
        symbol_market = self._exchange_interface.market.get_market_status(symbol, with_fixer=False)
        market_or_limit_price, ideal_quantity = (
            self._exchange_interface.orders.adapt_order_quantity_and_target_price_for_order_creation(
                resolved_type,
                symbol,
                ideal_quantity,
                market_or_limit_price,
                adapt_price_for_limit_orders=False,
            )
        )
        created, _ = await self._exchange_interface.orders.create_orders(
            resolved_type,
            symbol,
            current_price,
            ideal_quantity,
            market_or_limit_price,
            symbol_market,
            tag=copy_constants.MIRRORED_ORDER_TAG,
            order_id=reference_order_id,
            raise_all_creation_error=True,
        )
        out = [o for o in created if o is not None]
        for order in out:
            self._get_logger().info(
                f"Created mirrored order: symbol={order.symbol} "
                f"bot_order_id={order.order_id} side={order.side} type={order.order_type} "
                f"quantity={order.origin_quantity} (reference_id={reference_order_id})"
            )
        return out, replaced_cancelled, 0

    async def _compute_mirrored_quantity_type_and_price(
        self,
        symbol: str,
        side: trading_enums.TradeOrderSide,
        scaled_quantity: decimal.Decimal,
        order_target_price: decimal.Decimal,
        trader_order_type: trading_enums.TraderOrderType,
    ) -> tuple[decimal.Decimal, trading_enums.TraderOrderType, decimal.Decimal, decimal.Decimal]:
        (
            total_symbol_holding,
            total_market_holding,
            _market_quantity,
            current_price,
            _symbol_market,
        ) = await self._exchange_interface.orders.get_pre_order_data(
            symbol=symbol,
            timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT,
            portfolio_type=commons_constants.PORTFOLIO_TOTAL,
        )
        effective_target_price = (
            order_target_price
            if order_target_price > trading_constants.ZERO
            else current_price
        )
        resolved_trader_order_type = trader_order_type
        if trading_personal_data.get_trade_order_type(trader_order_type) is trading_enums.TradeOrderType.MARKET:
            if not self._exchange_interface.market.is_market_open_for_order_type(
                symbol, trader_order_type
            ):
                resolved_trader_order_type = (
                    trading_enums.TraderOrderType.BUY_LIMIT
                    if side is trading_enums.TradeOrderSide.BUY
                    else trading_enums.TraderOrderType.SELL_LIMIT
                )
        resolved_trade_type = trading_personal_data.get_trade_order_type(
            resolved_trader_order_type
        )
        limit_price = (
            current_price
            if resolved_trade_type is trading_enums.TradeOrderType.MARKET
            else effective_target_price
        )
        if side is trading_enums.TradeOrderSide.BUY:
            target_quantity = min(
                scaled_quantity,
                total_market_holding / effective_target_price
                if effective_target_price
                else scaled_quantity,
            )
        else:
            target_quantity = min(scaled_quantity, total_symbol_holding)
        if target_quantity <= trading_constants.ZERO:
            target_quantity = trading_constants.ZERO
        return target_quantity, resolved_trader_order_type, limit_price, current_price

    def _get_logger(self) -> logging.BotLogger:
        return logging.get_logger(self.__class__.__name__)
