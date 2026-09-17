#  Demo agent-seed wallet guard unit tests.

import datetime
import uuid

import mock
import pytest

import octobot_protocol.models as protocol_models
import octobot_sync.sync.collection_providers as collection_providers

import octobot_node.agent_seed.constants as demo_agent_seed_constants
import octobot_node.agent_seed.demo_wallet as demo_agent_seed_wallet


def _demo_user_id() -> str:
    return demo_agent_seed_constants.DEMO_AGENT_SEED_USER_ID


def _user_action_with_configuration(
    configuration: protocol_models.UserActionConfiguration,
) -> protocol_models.UserAction:
    return protocol_models.UserAction(
        id=f"ua-demo-guard-{uuid.uuid4()}",
        configuration=configuration,
    )


def _minimal_exchange_account() -> protocol_models.ExchangeAccount:
    return protocol_models.ExchangeAccount(
        account_type=protocol_models.AccountType.EXCHANGE,
        remote_account_id="remote",
        exchange_config_ids=[demo_agent_seed_constants.DEMO_AGENT_SEED_EXCHANGE_CONFIG_ID],
    )


def _minimal_account(is_simulated: bool) -> protocol_models.Account:
    return protocol_models.Account(
        id="acct-guard-test",
        name="guard-test",
        is_simulated=is_simulated,
        created_at=datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC),
        updated_at=datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC),
        specifics=protocol_models.AccountSpecifics(actual_instance=_minimal_exchange_account()),
    )


@mock.patch.object(collection_providers.AccountProvider, "instance")
@mock.patch.object(demo_agent_seed_wallet.community_authentication.CommunityAuthentication, "instance")
class TestValidateDemoAgentSeedUserActionBlocked:
    def _setup_demo_wallet_auth(self, auth_mock: mock.Mock) -> None:
        wallet_mock = mock.Mock(address=demo_agent_seed_constants.DEMO_AGENT_SEED_WALLET_EVM_ADDRESS)
        auth_mock.return_value.get_wallet_by_user_id.return_value = wallet_mock
        auth_mock.return_value.get_wallet_name.return_value = (
            demo_agent_seed_constants.DEMO_AGENT_SEED_WALLET_DISPLAY_NAME
        )

    def test_blocks_account_auth_create(self, auth_mock, account_provider_mock):
        self._setup_demo_wallet_auth(auth_mock)
        payload = protocol_models.CreateAccountAuthConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_AUTH_CREATE,
            configuration=protocol_models.AccountAuthentication(
                id="auth-1",
                api_key="key",
                api_secret="secret",
            ),
        )
        user_action = _user_action_with_configuration(
            protocol_models.UserActionConfiguration(payload),
        )
        with pytest.raises(demo_agent_seed_wallet.DemoAgentSeedUserActionForbiddenError):
            demo_agent_seed_wallet.validate_demo_agent_seed_user_action(
                _demo_user_id(),
                user_action,
            )

    def test_blocks_account_auth_edit(self, auth_mock, account_provider_mock):
        self._setup_demo_wallet_auth(auth_mock)
        payload = protocol_models.EditAccountAuthConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_AUTH_EDIT,
            id="auth-1",
            configuration=protocol_models.AccountAuthentication(
                id="auth-1",
                api_key="key",
                api_secret="secret",
            ),
        )
        user_action = _user_action_with_configuration(
            protocol_models.UserActionConfiguration(payload),
        )
        with pytest.raises(demo_agent_seed_wallet.DemoAgentSeedUserActionForbiddenError):
            demo_agent_seed_wallet.validate_demo_agent_seed_user_action(
                _demo_user_id(),
                user_action,
            )

    def test_blocks_exchange_config_create(self, auth_mock, account_provider_mock):
        self._setup_demo_wallet_auth(auth_mock)
        payload = protocol_models.CreateExchangeConfigConfiguration(
            action_type=protocol_models.UserActionType.EXCHANGE_CONFIG_CREATE,
            configuration=agent_seed_exchange_config(),
        )
        user_action = _user_action_with_configuration(
            protocol_models.UserActionConfiguration(payload),
        )
        with pytest.raises(demo_agent_seed_wallet.DemoAgentSeedUserActionForbiddenError):
            demo_agent_seed_wallet.validate_demo_agent_seed_user_action(
                _demo_user_id(),
                user_action,
            )

    def test_blocks_exchange_config_edit(self, auth_mock, account_provider_mock):
        self._setup_demo_wallet_auth(auth_mock)
        payload = protocol_models.EditExchangeConfigConfiguration(
            action_type=protocol_models.UserActionType.EXCHANGE_CONFIG_EDIT,
            id="extra-exchange-config",
            configuration=agent_seed_exchange_config(),
        )
        user_action = _user_action_with_configuration(
            protocol_models.UserActionConfiguration(payload),
        )
        with pytest.raises(demo_agent_seed_wallet.DemoAgentSeedUserActionForbiddenError):
            demo_agent_seed_wallet.validate_demo_agent_seed_user_action(
                _demo_user_id(),
                user_action,
            )

    def test_blocks_live_account_create(self, auth_mock, account_provider_mock):
        self._setup_demo_wallet_auth(auth_mock)
        payload = protocol_models.CreateAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_CREATE,
            configuration=_minimal_account(is_simulated=False),
        )
        user_action = _user_action_with_configuration(
            protocol_models.UserActionConfiguration(payload),
        )
        with pytest.raises(demo_agent_seed_wallet.DemoAgentSeedUserActionForbiddenError):
            demo_agent_seed_wallet.validate_demo_agent_seed_user_action(
                _demo_user_id(),
                user_action,
            )

    def test_blocks_account_edit_setting_live(self, auth_mock, account_provider_mock):
        self._setup_demo_wallet_auth(auth_mock)
        payload = protocol_models.EditAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_EDIT,
            id="acct-guard-test",
            configuration=_minimal_account(is_simulated=False),
        )
        user_action = _user_action_with_configuration(
            protocol_models.UserActionConfiguration(payload),
        )
        with pytest.raises(demo_agent_seed_wallet.DemoAgentSeedUserActionForbiddenError):
            demo_agent_seed_wallet.validate_demo_agent_seed_user_action(
                _demo_user_id(),
                user_action,
            )

    def test_blocks_automation_create_with_live_account(self, auth_mock, account_provider_mock):
        self._setup_demo_wallet_auth(auth_mock)
        account_provider_mock.return_value.get_item.return_value = _minimal_account(
            is_simulated=False,
        )
        payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=protocol_models.AutomationConfiguration(
                id="automation-live",
                name="live automation",
                created_at=datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC),
                strategy=protocol_models.StrategyReference(
                    id=demo_agent_seed_constants.DEMO_AGENT_SEED_STRATEGY_GRID_ID,
                    version=demo_agent_seed_constants.DEMO_AGENT_SEED_STRATEGY_VERSION,
                ),
                accounts=[protocol_models.AccountReference(id="acct-guard-test")],
            ),
        )
        user_action = _user_action_with_configuration(
            protocol_models.UserActionConfiguration(payload),
        )
        with pytest.raises(demo_agent_seed_wallet.DemoAgentSeedUserActionForbiddenError):
            demo_agent_seed_wallet.validate_demo_agent_seed_user_action(
                _demo_user_id(),
                user_action,
            )


