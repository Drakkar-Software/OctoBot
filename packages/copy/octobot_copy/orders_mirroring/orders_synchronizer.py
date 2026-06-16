import decimal
import time
import typing

import octobot_commons.constants as commons_constants
import octobot_commons.logging as logging
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_protocol.models as protocol_models
import octobot_trading.constants as trading_constants
import octobot_trading.errors as trading_errors
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data as trading_personal_data

import octobot_copy.constants as copy_constants
import octobot_copy.entities as copy_entities
import octobot_copy.exchange as copy_exchange
import octobot_copy.orders_mirroring.mirrored_order_replication_failure as mirrored_order_replication_failure
import octobot_copy.orders_mirroring.mirrored_order_replication_failure_util as mirrored_order_replication_failure_util
import octobot_copy.orders_mirroring.mirrored_quantity_compute_result as mirrored_quantity_compute_result


class OrdersSynchronizer:
    """Synches reference account open orders onto the copier exchange (spot mirror rows)."""

    def __init__(
        self,
        reference_account: protocol_models.CopiedAccount,
        exchange_interface: copy_exchange.ExchangeInterface,
        copy_settings: copy_entities.AccountCopySettings,
    ) -> None:
        self._reference_account = reference_account
        self._exchange_interface = exchange_interface
        self._copy_settings = copy_settings
        self._force_immediate_orphan_cancel_next: bool = False
        self._mirrored_orphan_cancel_was_deferred_in_episode: bool = False

    def _get_replicable_reference_orders_from(
        self,
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

    def _get_replicable_reference_orders(self) -> list[protocol_models.Order]:
        return self._get_replicable_reference_orders_from(self._reference_account)

    def _active_reference_order_ids(self, replicable: list[protocol_models.Order]) -> set:
        return {str(order.id) for order in replicable}

    async def cancel_orders_pending_synchronization(
        self,
        replicable_orders: typing.Optional[list[protocol_models.Order]],
    ) -> int:
        """
        Cancel mirrored copier open orders that no longer match a replicable reference open order
        """
        replicable = replicable_orders or self._get_replicable_reference_orders()
        to_keep_ids = self._active_reference_order_ids(replicable)
        return await self._cancel_mirrored_orphan_orders(to_keep_ids, replicable)

    def abort_mirrored_orphan_grace(self) -> None:
        self._force_immediate_orphan_cancel_next = True

    def is_mirrored_orphan_grace_identified(
        self,
        replicable: typing.Optional[list[protocol_models.Order]] = None,
    ) -> bool:
        """True when grace would defer orphan cancel and/or skip reference upserts on at least one symbol."""
        if replicable is None:
            replicable = self._get_replicable_reference_orders()
        return bool(self._reference_symbols_skipped_while_grace_orphans_uncancelled(replicable))

    def is_mirrored_orphan_grace_identified_for_reference_orders(self) -> bool:
        return self.is_mirrored_orphan_grace_identified()

    def is_mirrored_orphan_grace_invalid_no_compliant_snapshot(self) -> bool:
        """
        True when ``historical_snapshots`` is non-empty but no stored snapshot aligns with the copier
        under grace checks, so grace cannot be anchored to history. Empty history is **not** invalid:
        callers without prior reference states use the live account only (see
        ``get_mirrored_orphan_grace_started_at``).
        """
        if not self._reference_account.historical_snapshots:
            return False
        for snapshot in self._reference_account.historical_snapshots:
            if self._reference_state_complies_with_copier_for_grace(snapshot):
                return False
        return True

    def get_mirrored_orphan_grace_started_at(self) -> typing.Optional[float]:
        """
        Wall-clock start of the mirrored-orphan grace window derived from reference
        historical_snapshots and updated_at. With no history, uses ``reference_account.updated_at``.
        None when non-empty history has no compliant snapshot (invalid) or not applicable.
        """
        if not self._reference_account.historical_snapshots:
            return self._reference_account.updated_at
        if self.is_mirrored_orphan_grace_invalid_no_compliant_snapshot():
            return None
        for index, snapshot in enumerate(self._reference_account.historical_snapshots):
            if self._reference_state_complies_with_copier_for_grace(snapshot):
                if index > 0:
                    return self._reference_account.historical_snapshots[index - 1].updated_at
                return self._reference_account.updated_at
        return None

    def _reference_state_complies_with_copier_for_grace(
        self,
        reference_state: protocol_models.CopiedAccount,
    ) -> bool:
        replicable = self._get_replicable_reference_orders_from(reference_state)
        active_reference_ids = self._active_reference_order_ids(replicable)
        orphan_orders = self._mirrored_orphan_open_orders(active_reference_ids)
        orphan_count = len(orphan_orders)
        late_fill_orders = self._late_reference_fill_candidate_orders(
            replicable,
            orphan_orders,
            reference_state,
        )
        late_reference_fill_count = len(late_fill_orders)
        grace_total = orphan_count + late_reference_fill_count
        settings = self._copy_settings
        threshold = settings.mirrored_orphan_grace_abort_threshold
        if grace_total == 0:
            return True
        if grace_total >= threshold:
            return False
        if orphan_count > 0 and not self._mirrored_orphan_batch_eligible_for_grace(
            orphan_orders,
            reference_state,
        ):
            return False
        return True

    def is_mirrored_orphan_grace_aborted_for_missed_historical_signals(self) -> bool:
        """
        True when ``historical_snapshots`` is non-empty, at least one snapshot complies with
        ``_reference_state_complies_with_copier_for_grace``, and the first compliant snapshot is at
        index ``>= missed_signals_grace_abort_threshold`` (newest-first order). Empty history and
        the no-compliant-snapshot invalid case are handled elsewhere.
        """
        snapshots = self._reference_account.historical_snapshots
        if not snapshots:
            return False
        threshold = self._copy_settings.missed_signals_grace_abort_threshold
        for index, snapshot in enumerate(snapshots):
            if self._reference_state_complies_with_copier_for_grace(snapshot):
                return index >= threshold
        return False

    def is_mirrored_orphan_grace_blocking_rebalance(self) -> bool:
        replicable = self._get_replicable_reference_orders()
        active_reference_ids = self._active_reference_order_ids(replicable)
        return self._is_grace_blocking_rebalance(active_reference_ids, replicable)

    def _mirrored_orphan_open_orders(self, active_reference_ids: set) -> list[trading_personal_data.Order]:
        return [
            order
            for order in self._exchange_interface.orders.get_open_orders()
            if order.tag == copy_constants.MIRRORED_ORDER_TAG
            and str(order.order_id) not in active_reference_ids
            and order.order_type
            not in (
                # market orders can't be orphaned or cancelled: they are always filled
                trading_enums.TraderOrderType.BUY_MARKET,
                trading_enums.TraderOrderType.SELL_MARKET,
            )
        ]

    def _reference_pair_leg_share(
        self,
        symbol: str,
        reference_state: typing.Optional[protocol_models.CopiedAccount] = None,
    ) -> typing.Optional[decimal.Decimal]:
        reference_account = reference_state or self._reference_account
        parsed = symbol_util.parse_symbol(symbol)
        base_currency = parsed.base
        quote_currency = parsed.quote
        if not base_currency or not quote_currency:
            return None
        ratios = copy_entities.copied_asset_ratio_by_name(reference_account)
        if base_currency not in ratios:
            return trading_constants.ZERO
        if quote_currency not in ratios:
            return trading_constants.ONE
        allocation_base = ratios[base_currency]
        allocation_quote = ratios[quote_currency]
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

    def _reference_order_execution_price_from_protocol(
        self,
        order: protocol_models.Order,
    ) -> typing.Optional[decimal.Decimal]:
        price_val = order.price
        if price_val not in (None, ""):
            parsed_price = decimal.Decimal(str(price_val))
            if parsed_price > trading_constants.ZERO:
                return parsed_price
        market_price, _ = self._exchange_interface.market.get_potentially_outdated_price(order.symbol)
        if market_price <= trading_constants.ZERO:
            return None
        return market_price

    def _pair_leg_share_value_weighted(
        self,
        base_currency: str,
        quote_currency: str,
        base_amount: decimal.Decimal,
        quote_amount: decimal.Decimal,
    ) -> typing.Optional[decimal.Decimal]:
        if base_amount < trading_constants.ZERO or quote_amount < trading_constants.ZERO:
            return None
        value_base = self._copier_asset_value_in_reference_market(base_currency, base_amount)
        value_quote = self._copier_asset_value_in_reference_market(quote_currency, quote_amount)
        if value_base is None or value_quote is None:
            return None
        value_total = value_base + value_quote
        if value_total <= trading_constants.ZERO:
            return None
        return value_base / value_total

    def _copier_pair_base_quote_totals_for_symbol(
        self,
        symbol: str,
    ) -> typing.Optional[tuple[str, str, decimal.Decimal, decimal.Decimal]]:
        parsed = symbol_util.parse_symbol(symbol)
        base_currency = parsed.base
        quote_currency = parsed.quote
        if not base_currency or not quote_currency:
            return None
        base_total = self._exchange_interface.portfolio.get_currency_portfolio_total(base_currency)
        quote_total = self._exchange_interface.portfolio.get_currency_portfolio_total(quote_currency)
        return (base_currency, quote_currency, base_total, quote_total)

    def _copier_pair_leg_share(self, symbol: str) -> typing.Optional[decimal.Decimal]:
        pair_totals = self._copier_pair_base_quote_totals_for_symbol(symbol)
        if pair_totals is None:
            return None
        base_currency, quote_currency, base_total, quote_total = pair_totals
        return self._pair_leg_share_value_weighted(base_currency, quote_currency, base_total, quote_total)

    def _simulated_copier_pair_leg_share_after_orphan_fill(
        self,
        order: trading_personal_data.Order,
    ) -> typing.Optional[decimal.Decimal]:
        pair_totals = self._copier_pair_base_quote_totals_for_symbol(order.symbol)
        if pair_totals is None:
            return None
        base_currency, quote_currency, base_total, quote_total = pair_totals
        execution_price = self._orphan_order_execution_price(order)
        if execution_price is None:
            return None
        order_quantity = order.origin_quantity
        if order.side is trading_enums.TradeOrderSide.BUY:
            base_adjusted = base_total + order_quantity
            quote_adjusted = quote_total - order_quantity * execution_price
        elif order.side is trading_enums.TradeOrderSide.SELL:
            base_adjusted = base_total - order_quantity
            quote_adjusted = quote_total + order_quantity * execution_price
        else:
            return None
        return self._pair_leg_share_value_weighted(base_currency, quote_currency, base_adjusted, quote_adjusted)

    def _simulated_reference_pair_leg_share_after_order_fill(
        self,
        order: protocol_models.Order,
        reference_state: typing.Optional[protocol_models.CopiedAccount] = None,
    ) -> typing.Optional[decimal.Decimal]:
        reference_account = reference_state or self._reference_account
        symbol = order.symbol
        parsed = symbol_util.parse_symbol(symbol)
        base_currency = parsed.base
        quote_currency = parsed.quote
        if not base_currency or not quote_currency:
            return None
        raw = trading_personal_data.exchange_columns_dict_from_protocol_order(order)
        side, _trader_order_type = trading_personal_data.parse_order_type(raw)
        if side is None:
            return None
        execution_price = self._reference_order_execution_price_from_protocol(order)
        if execution_price is None:
            return None
        order_quantity = decimal.Decimal(str(order.quantity))
        if order_quantity <= trading_constants.ZERO:
            return None
        values = copy_entities.copied_asset_total_by_name(reference_account)
        base_total = values.get(base_currency, trading_constants.ZERO)
        quote_total = values.get(quote_currency, trading_constants.ZERO)
        if side is trading_enums.TradeOrderSide.BUY:
            base_adjusted = base_total + order_quantity
            quote_adjusted = quote_total - order_quantity * execution_price
        elif side is trading_enums.TradeOrderSide.SELL:
            base_adjusted = base_total - order_quantity
            quote_adjusted = quote_total + order_quantity * execution_price
        else:
            return None
        return self._pair_leg_share_value_weighted(base_currency, quote_currency, base_adjusted, quote_adjusted)

    def _passes_late_reference_fill_heuristic(
        self,
        order: protocol_models.Order,
        reference_state: typing.Optional[protocol_models.CopiedAccount] = None,
    ) -> bool:
        symbol = order.symbol
        max_delta = self._copy_settings.mirrored_orphan_grace_pair_ratio_max_delta
        copier_share = self._copier_pair_leg_share(symbol)
        simulated_reference_share = self._simulated_reference_pair_leg_share_after_order_fill(
            order,
            reference_state,
        )
        if copier_share is None or simulated_reference_share is None:
            return False
        return abs(simulated_reference_share - copier_share) <= max_delta

    def _is_late_reference_fill_for_order(
        self,
        order: protocol_models.Order,
        orphan_orders: list[trading_personal_data.Order],
        reference_state: typing.Optional[protocol_models.CopiedAccount] = None,
    ) -> bool:
        reference_order_id = str(order.id)
        if self._find_open_order_by_bot_order_id(reference_order_id) is not None:
            return False
        raw = trading_personal_data.exchange_columns_dict_from_protocol_order(order)
        reference_side, _trader_order_type = trading_personal_data.parse_order_type(raw)
        if reference_side is None:
            return False
        reference_symbol = order.symbol
        reference_timestamp = order.created_at.timestamp()
        for orphan_order in orphan_orders:
            if orphan_order.symbol != reference_symbol:
                continue
            if orphan_order.side == reference_side:
                continue
            orphan_timestamp = orphan_order.creation_time or orphan_order.timestamp
            if orphan_timestamp is None:
                continue
            try:
                orphan_timestamp_float = float(orphan_timestamp)
            except (TypeError, ValueError):
                continue
            if reference_timestamp > orphan_timestamp_float:
                # reference account order was created after the orphan order,
                # on the same symbol and a different side => it likely is the
                # "other side" equivalent of the orphan order: it's not a late reference fill.
                return False
        return self._passes_late_reference_fill_heuristic(order, reference_state)

    def _late_reference_fill_candidate_orders(
        self,
        replicable: list[protocol_models.Order],
        orphan_orders: list[trading_personal_data.Order],
        reference_state: typing.Optional[protocol_models.CopiedAccount],
    ) -> list[protocol_models.Order]:
        return [
            order
            for order in replicable
            if self._is_late_reference_fill_for_order(order, orphan_orders, reference_state)
        ]

    def _mirrored_orphan_batch_eligible_for_grace(
        self,
        orphan_orders: list[trading_personal_data.Order],
        reference_state: typing.Optional[protocol_models.CopiedAccount] = None,
    ) -> bool:
        max_delta = self._copy_settings.mirrored_orphan_grace_pair_ratio_max_delta
        for orphan_order in orphan_orders:
            reference_share = self._reference_pair_leg_share(orphan_order.symbol, reference_state)
            simulated_share = self._simulated_copier_pair_leg_share_after_orphan_fill(orphan_order)
            if reference_share is None or simulated_share is None:
                return False
            if abs(simulated_share - reference_share) > max_delta:
                return False
        return True

    def _is_grace_blocking_rebalance(
        self,
        active_reference_ids: set,
        replicable: list[protocol_models.Order],
    ) -> bool:
        settings = self._copy_settings
        grace_seconds = settings.mirrored_orphan_cancel_grace_seconds
        if grace_seconds <= 0:
            return False
        if self.is_mirrored_orphan_grace_invalid_no_compliant_snapshot():
            return False
        if self.is_mirrored_orphan_grace_aborted_for_missed_historical_signals():
            missed_threshold = settings.missed_signals_grace_abort_threshold
            self._get_logger().info(
                "Mirrored orphans grace period aborted: first compliant reference snapshot index "
                f">= missed_signals_grace_abort_threshold ({missed_threshold})"
            )
            return False
        orphan_orders = self._mirrored_orphan_open_orders(active_reference_ids)
        orphan_count = len(orphan_orders)
        late_reference_fill_count = len(self._late_reference_fill_candidate_orders(replicable, orphan_orders, None))
        grace_total = orphan_count + late_reference_fill_count
        threshold = settings.mirrored_orphan_grace_abort_threshold
        if grace_total == 0:
            return False
        if grace_total >= threshold:
            self._get_logger().info(
                f"Mirrored orphans grace period aborted: {grace_total} grace item(s) >= threshold ({threshold})"
            )
            return False
        if orphan_count > 0 and not self._mirrored_orphan_batch_eligible_for_grace(orphan_orders):
            return False
        started_at = self.get_mirrored_orphan_grace_started_at()
        if started_at is None:
            return True
        now = time.time()
        return (now - started_at) < grace_seconds

    def _reference_symbols_skipped_while_grace_orphans_uncancelled(
        self,
        replicable: list[protocol_models.Order],
    ) -> set[str]:
        """
        Symbols whose mirrored orphan open orders are still on the copier because cancel is deferred
        during the grace window, or symbols with late-reference-fill candidates (copier filled first).
        Reference upserts on these symbols are skipped to avoid stacking a new mirrored side while
        alignment is uncertain.
        """
        settings = self._copy_settings
        grace_seconds = settings.mirrored_orphan_cancel_grace_seconds
        if grace_seconds <= 0:
            return set()
        if self.is_mirrored_orphan_grace_invalid_no_compliant_snapshot():
            return set()
        if self.is_mirrored_orphan_grace_aborted_for_missed_historical_signals():
            return set()
        active_reference_ids = self._active_reference_order_ids(replicable)
        orphan_orders = self._mirrored_orphan_open_orders(active_reference_ids)
        orphan_count = len(orphan_orders)
        late_fill_orders = (
            [] if self._force_immediate_orphan_cancel_next
            else self._late_reference_fill_candidate_orders(replicable, orphan_orders, None)
        )
        late_reference_fill_count = len(late_fill_orders)
        grace_total = orphan_count + late_reference_fill_count
        threshold = settings.mirrored_orphan_grace_abort_threshold
        if grace_total == 0 or grace_total >= threshold:
            return set()
        if orphan_count > 0 and not self._mirrored_orphan_batch_eligible_for_grace(orphan_orders):
            return set()
        started_at = self.get_mirrored_orphan_grace_started_at()
        now = time.time()
        if started_at is not None and (now - started_at) >= grace_seconds:
            return set()
        symbols = {order.symbol for order in orphan_orders}
        for late_order in late_fill_orders:
            symbols.add(late_order.symbol)
        return symbols

    async def synchronize(self) -> list:
        """Align copier open orders with reference_account.orders (synched mirror rows)."""
        async with self._exchange_interface.portfolio.mirror_sync_available_updates():
            return await self._synchronize_impl()

    async def _synchronize_impl(self) -> list:
        """Align copier open orders with reference_account.orders (synched mirror rows)."""
        replicable = self._get_replicable_reference_orders()
        skip_symbols_for_upsert = self._reference_symbols_skipped_while_grace_orphans_uncancelled(replicable)
        skip_symbols_for_upsert = self._maybe_bypass_grace_for_missing_mirrored_reference_orders(
            replicable, skip_symbols_for_upsert
        )
        orphan_cancelled_count = await self.cancel_orders_pending_synchronization(replicable)
        created: list = []
        replaced_cancelled_count = 0
        already_synchronized_count = 0
        skipped_grace_upserts: list[tuple[str, typing.Any]] = []
        replication_failures: list[mirrored_order_replication_failure.MirroredOrderReplicationFailure] = []
        for order in replicable:
            order_symbol = order.symbol
            if order_symbol in skip_symbols_for_upsert:
                skipped_grace_upserts.append(
                    (
                        order_symbol,
                        order.id,
                    )
                )
                replication_failures.append(
                    mirrored_order_replication_failure_util.replication_failure_from_order(
                        order, "grace_period_active"
                    )
                )
                continue
            try:
                batch, replace_count, already_count, replication_failure = (
                    await self._upsert_mirrored_reference_order(order)
                )
                created.extend(batch)
                replaced_cancelled_count += replace_count
                already_synchronized_count += already_count
                if replication_failure is not None:
                    replication_failures.append(replication_failure)
            except trading_errors.MissingMinimalExchangeTradeVolume as err:
                self._get_logger().exception(
                    err,
                    True,
                    f"Skipping synched reference order mirror: {err} ({err.__class__.__name__})",
                )
                replication_failures.append(
                    mirrored_order_replication_failure_util.replication_failure_from_order(
                        order, "min_volume"
                    )
                )
            except trading_errors.OrderCreationError as err:
                self._get_logger().exception(
                    err,
                    True,
                    f"Skipping synched reference order mirror: {err} ({err.__class__.__name__})",
                )
                replication_failures.append(
                    mirrored_order_replication_failure_util.replication_failure_from_order(
                        order, "creation_error"
                    )
                )
        if skipped_grace_upserts:
            skipped_summary = ", ".join(
                mirrored_order_replication_failure_util.format_replication_failure_entry(failure)
                for failure in replication_failures
                if failure.short_reason == "grace_period_active"
            )
            self._get_logger().info(
                "Skipped reference mirror upsert for %s order(s) (mirrored orphan grace period active): %s",
                len(skipped_grace_upserts),
                skipped_summary,
            )
        completion_message = mirrored_order_replication_failure_util.format_order_mirror_completion_message(
            orphan_cancelled_count=orphan_cancelled_count,
            replaced_cancelled_count=replaced_cancelled_count,
            total_created=len(created),
            already_synchronized_count=already_synchronized_count,
            replication_failures=replication_failures,
        )
        self._get_logger().info(completion_message)
        return created

    def _format_grace_deferral_order_details(
        self,
        orphan_orders: list[trading_personal_data.Order],
        late_fill_orders: list[protocol_models.Order],
    ) -> str:
        detail_parts: list[str] = []
        if orphan_orders:
            detail_parts.append(
                "orphan order(s): "
                f"{mirrored_order_replication_failure_util.format_mirrored_orphan_orders_summary(orphan_orders)}"
            )
        if late_fill_orders:
            detail_parts.append(
                "late-reference-fill candidate(s): "
                f"{mirrored_order_replication_failure_util.format_late_reference_fill_candidates_summary(late_fill_orders)}"
            )
        if not detail_parts:
            return ""
        return "; " + "; ".join(detail_parts)

    async def _cancel_mirrored_orphan_orders(
        self,
        active_reference_ids: set,
        replicable: list[protocol_models.Order],
    ) -> int:
        orphan_orders = self._mirrored_orphan_open_orders(active_reference_ids)
        return await self._apply_grace_policy_and_cancel_mirrored_orphans(orphan_orders, replicable)

    async def _apply_grace_policy_and_cancel_mirrored_orphans(
        self,
        orphan_orders: list[trading_personal_data.Order],
        replicable: list[protocol_models.Order],
    ) -> int:
        """
        When mirrored orphans exist and/or late-reference-fill candidates exist (or neither, to clear
        grace state): defer cancel during an active grace window unless ``abort_mirrored_orphan_grace``
        requested immediate cancel, grace is disabled, combined count reaches abort threshold,
        no compliant reference snapshot exists in ``historical_snapshots``, or wall-clock grace
        (from ``get_mirrored_orphan_grace_started_at()``) has elapsed, or when the first compliant
        reference snapshot is too deep in ``historical_snapshots`` (missed historical signals abort).
        """
        settings = self._copy_settings
        late_fill_orders = self._late_reference_fill_candidate_orders(replicable, orphan_orders, None)
        late_reference_fill_count = len(late_fill_orders)
        orphan_count = len(orphan_orders)
        grace_total = orphan_count + late_reference_fill_count

        # Idle: reset abort flag. Log episode cleared only after a prior deferral of orphan cancel.
        if grace_total == 0:
            self._force_immediate_orphan_cancel_next = False
            had_cancel_deferred_while_aligned = self._mirrored_orphan_cancel_was_deferred_in_episode
            self._mirrored_orphan_cancel_was_deferred_in_episode = False
            if had_cancel_deferred_while_aligned:
                self._get_logger().info(
                    "Mirrored open-order grace episode cleared: no mirrored orphan orders remain "
                    "and no late-reference-fill candidates."
                )
            return 0

        grace_seconds = settings.mirrored_orphan_cancel_grace_seconds
        threshold = settings.mirrored_orphan_grace_abort_threshold
        # Explicit abort or grace disabled: cancel orphans immediately, do not start or extend grace.
        if self._force_immediate_orphan_cancel_next or grace_seconds <= 0:
            self._mirrored_orphan_cancel_was_deferred_in_episode = False
            return await self._cancel_mirrored_orphan_order_list(orphan_orders)

        # No compliant snapshot in reference history: cannot anchor grace; same outcome as runaway desync.
        if self.is_mirrored_orphan_grace_invalid_no_compliant_snapshot():
            self._get_logger().info(
                "Mirrored orphan grace invalid: no compliant reference snapshot in history; "
                "cancelling orphan order(s) immediately (full resync required)."
            )
            self._mirrored_orphan_cancel_was_deferred_in_episode = False
            return await self._cancel_mirrored_orphan_order_list(orphan_orders)

        if self.is_mirrored_orphan_grace_aborted_for_missed_historical_signals():
            missed_threshold = settings.missed_signals_grace_abort_threshold
            self._get_logger().info(
                "Mirrored orphan grace aborted: first compliant reference snapshot index "
                f">= missed_signals_grace_abort_threshold ({missed_threshold}); "
                "cancelling orphan order(s) immediately (reference history desync)."
            )
            self._mirrored_orphan_cancel_was_deferred_in_episode = False
            return await self._cancel_mirrored_orphan_order_list(orphan_orders)

        # Too many grace items at once: treat as runaway desync, cancel orphans immediately.
        if grace_total >= threshold:
            self._get_logger().info(
                f"Mirrored orphan grace aborted: {grace_total} grace item(s) >= threshold {threshold} "
                f"({orphan_count} orphan(s), {late_reference_fill_count} late-reference-fill candidate(s))"
            )
            self._mirrored_orphan_cancel_was_deferred_in_episode = False
            return await self._cancel_mirrored_orphan_order_list(orphan_orders)

        # Orphans present but pair-ratio heuristic fails: cancel those orphans; may still defer on late fills.
        if orphan_count > 0 and not self._mirrored_orphan_batch_eligible_for_grace(orphan_orders):
            cancelled = await self._cancel_mirrored_orphan_order_list(orphan_orders)
            if late_reference_fill_count == 0:
                had_grace_window = self.get_mirrored_orphan_grace_started_at() is not None
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
                self._mirrored_orphan_cancel_was_deferred_in_episode = False
                return cancelled
            # Orphans cancelled; continue grace driven by late-reference fills (do not exit deferral here).
            orphan_orders = []
            orphan_count = 0
            grace_total = late_reference_fill_count
            continuation_details = self._format_grace_deferral_order_details([], late_fill_orders)
            self._get_logger().info(
                f"Mirrored orphan grace ineligible for orphan deferral; {cancelled} orphan order(s) cancelled. "
                f"Continuing grace window for {late_reference_fill_count} late-reference-fill candidate(s)"
                f"{continuation_details}"
            )

        # Grace window start time is derived from reference historical_snapshots + updated_at (not wall time here).
        now = time.time()
        started_at = self.get_mirrored_orphan_grace_started_at()
        if started_at is None:
            self._get_logger().info(
                "Mirrored orphan grace: could not resolve grace start from reference history; "
                "cancelling orphan order(s) immediately."
            )
            self._mirrored_orphan_cancel_was_deferred_in_episode = False
            return await self._cancel_mirrored_orphan_order_list(orphan_orders)
        # Still inside grace window: wait for copier fills / alignment.
        if (now - started_at) < grace_seconds:
            remaining_seconds = grace_seconds - (now - started_at)
            deferral_details = self._format_grace_deferral_order_details(orphan_orders, late_fill_orders)
            self._get_logger().info(
                f"Mirrored orphan cancel deferred: {orphan_count} orphan(s), "
                f"{late_reference_fill_count} late-reference-fill candidate(s), "
                f"{remaining_seconds:.1f}s grace remaining"
                f"{deferral_details}"
            )
            self._mirrored_orphan_cancel_was_deferred_in_episode = True
            return 0

        # Grace window finished: cancel orphans that are still open.
        self._get_logger().info(
            f"Mirrored orphan grace elapsed after {grace_seconds}s: cancelling {orphan_count} orphan(s)"
        )
        self._mirrored_orphan_cancel_was_deferred_in_episode = False
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
        order: protocol_models.Order,
        symbol: str,
        side: trading_enums.TradeOrderSide,
    ) -> typing.Optional[decimal.Decimal]:
        # Spot: sells spend base, buys spend quote — scale the reference order amount by the same leg's
        # holdings ratio. This will need to be adapted for futures (margin/position sizing, not spot wallets).
        parsed = symbol_util.parse_symbol(symbol)
        scale_currency = parsed.quote if side is trading_enums.TradeOrderSide.BUY else parsed.base
        values = copy_entities.copied_asset_total_by_name(self._reference_account)
        reference_total = values.get(scale_currency, trading_constants.ZERO)
        if reference_total <= trading_constants.ZERO:
            return None
        copier_total = self._exchange_interface.portfolio.get_currency_portfolio_total(scale_currency)
        amount = decimal.Decimal(str(order.quantity))
        if amount <= trading_constants.ZERO:
            return None
        scale = copier_total / reference_total
        return amount * scale

    def _find_open_order_by_bot_order_id(self, order_id: str) -> typing.Optional[trading_personal_data.Order]:
        for order in self._exchange_interface.orders.get_open_orders():
            if str(order.order_id) == str(order_id):
                return order
        return None

    def _count_unmirrored_reference_orders(self, replicable: list[protocol_models.Order]) -> int:
        missing_count = 0
        for order in replicable:
            if self._find_open_order_by_bot_order_id(str(order.id)) is None:
                missing_count += 1
        return missing_count

    def _maybe_bypass_grace_for_missing_mirrored_reference_orders(
        self,
        replicable: list[protocol_models.Order],
        skip_symbols_for_upsert: set[str],
    ) -> set[str]:
        if not skip_symbols_for_upsert:
            return skip_symbols_for_upsert
        missing_count = self._count_unmirrored_reference_orders(replicable)
        threshold = self._copy_settings.mirrored_orphan_grace_abort_threshold
        if missing_count > threshold:
            self._get_logger().info(
                f"Bypassing mirrored orphan grace: {missing_count} reference order(s) "
                f"missing on copier (> abort threshold {threshold})"
            )
            self.abort_mirrored_orphan_grace()
            return set()
        return skip_symbols_for_upsert

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
        quantity_tolerance = ideal_quantity * self._copy_settings.mirrored_order_quantity_ratio_threshold
        quantity_threshold = max(quantity_tolerance, decimal.Decimal("1e-12"))
        if abs(order.origin_quantity - ideal_quantity) > quantity_threshold:
            return (
                f"quantity mismatch (open_order={order.origin_quantity}, target={ideal_quantity}, "
                f"threshold={quantity_threshold})"
            )
        if trading_personal_data.get_trade_order_type(order_type) is trading_enums.TradeOrderType.MARKET:
            return None
        price_tolerance = order_target_price * self._copy_settings.mirrored_order_price_ratio_threshold
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

    async def _upsert_mirrored_reference_order(
        self,
        order: protocol_models.Order,
    ) -> tuple[list, int, int, typing.Optional[mirrored_order_replication_failure.MirroredOrderReplicationFailure]]:
        raw = trading_personal_data.exchange_columns_dict_from_protocol_order(order)
        symbol = order.symbol
        side, trader_order_type = trading_personal_data.parse_order_type(raw)
        if side is None or trader_order_type is None:
            self._get_logger().info(
                f"Skipping reference order mirror: unsupported type for {symbol} ({trader_order_type})"
            )
            return [], 0, 0, None
        reference_order_id = str(order.id)
        existing = self._find_open_order_by_bot_order_id(reference_order_id)
        replicable_orders = self._get_replicable_reference_orders()
        active_reference_ids = self._active_reference_order_ids(replicable_orders)
        orphan_orders = self._mirrored_orphan_open_orders(active_reference_ids)
        if existing is None and not self._force_immediate_orphan_cancel_next and self._is_late_reference_fill_for_order(order, orphan_orders):
            self._get_logger().info(
                f"Skipping mirrored order creation (late reference fill on copier): symbol={symbol} "
                f"reference_order_id={reference_order_id}"
            )
            return [], 0, 0, None
        scaled_quantity = self._scale_mirrored_order_quantity(order, symbol, side)
        if scaled_quantity is None or scaled_quantity <= trading_constants.ZERO:
            return mirrored_order_replication_failure_util.upsert_failure_return(
                self._get_logger(),
                order,
                "zero_scaled_quantity",
                trader_order_type,
                **mirrored_order_replication_failure_util.mirror_scale_failure_context(
                    order,
                    symbol,
                    side,
                    scaled_quantity,
                    self._reference_account,
                    self._exchange_interface,
                ),
            )
        current_price_val = order.price
        order_target_price = (
            decimal.Decimal(str(current_price_val))
            if current_price_val not in (None, "")
            else trading_constants.ZERO
        )
        compute_result = await self._compute_mirrored_quantity_type_and_price(
            symbol,
            side,
            scaled_quantity,
            order_target_price,
            trader_order_type,
            open_mirrored_order=existing,
        )
        ideal_quantity = compute_result.ideal_quantity
        resolved_type = compute_result.resolved_trader_order_type
        market_or_limit_price = compute_result.limit_price
        current_price = compute_result.current_price
        if ideal_quantity <= trading_constants.ZERO:
            short_reason = compute_result.zero_short_reason or "zero_target_quantity"
            return mirrored_order_replication_failure_util.upsert_failure_return(
                self._get_logger(),
                order,
                short_reason,
                trader_order_type,
                scaled_quantity=scaled_quantity,
                ideal_quantity=ideal_quantity,
                order_target_price=order_target_price,
                available_market_holding=compute_result.available_market_holding,
                available_symbol_holding=compute_result.available_symbol_holding,
                total_symbol_holding=compute_result.total_symbol_holding,
                quote_for_cap=compute_result.quote_for_cap,
            )
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
                return [], 0, 1, None
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
        pre_adapt_quantity = ideal_quantity
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
        if ideal_quantity <= trading_constants.ZERO:
            return mirrored_order_replication_failure_util.upsert_failure_return(
                self._get_logger(),
                order,
                "post_adapt_zero_quantity",
                trader_order_type,
                pre_adapt_quantity=pre_adapt_quantity,
                post_adapt_quantity=ideal_quantity,
            )
        created, orders_should_have_been_created = await self._exchange_interface.orders.create_orders(
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
        out = [created_order for created_order in created if created_order is not None]
        if not out and ideal_quantity > trading_constants.ZERO:
            return mirrored_order_replication_failure_util.upsert_failure_return(
                self._get_logger(),
                order,
                "create_returned_empty",
                trader_order_type,
                ideal_quantity=ideal_quantity,
                orders_should_have_been_created=orders_should_have_been_created,
            )
        for created_order in out:
            self._get_logger().info(
                f"Created mirrored order: symbol={created_order.symbol} "
                f"bot_order_id={created_order.order_id} side={created_order.side} type={created_order.order_type} "
                f"quantity={created_order.origin_quantity} (reference_id={reference_order_id})"
            )
        return out, replaced_cancelled, 0, None

    async def _compute_mirrored_quantity_type_and_price(
        self,
        symbol: str,
        side: trading_enums.TradeOrderSide,
        scaled_quantity: decimal.Decimal,
        order_target_price: decimal.Decimal,
        trader_order_type: trading_enums.TraderOrderType,
        open_mirrored_order: typing.Optional[trading_personal_data.Order] = None,
    ) -> mirrored_quantity_compute_result.MirroredQuantityComputeResult:
        # Buys cap using free quote for new orders (sibling buys reserve quote). When re-checking an open
        # mirrored buy, add this order's locked quote back so ideal size matches portfolio semantics.
        # New sells use total base (sibling sell locks still count). Open mirrored sells use available
        # base plus this order's locked base for the same reason as buys.
        (
            total_symbol_holding,
            _total_market_holding,
            _market_quantity,
            current_price,
            _symbol_market,
        ) = await self._exchange_interface.orders.get_pre_order_data(
            symbol=symbol,
            timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT,
            portfolio_type=commons_constants.PORTFOLIO_TOTAL,
        )
        (
            available_symbol_holding,
            available_market_holding,
            _available_market_quantity,
            _unused_price,
            _unused_symbol_market,
        ) = await self._exchange_interface.orders.get_pre_order_data(
            symbol=symbol,
            timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT,
            portfolio_type=commons_constants.PORTFOLIO_AVAILABLE,
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
        quote_for_cap: typing.Optional[decimal.Decimal] = None
        if side is trading_enums.TradeOrderSide.BUY:
            quote_for_cap = available_market_holding
            if (
                open_mirrored_order is not None
                and open_mirrored_order.side is trading_enums.TradeOrderSide.BUY
            ):
                quote_for_cap = available_market_holding + self._exchange_interface.orders.get_order_locked_amount(
                    open_mirrored_order
                )
            target_quantity = min(
                scaled_quantity,
                quote_for_cap / effective_target_price
                if effective_target_price
                else scaled_quantity,
            )
        elif (
            open_mirrored_order is not None
            and open_mirrored_order.side is trading_enums.TradeOrderSide.SELL
        ):
            base_budget = available_symbol_holding + self._exchange_interface.orders.get_order_locked_amount(
                open_mirrored_order
            )
            target_quantity = min(scaled_quantity, base_budget)
        else:
            target_quantity = min(scaled_quantity, total_symbol_holding)
        zero_short_reason: typing.Optional[str] = None
        if target_quantity <= trading_constants.ZERO:
            zero_short_reason = (
                "insufficient_quote"
                if side is trading_enums.TradeOrderSide.BUY
                else "insufficient_base"
            )
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
                zero_short_reason = "below_min_volume"
                target_quantity = trading_constants.ZERO
            else:
                target_quantity = sum(
                    (quantity for quantity, _ in adapted_details),
                    trading_constants.ZERO,
                )
                limit_price = adapted_details[0][1]
        return mirrored_quantity_compute_result.MirroredQuantityComputeResult(
            ideal_quantity=target_quantity,
            resolved_trader_order_type=resolved_trader_order_type,
            limit_price=limit_price,
            current_price=current_price,
            zero_short_reason=zero_short_reason,
            scaled_quantity=scaled_quantity,
            available_market_holding=available_market_holding,
            available_symbol_holding=available_symbol_holding,
            total_symbol_holding=total_symbol_holding,
            quote_for_cap=quote_for_cap,
        )

    def _get_logger(self) -> logging.BotLogger:
        return logging.get_logger(self.__class__.__name__)
