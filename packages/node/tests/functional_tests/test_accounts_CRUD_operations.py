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
import octobot_node.scheduler.user_actions.user_actions_executor.util.account_state_updater as account_state_updater_module
import octobot_protocol.models as protocol_models
import octobot_trading.errors as trading_errors
import octobot_trading.exchanges.connectors.ccxt.ccxt_connector as ccxt_connector_module

import tests.scheduler as scheduler_tests

_TEST_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_TEST_WALLET_PASSPHRASE = "accountsCRUD1!"
_DOOMED_ACCOUNT_ID = "functional-account-doomed"
_WORKFLOW_RESULT_TIMEOUT_SECONDS = 120.0
_USER_ACTION_LIST_POLL_TIMEOUT_SECONDS = 15.0

_FUNCTIONAL_USDT_HOLDINGS = 1000.0
_FUNCTIONAL_BTC_HOLDINGS = 0.5
_FUNCTIONAL_ETH_HOLDINGS = 2.0
_FUNCTIONAL_SOL_HOLDINGS = 10.0

_REAL_UPDATE_ACCOUNT_STATE = account_state_updater_module.update_account_state


@pytest.fixture
def patched_user_action_workflow_max_iteration_retries():
    with mock.patch.object(octobot_node_constants, "USER_ACTION_WORKFLOW_MAX_ITERATION_RETRIES", 2):
        yield


