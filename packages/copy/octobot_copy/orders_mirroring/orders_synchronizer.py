import decimal
import time
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
        copy_settings: copy_entities.AccountCopySettings,
    ) -> None:
        self._reference_account = reference_account
        self._exchange_interface = exchange_interface
        self._copy_settings = copy_settings
        self._force_immediate_orphan_cancel_next: bool = False

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

    def _active_reference_order_ids(self, replicable: list[dict[str, typing.Any]]) -> set:
        return {
            str(
                doc[trading_constants.STORAGE_ORIGIN_VALUE][
                    trading_enums.ExchangeConstantsOrderColumns.ID.value
                ]
            )
            for doc in replicable
        }

    async def cancel_orders_pending_synchronization(
        self,
        replicable_orders: typing.Optional[list[dict[str, typing.Any]]],
    ) -> int:
        """
        Cancel mirrored copier open orders that no longer match a replicable reference open order
        """
        replicable = replicable_orders or self._get_replicable_reference_orders()
        to_keep_ids = self._active_reference_order_ids(replicable)
        return await self._cancel_mirrored_orphan_orders(to_keep_ids)

    def abort_mirrored_orphan_grace(self) -> None:
        self._copy_settings.mirrored_orphan_grace_started_at = None
        self._force_immediate_orphan_cancel_next = True

    def is_mirrored_orphan_grace_blocking_rebalance(self) -> bool:
        replicable = self._get_replicable_reference_orders()
        active_reference_ids = self._active_reference_order_ids(replicable)
        return self._is_grace_blocking_rebalance(active_reference_ids)

    def _mirrored_orphan_open_orders(self, active_reference_ids: set) -> list[trading_personal_data.Order]:
        return [
            order
            for order in self._exchange_interface.orders.get_open_orders()
            if order.tag == copy_constants.MIRRORED_ORDER_TAG
            and str(order.order_id) not in active_reference_ids
        ]

    def _reference_pair_leg_share(self, symbol: str) -> typing.Optional[decimal.Decimal]:
        parsed = symbol_util.parse_symbol(symbol)
        base_currency = parsed.base
        quote_currency = parsed.quote
        if not base_currency or not quote_currency:
            return None
        reference_content = self._reference_account.content
        if base_currency not in reference_content:
            return trading_constants.ZERO
        if quote_currency not in reference_content:
            return trading_constants.ONE
        base_holdings = reference_content[base_currency] or {}
        quote_holdings = reference_content[quote_currency] or {}
        allocation_base = base_holdings.get(copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO, trading_constants.ZERO)
        allocation_quote = quote_holdings.get(copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO, trading_constants.ZERO)
        pair_denom = allocation_base + allocation_quote
        if pair_denom <= trading_constants.ZERO:
            return None
        return allocation_base / pair_denom

    def _copier_asset_value_in_reference_market(
        self,
        asset: str,
        amount: decimal.Decimal,
    ) -> typing.Optional[decimal.Decimal]:
        reference_market = self._exchange_interface.portfolio.reference_market
        if amount < trading_constants.ZERO:
            return None
        if asset == reference_market:
            return amount
        pair_symbol = symbol_util.merge_currencies(asset, reference_market)
        market_price, _ = self._exchange_interface.market.get_potentially_outdated_price(pair_symbol)
        if market_price <= trading_constants.ZERO:
            return None
        return amount * market_price

    def _orphan_order_execution_price(self, order: trading_personal_data.Order) -> typing.Optional[decimal.Decimal]:
        if order.origin_price > trading_constants.ZERO:
            return order.origin_price
        market_price, _ = self._exchange_interface.market.get_potentially_outdated_price(order.symbol)
        if market_price <= trading_constants.ZERO:
            return None
        return market_price

    def _simulated_copier_pair_leg_share_after_orphan_fill(
        self,
        order: trading_personal_data.Order,
    ) -> typing.Optional[decimal.Decimal]:
        parsed = symbol_util.parse_symbol(order.symbol)
        base_currency = parsed.base
        quote_currency = parsed.quote
        if not base_currency or not quote_currency:
            return None
        execution_price = self._orphan_order_execution_price(order)
        if execution_price is None:
            return None
        order_quantity = order.origin_quantity
        base_total = self._exchange_interface.portfolio.get_currency_portfolio_total(base_currency)
        quote_total = self._exchange_interface.portfolio.get_currency_portfolio_total(quote_currency)
        if order.side is trading_enums.TradeOrderSide.BUY:
            base_adjusted = base_total + order_quantity
            quote_adjusted = quote_total - order_quantity * execution_price
        elif order.side is trading_enums.TradeOrderSide.SELL:
            base_adjusted = base_total - order_quantity
            quote_adjusted = quote_total + order_quantity * execution_price
        else:
            return None
        if base_adjusted < trading_constants.ZERO or quote_adjusted < trading_constants.ZERO:
            return None
        value_base = self._copier_asset_value_in_reference_market(base_currency, base_adjusted)
        value_quote = self._copier_asset_value_in_reference_market(quote_currency, quote_adjusted)
        if value_base is None or value_quote is None:
            return None
        value_total = value_base + value_quote
        if value_total <= trading_constants.ZERO:
            return None
        return value_base / value_total

    def _mirrored_orphan_batch_eligible_for_grace(
        self,
        orphan_orders: list[trading_personal_data.Order],
    ) -> bool:
        max_delta = self._copy_settings.mirrored_orphan_grace_pair_ratio_max_delta
        for orphan_order in orphan_orders:
            reference_share = self._reference_pair_leg_share(orphan_order.symbol)
            simulated_share = self._simulated_copier_pair_leg_share_after_orphan_fill(orphan_order)
            if reference_share is None or simulated_share is None:
                return False
            if abs(simulated_share - reference_share) > max_delta:
                return False
        return True

    def _is_grace_blocking_rebalance(self, active_reference_ids: set) -> bool:
        settings = self._copy_settings
        grace_seconds = settings.mirrored_orphan_cancel_grace_seconds
        if grace_seconds <= 0:
            return False
        orphan_orders = self._mirrored_orphan_open_orders(active_reference_ids)
        orphan_count = len(orphan_orders)
        threshold = settings.mirrored_orphan_grace_abort_threshold
        if orphan_count == 0:
            return False
        if orphan_count >= threshold:
            self._get_logger().info(
                f"Mirrored orphans grace period aborted: {orphan_count} orphans >= threshold ({threshold})"
            )
            return False
        if not self._mirrored_orphan_batch_eligible_for_grace(orphan_orders):
            return False
        started_at = settings.mirrored_orphan_grace_started_at
        if started_at is None:
            return True
        now = time.time()
        return (now - started_at) < grace_seconds

    def _reference_symbols_skipped_while_grace_orphans_uncancelled(
        self,
        replicable: list[dict[str, typing.Any]],
    ) -> set[str]:
        """
        Symbols whose mirrored orphan open orders are still on the copier because cancel is deferred
        during the grace window. Reference upserts on these symbols are skipped to avoid stacking a new
        mirrored side (e.g. sell) while an orphan (e.g. buy) may still fill.
        """
        settings = self._copy_settings
        grace_seconds = settings.mirrored_orphan_cancel_grace_seconds
        if grace_seconds <= 0:
            return set()
        active_reference_ids = self._active_reference_order_ids(replicable)
        orphan_orders = self._mirrored_orphan_open_orders(active_reference_ids)
        orphan_count = len(orphan_orders)
        threshold = settings.mirrored_orphan_grace_abort_threshold
        if orphan_count == 0 or orphan_count >= threshold:
            return set()
        if not self._mirrored_orphan_batch_eligible_for_grace(orphan_orders):
            return set()
        started_at = settings.mirrored_orphan_grace_started_at
        now = time.time()
        if started_at is not None and (now - started_at) >= grace_seconds:
            return set()
        return {order.symbol for order in orphan_orders}

    async def synchronize(self) -> list:
        """Align copier open orders with reference_account.orders (synched mirror rows)."""
        replicable = self._get_replicable_reference_orders()
        orphan_cancelled_count = await self.cancel_orders_pending_synchronization(replicable)
        skip_symbols_for_upsert = self._reference_symbols_skipped_while_grace_orphans_uncancelled(replicable)
        created: list = []
        replaced_cancelled_count = 0
        already_synchronized_count = 0
        skipped_grace_upserts: list[tuple[str, typing.Any]] = []
        for doc in replicable:
            origin = doc[trading_constants.STORAGE_ORIGIN_VALUE]
            order_symbol = origin[trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value]
            if order_symbol in skip_symbols_for_upsert:
                skipped_grace_upserts.append(
                    (
                        order_symbol,
                        origin.get(trading_enums.ExchangeConstantsOrderColumns.ID.value),
                    )
                )
                continue
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
        if skipped_grace_upserts:
            skipped_summary = ", ".join(
                f"{symbol}:{reference_order_id}"
                for symbol, reference_order_id in skipped_grace_upserts
            )
            self._get_logger().info(
                "Skipped reference mirror upsert for %s order(s) (mirrored orphan grace period active): %s",
                len(skipped_grace_upserts),
                skipped_summary,
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

    async def _cancel_mirrored_orphan_orders(
        self,
        active_reference_ids: set,
    ) -> int:
        orphan_orders = self._mirrored_orphan_open_orders(active_reference_ids)
        return await self._apply_grace_policy_and_cancel_mirrored_orphans(orphan_orders)

    async def _apply_grace_policy_and_cancel_mirrored_orphans(
        self,
        orphan_orders: list[trading_personal_data.Order],
    ) -> int:
        """
        When mirrored orphans exist (or none, to clear grace state): defer cancel during an active
        grace window unless ``abort_mirrored_orphan_grace`` requested immediate cancel, grace is
        disabled, orphan count reaches abort threshold, or wall-clock grace has elapsed.
        """
        settings = self._copy_settings
        orphan_count = len(orphan_orders)

        # No mirrored orphans: nothing to cancel; drop any in-memory grace start (episode over or idle).
        if orphan_count == 0:
            self._force_immediate_orphan_cancel_next = False
            if settings.mirrored_orphan_grace_started_at is not None:
                self._get_logger().info(
                    "Mirrored open-order grace period ended early: no mirrored orphan orders remain "
                    "(reference and copier mirrors aligned as expected). "
                    "Downstream copy flow proceeds without grace deferral."
                )
            settings.mirrored_orphan_grace_started_at = None
            return 0

        grace_seconds = settings.mirrored_orphan_cancel_grace_seconds
        threshold = settings.mirrored_orphan_grace_abort_threshold
        # Explicit abort or grace disabled: cancel orphans immediately, do not start or extend grace.
        if self._force_immediate_orphan_cancel_next or grace_seconds <= 0:
            self._force_immediate_orphan_cancel_next = False
            settings.mirrored_orphan_grace_started_at = None
            return await self._cancel_mirrored_orphan_order_list(orphan_orders)

        # Too many orphans at once: treat as runaway desync, cancel immediately (same as threshold abort).
        if orphan_count >= threshold:
            if settings.mirrored_orphan_grace_started_at:
                self._get_logger().info(
                    f"Mirrored orphan grace aborted: {orphan_count} orphan(s) >= threshold {threshold}"
                )
            settings.mirrored_orphan_grace_started_at = None
            return await self._cancel_mirrored_orphan_order_list(orphan_orders)

        if not self._mirrored_orphan_batch_eligible_for_grace(orphan_orders):
            had_grace_window = settings.mirrored_orphan_grace_started_at is not None
            settings.mirrored_orphan_grace_started_at = None
            if had_grace_window:
                self._get_logger().info(
                    "Mirrored orphan grace aborted: post-fill pair-ratio heuristic failed for at least one "
                    f"orphan (threshold={settings.mirrored_orphan_grace_pair_ratio_max_delta}); "
                    "cancelling immediately"
                )
            else:
                self._get_logger().info(
                    "Mirrored orphan grace skipped: post-fill pair-ratio heuristic failed for at least one "
                    f"orphan (threshold={settings.mirrored_orphan_grace_pair_ratio_max_delta}); "
                    "cancelling immediately"
                )
            return await self._cancel_mirrored_orphan_order_list(orphan_orders)

        now = time.time()
        started_at = settings.mirrored_orphan_grace_started_at
        # First observation of orphans this episode: begin wall-clock grace window, do not cancel yet.
        if started_at is None:
            settings.mirrored_orphan_grace_started_at = now
            self._get_logger().info(
                f"Mirrored orphan grace period started: deferring cancel of {orphan_count} "
                f"orphan order(s) for up to {grace_seconds}s"
            )
            return 0
        # Still inside grace window: wait for copier fills / alignment.
        if (now - started_at) < grace_seconds:
            remaining_seconds = grace_seconds - (now - started_at)
            self._get_logger().info(
                f"Mirrored orphan cancel deferred: {orphan_count} orphan(s), "
                f"{remaining_seconds:.1f}s grace remaining"
            )
            return 0

        # Grace window finished: cancel orphans that are still open.
        settings.mirrored_orphan_grace_started_at = None
        self._get_logger().info(
            f"Mirrored orphan grace elapsed after {grace_seconds}s: cancelling {orphan_count} orphan(s)"
        )
        return await self._cancel_mirrored_orphan_order_list(orphan_orders)

    async def _cancel_mirrored_orphan_order_list(
        self,
        orphan_orders: list[trading_personal_data.Order],
    ) -> int:
        cancelled_count = 0
        for order in orphan_orders:
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
        else:
            adapted_order_chunks, _ = (
                self._exchange_interface.orders.check_and_adapt_order_details_if_necessary(
                    symbol,
                    target_quantity,
                    limit_price,
                )
            )
            adapted_details: list[tuple[decimal.Decimal, decimal.Decimal]] = typing.cast(
                list[tuple[decimal.Decimal, decimal.Decimal]],
                adapted_order_chunks,
            )
            if not adapted_details:
                target_quantity = trading_constants.ZERO
            else:
                target_quantity = sum(
                    (quantity for quantity, _ in adapted_details),
                    trading_constants.ZERO,
                )
                limit_price = adapted_details[0][1]
        return target_quantity, resolved_trader_order_type, limit_price, current_price

    def _get_logger(self) -> logging.BotLogger:
        return logging.get_logger(self.__class__.__name__)
