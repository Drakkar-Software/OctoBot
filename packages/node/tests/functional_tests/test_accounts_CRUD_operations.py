import datetime
import pathlib

import mock
import pytest

import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers.user_account_provider as account_provider_module
import octobot.community.authentication as community_authentication_module
import octobot.community.local_authenticator as local_authenticator_module
import octobot_commons.user_root_folder_provider as user_root_folder_provider_module
import octobot_node.protocol.user_actions as user_actions_module
import octobot_node.scheduler.user_actions.user_actions_executor.util.account_state_updater as account_state_updater_module
import octobot_protocol.models as protocol_models
import octobot_sync.chain.evm as sync_evm_module
import octobot_trading.errors as trading_errors
import octobot_trading.exchanges.connectors.ccxt.ccxt_connector as ccxt_connector_module

_TEST_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_TEST_WALLET_PASSPHRASE = "accountsCRUD1!"


async def _enqueue_user_action_synchronously_via_executor_like_workflow(
    user_action_instance: protocol_models.UserAction,
    wallet_address_segment: str,
) -> None:
    """Run the executor path without initializing DBOS (mirrors ``UserActionWorkflow._execute_user_action``)."""
    import octobot_node.scheduler.user_actions.user_actions_executor as ua_executor_package_integration
    import octobot_node.scheduler.workflows.params as ua_workflow_params_integration

    bundle_inputs_encoded = ua_workflow_params_integration.UserActionWorkflowInputs(
        wallet_address=wallet_address_segment,
        user_action=user_action_instance,
    ).to_dict(include_default_values=False)
    parsed_inputs_bundle_workspace = ua_workflow_params_integration.UserActionWorkflowInputs.from_dict(bundle_inputs_encoded)
    reconstructed_user_action_workspace_payload = protocol_models.UserAction.from_json(
        parsed_inputs_bundle_workspace.user_action.to_json(),
    )
    if reconstructed_user_action_workspace_payload is None:
        raise AssertionError("functional user_action failed to reconstruct from workflow inputs envelope")
    resolved_executor_constructor_workspace_payload = ua_executor_package_integration.user_action_executor_factory(
        reconstructed_user_action_workspace_payload,
    )
    constructed_executor_workspace_shell = resolved_executor_constructor_workspace_payload(
        parsed_inputs_bundle_workspace.wallet_address,
    )
    await constructed_executor_workspace_shell.execute(reconstructed_user_action_workspace_payload)


async def _stub_load_symbol_markets_no_network(self, reload=False, market_filter=None):
    """
    Skip CCXT load_markets network I/O (see CCXTConnector._unauth_ensure_exchange_init).
    Seed minimal spot markets so initialize_impl can resolve symbols/timeframes.
    """
    self.client.markets = {
        "BTC/USDT": {"symbol": "BTC/USDT", "active": True, "spot": True},
    }
    self.client.symbols = ["BTC/USDT"]


def _wrap_user_action_configuration(
    payload,
) -> protocol_models.UserActionConfiguration:
    return protocol_models.UserActionConfiguration.from_json(payload.to_json())


def _build_exchange_account() -> protocol_models.ExchangeAccount:
    return protocol_models.ExchangeAccount(
        account_type=protocol_models.AccountType.EXCHANGE,
        trading_type=protocol_models.TradingType.SPOT,
        exchange="binanceus",
        remote_account_id="functional-test-remote-account",
        api_key="functional-test-api-key",
        api_secret="functional-test-api-secret",
    )


def _build_account(*, account_id: str, account_name: str) -> protocol_models.Account:
    sample_timestamp = datetime.datetime(2026, 4, 1, 12, 0, 0, tzinfo=datetime.UTC)
    return protocol_models.Account(
        id=account_id,
        name=account_name,
        is_simulated=True,
        created_at=sample_timestamp,
        updated_at=sample_timestamp,
        details=protocol_models.AccountDetails(
            actual_instance=_build_exchange_account(),
        ),
    )


def _build_create_account_user_action(
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
        configuration=_wrap_user_action_configuration(payload),
    )


def _build_edit_account_user_action(
    *,
    user_action_id: str,
    account_id: str,
    account: protocol_models.Account,
) -> protocol_models.UserAction:
    payload = protocol_models.EditAccountConfiguration(
        action_type=protocol_models.UserActionType.ACCOUNT_EDIT,
        id=account_id,
        configuration=account,
    )
    return protocol_models.UserAction(
        id=user_action_id,
        configuration=_wrap_user_action_configuration(payload),
    )


def _build_refresh_accounts_user_action(*, user_action_id: str) -> protocol_models.UserAction:
    payload = protocol_models.RefreshAccountsConfiguration(
        action_type=protocol_models.UserActionType.ACCOUNTS_REFRESH,
    )
    return protocol_models.UserAction(
        id=user_action_id,
        configuration=_wrap_user_action_configuration(payload),
    )


