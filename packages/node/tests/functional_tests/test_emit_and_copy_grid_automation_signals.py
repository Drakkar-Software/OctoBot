#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at your
#  option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful, but WITHOUT ANY
#  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#  FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along with
#  OctoBot. If not, see https://www.gnu.org/licenses/.
from __future__ import annotations

import asyncio
import datetime
import decimal
import json
import logging
import mock
import os
import tempfile
import time
import typing

import pytest

import octobot_flow.repositories.community.trading_signals_channel as trading_signals_channel_module
import octobot_node.scheduler
import octobot_node.scheduler.internal_trading_signals as internal_trading_signals_module
import octobot_protocol.models as octobot_protocol_models
import octobot_node.scheduler.tasks
import starfish_server.config.schema as starfish_server_config_schema

from . import grid_workflow_simulator_test_util as grid_sim_util
from tests.scheduler import temp_dbos_scheduler


IMPORTED_OCTOBOT_FLOW_GRID_DEPS = False
if grid_sim_util.IMPORTED_OCTOBOT_FLOW_GRID_DEPS:
    try:
        import octobot.community.local_authenticator as local_authenticator_module
        import octobot_commons.constants as octobot_commons_constants_module
        import octobot_commons.os_util as commons_os_util_module
        import octobot_copy.constants as octobot_copy_constants_module
        import octobot_flow.entities as octobot_flow_entities
        import octobot_flow.repositories.community as octobot_flow_repositories_community_module
        import octobot_flow.repositories.exchange as octobot_flow_repositories_exchange_module
        import octobot_trading.enums as trading_enums_module
        import octobot_sync.constants as octobot_sync_constants_module
        import octobot_sync.server as octobot_sync_server_module
        import octobot_sync.sync.collections as sync_collections_module
        import starlette.routing as starlette_routing_module
        import uvicorn
        IMPORTED_OCTOBOT_FLOW_GRID_DEPS = True
    except ImportError:
        octobot_flow = None  # type: ignore
        octobot_commons_constants_module = None  # type: ignore
        octobot_copy_constants_module = None  # type: ignore
        octobot_flow_entities = None  # type: ignore
        octobot_flow_repositories_exchange_module = None  # type: ignore
        octobot_flow_repositories_community_module = None  # type: ignore
        local_authenticator_module = None  # type: ignore
        commons_os_util_module = None  # type: ignore
        octobot_sync_constants_module = None  # type: ignore
        octobot_sync_server_module = None  # type: ignore
        sync_collections_module = None  # type: ignore
        starlette_routing_module = None  # type: ignore
        uvicorn = None  # type: ignore


_COPY_AUTOMATION_ID = "copy_grid_follower"
_SHARED_STRATEGY_ID = "functional_test_copy_strategy"

_MASTER_INIT_USDC = 10000.0
_COPY_INIT_USDC = 2000.0

_T_ENQUEUE_SECONDS = 5.0
_T_GRID_SECONDS = 25.0
_T_BOOTSTRAP_COPY_SECONDS = 25.0
_T_POST_SHOCK_SECONDS = 55.0
_T_STOP_SEND_SECONDS = 5.0
_T_STOP_COMPLETE_SECONDS = 15.0

_D_DECIMAL_INCREMENT = decimal.Decimal(str(grid_sim_util.GRID_INCREMENT))

# Fixed 32-byte secret (hex) for local Starfish identity-encrypted collections; not used outside this test.
_FUNCTIONAL_TEST_SYNC_ENCRYPTION_SECRET = "0123456789abcdef" * 4