@pytest.fixture
def temp_dbos_scheduler_account_crud(
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
        "SOL/BTC": {"symbol": "SOL/BTC", "active": True, "spot": True},
    }
    self.client.symbols = ["BTC/USDT", "SOL/BTC"]


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
        "ETH": {
            commons_constants.PORTFOLIO_TOTAL: _FUNCTIONAL_ETH_HOLDINGS,
            commons_constants.PORTFOLIO_AVAILABLE: _FUNCTIONAL_ETH_HOLDINGS,
        },
        "SOL": {
            commons_constants.PORTFOLIO_TOTAL: _FUNCTIONAL_SOL_HOLDINGS,
            commons_constants.PORTFOLIO_AVAILABLE: _FUNCTIONAL_SOL_HOLDINGS,
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


async def _update_account_state_fail_doomed_create(
    account: protocol_models.Account,
    wallet_address: str,
) -> protocol_models.Account:
    if account.id == _DOOMED_ACCOUNT_ID:
        raise node_errors_module.WorkflowInputError("forced doomed create failure")
    return await _REAL_UPDATE_ACCOUNT_STATE(account, wallet_address)


def _assert_listed_user_actions_match_expected_id_status_pairs(
    listed_user_actions: list[protocol_models.UserAction],
    expected_id_status_pairs: list[tuple[str, protocol_models.UserActionStatus]],
) -> None:
    actual_sorted = sorted((row.id, row.status) for row in listed_user_actions)
    expected_sorted = sorted(expected_id_status_pairs)
    assert actual_sorted == expected_sorted


def _assert_functional_assets(
    assets: list[protocol_models.DetailedAsset] | None,
) -> None:
    assert assets is not None
    assets_by_symbol = {asset.symbol: asset for asset in assets}
    assert set(assets_by_symbol) == {"USDT", "BTC", "ETH", "SOL"}

    usdt_asset = assets_by_symbol["USDT"]
    assert usdt_asset.total == pytest.approx(_FUNCTIONAL_USDT_HOLDINGS)
    assert usdt_asset.available == pytest.approx(_FUNCTIONAL_USDT_HOLDINGS)

    bitcoin_asset = assets_by_symbol["BTC"]
    assert bitcoin_asset.total == pytest.approx(_FUNCTIONAL_BTC_HOLDINGS)
    assert bitcoin_asset.available == pytest.approx(_FUNCTIONAL_BTC_HOLDINGS)

    ethereum_asset = assets_by_symbol["ETH"]
    assert ethereum_asset.total == pytest.approx(_FUNCTIONAL_ETH_HOLDINGS)
    assert ethereum_asset.available == pytest.approx(_FUNCTIONAL_ETH_HOLDINGS)

    sol_asset = assets_by_symbol["SOL"]
    assert sol_asset.total == pytest.approx(_FUNCTIONAL_SOL_HOLDINGS)
    assert sol_asset.available == pytest.approx(_FUNCTIONAL_SOL_HOLDINGS)


@pytest.mark.asyncio
class TestExecuteUserActionAccountCrud:
    async def test_create_edit_refresh_delete_accounts_on_temp_filesystem(
        self,
        tmp_path: pathlib.Path,
        temp_dbos_scheduler_account_crud,
    ):
        # Step: Isolate sync collections under a temp user-root folder (restored in ``finally``).
        user_root_provider = user_root_folder_provider_module.instance()
        previous_user_root = user_root_provider.get_root()
        test_user_root = tmp_path / "functional_accounts_user_root"
        user_root_provider.set_root(str(test_user_root))

        authentication_instance: community_authentication_module.CommunityAuthentication | None = None
        sample_timestamp = datetime.datetime(2026, 4, 1, 12, 0, 0, tzinfo=datetime.UTC)

        # Step: Nested builders for protocol payloads; user actions start as PENDING so active-queue listings match enqueue snapshots.
        def wrap_configuration(payload) -> protocol_models.UserActionConfiguration:
            return protocol_models.UserActionConfiguration.from_json(payload.to_json())

        def build_exchange_account() -> protocol_models.ExchangeAccount:
            return protocol_models.ExchangeAccount(
                account_type=protocol_models.AccountType.EXCHANGE,
                trading_type=protocol_models.TradingType.SPOT,
                exchange="binanceus",
                remote_account_id="functional-test-remote-account",
            )

        def build_account(*, account_id: str, account_name: str) -> protocol_models.Account:
            return protocol_models.Account(
                id=account_id,
                name=account_name,
                is_simulated=True,
                created_at=sample_timestamp,
                updated_at=sample_timestamp,
                specifics=protocol_models.AccountSpecifics(
                    actual_instance=build_exchange_account(),
                ),
            )

        def build_create_user_action(*, user_action_id: str, account: protocol_models.Account) -> protocol_models.UserAction:
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

        def build_edit_user_action(*, user_action_id: str, account_id: str, account: protocol_models.Account) -> protocol_models.UserAction:
            payload = protocol_models.EditAccountConfiguration(
                action_type=protocol_models.UserActionType.ACCOUNT_EDIT,
                id=account_id,
                configuration=account,
            )
            return protocol_models.UserAction(
                id=user_action_id,
                status=protocol_models.UserActionStatus.PENDING,
                created_at=sample_timestamp,
                updated_at=sample_timestamp,
                configuration=wrap_configuration(payload),
            )

        def build_refresh_user_action(*, user_action_id: str) -> protocol_models.UserAction:
            payload = protocol_models.RefreshAccountsConfiguration(
                action_type=protocol_models.UserActionType.ACCOUNTS_REFRESH,
            )
            return protocol_models.UserAction(
                id=user_action_id,
                status=protocol_models.UserActionStatus.PENDING,
                created_at=sample_timestamp,
                updated_at=sample_timestamp,
                configuration=wrap_configuration(payload),
            )

        def build_delete_user_action(*, user_action_id: str, account_id: str) -> protocol_models.UserAction:
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

            # Step: Permission mock sequence — happy create OK; edit hits RetriableFailedRequest then whitelist error; refresh OK.
            # RetriableFailedRequest is re-raised from account_state_updater (unlike RuntimeError, which is swallowed).
            ensure_permissions_mock = mock.AsyncMock(
                side_effect=[
                    None,
                    trading_errors.RetriableFailedRequest("transient edit failure"),
                    trading_errors.InvalidAPIKeyIPWhitelistError("invalid api key ip whitelist"),
                    None,
                ]
            )

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
                    account_state_updater_module,
                    "_ensure_api_key_permissions",
                    new=ensure_permissions_mock,
                ),
                mock.patch.object(
                    account_state_updater_module,
                    "update_account_state",
                    side_effect=_update_account_state_fail_doomed_create,
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
                # Step: Patches above strip network/CCXT and steer ``update_account_state`` / permissions for this scenario.

                # Step: No persisted accounts before any workflow runs.
                assert account_provider.list_items(wallet_address) == []

                # Step 1 — Create (doomed): ``WorkflowInputError`` from the doomed-account branch; workflow fails; nothing persisted.
                doomed_account = build_account(
                    account_id=_DOOMED_ACCOUNT_ID,
                    account_name="Doomed account",
                )
                doomed_create = build_create_user_action(
                    user_action_id="ua-account-create-fail",
                    account=doomed_account,
                )
                await _run_user_action_to_completion(
                    wallet_address,
                    doomed_create,
                    expect_exceptions=(node_errors_module.WorkflowInputError,),
                )

                # Step 1 (continued) — Listing: only the doomed row, FAILED with executor-built ``AccountActionResult``.
                listed_after_doomed = await scheduler_api.list_user_actions(wallet_address)
                _assert_listed_user_actions_match_expected_id_status_pairs(
                    listed_after_doomed,
                    [(doomed_create.id, protocol_models.UserActionStatus.FAILED)],
                )
                doomed_latest = next(
                    row for row in listed_after_doomed if row.id == doomed_create.id
                )
                assert doomed_latest.status == protocol_models.UserActionStatus.FAILED
                assert doomed_latest.result is not None
                doomed_inner = doomed_latest.result.actual_instance
                assert isinstance(doomed_inner, protocol_models.AccountActionResult)
                assert doomed_inner.result_type == protocol_models.UserActionResultType.ACCOUNT
                assert doomed_inner.error_message == protocol_models.AccountActionResultErrorMessage.INTERNAL_ERROR
                assert doomed_inner.error_details is not None
                assert "forced doomed create failure" in doomed_inner.error_details

                # Step 2 — Create (happy path): workflow completes; provider stores VALID account.
                created_account = build_account(account_id="functional-account-1", account_name="Functional account")
                happy_create = build_create_user_action(
                    user_action_id="ua-account-create",
                    account=created_account,
                )
                await _run_user_action_to_completion(wallet_address, happy_create)

                # Step 2 (continued) — Listing: doomed FAILED + happy COMPLETED.
                listed_after_create = await scheduler_api.list_user_actions(wallet_address)
                _assert_listed_user_actions_match_expected_id_status_pairs(
                    listed_after_create,
                    [
                        (doomed_create.id, protocol_models.UserActionStatus.FAILED),
                        (happy_create.id, protocol_models.UserActionStatus.COMPLETED),
                    ],
                )
                created_latest = next(
                    row for row in listed_after_create if row.id == happy_create.id
                )
                assert created_latest.status == protocol_models.UserActionStatus.COMPLETED
                assert created_latest.result is not None
                created_inner = created_latest.result.actual_instance
                assert isinstance(created_inner, protocol_models.AccountActionResult)
                assert created_inner.result_type == protocol_models.UserActionResultType.ACCOUNT
                assert created_inner.error_message is None
                assert created_inner.error_details is None

                persisted_created_account = account_provider.get_item(wallet_address, "functional-account-1")
                assert persisted_created_account.name == "Functional account"
                assert persisted_created_account.state is not None
                assert persisted_created_account.state.status == protocol_models.AccountStatus.VALID
                assert persisted_created_account.state.message == protocol_models.AccountStatusMessage.VALID
                assert len(account_provider.list_items(wallet_address)) == 1
                _assert_functional_assets(persisted_created_account.assets)

                # Step 3 — Edit: enqueue workflow only first; poll listings mid retry before awaiting terminal output.
                edited_account = build_account(
                    account_id="functional-account-1",
                    account_name="Functional account renamed",
                )
                edit_action = build_edit_user_action(
                    user_action_id="ua-account-edit",
                    account_id="functional-account-1",
                    account=edited_account,
                )
                edit_workflow_id = await scheduler_tasks.trigger_user_action_workflow(edit_action, wallet_address)

                # Step 3 (mid retry) — While DBOS retries the step after RetriableFailedRequest, listing keeps edit as PENDING (input snapshot).
                spin_deadline_seconds = asyncio.get_running_loop().time() + _USER_ACTION_LIST_POLL_TIMEOUT_SECONDS
                saw_mid_retry_pending = False
                while asyncio.get_running_loop().time() < spin_deadline_seconds:
                    if ensure_permissions_mock.await_count >= 2:
                        listed_mid = await scheduler_api.list_user_actions(wallet_address)
                        _assert_listed_user_actions_match_expected_id_status_pairs(
                            listed_mid,
                            [
                                (doomed_create.id, protocol_models.UserActionStatus.FAILED),
                                (happy_create.id, protocol_models.UserActionStatus.COMPLETED),
                                (edit_action.id, protocol_models.UserActionStatus.PENDING),
                            ],
                        )
                        edit_latest_mid = next(row for row in listed_mid if row.id == edit_action.id)
                        if edit_latest_mid.status == protocol_models.UserActionStatus.PENDING:
                            saw_mid_retry_pending = True
                            break
                    await asyncio.sleep(0.05)

                assert saw_mid_retry_pending, (
                    "expected ua-account-edit listed as pending during DBOS retry backoff "
                    f"(perm_mock.await_count={ensure_permissions_mock.await_count})"
                )

                # Step 3 (continued) — Finish edit: second permission outcome yields INVALID whitelist on persisted account.
                edit_handle = await octobot_node.scheduler.SCHEDULER.INSTANCE.retrieve_workflow_async(edit_workflow_id)
                await asyncio.wait_for(edit_handle.get_result(), timeout=_WORKFLOW_RESULT_TIMEOUT_SECONDS)

                # Step 3 (listing) — Terminal edit row COMPLETED alongside prior workflows.
                listed_after_edit = await scheduler_api.list_user_actions(wallet_address)
                _assert_listed_user_actions_match_expected_id_status_pairs(
                    listed_after_edit,
                    [
                        (doomed_create.id, protocol_models.UserActionStatus.FAILED),
                        (happy_create.id, protocol_models.UserActionStatus.COMPLETED),
                        (edit_action.id, protocol_models.UserActionStatus.COMPLETED),
                    ],
                )
                edit_latest = next(row for row in listed_after_edit if row.id == edit_action.id)
                assert edit_latest.status == protocol_models.UserActionStatus.COMPLETED
                assert edit_latest.result is not None
                edit_list_inner = edit_latest.result.actual_instance
                assert isinstance(edit_list_inner, protocol_models.AccountActionResult)
                assert edit_list_inner.result_type == protocol_models.UserActionResultType.ACCOUNT
                assert edit_list_inner.error_message is None
                assert edit_list_inner.error_details is None

                persisted_edited_account = account_provider.get_item(wallet_address, "functional-account-1")
                assert persisted_edited_account.name == "Functional account renamed"
                assert persisted_edited_account.state is not None
                assert persisted_edited_account.state.status == protocol_models.AccountStatus.INVALID
                assert (
                    persisted_edited_account.state.message
                    == protocol_models.AccountStatusMessage.INVALID_API_IP_WHITELIST
                )
                assert len(account_provider.list_items(wallet_address)) == 1

                # Step 4 — Refresh: reruns checks with final permission mock returning OK; provider VALID again.
                refresh_action = build_refresh_user_action(user_action_id="ua-account-refresh")
                await _run_user_action_to_completion(wallet_address, refresh_action)

                # Step 4 (continued) — Listing adds COMPLETED refresh row.
                listed_after_refresh = await scheduler_api.list_user_actions(wallet_address)
                _assert_listed_user_actions_match_expected_id_status_pairs(
                    listed_after_refresh,
                    [
                        (doomed_create.id, protocol_models.UserActionStatus.FAILED),
                        (happy_create.id, protocol_models.UserActionStatus.COMPLETED),
                        (edit_action.id, protocol_models.UserActionStatus.COMPLETED),
                        (refresh_action.id, protocol_models.UserActionStatus.COMPLETED),
                    ],
                )
                refresh_latest = next(row for row in listed_after_refresh if row.id == refresh_action.id)
                assert refresh_latest.status == protocol_models.UserActionStatus.COMPLETED
                assert refresh_latest.result is not None
                refresh_inner = refresh_latest.result.actual_instance
                assert isinstance(refresh_inner, protocol_models.AccountActionResult)
                assert refresh_inner.result_type == protocol_models.UserActionResultType.ACCOUNT
                assert refresh_inner.error_message is None
                assert refresh_inner.error_details is None

                persisted_refreshed_account = account_provider.get_item(wallet_address, "functional-account-1")
                assert persisted_refreshed_account.state is not None
                assert persisted_refreshed_account.state.status == protocol_models.AccountStatus.VALID
                assert persisted_refreshed_account.state.message == protocol_models.AccountStatusMessage.VALID
                _assert_functional_assets(persisted_refreshed_account.assets)

                # Step 5 — Delete: remove account from provider; listing gains COMPLETED delete row.
                delete_action = build_delete_user_action(
                    user_action_id="ua-account-delete",
                    account_id="functional-account-1",
                )
                await _run_user_action_to_completion(wallet_address, delete_action)

                # Step 5 (continued) — Full listing is five terminal rows with expected id/status pairs.
                listed_after_delete = await scheduler_api.list_user_actions(wallet_address)
                _assert_listed_user_actions_match_expected_id_status_pairs(
                    listed_after_delete,
                    [
                        (doomed_create.id, protocol_models.UserActionStatus.FAILED),
                        (happy_create.id, protocol_models.UserActionStatus.COMPLETED),
                        (edit_action.id, protocol_models.UserActionStatus.COMPLETED),
                        (refresh_action.id, protocol_models.UserActionStatus.COMPLETED),
                        (delete_action.id, protocol_models.UserActionStatus.COMPLETED),
                    ],
                )
                delete_latest = next(row for row in listed_after_delete if row.id == delete_action.id)
                assert delete_latest.status == protocol_models.UserActionStatus.COMPLETED
                assert delete_latest.result is not None
                delete_inner = delete_latest.result.actual_instance
                assert isinstance(delete_inner, protocol_models.AccountActionResult)
                assert delete_inner.result_type == protocol_models.UserActionResultType.ACCOUNT
                assert delete_inner.error_message is None
                assert delete_inner.error_details is None

                # Step: Collection layer confirms delete (no item, empty list).
                with pytest.raises(octobot_sync.sync.ItemNotFoundError):
                    account_provider.get_item(wallet_address, "functional-account-1")
                assert account_provider.list_items(wallet_address) == []
        finally:
            # Step: Tear down wallet task and restore prior user-root path.
            if authentication_instance is not None:
                await authentication_instance.stop()
            user_root_provider.set_root(previous_user_root)