def agent_seed_exchange_config() -> protocol_models.ExchangeConfig:
    return protocol_models.ExchangeConfig(
        id="extra-exchange-config",
        name="extra",
        exchange="binance",
        sandboxed=False,
    )


@mock.patch.object(collection_providers.AccountProvider, "instance")
@mock.patch.object(demo_agent_seed_wallet.community_authentication.CommunityAuthentication, "instance")
class TestValidateDemoAgentSeedUserActionAllowed:
    def _setup_demo_wallet_auth(self, auth_mock: mock.Mock) -> None:
        wallet_mock = mock.Mock(address=demo_agent_seed_constants.DEMO_AGENT_SEED_WALLET_EVM_ADDRESS)
        auth_mock.return_value.get_wallet_by_user_id.return_value = wallet_mock
        auth_mock.return_value.get_wallet_name.return_value = (
            demo_agent_seed_constants.DEMO_AGENT_SEED_WALLET_DISPLAY_NAME
        )

    def test_allows_simulated_automation_create(self, auth_mock, account_provider_mock):
        self._setup_demo_wallet_auth(auth_mock)
        account_provider_mock.return_value.get_item.return_value = _minimal_account(
            is_simulated=True,
        )
        payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=protocol_models.AutomationConfiguration(
                id=demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_GRID_ID,
                name=demo_agent_seed_constants.DEMO_AGENT_SEED_GRID_AUTOMATION_DISPLAY_NAME,
                created_at=datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC),
                strategy=protocol_models.StrategyReference(
                    id=demo_agent_seed_constants.DEMO_AGENT_SEED_STRATEGY_GRID_ID,
                    version=demo_agent_seed_constants.DEMO_AGENT_SEED_STRATEGY_VERSION,
                ),
                accounts=[
                    protocol_models.AccountReference(
                        id=demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_GRID_ID,
                    ),
                ],
            ),
        )
        user_action = _user_action_with_configuration(
            protocol_models.UserActionConfiguration(payload),
        )
        demo_agent_seed_wallet.validate_demo_agent_seed_user_action(
            _demo_user_id(),
            user_action,
        )

    def test_allows_automation_stop(self, auth_mock, account_provider_mock):
        self._setup_demo_wallet_auth(auth_mock)
        payload = protocol_models.StopAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_STOP,
            id=demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_GRID_ID,
        )
        user_action = _user_action_with_configuration(
            protocol_models.UserActionConfiguration(payload),
        )
        demo_agent_seed_wallet.validate_demo_agent_seed_user_action(
            _demo_user_id(),
            user_action,
        )