if IMPORTED_OCTOBOT_FLOW_GRID_DEPS:

    def _grid_functional_test_sync_config():
        """Package default sync config plus a collection for ``TradingSignalsRepository`` HTTP paths."""
        base_config = sync_collections_module.DEFAULT_SYNC_CONFIG
        sync_namespace_key = sync_collections_module.constants.SYNC_NAMESPACE
        assert base_config.namespaces is not None
        assert sync_namespace_key in base_config.namespaces
        octobot_namespace = base_config.namespaces[sync_namespace_key]
        trading_signals_collection = sync_collections_module.CollectionConfig(
            name="trading-signals",
            storagePath="products/{strategyId}/{version}/signals",
            readRoles=["public"],
            writeRoles=["public"],
            encryption="none",
            maxBodyBytes=octobot_sync_constants_module.MAX_BODY_SIZE_SIGNAL,
            appendOnly=starfish_server_config_schema.AppendOnlyConfig(
                type="by_timestamp",
                requireAuthorSignature=False,
            ),
        )
        extended_octobot = sync_collections_module.NamespaceConfig(
            collections=[*octobot_namespace.collections, trading_signals_collection],
        )
        return base_config.model_copy(
            update={
                "namespaces": {
                    **dict(base_config.namespaces),
                    sync_namespace_key: extended_octobot,
                }
            }
        )

    def _post_fill_open_order_shape(buy_count: int, sell_count: int) -> bool:
        """Accept expected post-shock ladder shapes after forced trigger and mirroring."""
        return buy_count == 3 and sell_count == 1

    def _account_for_id(
        *,
        account_id: str,
        master_account_id: str,
        master_account: typing.Any,
        copy_account_id: str,
        copy_account: typing.Any,
    ) -> typing.Any:
        if account_id == master_account_id:
            return master_account
        if account_id == copy_account_id:
            return copy_account
        raise AssertionError(f"Unexpected account_id lookup: {account_id!r}")

    def _d_order_price(raw: typing.Union[int, float, str, decimal.Decimal]) -> decimal.Decimal:
        if isinstance(raw, decimal.Decimal):
            return raw
        return decimal.Decimal(str(raw))

    def _sorted_limit_prices_from_elements(
        exchange_account_elements: typing.Any,
        *,
        trade_order_side,
    ) -> list[decimal.Decimal]:
        if exchange_account_elements is None:
            return []
        orders_container = getattr(exchange_account_elements, "orders", None)
        if orders_container is None and isinstance(exchange_account_elements, dict):
            orders_container = exchange_account_elements.get("orders")
        if orders_container is None:
            return []
        open_orders = getattr(orders_container, "open_orders", None)
        if open_orders is None and isinstance(orders_container, dict):
            open_orders = orders_container.get("open_orders", [])
        open_orders = open_orders or []

        storage_origin = grid_sim_util.trading_constants_module.STORAGE_ORIGIN_VALUE

        def _open_order_payload(order_row: typing.Any) -> typing.Any:
            """Exchange rows may nest ccxt fields under ``STORAGE_ORIGIN_VALUE``; protocol orders are flat."""
            if isinstance(order_row, dict):
                nested = order_row.get(storage_origin)
                if isinstance(nested, dict):
                    return nested
                return order_row
            nested = getattr(order_row, storage_origin, None)
            if nested is not None:
                return nested
            return order_row

        side_key = trading_enums_module.ExchangeConstantsOrderColumns.SIDE.value
        price_col = trading_enums_module.ExchangeConstantsOrderColumns.PRICE.value
        type_col = trading_enums_module.ExchangeConstantsOrderColumns.TYPE.value
        want_side = trade_order_side.value
        limit_type = trading_enums_module.TradeOrderType.LIMIT.value
        prices: list[decimal.Decimal] = []
        for order in open_orders:
            payload = _open_order_payload(order)
            if isinstance(payload, dict):
                side = payload.get(side_key)
                price_raw = payload.get(price_col)
                order_type = payload.get(type_col)
            else:
                side = getattr(payload, side_key, None)
                price_raw = getattr(payload, price_col, None)
                order_type = getattr(payload, type_col, None)
            if hasattr(side, "value"):
                side = side.value
            if side != want_side:
                continue
            if price_raw is None:
                continue
            if hasattr(order_type, "value"):
                order_type = order_type.value
            if order_type is not None and order_type != limit_type:
                continue
            prices.append(_d_order_price(price_raw))
        prices.sort()
        return prices

    def _assert_open_limit_prices_match_reference(
        reference_elements: typing.Any,
        follower_elements: typing.Any,
    ) -> None:
        for side in (
            trading_enums_module.TradeOrderSide.BUY,
            trading_enums_module.TradeOrderSide.SELL,
        ):
            ref_prices = _sorted_limit_prices_from_elements(reference_elements, trade_order_side=side)
            got_prices = _sorted_limit_prices_from_elements(follower_elements, trade_order_side=side)
            assert ref_prices == got_prices, f"side={side!r} ref={ref_prices!s} follower={got_prices!s}"

    def _portfolio_content_from_exchange_elements(exchange_account_elements: typing.Any) -> dict[str, typing.Any]:
        portfolio = getattr(exchange_account_elements, "portfolio", None)
        if portfolio is None and isinstance(exchange_account_elements, dict):
            portfolio = exchange_account_elements.get("portfolio")
        if portfolio is None:
            return {}
        content = getattr(portfolio, "content", None)
        if content is None and isinstance(portfolio, dict):
            content = portfolio.get("content")
        return content if isinstance(content, dict) else {}

    def _portfolio_row_total(row: typing.Any) -> decimal.Decimal:
        total_key = octobot_commons_constants_module.PORTFOLIO_TOTAL
        if isinstance(row, dict):
            raw = row.get(total_key, row.get("total"))
        else:
            raw = getattr(row, total_key, None) or getattr(row, "total", None)
        if raw is None:
            raise AssertionError("portfolio row has no total amount")
        return raw if isinstance(raw, decimal.Decimal) else decimal.Decimal(str(raw))

    def _value_weighted_btc_usdc_shares(
        content: dict[str, typing.Any],
        *,
        btc_usdc_close: decimal.Decimal,
    ) -> dict[str, decimal.Decimal]:
        """USDC notionals: ``btc_total * btc_usdc_close`` vs USDC total; shares sum to 1."""
        for asset in ("BTC", "USDC"):
            assert asset in content, f"missing portfolio row for {asset}"
        btc_total = _portfolio_row_total(content["BTC"])
        usdc_total = _portfolio_row_total(content["USDC"])
        btc_notional_usdc = btc_total * btc_usdc_close
        usdc_notional = usdc_total
        total_notional = btc_notional_usdc + usdc_notional
        assert total_notional > 0, "expected positive portfolio value in USDC"
        return {
            "BTC": btc_notional_usdc / total_notional,
            "USDC": usdc_notional / total_notional,
        }

    def _assert_btc_usdc_value_shares_match_reference(
        reference_elements: typing.Any,
        follower_elements: typing.Any,
        *,
        btc_usdc_close: decimal.Decimal,
    ) -> None:
        ref_content = _portfolio_content_from_exchange_elements(reference_elements)
        follower_content = _portfolio_content_from_exchange_elements(follower_elements)
        ref_shares = _value_weighted_btc_usdc_shares(ref_content, btc_usdc_close=btc_usdc_close)
        follower_shares = _value_weighted_btc_usdc_shares(follower_content, btc_usdc_close=btc_usdc_close)
        # ~3 percentage points slack (master vs copy notionals / float portfolio totals).
        max_abs_diff = decimal.Decimal("0.03")
        for asset in ("BTC", "USDC"):
            delta = abs(ref_shares[asset] - follower_shares[asset])
            assert delta <= max_abs_diff, (
                f"{asset} value-share mismatch ref={ref_shares[asset]!s} "
                f"follower={follower_shares[asset]!s} (abs diff {delta!s}, max {max_abs_diff!s}) "
                f"at close={btc_usdc_close!s}"
            )

    def _first_sell_limit_price(exchange_account_elements: typing.Any) -> decimal.Decimal:
        sells = _sorted_limit_prices_from_elements(
            exchange_account_elements,
            trade_order_side=trading_enums_module.TradeOrderSide.SELL,
        )
        assert sells, "expected at least one open sell limit"
        return sells[0]

    def _first_fetched_trading_signal(fetched: list[typing.Any]) -> octobot_flow_entities.TradingSignal:
        assert fetched, "expected fetch_trading_signals to return at least one entry"
        entry = fetched[0]
        if isinstance(entry, list):
            assert entry, "expected non-empty signals list in fetch payload"
            return entry[-1]
        return entry

    def _sorted_limit_prices_from_trading_signal_account(
        trading_signal: octobot_flow_entities.TradingSignal,
        *,
        trade_order_side,
    ) -> list[decimal.Decimal]:
        wrapper = {"orders": {"open_orders": list(trading_signal.account.orders or [])}}
        return _sorted_limit_prices_from_elements(wrapper, trade_order_side=trade_order_side)

    async def _fetch_strategy_signals_from_sync(wallet_address: str) -> list[typing.Any]:
        async with local_authenticator_module.local_user_authenticator() as auth:
            repository = octobot_flow_repositories_community_module.TradingSignalsRepository.from_community_repository(
                octobot_flow_repositories_community_module.CommunityRepository(auth, wallet_address)
            )
            return await repository.fetch_trading_signals(
                [_SHARED_STRATEGY_ID],
                octobot_copy_constants_module.DEFAULT_MISSED_SIGNALS_GRACE_ABORT_THRESHOLD,
            )

    def _ladder_limit_prices_match_reference(
        trading_signal: octobot_flow_entities.TradingSignal,
        reference_exchange_account_elements: typing.Any,
    ) -> tuple[bool, str]:
        mismatch_parts: list[str] = []
        for order_side in (
            trading_enums_module.TradeOrderSide.BUY,
            trading_enums_module.TradeOrderSide.SELL,
        ):
            reference_prices = _sorted_limit_prices_from_elements(
                reference_exchange_account_elements,
                trade_order_side=order_side,
            )
            pulled_prices = _sorted_limit_prices_from_trading_signal_account(
                trading_signal,
                trade_order_side=order_side,
            )
            if reference_prices != pulled_prices:
                mismatch_parts.append(
                    f"{order_side.value}: ref={reference_prices!s} pulled={pulled_prices!s}"
                )
        if not mismatch_parts:
            return True, ""
        return False, "; ".join(mismatch_parts)

    async def _poll_fetched_trading_signal_until_ladder_matches(
        wallet_address: str,
        reference_exchange_account_elements: typing.Any,
        deadline_seconds: float,
        failure_label: str,
    ) -> octobot_flow_entities.TradingSignal:
        """Wait until ``fetch_trading_signals`` matches the reference ladder (upload can lag the reader)."""
        poll_interval = grid_sim_util.DEFAULT_GRID_WORKFLOW_POLL_INTERVAL_SECONDS
        poll_deadline = time.monotonic() + deadline_seconds
        last_mismatch = ""
        while time.monotonic() < poll_deadline:
            fetched_batch = await _fetch_strategy_signals_from_sync(wallet_address)
            if fetched_batch:
                candidate_signal = _first_fetched_trading_signal(fetched_batch)
                matches, detail = _ladder_limit_prices_match_reference(
                    candidate_signal,
                    reference_exchange_account_elements,
                )
                if matches:
                    return candidate_signal
                last_mismatch = detail
            await asyncio.sleep(poll_interval)
        pytest.fail(f"Timed out waiting for {failure_label} ({last_mismatch})")

    async def _poll_state_reader_until(
        scheduler,
        automation_id: str,
        predicate: typing.Callable[[typing.Any], bool],
        deadline_seconds: float,
        failure_label: str,
    ) -> typing.Any:
        poll_interval = grid_sim_util.DEFAULT_GRID_WORKFLOW_POLL_INTERVAL_SECONDS
        poll_deadline = time.monotonic() + deadline_seconds
        last_reader: typing.Any = None
        while time.monotonic() < poll_deadline:
            workflow_rows = await scheduler.INSTANCE.list_workflows_async()
            for workflow_row in workflow_rows:
                if grid_sim_util.workflows_util_module.get_automation_id(workflow_row) != automation_id:
                    continue
                state_reader = grid_sim_util.workflows_util_module.get_automation_state_reader(workflow_row)
                if state_reader is None:
                    continue
                last_reader = state_reader
                if predicate(state_reader):
                    return state_reader
            await asyncio.sleep(poll_interval)
        detail = "no reader"
        if last_reader is not None:
            elements = last_reader.state.automation.exchange_account_elements
            detail = (
                f"last counts={grid_sim_util.buy_sell_trade_counts_from_exchange_elements(elements)}"
            )
        pytest.fail(f"Timed out waiting for {failure_label} ({detail})")

    _ORDERS_SYNCHRONIZER_LOGGER = "OrdersSynchronizer"
    _FORBIDDEN_ORDERS_SYNC_SUBSTRINGS = (
        "Cancelling mirrored order for replace",
        "Cancelled mirrored order for replace",
        "Mirrored orphan grace elapsed after",
        "Cancelled mirrored orphan order",
    )

    def _assert_orders_synchronizer_no_mirror_cancel_or_grace_logs(caplog) -> None:
        for record in caplog.records:
            if record.name != _ORDERS_SYNCHRONIZER_LOGGER:
                continue
            message_text = record.getMessage()
            for forbidden in _FORBIDDEN_ORDERS_SYNC_SUBSTRINGS:
                assert forbidden not in message_text, (
                    f"unexpected OrdersSynchronizer log ({forbidden!r}): {message_text!r}"
                )

    def _workflow_row_id_matches_user_action_selector_created_automation_id(
        *,
        workflow_row_id: str,
        user_action_selector_created_automation_id: str | None,
    ) -> None:
        assert user_action_selector_created_automation_id
        assert (
            workflow_row_id == user_action_selector_created_automation_id
            or workflow_row_id.startswith(f"{user_action_selector_created_automation_id}_")
        ), (
            f"workflow row id {workflow_row_id!r} should equal or extend user action selector created_automation_id "
            f"{user_action_selector_created_automation_id!r}"
        )

    def _merge_user_actions_latest_per_id(
        user_actions: list[octobot_protocol_models.UserAction],
    ) -> dict[str, octobot_protocol_models.UserAction]:
        grouped: dict[str, list[octobot_protocol_models.UserAction]] = {}
        for user_action in user_actions:
            grouped.setdefault(user_action.id, []).append(user_action)
        min_utc = datetime.datetime.min.replace(tzinfo=datetime.UTC)

        def activity_stamp(user_action: octobot_protocol_models.UserAction) -> datetime.datetime:
            stamp = user_action.updated_at or user_action.created_at
            if stamp is None:
                return min_utc
            if stamp.tzinfo is None:
                return stamp.replace(tzinfo=datetime.UTC)
            return stamp

        return {
            user_action_id: max(group, key=activity_stamp)
            for user_action_id, group in grouped.items()
        }

    async def _assert_user_action_selector_completed_automation_create(
        *,
        wallet_address: str,
        user_action_id: str,
        expected_workflow_id: str | None,
    ) -> None:
        listed = await octobot_node.scheduler.SCHEDULER.list_user_actions(wallet_address)
        by_id = _merge_user_actions_latest_per_id(listed)
        assert user_action_id in by_id, f"expected {user_action_id!r} in user action workflows, got {sorted(by_id)!r}"
        stored = by_id[user_action_id]
        assert stored.status == octobot_protocol_models.UserActionStatus.COMPLETED
        assert stored.result is not None
        inner = stored.result.actual_instance
        assert isinstance(inner, octobot_protocol_models.AutomationActionResult)
        assert inner.result_type == octobot_protocol_models.UserActionResultType.AUTOMATION
        assert inner.error_details is None
        assert inner.error_message is None
        if expected_workflow_id is not None:
            _workflow_row_id_matches_user_action_selector_created_automation_id(
                workflow_row_id=expected_workflow_id,
                user_action_selector_created_automation_id=inner.created_automation_id,
            )
        else:
            assert inner.created_automation_id
            assert len(inner.created_automation_id) > 0

    async def _assert_user_action_selector_completed_automation_stop(*, wallet_address: str, user_action_id: str) -> None:
        listed = await octobot_node.scheduler.SCHEDULER.list_user_actions(wallet_address)
        by_id = _merge_user_actions_latest_per_id(listed)
        assert user_action_id in by_id, f"expected {user_action_id!r} in user action workflows, got {sorted(by_id)!r}"
        stored = by_id[user_action_id]
        assert stored.status == octobot_protocol_models.UserActionStatus.COMPLETED
        assert stored.result is not None
        inner = stored.result.actual_instance
        assert isinstance(inner, octobot_protocol_models.AutomationActionResult)
        assert inner.result_type == octobot_protocol_models.UserActionResultType.AUTOMATION
        assert inner.error_details is None
        assert inner.error_message is None


