import asyncio
import datetime
import pathlib
import tempfile

import mock
import pytest

import octobot_sync.chain.evm as sync_evm_module
import octobot_sync.sync
import octobot.community.authentication as community_authentication_module
import octobot.community.local_authenticator as local_authenticator_module
import octobot_commons.user_root_folder_provider as user_root_folder_provider_module
import octobot_commons.constants as commons_constants
import octobot_node.constants as octobot_node_constants
import octobot_node.errors as node_errors_module
import octobot_node.scheduler
import octobot_node.scheduler.api as scheduler_api
import octobot_node.scheduler.tasks as scheduler_tasks
import octobot_protocol.models as protocol_models
import octobot_trading.exchanges.connectors.ccxt.ccxt_connector as ccxt_connector_module

import tests.scheduler as scheduler_tests

_TEST_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_TEST_WALLET_PASSPHRASE = "exchangeConfigsCRUD1!"
_DOOMED_EXCHANGE_CONFIG_ID = "functional-exchange-config-doomed"
_FUNCTIONAL_EXCHANGE_CONFIG_ID = "functional-exchange-config-id"
_FUNCTIONAL_ACCOUNT_ID = "functional-exchange-account-1"
_WORKFLOW_RESULT_TIMEOUT_SECONDS = 120.0

_FUNCTIONAL_USDT_HOLDINGS = 1000.0
_FUNCTIONAL_BTC_HOLDINGS = 0.5


@pytest.fixture
def patched_user_action_workflow_max_iteration_retries():
    with mock.patch.object(octobot_node_constants, "USER_ACTION_WORKFLOW_MAX_ITERATION_RETRIES", 2):
        yield


@pytest.fixture
def temp_dbos_scheduler_exchange_config_crud(
    patched_user_action_workflow_max_iteration_retries,  # noqa: ARG001
):
    """Mirrors ``tests.scheduler.temp_dbos_scheduler``; requests the patch fixture so registration sees capped retries."""
    with tempfile.NamedTemporaryFile() as temp_file:
        dbos_runtime = scheduler_tests.init_scheduler(temp_file.name)
        dbos_runtime.reset_system_database()
        dbos_runtime.launch()
        try:
            yield octobot_node.scheduler.SCHEDULER
        finally:
            dbos_runtime.destroy()


async def _stub_load_symbol_markets_no_network(self, reload=False, market_filter=None):
    """
    Skip CCXT load_markets network I/O (see CCXTConnector._unauth_ensure_exchange_init).
    Seed minimal spot markets so initialize_impl can resolve symbols/timeframes.
    """
    self.client.markets = {
        "BTC/USDT": {"symbol": "BTC/USDT", "active": True, "spot": True},
    }
    self.client.symbols = ["BTC/USDT"]


async def _stub_get_balance_no_network(self, **kwargs):
    return {
        "USDT": {
            commons_constants.PORTFOLIO_TOTAL: _FUNCTIONAL_USDT_HOLDINGS,
            commons_constants.PORTFOLIO_AVAILABLE: _FUNCTIONAL_USDT_HOLDINGS,
        },
        "BTC": {
            commons_constants.PORTFOLIO_TOTAL: _FUNCTIONAL_BTC_HOLDINGS,
            commons_constants.PORTFOLIO_AVAILABLE: _FUNCTIONAL_BTC_HOLDINGS,
        },
    }


async def _run_user_action_to_completion(
    wallet_address: str,
    user_action: protocol_models.UserAction,
    *,
    expect_exceptions: tuple[type[BaseException], ...] = (),
) -> str:
    workflow_id = await scheduler_tasks.trigger_user_action_workflow(user_action, wallet_address)
    workflow_handle = await octobot_node.scheduler.SCHEDULER.INSTANCE.retrieve_workflow_async(workflow_id)
    try:
        await asyncio.wait_for(workflow_handle.get_result(), timeout=_WORKFLOW_RESULT_TIMEOUT_SECONDS)
    except BaseException as caught:
        if expect_exceptions and isinstance(caught, expect_exceptions):
            return workflow_id
        raise
    return workflow_id


