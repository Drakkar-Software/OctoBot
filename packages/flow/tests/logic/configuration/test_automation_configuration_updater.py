import octobot_commons.profiles.profile_data as profiles_import
import octobot_flow.entities
import octobot_flow.logic.configuration.automation_configuration_updater as automation_configuration_updater
import octobot_trading.exchanges.util.exchange_data as exchange_data_import


def _configured_action() -> octobot_flow.entities.ConfiguredActionDetails:
    return octobot_flow.entities.ConfiguredActionDetails(
        id="apply_config",
        action="apply_configuration",
        config={},
    )


def _updater(
    state: octobot_flow.entities.AutomationState,
    action: octobot_flow.entities.ConfiguredActionDetails | None = None,
) -> automation_configuration_updater.AutomationConfigurationUpdater:
    return automation_configuration_updater.AutomationConfigurationUpdater(
        state, action or _configured_action()
    )


def _exchange_account_details(
    *,
    exchange_account_id: str = "account_a",
    internal_name: str = "binance",
    simulated: bool = True,
    portfolio_unit: str = "",
) -> octobot_flow.entities.ExchangeAccountDetails:
    exchange_details = profiles_import.ExchangeData(internal_name=internal_name)
    exchange_details.exchange_account_id = exchange_account_id
    if simulated:
        auth_details = exchange_data_import.ExchangeAuthDetails()
    else:
        auth_details = exchange_data_import.ExchangeAuthDetails(api_key="existing_key")
    return octobot_flow.entities.ExchangeAccountDetails(
        exchange_details=exchange_details,
        auth_details=auth_details,
        portfolio=octobot_flow.entities.ExchangeAccountPortfolio(unit=portfolio_unit),
    )


def _automation_state(
    *,
    exchange_account_id: str = "account_a",
    simulated: bool = True,
    automation_id: str = "automation_1",
    strategy_id: str = "",
    previous_triggered_at: float = 0.0,
    internal_name: str = "binance",
    portfolio_unit: str = "",
) -> octobot_flow.entities.AutomationState:
    automation = octobot_flow.entities.AutomationDetails(
        metadata=octobot_flow.entities.AutomationMetadata(
            automation_id=automation_id,
            strategy_id=strategy_id,
        ),
        execution=octobot_flow.entities.ExecutionDetails(
            previous_execution=octobot_flow.entities.TriggerDetails(
                triggered_at=previous_triggered_at,
            ),
        ),
    )
    return octobot_flow.entities.AutomationState(
        exchange_account_details=_exchange_account_details(
            exchange_account_id=exchange_account_id,
            internal_name=internal_name,
            simulated=simulated,
            portfolio_unit=portfolio_unit,
        ),
        automation=automation,
    )


class TestApplyAutomationStateConfigurationUpdate:
    def test_skips_exchange_when_update_has_no_exchange_account_details(self):
        state = _automation_state(internal_name="binance", strategy_id="before")
        update = octobot_flow.entities.AutomationState(
            exchange_account_details=None,
            automation=octobot_flow.entities.AutomationDetails(
                metadata=octobot_flow.entities.AutomationMetadata(strategy_id="after"),
            ),
        )
        _updater(state)._apply_automation_state_configuration_update(update)
        assert state.exchange_account_details.exchange_details.internal_name == "binance"
        assert state.automation.metadata.strategy_id == "after"

    def test_resets_auth_when_exchange_account_id_changes(self):
        state = _automation_state(exchange_account_id="account_a", simulated=True)
        update_details = _exchange_account_details(
            exchange_account_id="account_b",
            internal_name="binance",
            simulated=False,
        )
        update_details.auth_details.api_key = "from_update"
        update = octobot_flow.entities.AutomationState(
            exchange_account_details=update_details,
            automation=octobot_flow.entities.AutomationDetails(),
        )
        _updater(state)._apply_automation_state_configuration_update(update)
        assert state.exchange_account_details.exchange_details.exchange_account_id == "account_b"
        assert not state.exchange_account_details.auth_details.api_key

    def test_merges_auth_when_exchange_account_id_unchanged(self):
        state = _automation_state(exchange_account_id="account_a", simulated=True)
        update_details = _exchange_account_details(
            exchange_account_id="account_a",
            internal_name="binance",
            simulated=False,
        )
        update_details.auth_details.api_key = "merged_key"
        update = octobot_flow.entities.AutomationState(
            exchange_account_details=update_details,
            automation=octobot_flow.entities.AutomationDetails(),
        )
        _updater(state)._apply_automation_state_configuration_update(update)
        assert state.exchange_account_details.auth_details.api_key == "merged_key"