@pytest.mark.skipif(not IMPORTED_OCTOBOT_FLOW_GRID_DEPS, reason="octobot_flow / grid tentacle deps not available")
class TestEmitAndCopyGridAutomationSignals:
    @pytest.mark.asyncio
    async def test_emit_and_copy_grid_master_forced_trigger_copies_signals(
        self, temp_dbos_scheduler, caplog
    ):
        """
        Master grid uploads trading signals to a local OctoBot-Sync server; copy bootstraps via real
        fetch_trading_signals from that server. After a forced trigger and price shock, the sync snapshot
        matches the master's ladder; copy mirrors master via the internal trading-signal channel; both
        automations stop cleanly.
        """
        # Deterministic ticker/OHLCV close; bumped later past the lowest sell so that limit can fill.
        simulated_close: dict[str, float] = {"value": float(grid_sim_util.FIXED_BTC_USDC_CLOSE)}
        patched_fetch_tickers = grid_sim_util.tickers_repository_fetch_tickers_btc_usdc_close_override(
            lambda: simulated_close["value"]
        )
        patched_fetch_ohlcv = grid_sim_util.fetch_ohlcv_side_effect_for_close_price(
            lambda: simulated_close["value"]
        )

        wallet_address = grid_sim_util.SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS
        master_account_id = "functional_master_emit_account"
        copy_account_id = "functional_copy_emit_account"
        master_user_action = grid_sim_util.build_create_grid_user_action(
            account_id=master_account_id,
            name="test_master_emit_grid",
            strategy_id=_SHARED_STRATEGY_ID,
            emit_signals=True,
        )
        copy_user_action = grid_sim_util.build_create_copy_follower_user_action(
            automation_id=_COPY_AUTOMATION_ID,
            account_id=copy_account_id,
            name="test_copy_grid_follower",
            strategy_id=_SHARED_STRATEGY_ID,
        )

        await internal_trading_signals_module.subscribe_internal_trading_signal_consumer()
        try:
            with tempfile.TemporaryDirectory() as tmp_root:
                sync_data_dir = os.path.join(tmp_root, "sync_data")
                os.makedirs(sync_data_dir, exist_ok=True)
                wallet_file_path = os.path.join(tmp_root, "wallets.json")
                previous_sync_data_dir = os.environ.get("SYNC_DATA_DIR")
                os.environ["SYNC_DATA_DIR"] = sync_data_dir

                listen_port = commons_os_util_module.find_first_free_listen_port_after_base(
                    "127.0.0.1",
                    31000,
                    max_offset=256,
                )
                sync_url = f"http://127.0.0.1:{listen_port}"

                # A user ``~/.octobot/collections.json`` can omit ``namespaces``; then
                # ``NamespaceRewriteMiddleware`` is not applied and Starfish paths
                # ``/octobot/v1/...`` never match (HTTP 404). Use the package default
                # so the ``octobot`` namespace and rewrite are always active.
                with mock.patch(
                    "octobot_sync.app.sync.load_sync_config",
                    return_value=_grid_functional_test_sync_config(),
                ):
                    sync_asgi_app = octobot_sync_server_module.build_default_sync_app(
                        is_allowed_user_id=lambda _address: True,
                    )
                    # StarfishClient builds URLs as ``{base}/sync/v1/{namespace}/...``.
                    # Mount sync_asgi_app under /sync to match the SYNC_MOUNT_PATH prefix.
                    mounted_app = starlette_routing_module.Router(
                        routes=[starlette_routing_module.Mount("/sync", app=sync_asgi_app)]
                    )
                    uvicorn_server = uvicorn.Server(
                        uvicorn.Config(
                            mounted_app,
                            host="127.0.0.1",
                            port=listen_port,
                            log_level="warning",
                        )
                    )
                serve_task = asyncio.create_task(uvicorn_server.serve())
                await asyncio.sleep(0.25)
                try:
                    with (
                        mock.patch("octobot.constants.WALLET_STORAGE_BACKEND", "file"),
                        mock.patch("octobot.constants.WALLET_FILE_PATH", wallet_file_path),
                        mock.patch("octobot.constants.SYNC_SERVER_URL", sync_url),
                    ):
                        # Seed wallet used by sync client + automation tasks (same key as SIMULATOR_GRID_TEST_*).
                        async with local_authenticator_module.local_user_authenticator() as seed_auth:
                            seed_auth.import_wallet(
                                grid_sim_util.SIMULATOR_GRID_TEST_PRIVATE_KEY,
                                grid_sim_util.SIMULATOR_GRID_TEST_WALLET_PASSPHRASE,
                                None,
                                True,
                            )
                        master_account = grid_sim_util.protocol_account_for_functional(
                            account_id=master_account_id,
                            usdc_total=_MASTER_INIT_USDC,
                            account_name="Master emit functional account",
                        )
                        copy_account = grid_sim_util.protocol_account_for_functional(
                            account_id=copy_account_id,
                            usdc_total=_COPY_INIT_USDC,
                            account_name="Copy emit functional account",
                        )

                        def _functional_seed_strategy_for_emit_copy_test(_wallet_address, stored_item_id):
                            if stored_item_id == _SHARED_STRATEGY_ID:
                                return grid_sim_util.seeded_grid_strategy_for_functional_wallet(
                                    stored_strategy_id=_SHARED_STRATEGY_ID,
                                )
                            if stored_item_id == grid_sim_util.SIMULATOR_COPY_FOLLOWER_STORED_STRATEGY_ID:
                                return grid_sim_util.seeded_copy_follower_strategy_for_functional_wallet(
                                    copy_master_strategy_id=_SHARED_STRATEGY_ID,
                                )
                            raise AssertionError(
                                f"unexpected strategy id for functional seed: {stored_item_id!r}"
                            )

                        with (
                            mock.patch.object(
                                octobot_flow_repositories_exchange_module.TickersRepository,
                                "fetch_tickers",
                                new=patched_fetch_tickers,
                            ),
                            mock.patch.object(
                                octobot_flow_repositories_exchange_module.OhlcvRepository,
                                "fetch_ohlcv",
                                side_effect=patched_fetch_ohlcv,
                            ),
                            mock.patch(
                                "octobot_sync.sync.collection_providers.StrategyProvider.instance",
                                return_value=mock.Mock(
                                    get_item=mock.Mock(
                                        side_effect=_functional_seed_strategy_for_emit_copy_test,
                                    ),
                                ),
                            ),
                            mock.patch(
                                "octobot_sync.sync.collection_providers.AccountProvider.instance",
                                return_value=mock.Mock(
                                    get_item=mock.Mock(
                                        side_effect=lambda _wallet, account_id: _account_for_id(
                                            account_id=account_id,
                                            master_account_id=master_account_id,
                                            master_account=master_account,
                                            copy_account_id=copy_account_id,
                                            copy_account=copy_account,
                                        )
                                    ),
                                    get_exchange_config=mock.Mock(
                                        return_value=grid_sim_util.protocol_exchange_config_for_grid_functional(),
                                    ),
                                ),
                            ),
                        ):
                            caplog.set_level(logging.INFO)

                            # Step 1 — enqueue master emitting grid signals (pushes to local sync server).
                            try:
                                await asyncio.wait_for(
                                    grid_sim_util.enqueue_user_action_workflow_and_await_terminal_result(
                                        temp_dbos_scheduler,
                                        master_user_action,
                                        wallet_address,
                                    ),
                                    timeout=_T_ENQUEUE_SECONDS,
                                )
                            except TimeoutError as exc:
                                raise AssertionError("execute_user_action timed out enqueueing master workflow") from exc

                            await _assert_user_action_selector_completed_automation_create(
                                wallet_address=wallet_address,
                                user_action_id=master_user_action.id,
                                expected_workflow_id=None,
                            )

                            baseline_master_reader = await _poll_state_reader_until(
                                temp_dbos_scheduler,
                                master_user_action.id,
                                lambda reader: grid_sim_util.is_simulator_grid_baseline_at_least_one_trade(
                                    *grid_sim_util.buy_sell_trade_counts_from_exchange_elements(
                                        reader.state.automation.exchange_account_elements
                                    )
                                ),
                                _T_GRID_SECONDS,
                                "master baseline grid (2 buy, 2 sell, >=1 trade)",
                            )
                            baseline_master_elements = baseline_master_reader.state.automation.exchange_account_elements
                            buy_b, sell_b, trade_b = grid_sim_util.buy_sell_trade_counts_from_exchange_elements(
                                baseline_master_elements
                            )
                            assert grid_sim_util.is_simulator_grid_baseline_at_least_one_trade(
                                buy_b, sell_b, trade_b
                            )
                            master_metadata = baseline_master_reader.state.automation.metadata
                            master_automation_id = master_metadata.automation_id
                            assert master_metadata.strategy_id == _SHARED_STRATEGY_ID
                            assert master_metadata.emit_signals is True

                            master_workflow_rows_for_user_action_selector = [
                                workflow_row
                                for workflow_row in await temp_dbos_scheduler.INSTANCE.list_workflows_async()
                                if grid_sim_util.workflows_util_module.get_automation_id(workflow_row)
                                == master_user_action.id
                            ]
                            assert master_workflow_rows_for_user_action_selector
                            master_workflow_row_for_user_action_selector = max(
                                master_workflow_rows_for_user_action_selector,
                                key=lambda workflow_status: workflow_status.updated_at or 0,
                            )
                            await _assert_user_action_selector_completed_automation_create(
                                wallet_address=wallet_address,
                                user_action_id=master_user_action.id,
                                expected_workflow_id=master_workflow_row_for_user_action_selector.workflow_id,
                            )

                            bootstrap_fetched = await _fetch_strategy_signals_from_sync(wallet_address)
                            bootstrap_signal = _first_fetched_trading_signal(bootstrap_fetched)
                            assert bootstrap_signal.strategy_id == _SHARED_STRATEGY_ID
                            bootstrap_account = bootstrap_signal.account
                            assert bootstrap_account.copied_assets, (
                                "bootstrap signal should snapshot portfolio copied_assets"
                            )
                            assert {"BTC", "USDC"} == {
                                copied_asset.name for copied_asset in bootstrap_account.copied_assets
                            }
                            assert bootstrap_account.orders, "bootstrap signal should include open ladder orders"
                            assert len(bootstrap_account.orders) == 4

                            # Step 2 — enqueue copy (pulls bootstrap snapshot from server).
                            try:
                                await asyncio.wait_for(
                                    grid_sim_util.enqueue_user_action_workflow_and_await_terminal_result(
                                        temp_dbos_scheduler,
                                        copy_user_action,
                                        wallet_address,
                                    ),
                                    timeout=_T_ENQUEUE_SECONDS,
                                )
                            except TimeoutError as exc:
                                raise AssertionError("execute_user_action timed out enqueueing copy workflow") from exc

                            listed_after_copy = await octobot_node.scheduler.SCHEDULER.list_user_actions(wallet_address)
                            by_id_after_copy = _merge_user_actions_latest_per_id(listed_after_copy)
                            assert master_user_action.id in by_id_after_copy
                            assert copy_user_action.id in by_id_after_copy
                            master_after_copy = by_id_after_copy[master_user_action.id]
                            copy_row = by_id_after_copy[copy_user_action.id]
                            assert master_after_copy.status == octobot_protocol_models.UserActionStatus.COMPLETED
                            assert copy_row.status == octobot_protocol_models.UserActionStatus.COMPLETED
                            master_inner_after_copy = master_after_copy.result.actual_instance
                            copy_inner = copy_row.result.actual_instance
                            assert isinstance(
                                master_inner_after_copy,
                                octobot_protocol_models.AutomationActionResult,
                            )
                            assert isinstance(copy_inner, octobot_protocol_models.AutomationActionResult)
                            assert (
                                master_inner_after_copy.result_type
                                == octobot_protocol_models.UserActionResultType.AUTOMATION
                            )
                            assert copy_inner.result_type == octobot_protocol_models.UserActionResultType.AUTOMATION
                            _workflow_row_id_matches_user_action_selector_created_automation_id(
                                workflow_row_id=master_workflow_row_for_user_action_selector.workflow_id,
                                user_action_selector_created_automation_id=master_inner_after_copy.created_automation_id,
                            )
                            assert copy_inner.created_automation_id
                            assert len(copy_inner.created_automation_id) > 0
                            assert copy_inner.error_details is None
                            assert copy_inner.error_message is None

                            copy_reader = await _poll_state_reader_until(
                                temp_dbos_scheduler,
                                _COPY_AUTOMATION_ID,
                                lambda reader: grid_sim_util.is_simulator_grid_baseline_at_least_one_trade(
                                    *grid_sim_util.buy_sell_trade_counts_from_exchange_elements(
                                        reader.state.automation.exchange_account_elements
                                    )
                                ),
                                _T_BOOTSTRAP_COPY_SECONDS,
                                "copy baseline grid mirroring master",
                            )
                            _assert_open_limit_prices_match_reference(
                                baseline_master_reader.state.automation.exchange_account_elements,
                                copy_reader.state.automation.exchange_account_elements,
                            )
                            _assert_btc_usdc_value_shares_match_reference(
                                baseline_master_reader.state.automation.exchange_account_elements,
                                copy_reader.state.automation.exchange_account_elements,
                                btc_usdc_close=decimal.Decimal(str(simulated_close["value"])),
                            )

                            copy_workflow_rows_for_user_action_selector = [
                                workflow_row
                                for workflow_row in await temp_dbos_scheduler.INSTANCE.list_workflows_async()
                                if grid_sim_util.workflows_util_module.get_automation_id(workflow_row)
                                == _COPY_AUTOMATION_ID
                            ]
                            assert copy_workflow_rows_for_user_action_selector
                            copy_workflow_row_for_user_action_selector = max(
                                copy_workflow_rows_for_user_action_selector,
                                key=lambda workflow_status: workflow_status.updated_at or 0,
                            )
                            await _assert_user_action_selector_completed_automation_create(
                                wallet_address=wallet_address,
                                user_action_id=copy_user_action.id,
                                expected_workflow_id=copy_workflow_row_for_user_action_selector.workflow_id,
                            )

                            caplog.clear()

                            # Step 3 — raise mock spot between first sell and neighbour; force-trigger master DAG.
                            first_sell_price = _first_sell_limit_price(baseline_master_elements)
                            simulated_close["value"] = float(
                                first_sell_price + _D_DECIMAL_INCREMENT / decimal.Decimal("2")
                            )

                            try:
                                await asyncio.wait_for(
                                    octobot_node.scheduler.tasks.send_forced_trigger_to_automation(
                                        master_automation_id
                                    ),
                                    timeout=_T_STOP_SEND_SECONDS,
                                )
                            except TimeoutError as exc:
                                raise AssertionError(
                                    "send_forced_trigger_to_automation(master) timed out"
                                ) from exc

                            # Step 4 — ladder refresh + emit; copy follows internal trading-signal notifications.
                            master_reader = await _poll_state_reader_until(
                                temp_dbos_scheduler,
                                master_automation_id,
                                lambda reader: _post_fill_open_order_shape(
                                    *grid_sim_util.buy_sell_trade_counts_from_exchange_elements(
                                        reader.state.automation.exchange_account_elements
                                    )[:2],
                                ),
                                _T_POST_SHOCK_SECONDS,
                                "master post-shock ladder (3 buy, 1 sell open)",
                            )

                            copy_reader = await _poll_state_reader_until(
                                temp_dbos_scheduler,
                                _COPY_AUTOMATION_ID,
                                lambda reader: _post_fill_open_order_shape(
                                    *grid_sim_util.buy_sell_trade_counts_from_exchange_elements(
                                        reader.state.automation.exchange_account_elements
                                    )[:2],
                                ),
                                _T_POST_SHOCK_SECONDS,
                                "copy post-signal ladder (3 buy, 1 sell open)",
                            )

                            _assert_open_limit_prices_match_reference(
                                master_reader.state.automation.exchange_account_elements,
                                copy_reader.state.automation.exchange_account_elements,
                            )
                            _assert_btc_usdc_value_shares_match_reference(
                                master_reader.state.automation.exchange_account_elements,
                                copy_reader.state.automation.exchange_account_elements,
                                btc_usdc_close=decimal.Decimal(str(simulated_close["value"])),
                            )

                            master_post_elements = master_reader.state.automation.exchange_account_elements
                            await _poll_fetched_trading_signal_until_ladder_matches(
                                wallet_address,
                                master_post_elements,
                                deadline_seconds=_T_POST_SHOCK_SECONDS,
                                failure_label="sync snapshot ladder vs master post-shock",
                            )

                            _assert_orders_synchronizer_no_mirror_cancel_or_grace_logs(caplog)

                            # Step 5 — priority-stop both workflows.
                            for automation_id in (master_automation_id, _COPY_AUTOMATION_ID):
                                matching_parent_id = None
                                workflow_rows_for_stop = await temp_dbos_scheduler.INSTANCE.list_workflows_async()
                                for workflow_row in sorted(
                                    workflow_rows_for_stop,
                                    key=lambda workflow_status: workflow_status.updated_at or 0,
                                    reverse=True,
                                ):
                                    if grid_sim_util.workflows_util_module.get_automation_id(workflow_row) != automation_id:
                                        continue
                                    matching_parent_id = workflow_row.workflow_id[
                                        : grid_sim_util.node_constants_module.PARENT_WORKFLOW_ID_LENGTH
                                    ]
                                    break
                                assert matching_parent_id is not None
                                stop_user_action = grid_sim_util.build_stop_user_action(
                                    automation_id=matching_parent_id,
                                    user_action_id=f"ua-stop-{automation_id}",
                                )
                                try:
                                    await asyncio.wait_for(
                                        grid_sim_util.enqueue_user_action_workflow_and_await_terminal_result(
                                            temp_dbos_scheduler,
                                            stop_user_action,
                                            wallet_address,
                                        ),
                                        timeout=_T_STOP_SEND_SECONDS,
                                    )
                                except TimeoutError as exc:
                                    raise AssertionError(
                                        f"execute_user_action stop timed out for {automation_id}"
                                    ) from exc

                            await _assert_user_action_selector_completed_automation_stop(
                                wallet_address=wallet_address,
                                user_action_id=f"ua-stop-{master_automation_id}",
                            )
                            await _assert_user_action_selector_completed_automation_stop(
                                wallet_address=wallet_address,
                                user_action_id=f"ua-stop-{_COPY_AUTOMATION_ID}",
                            )

                            for automation_id in (master_automation_id, _COPY_AUTOMATION_ID):
                                final_text = await grid_sim_util.wait_for_stop_success_output(
                                    temp_dbos_scheduler,
                                    automation_id,
                                    _T_STOP_COMPLETE_SECONDS,
                                )
                                parsed_final = grid_sim_util.parse_automation_workflow_output(final_text)
                                assert parsed_final.error is None
                                final_job = grid_sim_util.job_description_dict_from_output(parsed_final)
                                assert final_job["state"]["automation"]["post_actions"]["stop_automation"] is True
                finally:
                    uvicorn_server.should_exit = True
                    await serve_task
                    if previous_sync_data_dir is None:
                        os.environ.pop("SYNC_DATA_DIR", None)
                    else:
                        os.environ["SYNC_DATA_DIR"] = previous_sync_data_dir

        finally:
            await trading_signals_channel_module.shutdown_internal_trading_signal_channel()
