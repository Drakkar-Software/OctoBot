import asyncio
import json

import mock
import pytest

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_copy.enums as copy_enums
import octobot_flow.entities as flow_entities
import octobot_protocol.models as protocol_models
import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading

import octobot_node.errors as node_errors
import octobot_node.models as node_models
import octobot_node.user_actions.user_actions_provider as user_actions_provider_module
import octobot_node.user_actions.user_actions_executor.create_automation as create_automation_executor
import octobot_node.user_actions.user_actions_executor.util.action_details_factory as action_details_factory

from . import provider_assertions

_ACCOUNT_PROVIDER_INSTANCE_PATCH = (
    "octobot.community.account_backend.AccountProvider.instance"
)
_TEST_WALLET_ADDRESS = "0xaaabbbcccddd"
_TRIGGER_TASK_PATCH = (
    "octobot_node.user_actions.user_actions_executor.create_automation.octobot_node.scheduler.tasks.trigger_task"
)


def _wrap(configuration_payload) -> protocol_models.UserActionConfiguration:
    return protocol_models.UserActionConfiguration.from_json(configuration_payload.to_json())


def _minimal_exchange_account(*, account_id: str) -> protocol_models.Account:
    return protocol_models.Account(
        id=account_id,
        name="Test account",
        is_simulated=True,
        details=protocol_models.AccountDetails(
            actual_instance=protocol_models.ExchangeAccount(
                account_type=protocol_models.AccountType.EXCHANGE,
                exchange="binanceus",
                remote_account_id="remote-1",
                api_key="k",
                api_secret="s",
                assets=[
                    protocol_models.Asset(
                        symbol="USDT",
                        total=1000.0,
                        available=1000.0,
                        unit="USDT",
                    )
                ],
            ),
        ),
    )


def _user_action_with_context(
    *,
    action_id: str,
    payload: protocol_models.CreateAutomationConfiguration,
) -> protocol_models.UserAction:
    return protocol_models.UserAction(id=action_id, configuration=_wrap(payload))


def _assert_init_action_matches_minimal_account(
    *,
    init_action_details,
    user_action_id: str,
    account_id: str,
    strategy_id: str | None = None,
    emit_signals: bool | None = None,
) -> None:
    assert init_action_details.id == "action_init"
    init_config = init_action_details.config
    metadata = init_config["automation"]["metadata"]
    assert metadata["automation_id"] == user_action_id
    if strategy_id is not None:
        assert metadata["strategy_id"] == strategy_id
    else:
        assert "strategy_id" not in metadata
    if emit_signals is not None:
        assert metadata["emit_signals"] is emit_signals
    else:
        assert "emit_signals" not in metadata
    portfolio_content = init_config["automation"]["exchange_account_elements"]["portfolio"]["content"]
    assert portfolio_content["USDT"]["available"] == 1000.0
    assert portfolio_content["USDT"]["total"] == 1000.0
    assert init_config["exchange_account_details"]["metadata"]["id"] == account_id
    assert init_config["exchange_account_details"]["metadata"]["name"] == "Test account"
    assert init_config["exchange_account_details"]["exchange_details"]["internal_name"] == "binanceus"
    assert init_config["exchange_account_details"]["exchange_details"]["exchange_account_id"] == "remote-1"
    assert init_config["exchange_account_details"]["portfolio"]["unit"] == "USDT"


def _expected_index_dsl_script(
    *,
    coins: list[protocol_models.IndexCoin],
    rebalance_trigger_min_percent: float,
) -> str:
    index_content = [
        {
            copy_enums.DistributionKeys.NAME: coin.name,
            copy_enums.DistributionKeys.VALUE: coin.ratio,
        }
        for coin in coins
    ]
    return (
        f"index_trading_mode(index_content={json.dumps(index_content)}, "
        f"rebalance_trigger_min_percent={rebalance_trigger_min_percent})"
    )


def _expected_grid_dsl_script(*, grid_configuration: protocol_models.GridConfiguration) -> str:
    pair_settings = [
        grid_trading.GridTradingMode.get_default_pair_config(
            grid_configuration.symbol,
            float(grid_configuration.spread),
            float(grid_configuration.increment),
            int(grid_configuration.buy_count),
            int(grid_configuration.sell_count),
            bool(grid_configuration.enable_trailing_up),
            bool(grid_configuration.enable_trailing_down),
            bool(grid_configuration.order_by_order_trailing),
        )
    ]
    return f"grid_trading_mode(pair_settings={dsl_interpreter.format_parameter_value(pair_settings)})"