def _assert_listed_user_actions_match_expected_id_status_pairs(
    listed_user_actions: list[protocol_models.UserAction],
    expected_id_status_pairs: list[tuple[str, protocol_models.UserActionStatus]],
) -> None:
    actual_sorted = sorted((row.id, row.status) for row in listed_user_actions)
    expected_sorted = sorted(expected_id_status_pairs)
    assert actual_sorted == expected_sorted


@pytest.mark.asyncio
class TestExecuteUserActionExchangeConfigCrud:
    async def test_create_edit_delete_exchange_configs_with_linked_exchange_account(
        self,
        tmp_path: pathlib.Path,
        temp_dbos_scheduler_exchange_config_crud,
    ):
        # Step: Isolate sync collections under a temp user-root folder (restored in ``finally``).
        user_root_provider = user_root_folder_provider_module.instance()
        previous_user_root = user_root_provider.get_root()
        test_user_root = tmp_path / "functional_exchange_configs_user_root"
        user_root_provider.set_root(str(test_user_root))

        authentication_instance: community_authentication_module.CommunityAuthentication | None = None
        sample_timestamp = datetime.datetime(2026, 5, 1, 12, 0, 0, tzinfo=datetime.UTC)

        # Step: Nested builders for protocol payloads; user actions start as PENDING so active-queue listings match enqueue snapshots.
        def wrap_configuration(payload) -> protocol_models.UserActionConfiguration:
            return protocol_models.UserActionConfiguration.from_json(payload.to_json())

        def build_exchange_config(
            *,
            config_id: str,
            name: str = "binance-main",
            exchange: str = "binanceus",
        ) -> protocol_models.ExchangeConfig:
            return protocol_models.ExchangeConfig(
                id=config_id,
                name=name,
                exchange=exchange,
                sandboxed=False,
            )

        def build_exchange_account(*, exchange_config_id: str) -> protocol_models.ExchangeAccount:
            return protocol_models.ExchangeAccount(
                account_type=protocol_models.AccountType.EXCHANGE,
                remote_account_id="functional-test-remote-account",
                exchange_config_ids=[exchange_config_id],
            )

        def build_account(*, account_id: str, account_name: str, exchange_config_id: str) -> protocol_models.Account:
            return protocol_models.Account(
                id=account_id,
                name=account_name,
                is_simulated=True,
                created_at=sample_timestamp,
                updated_at=sample_timestamp,
                specifics=protocol_models.AccountSpecifics(
                    actual_instance=build_exchange_account(exchange_config_id=exchange_config_id),
                ),
            )

        def build_create_exchange_config_user_action(
            *,
            user_action_id: str,
            exchange_config: protocol_models.ExchangeConfig,
        ) -> protocol_models.UserAction:
            payload = protocol_models.CreateExchangeConfigConfiguration(
                action_type=protocol_models.UserActionType.EXCHANGE_CONFIG_CREATE,
                configuration=exchange_config,
            )
            return protocol_models.UserAction(
                id=user_action_id,
                status=protocol_models.UserActionStatus.PENDING,
                created_at=sample_timestamp,
                updated_at=sample_timestamp,
                configuration=wrap_configuration(payload),
            )

        def build_edit_exchange_config_user_action(
            *,
            user_action_id: str,
            config_id: str,
            exchange_config: protocol_models.ExchangeConfig,
        ) -> protocol_models.UserAction:
            payload = protocol_models.EditExchangeConfigConfiguration(
                action_type=protocol_models.UserActionType.EXCHANGE_CONFIG_EDIT,
                id=config_id,
                configuration=exchange_config,
            )
            return protocol_models.UserAction(
                id=user_action_id,
                status=protocol_models.UserActionStatus.PENDING,
                created_at=sample_timestamp,
                updated_at=sample_timestamp,
                configuration=wrap_configuration(payload),
            )

        def build_delete_exchange_config_user_action(
            *,
            user_action_id: str,
            config_id: str,
        ) -> protocol_models.UserAction:
            payload = protocol_models.DeleteExchangeConfigConfiguration(
                action_type=protocol_models.UserActionType.EXCHANGE_CONFIG_DELETE,
                id=config_id,
            )
            return protocol_models.UserAction(
                id=user_action_id,
                status=protocol_models.UserActionStatus.PENDING,
                created_at=sample_timestamp,
                updated_at=sample_timestamp,
                configuration=wrap_configuration(payload),
            )

        def build_create_account_user_action(
            *,
            user_action_id: str,
            account: protocol_models.Account,
        ) -> protocol_models.UserAction:
            payload = protocol_models.CreateAccountConfiguration(
                action_type=protocol_models.UserActionType.ACCOUNT_CREATE,
                configuration=account,
            )
            return protocol_models.UserAction(
                id=user_action_id,
                status=protocol_models.UserActionStatus.PENDING,
                created_at=sample_timestamp,
                updated_at=sample_timestamp,
                configuration=wrap_configuration(payload),
            )

        def build_delete_account_user_action(
            *,
            user_action_id: str,
            account_id: str,
        ) -> protocol_models.UserAction:
            payload = protocol_models.DeleteAccountConfiguration(
                action_type=protocol_models.UserActionType.ACCOUNT_DELETE,
                id=account_id,
            )
            return protocol_models.UserAction(
                id=user_action_id,
                status=protocol_models.UserActionStatus.PENDING,
                created_at=sample_timestamp,
                updated_at=sample_timestamp,
                configuration=wrap_configuration(payload),
            )

        try:
            # Step: Import dev wallet; ``wallet_address`` ties AccountProvider paths and ``list_user_actions`` filtering together.
            authentication_configuration = local_authenticator_module.get_stateless_configuration()
            authentication_instance = community_authentication_module.CommunityAuthentication(
                config=authentication_configuration,
                use_as_singleton=False,
            )
            authentication_instance.import_wallet(
                _TEST_PRIVATE_KEY,
                _TEST_WALLET_PASSPHRASE,
                None,
                True,
            )
            wallet_address = sync_evm_module.address_from_evm_key(_TEST_PRIVATE_KEY).lower()

            # Step: Filesystem-backed provider for this test root (also patched as ``AccountProvider.instance()``).
            account_provider = octobot_sync.sync.AccountProvider(base_folder=str(test_user_root))
            real_create_exchange_config = account_provider.create_exchange_config

            # Step: Steer ``create_exchange_config`` so the doomed config id fails before persistence (happy path uses real method).
            def create_exchange_config_fail_doomed_create(
                address: str,
                exchange_config: protocol_models.ExchangeConfig,
            ) -> protocol_models.ExchangeConfig:
                if exchange_config.id == _DOOMED_EXCHANGE_CONFIG_ID:
                    raise node_errors_module.InvalidUserActionPayloadError("forced doomed create failure")
                return real_create_exchange_config(address, exchange_config)

            with (
                mock.patch.object(
                    community_authentication_module.CommunityAuthentication,
                    "instance",
                    return_value=authentication_instance,
                ),
                mock.patch.object(
                    octobot_sync.sync.AccountProvider,
                    "instance",
                    return_value=account_provider,
                ),
                mock.patch.object(
                    ccxt_connector_module.CCXTConnector,
                    "load_symbol_markets",
                    _stub_load_symbol_markets_no_network,
                ),
                mock.patch.object(
                    ccxt_connector_module.CCXTConnector,
                    "get_balance",
                    _stub_get_balance_no_network,
                ),
            ):
                create_exchange_config_mock = mock.Mock(side_effect=create_exchange_config_fail_doomed_create)
                with mock.patch.object(
                    account_provider,
                    "create_exchange_config",
                    create_exchange_config_mock,
                ):
                    # Step: Patches above strip network/CCXT; ``create_exchange_config`` mock only affects doomed create.
                    assert account_provider.list_exchange_configs(wallet_address) == []

                    # Step 1 — Create (doomed): ``InvalidUserActionPayloadError`` from patched create; workflow fails; nothing persisted.
                    doomed_create = build_create_exchange_config_user_action(
                        user_action_id="ua-exchange-config-create-fail",
                        exchange_config=build_exchange_config(config_id=_DOOMED_EXCHANGE_CONFIG_ID),
                    )
                    await _run_user_action_to_completion(
                        wallet_address,
                        doomed_create,
                    )

                    # Step 1 (continued) — Listing: only the doomed row, FAILED with executor-built ``ExchangeConfigActionResult``.
                    listed_after_doomed = await scheduler_api.list_user_actions(wallet_address, active_only=True)
                    _assert_listed_user_actions_match_expected_id_status_pairs(
                        listed_after_doomed,
                        [(doomed_create.id, protocol_models.UserActionStatus.FAILED)],
                    )
                    doomed_latest = next(row for row in listed_after_doomed if row.id == doomed_create.id)
                    assert doomed_latest.result is not None
                    doomed_inner = doomed_latest.result.actual_instance
                    assert isinstance(doomed_inner, protocol_models.ExchangeConfigActionResult)
                    assert doomed_inner.result_type == protocol_models.UserActionResultType.EXCHANGE_CONFIG
                    assert doomed_inner.error_message == protocol_models.ExchangeConfigActionResultErrorMessage.INVALID_CONFIGURATION
                    assert doomed_inner.error_details is not None
                    assert "forced doomed create failure" in doomed_inner.error_details

                    # Step 2 — Create (happy path): workflow completes; provider stores exchange config.
                    happy_create = build_create_exchange_config_user_action(
                        user_action_id="ua-exchange-config-create",
                        exchange_config=build_exchange_config(config_id=_FUNCTIONAL_EXCHANGE_CONFIG_ID),
                    )
                    await _run_user_action_to_completion(wallet_address, happy_create)

                    # Step 2 (continued) — Listing: doomed FAILED + happy COMPLETED; verify persisted config.
                    listed_after_create = await scheduler_api.list_user_actions(wallet_address, active_only=True)
                    _assert_listed_user_actions_match_expected_id_status_pairs(
                        listed_after_create,
                        [
                            (doomed_create.id, protocol_models.UserActionStatus.FAILED),
                            (happy_create.id, protocol_models.UserActionStatus.COMPLETED),
                        ],
                    )
                    created_latest = next(row for row in listed_after_create if row.id == happy_create.id)
                    assert created_latest.result is not None
                    created_inner = created_latest.result.actual_instance
                    assert isinstance(created_inner, protocol_models.ExchangeConfigActionResult)
                    assert created_inner.error_message is None

                    persisted_created_config = account_provider.get_exchange_config(
                        wallet_address,
                        _FUNCTIONAL_EXCHANGE_CONFIG_ID,
                    )
                    assert persisted_created_config.name == "binance-main"
                    assert len(account_provider.list_exchange_configs(wallet_address)) == 1

                    # Step 3 — Account create: exchange account references the config id; CCXT stubs satisfy ``update_account_state``.
                    created_account = build_account(
                        account_id=_FUNCTIONAL_ACCOUNT_ID,
                        account_name="Functional exchange account",
                        exchange_config_id=_FUNCTIONAL_EXCHANGE_CONFIG_ID,
                    )
                    account_create = build_create_account_user_action(
                        user_action_id="ua-account-create",
                        account=created_account,
                    )
                    await _run_user_action_to_completion(wallet_address, account_create)

                    # Step 3 (continued) — Listing adds COMPLETED account row; account persisted with matching ``exchange_config_ids``.
                    listed_after_account_create = await scheduler_api.list_user_actions(wallet_address, active_only=True)
                    _assert_listed_user_actions_match_expected_id_status_pairs(
                        listed_after_account_create,
                        [
                            (doomed_create.id, protocol_models.UserActionStatus.FAILED),
                            (happy_create.id, protocol_models.UserActionStatus.COMPLETED),
                            (account_create.id, protocol_models.UserActionStatus.COMPLETED),
                        ],
                    )
                    persisted_account = account_provider.get_item(wallet_address, _FUNCTIONAL_ACCOUNT_ID)
                    assert persisted_account.specifics is not None
                    account_specifics = persisted_account.specifics.actual_instance
                    assert isinstance(account_specifics, protocol_models.ExchangeAccount)
                    assert account_specifics.exchange_config_ids == [_FUNCTIONAL_EXCHANGE_CONFIG_ID]

                    # Step 4 — Config edit: rename exchange config while account still references the same id.
                    edited_config = build_exchange_config(
                        config_id=_FUNCTIONAL_EXCHANGE_CONFIG_ID,
                        name="binance-main-renamed",
                    )
                    edit_config_action = build_edit_exchange_config_user_action(
                        user_action_id="ua-exchange-config-edit",
                        config_id=_FUNCTIONAL_EXCHANGE_CONFIG_ID,
                        exchange_config=edited_config,
                    )
                    await _run_user_action_to_completion(wallet_address, edit_config_action)

                    # Step 4 (continued) — Listing adds COMPLETED edit row; config updated, account link unchanged.
                    listed_after_edit = await scheduler_api.list_user_actions(wallet_address, active_only=True)
                    _assert_listed_user_actions_match_expected_id_status_pairs(
                        listed_after_edit,
                        [
                            (doomed_create.id, protocol_models.UserActionStatus.FAILED),
                            (happy_create.id, protocol_models.UserActionStatus.COMPLETED),
                            (account_create.id, protocol_models.UserActionStatus.COMPLETED),
                            (edit_config_action.id, protocol_models.UserActionStatus.COMPLETED),
                        ],
                    )
                    persisted_edited_config = account_provider.get_exchange_config(
                        wallet_address,
                        _FUNCTIONAL_EXCHANGE_CONFIG_ID,
                    )
                    assert persisted_edited_config.name == "binance-main-renamed"
                    persisted_account_after_edit = account_provider.get_item(wallet_address, _FUNCTIONAL_ACCOUNT_ID)
                    account_specifics_after_edit = persisted_account_after_edit.specifics.actual_instance
                    assert account_specifics_after_edit.exchange_config_ids == [_FUNCTIONAL_EXCHANGE_CONFIG_ID]

                    # Step 5 — Account delete: remove account before tearing down the exchange config.
                    delete_account_action = build_delete_account_user_action(
                        user_action_id="ua-account-delete",
                        account_id=_FUNCTIONAL_ACCOUNT_ID,
                    )
                    await _run_user_action_to_completion(wallet_address, delete_account_action)

                    # Step 5 (continued) — Listing adds COMPLETED account-delete row; accounts collection empty.
                    listed_after_account_delete = await scheduler_api.list_user_actions(wallet_address, active_only=True)
                    _assert_listed_user_actions_match_expected_id_status_pairs(
                        listed_after_account_delete,
                        [
                            (doomed_create.id, protocol_models.UserActionStatus.FAILED),
                            (happy_create.id, protocol_models.UserActionStatus.COMPLETED),
                            (account_create.id, protocol_models.UserActionStatus.COMPLETED),
                            (edit_config_action.id, protocol_models.UserActionStatus.COMPLETED),
                            (delete_account_action.id, protocol_models.UserActionStatus.COMPLETED),
                        ],
                    )
                    assert account_provider.list_items(wallet_address) == []

                    # Step 6 — Config delete: remove exchange config from provider; listing gains COMPLETED delete row.
                    delete_config_action = build_delete_exchange_config_user_action(
                        user_action_id="ua-exchange-config-delete",
                        config_id=_FUNCTIONAL_EXCHANGE_CONFIG_ID,
                    )
                    await _run_user_action_to_completion(wallet_address, delete_config_action)

                    # Step 6 (continued) — Full listing is six terminal rows; exchange config collection empty.
                    listed_after_delete = await scheduler_api.list_user_actions(wallet_address, active_only=True)
                    _assert_listed_user_actions_match_expected_id_status_pairs(
                        listed_after_delete,
                        [
                            (doomed_create.id, protocol_models.UserActionStatus.FAILED),
                            (happy_create.id, protocol_models.UserActionStatus.COMPLETED),
                            (account_create.id, protocol_models.UserActionStatus.COMPLETED),
                            (edit_config_action.id, protocol_models.UserActionStatus.COMPLETED),
                            (delete_account_action.id, protocol_models.UserActionStatus.COMPLETED),
                            (delete_config_action.id, protocol_models.UserActionStatus.COMPLETED),
                        ],
                    )
                    delete_latest = next(row for row in listed_after_delete if row.id == delete_config_action.id)
                    assert delete_latest.result is not None
                    delete_inner = delete_latest.result.actual_instance
                    assert isinstance(delete_inner, protocol_models.ExchangeConfigActionResult)
                    assert delete_inner.error_message is None

                    # Step: Collection layer confirms config delete (no item, empty list).
                    with pytest.raises(octobot_sync.sync.ItemNotFoundError):
                        account_provider.get_exchange_config(wallet_address, _FUNCTIONAL_EXCHANGE_CONFIG_ID)
                    assert account_provider.list_exchange_configs(wallet_address) == []
        finally:
            # Step: Tear down wallet task and restore prior user-root path.
            if authentication_instance is not None:
                await authentication_instance.stop()
            user_root_provider.set_root(previous_user_root)