class TestUpdateExchangeDetails:
    def test_returns_false_and_merges_when_id_unchanged(self):
        state = _automation_state(exchange_account_id="account_a", internal_name="binance")
        update_details = _exchange_account_details(
            exchange_account_id="account_a",
            internal_name="kucoin",
        )
        updater = _updater(state)
        updating = updater._update_exchange_details(update_details)
        assert updating is False
        assert state.exchange_account_details.exchange_details.internal_name == "kucoin"

    def test_returns_false_when_new_id_missing(self):
        state = _automation_state(exchange_account_id="account_a")
        update_details = _exchange_account_details(exchange_account_id="account_a")
        update_details.exchange_details.exchange_account_id = None
        updater = _updater(state)
        updating = updater._update_exchange_details(update_details)
        assert updating is False

    def test_returns_true_when_both_ids_set_and_different(self):
        state = _automation_state(exchange_account_id="account_a")
        update_details = _exchange_account_details(exchange_account_id="account_b")
        updater = _updater(state)
        updating = updater._update_exchange_details(update_details)
        assert updating is True
        assert state.exchange_account_details.exchange_details.exchange_account_id == "account_b"


class TestUpdateAuthDetails:
    def test_merges_api_key_from_update(self):
        state = _automation_state(simulated=True)
        update_details = _exchange_account_details(simulated=True)
        update_details.auth_details.api_key = "new_key"
        _updater(state)._update_auth_details(update_details)
        assert state.exchange_account_details.auth_details.api_key == "new_key"

    def test_does_not_apply_exchange_credential_id_from_update(self):
        state = _automation_state(simulated=True)
        update_details = _exchange_account_details(simulated=True)
        update_details.auth_details.exchange_credential_id = "cred_x"
        _updater(state)._update_auth_details(update_details)
        assert state.exchange_account_details.auth_details.exchange_credential_id is None


class TestUpdatePortfolio:
    def test_updates_portfolio_for_simulated_account(self):
        state = _automation_state(simulated=True, portfolio_unit="")
        update_details = _exchange_account_details(simulated=True, portfolio_unit="USDT")
        _updater(state)._update_portfolio(update_details)
        assert state.exchange_account_details.portfolio.unit == "USDT"

    def test_no_op_for_authenticated_account(self):
        state = _automation_state(simulated=False, portfolio_unit="EUR")
        update_details = _exchange_account_details(simulated=True, portfolio_unit="USDT")
        _updater(state)._update_portfolio(update_details)
        assert state.exchange_account_details.portfolio.unit == "EUR"


class TestUpdateAutomation:
    def test_merges_automation_metadata(self):
        state = _automation_state(strategy_id="before")
        update = octobot_flow.entities.AutomationState(
            automation=octobot_flow.entities.AutomationDetails(
                metadata=octobot_flow.entities.AutomationMetadata(strategy_id="after"),
            ),
        )
        _updater(state)._update_automation(update)
        assert state.automation.metadata.strategy_id == "after"


class TestRegisterExecutionTime:
    def test_uses_previous_triggered_at_when_set(self):
        state = _automation_state(previous_triggered_at=100.0)
        _updater(state)._register_execution_time(200.0)
        assert state.automation.execution.current_execution.triggered_at == 100.0

    def test_uses_start_time_when_previous_not_set(self):
        state = _automation_state(previous_triggered_at=0.0)
        _updater(state)._register_execution_time(42.0)
        assert state.automation.execution.current_execution.triggered_at == 42.0