def _expected_copy_dsl_script(*, strategy_id: str) -> str:
    return (
        f"copy_exchange_account(strategy_id={json.dumps(strategy_id)}, "
        "reference_market='', reference_account='', account_copy_settings='{}')"
    )


def _assert_task_content_matches_actions(
    *,
    task: node_models.Task,
    user_action: protocol_models.UserAction,
    expected_action_count: int,
) -> None:
    assert task.wallet_address == _TEST_WALLET_ADDRESS
    assert task.type == node_models.TaskType.EXECUTE_ACTIONS.value
    envelope = json.loads(task.content or "{}")
    assert "state" in envelope
    state = envelope["state"]
    assert state["automation"]["metadata"]["automation_id"] == user_action.id
    actions = state["automation"]["actions_dag"]["actions"]
    assert len(actions) == expected_action_count


class TestCreateAutomationExecutor:
    def test_strategy_configuration_is_added_to_init_metadata(self):
        strategy_id = "strategy-1"
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=protocol_models.AutomationConfiguration(
                name="strategy-automation",
                account_ids=["acc-1"],
                strategy=protocol_models.StrategyConfiguration(
                    id=strategy_id,
                    emit_signals=True,
                ),
                configuration=protocol_models.AutomationConfigurationConfiguration(
                    protocol_models.IndexConfiguration(
                        configuration_type=protocol_models.ActionConfigurationType.INDEX,
                        coins=[protocol_models.IndexCoin(name="BTC", ratio=1.0)],
                        rebalance_trigger_min_percent=5.0,
                    )
                ),
            ),
        )
        user_action = _user_action_with_context(action_id="ua-strategy", payload=create_payload)

        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as provider_instance_mock:
            provider_instance_mock.return_value.get_account.return_value = _minimal_exchange_account(account_id="acc-1")
            actions = executor._create_automation_actions(user_action)

        _assert_init_action_matches_minimal_account(
            init_action_details=actions[0],
            user_action_id="ua-strategy",
            account_id="acc-1",
            strategy_id=strategy_id,
            emit_signals=True,
        )

    def test_index_returns_init_and_index_action(self):
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=protocol_models.AutomationConfiguration(
                name="index-automation",
                account_ids=["acc-1"],
                configuration=protocol_models.AutomationConfigurationConfiguration(
                    protocol_models.IndexConfiguration(
                        configuration_type=protocol_models.ActionConfigurationType.INDEX,
                        coins=[protocol_models.IndexCoin(name="BTC", ratio=1.0)],
                        rebalance_trigger_min_percent=5.0,
                    )
                ),
            ),
        )
        user_action = _user_action_with_context(action_id="ua-idx", payload=create_payload)

        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as provider_instance_mock:
            provider_instance_mock.return_value.get_account.return_value = _minimal_exchange_account(account_id="acc-1")
            actions = executor._create_automation_actions(user_action)

        assert len(actions) == 2
        index_configuration = create_payload.configuration.configuration.actual_instance
        assert isinstance(index_configuration, protocol_models.IndexConfiguration)
        main_action = actions[1]
        assert isinstance(main_action, flow_entities.DSLScriptActionDetails)
        assert actions[0].id == "action_init"
        assert main_action.id == "action_1"
        _assert_init_action_matches_minimal_account(
            init_action_details=actions[0],
            user_action_id="ua-idx",
            account_id="acc-1",
        )
        assert main_action.dsl_script == _expected_index_dsl_script(
            coins=index_configuration.coins,
            rebalance_trigger_min_percent=index_configuration.rebalance_trigger_min_percent,
        )
        assert len(main_action.dependencies) == 1
        assert main_action.dependencies[0].action_id == "action_init"

    def test_copy_returns_init_and_copy_action(self):
        strategy_id = "copy-strategy"
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=protocol_models.AutomationConfiguration(
                name="copy-automation",
                account_ids=["acc-1"],
                configuration=protocol_models.AutomationConfigurationConfiguration(
                    protocol_models.CopyConfiguration(
                        configuration_type=protocol_models.ActionConfigurationType.COPY,
                        strategy_id=strategy_id,
                    )
                ),
            ),
        )
        user_action = _user_action_with_context(action_id="ua-copy", payload=create_payload)

        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as provider_instance_mock:
            provider_instance_mock.return_value.get_account.return_value = _minimal_exchange_account(account_id="acc-1")
            actions = executor._create_automation_actions(user_action)

        assert len(actions) == 2
        assert actions[0].id == "action_init"
        assert actions[1].id == "action_copy_exchange_account"
        assert isinstance(actions[1], flow_entities.DSLScriptActionDetails)
        _assert_init_action_matches_minimal_account(
            init_action_details=actions[0],
            user_action_id="ua-copy",
            account_id="acc-1",
        )
        assert actions[1].dsl_script == _expected_copy_dsl_script(strategy_id=strategy_id)
        assert len(actions[1].dependencies) == 1
        assert actions[1].dependencies[0].action_id == "action_init"

    def test_grid_returns_init_and_grid_action(self):
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=protocol_models.AutomationConfiguration(
                name="grid-automation",
                account_ids=["acc-1"],
                configuration=protocol_models.AutomationConfigurationConfiguration(
                    protocol_models.GridConfiguration(
                        configuration_type=protocol_models.ActionConfigurationType.GRID,
                        symbol="BTC/USDT",
                        spread=6,
                        increment=2,
                        buy_count=2,
                        sell_count=2,
                        enable_trailing_up=False,
                        enable_trailing_down=False,
                        order_by_order_trailing=False,
                    )
                ),
            ),
        )
        user_action = _user_action_with_context(action_id="ua-grid", payload=create_payload)

        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as provider_instance_mock:
            provider_instance_mock.return_value.get_account.return_value = _minimal_exchange_account(account_id="acc-1")
            actions = executor._create_automation_actions(user_action)

        assert len(actions) == 2
        grid_configuration = create_payload.configuration.configuration.actual_instance
        assert isinstance(grid_configuration, protocol_models.GridConfiguration)
        main_action = actions[1]
        assert isinstance(main_action, flow_entities.DSLScriptActionDetails)
        assert actions[0].id == "action_init"
        assert main_action.id == "action_1"
        _assert_init_action_matches_minimal_account(
            init_action_details=actions[0],
            user_action_id="ua-grid",
            account_id="acc-1",
        )
        assert main_action.dsl_script == _expected_grid_dsl_script(grid_configuration=grid_configuration)
        assert len(main_action.dependencies) == 1
        assert main_action.dependencies[0].action_id == "action_init"

    def test_generic_workflow_returns_init_and_chain(self):
        workflow_actions = [
            protocol_models.Action(
                id="w1",
                action_type="dsl",
                status=protocol_models.TaskStatus.PENDING,
                dsl="wait(1)",
            ),
            protocol_models.Action(
                id="w2",
                action_type="dsl",
                status=protocol_models.TaskStatus.PENDING,
                dsl="wait(2)",
            ),
        ]
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=protocol_models.AutomationConfiguration(
                name="workflow-automation",
                account_ids=["acc-1"],
                configuration=protocol_models.AutomationConfigurationConfiguration(
                    protocol_models.GenericWorkflowConfiguration(
                        configuration_type=protocol_models.ActionConfigurationType.GENERIC_WORKFLOW,
                        actions=workflow_actions,
                    )
                ),
            ),
        )
        user_action = _user_action_with_context(action_id="ua-wf", payload=create_payload)

        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as provider_instance_mock:
            provider_instance_mock.return_value.get_account.return_value = _minimal_exchange_account(account_id="acc-1")
            actions = executor._create_automation_actions(user_action)

        assert [action.id for action in actions] == ["action_init", "w1", "w2"]
        _assert_init_action_matches_minimal_account(
            init_action_details=actions[0],
            user_action_id="ua-wf",
            account_id="acc-1",
        )
        first_workflow = actions[1]
        second_workflow = actions[2]
        assert isinstance(first_workflow, flow_entities.DSLScriptActionDetails)
        assert isinstance(second_workflow, flow_entities.DSLScriptActionDetails)
        assert first_workflow.dsl_script == "wait(1)"
        assert second_workflow.dsl_script == "wait(2)"
        assert len(first_workflow.dependencies) == 1
        assert first_workflow.dependencies[0].action_id == "action_init"
        assert len(second_workflow.dependencies) == 1
        assert second_workflow.dependencies[0].action_id == "w1"

    def test_market_making_returns_init_and_run_octobot_process(self):
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=protocol_models.AutomationConfiguration(
                name="market-making-automation",
                account_ids=["acc-1"],
                configuration=protocol_models.AutomationConfigurationConfiguration(
                    protocol_models.MarketMakingConfiguration(
                        configuration_type=protocol_models.ActionConfigurationType.MARKET_MAKING,
                        symbol_configurations=[
                            protocol_models.MarketMakingSymbolConfiguration(
                                symbol="BTC/USDT",
                                reference_price=[
                                    protocol_models.MarketMakingReferencePair(
                                        exchange="binanceus",
                                        pair="BTC/USDT",
                                    )
                                ],
                                min_spread=0.5,
                                max_spread=1.0,
                                bids_count=1,
                                asks_count=1,
                                orders_distribution=protocol_models.MarketMakingOrdersDistribution.LINEAR,
                                funds_distribution=protocol_models.MarketMakingFundsDistribution.FLAT,
                            )
                        ],
                    )
                ),
            ),
        )
        user_action = _user_action_with_context(action_id="ua-mm", payload=create_payload)

        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as provider_instance_mock:
            provider_instance_mock.return_value.get_account.return_value = _minimal_exchange_account(account_id="acc-1")
            actions = executor._create_automation_actions(user_action)

        assert len(actions) == 2
        market_making_configuration = create_payload.configuration.configuration.actual_instance
        assert isinstance(market_making_configuration, protocol_models.MarketMakingConfiguration)
        main_action = actions[1]
        assert isinstance(main_action, flow_entities.DSLScriptActionDetails)
        protocol_account = _minimal_exchange_account(account_id="acc-1")
        expected_profile = action_details_factory.market_making_profile_data_factory(
            protocol_account=protocol_account,
            market_making_configuration=market_making_configuration,
        )
        expected_profile_dict = expected_profile.to_dict(include_default_values=False)
        expected_exchange_auth_segment = dsl_interpreter.format_parameter_value(None)
        expected_dsl = (
            "run_octobot_process("
            f"{protocol_account.id!r}, {dsl_interpreter.format_parameter_value(expected_profile_dict)}, "
            f"{expected_exchange_auth_segment}, "
            "waiting_time=2.0, ping_timeout=30.0)"
        )
        _assert_init_action_matches_minimal_account(
            init_action_details=actions[0],
            user_action_id="ua-mm",
            account_id="acc-1",
        )
        assert len(main_action.dependencies) == 1
        assert main_action.dependencies[0].action_id == "action_init"
        assert main_action.dsl_script == expected_dsl
        assert expected_profile_dict["crypto_currencies"][0]["trading_pairs"] == ["BTC/USDT"]
        assert expected_profile_dict["tentacles"][0]["config"]["symbol_configurations"][0]["symbol"] == "BTC/USDT"
        assert expected_profile_dict["tentacles"][0]["config"]["symbol_configurations"][0]["min_spread"] == 0.5
        assert expected_profile_dict["tentacles"][0]["config"]["symbol_configurations"][0]["max_spread"] == 1.0

    def test_unsupported_types_raise_dedicated_errors(self):
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=protocol_models.AutomationConfiguration(
                name="unsupported-automation",
                account_ids=["acc-1"],
                configuration=protocol_models.AutomationConfigurationConfiguration(
                    protocol_models.DCAConfiguration(
                        configuration_type=protocol_models.ActionConfigurationType.DCA,
                        symbols=["BTC/USDT"],
                        buy_orders_count=1,
                        percent_amount_per_buy_order=10,
                        profit_target_percent=1,
                        buy_order_price_discount_percent=1,
                        enable_stop_loss=False,
                        stop_loss_price_discount_percent=1,
                        trigger_mode="Time based",
                        use_init_entry_orders=True,
                        time_frames=[],
                        evaluators=[],
                    )
                ),
            ),
        )
        user_action = _user_action_with_context(action_id="ua-dca", payload=create_payload)
        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)

        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as provider_instance_mock:
            provider_instance_mock.return_value.get_account.return_value = _minimal_exchange_account(account_id="acc-1")
            with pytest.raises(node_errors.UnsupportedAutomationConfigurationTypeError):
                executor._create_automation_actions(user_action)

    def test_create_automation_task_wraps_actions_in_state_envelope(self):
        automation_name = "named-automation"
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=protocol_models.AutomationConfiguration(
                name=automation_name,
                account_ids=["acc-1"],
                configuration=protocol_models.AutomationConfigurationConfiguration(
                    protocol_models.IndexConfiguration(
                        configuration_type=protocol_models.ActionConfigurationType.INDEX,
                        coins=[protocol_models.IndexCoin(name="ETH", ratio=1.0)],
                        rebalance_trigger_min_percent=3.0,
                    )
                ),
            ),
        )
        user_action = _user_action_with_context(action_id="ua-task", payload=create_payload)
        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as provider_instance_mock:
            provider_instance_mock.return_value.get_account.return_value = _minimal_exchange_account(account_id="acc-1")
            actions = executor._create_automation_actions(user_action)

        task = asyncio.run(executor._create_automation_task(user_action, actions))
        assert task.name == automation_name
        _assert_task_content_matches_actions(
            task=task,
            user_action=user_action,
            expected_action_count=2,
        )
        parsed = json.loads(task.content or "{}")
        action_dicts = parsed["state"]["automation"]["actions_dag"]["actions"]
        assert action_dicts[1]["dsl_script"] == _expected_index_dsl_script(
            coins=[protocol_models.IndexCoin(name="ETH", ratio=1.0)],
            rebalance_trigger_min_percent=3.0,
        )

    @pytest.mark.asyncio
    async def test_execute_builds_actions_enqueues_task_via_trigger_task(self):
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=protocol_models.AutomationConfiguration(
                name="execute-automation",
                account_ids=["acc-1"],
                configuration=protocol_models.AutomationConfigurationConfiguration(
                    protocol_models.IndexConfiguration(
                        configuration_type=protocol_models.ActionConfigurationType.INDEX,
                        coins=[protocol_models.IndexCoin(name="BTC", ratio=1.0)],
                        rebalance_trigger_min_percent=5.0,
                    )
                ),
            ),
        )
        user_action = _user_action_with_context(action_id="ua-exec", payload=create_payload)
        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        expected_workflow_id = "workflow-id-from-test-mock"
        with (
            mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as provider_instance_mock,
            mock.patch(_TRIGGER_TASK_PATCH, new_callable=mock.AsyncMock) as trigger_task_mock,
        ):
            trigger_task_mock.return_value = expected_workflow_id
            provider_instance_mock.return_value.get_account.return_value = _minimal_exchange_account(account_id="acc-1")
            await executor.execute(user_action)

        trigger_task_mock.assert_awaited_once()
        scheduled_task = trigger_task_mock.await_args.args[0]
        assert isinstance(scheduled_task, node_models.Task)
        _assert_task_content_matches_actions(
            task=scheduled_task,
            user_action=user_action,
            expected_action_count=2,
        )
        provider_assertions.assert_provider_user_action_terminal_state(
            user_action_id="ua-exec",
            expected_status=protocol_models.UserActionStatus.COMPLETED,
            result_channel="automation",
            expect_error_details=False,
            wallet_address=_TEST_WALLET_ADDRESS,
        )
        stored = user_actions_provider_module.UserActionsProvider.instance().get_user_action(
            _TEST_WALLET_ADDRESS,
            "ua-exec",
        )
        inner = stored.result.actual_instance
        assert isinstance(inner, protocol_models.AutomationActionResult)
        assert inner.created_automation_id == expected_workflow_id

    @pytest.mark.asyncio
    async def test_execute_unsupported_automation_configuration_records_failure_in_provider(self):
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=protocol_models.AutomationConfiguration(
                name="unsupported-automation",
                account_ids=["acc-1"],
                configuration=protocol_models.AutomationConfigurationConfiguration(
                    protocol_models.DCAConfiguration(
                        configuration_type=protocol_models.ActionConfigurationType.DCA,
                        symbols=["BTC/USDT"],
                        buy_orders_count=1,
                        percent_amount_per_buy_order=10,
                        profit_target_percent=1,
                        buy_order_price_discount_percent=1,
                        enable_stop_loss=False,
                        stop_loss_price_discount_percent=1,
                        trigger_mode="Time based",
                        use_init_entry_orders=True,
                        time_frames=[],
                        evaluators=[],
                    )
                ),
            ),
        )
        user_action = _user_action_with_context(action_id="ua-dca-exec", payload=create_payload)
        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as provider_instance_mock:
            provider_instance_mock.return_value.get_account.return_value = _minimal_exchange_account(account_id="acc-1")
            with pytest.raises(node_errors.UnsupportedAutomationConfigurationTypeError):
                await executor.execute(user_action)
        provider_assertions.assert_provider_user_action_terminal_state(
            user_action_id="ua-dca-exec",
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="automation",
            expect_error_details=True,
            expected_error_message=protocol_models.AutomationActionResultErrorMessage.INVALID_CONFIGURATION,
            wallet_address=_TEST_WALLET_ADDRESS,
        )