def _build_delete_account_user_action(
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
        configuration=_wrap_user_action_configuration(payload),
    )


@pytest.mark.asyncio
class TestExecuteUserActionAccountCrud:
    async def test_create_edit_refresh_delete_accounts_on_temp_filesystem(self, tmp_path: pathlib.Path):
        # Step 0: isolate user-root storage for this test run.
        user_root_provider = user_root_folder_provider_module.instance()
        previous_user_root = user_root_provider.get_root()
        test_user_root = tmp_path / "functional_accounts_user_root"
        user_root_provider.set_root(str(test_user_root))

        authentication_instance: community_authentication_module.CommunityAuthentication | None = None
        try:
            # Step 1: initialize a real local community authenticator and import a deterministic wallet.
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

            account_provider = account_provider_module.AccountProvider(base_folder=str(test_user_root))

            with (
                # Step 2: keep the flow end-to-end but locally scoped to test instances.
                mock.patch.object(
                    community_authentication_module.CommunityAuthentication,
                    "instance",
                    return_value=authentication_instance,
                ),
                mock.patch.object(
                    account_provider_module.AccountProvider,
                    "instance",
                    return_value=account_provider,
                ),
                mock.patch.object(
                    account_state_updater_module,
                    "_request_exchange_to_ensure_authentication",
                    new=mock.AsyncMock(return_value=None),
                ),
                mock.patch.object(
                    account_state_updater_module,
                    "_ensure_api_key_permissions",
                    new=mock.AsyncMock(
                        side_effect=[
                            None,
                            trading_errors.InvalidAPIKeyIPWhitelistError("invalid api key ip whitelist"),
                            None,
                        ]
                    ),
                ),
                mock.patch.object(
                    ccxt_connector_module.CCXTConnector,
                    "load_symbol_markets",
                    _stub_load_symbol_markets_no_network,
                ),
                mock.patch.object(
                    user_actions_module.scheduler_tasks,
                    "trigger_user_action_workflow",
                    new=_enqueue_user_action_synchronously_via_executor_like_workflow,
                ),
            ):
                # Step 3: sanity-check starting state.
                assert account_provider.list_items(wallet_address) == []

                # Step 4: create an account through protocol user action and verify persisted state.
                created_account = _build_account(account_id="functional-account-1", account_name="Functional account")
                await user_actions_module.execute_user_action(
                    _build_create_account_user_action(
                        user_action_id="ua-account-create",
                        account=created_account,
                    ),
                    wallet_address,
                )
                persisted_created_account = account_provider.get_item(wallet_address, "functional-account-1")
                assert persisted_created_account.name == "Functional account"
                assert persisted_created_account.state is not None
                assert persisted_created_account.state.status == protocol_models.AccountStatus.VALID
                assert persisted_created_account.state.message == protocol_models.AccountStatusMessage.VALID
                assert len(account_provider.list_items(wallet_address)) == 1

                # Step 5: edit the account and verify invalid-state mapping when IP whitelist fails.
                edited_account = _build_account(
                    account_id="functional-account-1",
                    account_name="Functional account renamed",
                )
                await user_actions_module.execute_user_action(
                    _build_edit_account_user_action(
                        user_action_id="ua-account-edit",
                        account_id="functional-account-1",
                        account=edited_account,
                    ),
                    wallet_address,
                )
                persisted_edited_account = account_provider.get_item(wallet_address, "functional-account-1")
                assert persisted_edited_account.name == "Functional account renamed"
                assert persisted_edited_account.state is not None
                assert persisted_edited_account.state.status == protocol_models.AccountStatus.INVALID
                assert (
                    persisted_edited_account.state.message
                    == protocol_models.AccountStatusMessage.INVALID_API_IP_WHITELIST
                )
                assert len(account_provider.list_items(wallet_address)) == 1

                # Step 6: refresh account state and confirm it is updated back to valid.
                await user_actions_module.execute_user_action(
                    _build_refresh_accounts_user_action(user_action_id="ua-account-refresh"),
                    wallet_address,
                )
                persisted_refreshed_account = account_provider.get_item(wallet_address, "functional-account-1")
                assert persisted_refreshed_account.state is not None
                assert persisted_refreshed_account.state.status == protocol_models.AccountStatus.VALID
                assert persisted_refreshed_account.state.message == protocol_models.AccountStatusMessage.VALID

                # Step 7: delete the account and verify final empty persistence state.
                await user_actions_module.execute_user_action(
                    _build_delete_account_user_action(
                        user_action_id="ua-account-delete",
                        account_id="functional-account-1",
                    ),
                    wallet_address,
                )
                with pytest.raises(collection_errors.ItemNotFoundError):
                    account_provider.get_item(wallet_address, "functional-account-1")
                assert account_provider.list_items(wallet_address) == []
        finally:
            # Step 8: cleanup authenticator resources and restore global user-root setting.
            if authentication_instance is not None:
                await authentication_instance.stop()
            user_root_provider.set_root(previous_user_root)
