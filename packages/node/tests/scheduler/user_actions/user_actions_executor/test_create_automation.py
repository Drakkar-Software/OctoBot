import asyncio
import datetime
import json
import typing

import mock
import pytest

import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_copy.enums as copy_enums
import octobot_flow.entities as flow_entities
import octobot_protocol.models as protocol_models
import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading

import octobot_node.errors as node_errors
import octobot_node.models as node_models
import octobot_node.scheduler.user_actions.user_actions_executor.create_automation as create_automation_executor
import octobot_node.scheduler.user_actions.user_actions_executor.util.action_details_factory as action_details_factory

from . import provider_assertions

_ACCOUNT_PROVIDER_INSTANCE_PATCH = (
    "octobot_sync.sync.collection_providers.AccountProvider.instance"
)
_STRATEGY_PROVIDER_INSTANCE_PATCH = (
    "octobot_sync.sync.collection_providers.StrategyProvider.instance"
)
_TEST_WALLET_ADDRESS = "0xaaabbbcccddd"

_DEFAULT_STORED_STRATEGY_ID = "7c5e8fd1-a3b9-41d2-b6c1-92e4e6b0c3a1"
_DEFAULT_STORED_STRATEGY_VERSION = "2.4.1"
_TEST_ACCOUNT_TS = datetime.datetime(2026, 3, 12, 9, 0, tzinfo=datetime.UTC)


def _default_strategy_reference(
    *,
    strategy_id: str = _DEFAULT_STORED_STRATEGY_ID,
    version: str = _DEFAULT_STORED_STRATEGY_VERSION,
    emit_signals: bool = False,
) -> protocol_models.StrategyReference:
    return protocol_models.StrategyReference(
        id=strategy_id,
        version=version,
        emit_signals=emit_signals,
    )


def _automation_configuration(
    *,
    name: str,
    strategy_reference: protocol_models.StrategyReference,
    account_id: str,
    created_at: datetime.datetime | None = None,
) -> protocol_models.AutomationConfiguration:
    return protocol_models.AutomationConfiguration(
        name=name,
        created_at=(
            created_at
            if created_at is not None
            else datetime.datetime(2026, 5, 14, 11, 30, tzinfo=datetime.UTC)
        ),
        strategy=strategy_reference,
        accounts=[protocol_models.AccountReference(id=account_id)],
    )


def _stored_strategy_matching_reference(
    strategy_reference: protocol_models.StrategyReference,
    configuration_instance: typing.Any,
) -> protocol_models.Strategy:
    return protocol_models.Strategy(
        id=strategy_reference.id,
        version=strategy_reference.version,
        name="Seeded automation strategy",
        reference_market="USDT",
        configuration=protocol_models.StrategyConfiguration(configuration_instance),
    )


def _wrap(configuration_payload) -> protocol_models.UserActionConfiguration:
    return protocol_models.UserActionConfiguration.from_json(configuration_payload.to_json())


def _minimal_exchange_account(*, account_id: str) -> protocol_models.Account:
    return protocol_models.Account(
        id=account_id,
        name="Test account",
        is_simulated=True,
        created_at=_TEST_ACCOUNT_TS,
        updated_at=_TEST_ACCOUNT_TS,
        assets=[
            protocol_models.DetailedAsset(
                symbol="USDT",
                total=1000.0,
                available=1000.0,
            )
        ],
        specifics=protocol_models.AccountSpecifics(
            actual_instance=protocol_models.ExchangeAccount(
                account_type=protocol_models.AccountType.EXCHANGE,
                trading_type=protocol_models.TradingType.SPOT,
                exchange="binanceus",
                remote_account_id="remote-1",
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
    protocol_account: protocol_models.Account,
    strategy_reference: protocol_models.StrategyReference,
) -> None:
    assert init_action_details.id == "action_init"
    init_config = init_action_details.config
    metadata = init_config["automation"]["metadata"]
    assert metadata["automation_id"] == user_action_id
    assert metadata["strategy_id"] == strategy_reference.id
    assert metadata["strategy_version"] == strategy_reference.version
    assert metadata.get("emit_signals", False) is bool(strategy_reference.emit_signals)

    portfolio_content = init_config["automation"]["exchange_account_elements"]["portfolio"]["content"]
    assert portfolio_content["USDT"]["available"] == 1000.0
    assert portfolio_content["USDT"]["total"] == 1000.0
    exch_meta = init_config["exchange_account_details"]["metadata"]
    assert exch_meta["id"] == account_id
    assert exch_meta["name"] == "Test account"
    expected_ts = protocol_account.updated_at
    if expected_ts.tzinfo is None:
        expected_ts = expected_ts.replace(tzinfo=datetime.UTC)
    assert exch_meta["updated_at"] == pytest.approx(expected_ts.timestamp())
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
    def test_strategy_reference_populates_init_metadata(self):
        strategy_id = "8b2c4410-5632-49a1-92ff-0192837465ab"
        version = "1.9.3"
        strategy_ref = protocol_models.StrategyReference(
            id=strategy_id,
            version=version,
            emit_signals=True,
        )
        idx = protocol_models.IndexConfiguration(
            configuration_type=protocol_models.ActionConfigurationType.INDEX,
            coins=[protocol_models.IndexCoin(name="BTC", ratio=1.0)],
            rebalance_trigger_min_percent=5.0,
        )
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=_automation_configuration(
                name="strategy-automation",
                strategy_reference=strategy_ref,
                account_id="acc-1",
            ),
        )
        user_action = _user_action_with_context(action_id="ua-strategy", payload=create_payload)

        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        account = _minimal_exchange_account(account_id="acc-1")
        stored = _stored_strategy_matching_reference(strategy_ref, idx)
        with (
            mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as account_mock,
            mock.patch(_STRATEGY_PROVIDER_INSTANCE_PATCH) as strategy_mock,
        ):
            account_mock.return_value.get_item.return_value = account
            strategy_mock.return_value.get_item.return_value = stored
            actions = executor._create_automation_actions(user_action)

        _assert_init_action_matches_minimal_account(
            init_action_details=actions[0],
            user_action_id="ua-strategy",
            account_id="acc-1",
            protocol_account=account,
            strategy_reference=strategy_ref,
        )

    def test_index_returns_init_and_index_action(self):
        idx = protocol_models.IndexConfiguration(
            configuration_type=protocol_models.ActionConfigurationType.INDEX,
            coins=[protocol_models.IndexCoin(name="BTC", ratio=1.0)],
            rebalance_trigger_min_percent=5.0,
        )
        strat_ref = _default_strategy_reference()
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=_automation_configuration(
                name="index-automation",
                strategy_reference=strat_ref,
                account_id="acc-1",
            ),
        )
        user_action = _user_action_with_context(action_id="ua-idx", payload=create_payload)

        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        account = _minimal_exchange_account(account_id="acc-1")
        stored = _stored_strategy_matching_reference(strat_ref, idx)
        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as account_mock, mock.patch(
            _STRATEGY_PROVIDER_INSTANCE_PATCH,
        ) as strategy_mock:
            account_mock.return_value.get_item.return_value = account
            strategy_mock.return_value.get_item.return_value = stored
            actions = executor._create_automation_actions(user_action)

        assert len(actions) == 2
        index_configuration = stored.configuration.actual_instance
        assert isinstance(index_configuration, protocol_models.IndexConfiguration)
        main_action = actions[1]
        assert isinstance(main_action, flow_entities.DSLScriptActionDetails)
        assert actions[0].id == "action_init"
        assert main_action.id == "action_1"
        _assert_init_action_matches_minimal_account(
            init_action_details=actions[0],
            user_action_id="ua-idx",
            account_id="acc-1",
            protocol_account=account,
            strategy_reference=strat_ref,
        )
        assert main_action.dsl_script == _expected_index_dsl_script(
            coins=index_configuration.coins,
            rebalance_trigger_min_percent=index_configuration.rebalance_trigger_min_percent,
        )
        assert len(main_action.dependencies) == 1
        assert main_action.dependencies[0].action_id == "action_init"

    def test_copy_returns_init_and_copy_action(self):
        copy_strategy_id = "copy-strategy"
        idx = protocol_models.CopyConfiguration(
            configuration_type=protocol_models.ActionConfigurationType.COPY,
            strategy_id=copy_strategy_id,
        )
        strat_ref = _default_strategy_reference()
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=_automation_configuration(
                name="copy-automation",
                strategy_reference=strat_ref,
                account_id="acc-1",
            ),
        )
        user_action = _user_action_with_context(action_id="ua-copy", payload=create_payload)

        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        account = _minimal_exchange_account(account_id="acc-1")
        stored = _stored_strategy_matching_reference(strat_ref, idx)
        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as account_mock, mock.patch(
            _STRATEGY_PROVIDER_INSTANCE_PATCH,
        ) as strategy_mock:
            account_mock.return_value.get_item.return_value = account
            strategy_mock.return_value.get_item.return_value = stored
            actions = executor._create_automation_actions(user_action)

        assert len(actions) == 2
        assert actions[0].id == "action_init"
        assert actions[1].id == "action_copy_exchange_account"
        assert isinstance(actions[1], flow_entities.DSLScriptActionDetails)
        _assert_init_action_matches_minimal_account(
            init_action_details=actions[0],
            user_action_id="ua-copy",
            account_id="acc-1",
            protocol_account=account,
            strategy_reference=strat_ref,
        )
        assert actions[1].dsl_script == _expected_copy_dsl_script(strategy_id=copy_strategy_id)
        assert len(actions[1].dependencies) == 1
        assert actions[1].dependencies[0].action_id == "action_init"

    def test_grid_returns_init_and_grid_action(self):
        grid_configuration = protocol_models.GridConfiguration(
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
        strat_ref = _default_strategy_reference()
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=_automation_configuration(
                name="grid-automation",
                strategy_reference=strat_ref,
                account_id="acc-1",
            ),
        )
        user_action = _user_action_with_context(action_id="ua-grid", payload=create_payload)

        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        account = _minimal_exchange_account(account_id="acc-1")
        stored = _stored_strategy_matching_reference(strat_ref, grid_configuration)
        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as account_mock, mock.patch(
            _STRATEGY_PROVIDER_INSTANCE_PATCH,
        ) as strategy_mock:
            account_mock.return_value.get_item.return_value = account
            strategy_mock.return_value.get_item.return_value = stored
            actions = executor._create_automation_actions(user_action)

        assert len(actions) == 2
        assert isinstance(stored.configuration.actual_instance, protocol_models.GridConfiguration)
        main_action = actions[1]
        assert isinstance(main_action, flow_entities.DSLScriptActionDetails)
        assert actions[0].id == "action_init"
        assert main_action.id == "action_1"
        _assert_init_action_matches_minimal_account(
            init_action_details=actions[0],
            user_action_id="ua-grid",
            account_id="acc-1",
            protocol_account=account,
            strategy_reference=strat_ref,
        )
        assert main_action.dsl_script == _expected_grid_dsl_script(
            grid_configuration=grid_configuration,
        )
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
        wf = protocol_models.GenericWorkflowConfiguration(
            configuration_type=protocol_models.ActionConfigurationType.GENERIC_WORKFLOW,
            actions=workflow_actions,
        )
        strat_ref = _default_strategy_reference()
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=_automation_configuration(
                name="workflow-automation",
                strategy_reference=strat_ref,
                account_id="acc-1",
            ),
        )
        user_action = _user_action_with_context(action_id="ua-wf", payload=create_payload)

        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        account = _minimal_exchange_account(account_id="acc-1")
        stored = _stored_strategy_matching_reference(strat_ref, wf)
        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as account_mock, mock.patch(
            _STRATEGY_PROVIDER_INSTANCE_PATCH,
        ) as strategy_mock:
            account_mock.return_value.get_item.return_value = account
            strategy_mock.return_value.get_item.return_value = stored
            actions = executor._create_automation_actions(user_action)

        assert [action.id for action in actions] == ["action_init", "w1", "w2"]
        _assert_init_action_matches_minimal_account(
            init_action_details=actions[0],
            user_action_id="ua-wf",
            account_id="acc-1",
            protocol_account=account,
            strategy_reference=strat_ref,
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
        mf = protocol_models.MarketMakingConfiguration(
            configuration_type=protocol_models.ActionConfigurationType.MARKET_MAKING,
            pair_settings=[
                protocol_models.MarketMakingSymbolConfiguration(
                    trading_pair="BTC/USDT",
                    exchange="binanceus",
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
        strat_ref = _default_strategy_reference()
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=_automation_configuration(
                name="market-making-automation",
                strategy_reference=strat_ref,
                account_id="acc-1",
            ),
        )
        user_action = _user_action_with_context(action_id="ua-mm", payload=create_payload)

        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        account = _minimal_exchange_account(account_id="acc-1")
        stored = _stored_strategy_matching_reference(strat_ref, mf)
        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as account_mock, mock.patch(
            _STRATEGY_PROVIDER_INSTANCE_PATCH,
        ) as strategy_mock:
            account_mock.return_value.get_item.return_value = account
            strategy_mock.return_value.get_item.return_value = stored
            actions = executor._create_automation_actions(user_action)

        assert len(actions) == 2
        market_making_configuration = stored.configuration.actual_instance
        assert isinstance(market_making_configuration, protocol_models.MarketMakingConfiguration)
        main_action = actions[1]
        assert isinstance(main_action, flow_entities.DSLScriptActionDetails)
        expected_profile = action_details_factory.market_making_profile_data_factory(
            protocol_account=account,
            market_making_configuration=market_making_configuration,
            reference_market=stored.reference_market,
        )
        expected_profile_dict = expected_profile.to_dict(include_default_values=False)
        expected_exchange_auth_segment = dsl_interpreter.format_parameter_value(None)
        expected_dsl = (
            "run_octobot_process("
            f"{account.id!r}, {dsl_interpreter.format_parameter_value(expected_profile_dict)}, "
            f"{expected_exchange_auth_segment}, "
            "waiting_time=2.0, ping_timeout=30.0)"
        )
        _assert_init_action_matches_minimal_account(
            init_action_details=actions[0],
            user_action_id="ua-mm",
            account_id="acc-1",
            protocol_account=account,
            strategy_reference=strat_ref,
        )
        assert len(main_action.dependencies) == 1
        assert main_action.dependencies[0].action_id == "action_init"
        assert main_action.dsl_script == expected_dsl
        assert expected_profile_dict["crypto_currencies"][0]["trading_pairs"] == ["BTC/USDT"]
        assert (
            expected_profile_dict["tentacles"][0]["config"]["pair_settings"][0]["trading_pair"]
            == "BTC/USDT"
        )
        assert expected_profile_dict["tentacles"][0]["config"]["pair_settings"][0]["min_spread"] == 0.5
        assert expected_profile_dict["tentacles"][0]["config"]["pair_settings"][0]["max_spread"] == 1.0

    def test_unsupported_types_raise_dedicated_errors(self):
        dca = protocol_models.DCAConfiguration(
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
        strat_ref = _default_strategy_reference()
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=_automation_configuration(
                name="unsupported-automation",
                strategy_reference=strat_ref,
                account_id="acc-1",
            ),
        )
        user_action = _user_action_with_context(action_id="ua-dca", payload=create_payload)
        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)

        stored = _stored_strategy_matching_reference(strat_ref, dca)
        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as account_mock, mock.patch(
            _STRATEGY_PROVIDER_INSTANCE_PATCH,
        ) as strategy_mock:
            account_mock.return_value.get_item.return_value = _minimal_exchange_account(account_id="acc-1")
            strategy_mock.return_value.get_item.return_value = stored
            with pytest.raises(node_errors.UnsupportedAutomationConfigurationTypeError):
                executor._create_automation_actions(user_action)

    def test_strategy_missing_raises_mapped_user_action_error_async(self):
        strat_ref = _default_strategy_reference()
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=_automation_configuration(
                name="missing-strategy-auto",
                strategy_reference=strat_ref,
                account_id="acc-1",
            ),
        )
        user_action = _user_action_with_context(action_id="ua-missing-strategy", payload=create_payload)
        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)

        async def run_execute():
            with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as account_mock, mock.patch(
                _STRATEGY_PROVIDER_INSTANCE_PATCH,
            ) as strategy_mock:
                account_mock.return_value.get_item.return_value = _minimal_exchange_account(
                    account_id="acc-1",
                )

                def _raise_missing(_wallet: str, sid: str):
                    raise collection_errors.ItemNotFoundError(sid)

                strategy_mock.return_value.get_item.side_effect = _raise_missing
                await executor.execute(user_action)

        with pytest.raises(node_errors.AutomationStrategyNotFoundError):
            asyncio.run(run_execute())
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="automation",
            expect_error_details=True,
            expected_error_message=protocol_models.AutomationActionResultErrorMessage.STRATEGY_NOT_FOUND,
        )

    def test_strategy_version_mismatch_raises_mapped_user_action_error_async(self):
        idx = protocol_models.IndexConfiguration(
            configuration_type=protocol_models.ActionConfigurationType.INDEX,
            coins=[protocol_models.IndexCoin(name="BTC", ratio=1.0)],
            rebalance_trigger_min_percent=5.0,
        )
        strat_ref = _default_strategy_reference(version=_DEFAULT_STORED_STRATEGY_VERSION)
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=_automation_configuration(
                name="version-mismatch-auto",
                strategy_reference=strat_ref,
                account_id="acc-1",
            ),
        )
        user_action = _user_action_with_context(action_id="ua-version-mismatch", payload=create_payload)
        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        mismatched_stored = protocol_models.Strategy(
            id=strat_ref.id,
            version="different-version",
            name="Stale version",
            reference_market="USDT",
            configuration=protocol_models.StrategyConfiguration(idx),
        )

        async def run_execute():
            with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as account_mock, mock.patch(
                _STRATEGY_PROVIDER_INSTANCE_PATCH,
            ) as strategy_mock:
                account_mock.return_value.get_item.return_value = _minimal_exchange_account(
                    account_id="acc-1",
                )
                strategy_mock.return_value.get_item.return_value = mismatched_stored
                await executor.execute(user_action)

        with pytest.raises(node_errors.AutomationStrategyVersionMismatchError):
            asyncio.run(run_execute())
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="automation",
            expect_error_details=True,
            expected_error_message=protocol_models.AutomationActionResultErrorMessage.STRATEGY_VERSION_NOT_FOUND,
        )

    def test_create_automation_task_wraps_actions_in_state_envelope(self):
        automation_name = "named-automation"
        idx = protocol_models.IndexConfiguration(
            configuration_type=protocol_models.ActionConfigurationType.INDEX,
            coins=[protocol_models.IndexCoin(name="ETH", ratio=1.0)],
            rebalance_trigger_min_percent=3.0,
        )
        strat_ref = _default_strategy_reference()
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=_automation_configuration(
                name=automation_name,
                strategy_reference=strat_ref,
                account_id="acc-1",
            ),
        )
        user_action = _user_action_with_context(action_id="ua-task", payload=create_payload)
        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        account = _minimal_exchange_account(account_id="acc-1")
        stored = _stored_strategy_matching_reference(strat_ref, idx)
        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as account_mock, mock.patch(
            _STRATEGY_PROVIDER_INSTANCE_PATCH,
        ) as strategy_mock:
            account_mock.return_value.get_item.return_value = account
            strategy_mock.return_value.get_item.return_value = stored
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
    async def test_execute_builds_actions_and_stages_automation_task_for_workflow(self):
        idx = protocol_models.IndexConfiguration(
            configuration_type=protocol_models.ActionConfigurationType.INDEX,
            coins=[protocol_models.IndexCoin(name="BTC", ratio=1.0)],
            rebalance_trigger_min_percent=5.0,
        )
        strat_ref = _default_strategy_reference()
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=_automation_configuration(
                name="execute-automation",
                strategy_reference=strat_ref,
                account_id="acc-1",
            ),
        )
        user_action = _user_action_with_context(action_id="ua-exec", payload=create_payload)
        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        stored = _stored_strategy_matching_reference(strat_ref, idx)
        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as account_mock, mock.patch(
            _STRATEGY_PROVIDER_INSTANCE_PATCH,
        ) as strategy_mock:
            account_mock.return_value.get_item.return_value = _minimal_exchange_account(account_id="acc-1")
            strategy_mock.return_value.get_item.return_value = stored
            await executor.execute(user_action)

        scheduled_task = executor.post_actions.to_create_automation_task
        assert scheduled_task is not None
        _assert_task_content_matches_actions(
            task=scheduled_task,
            user_action=user_action,
            expected_action_count=2,
        )
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.COMPLETED,
            result_channel="automation",
            expect_error_details=False,
        )
        inner = user_action.result.actual_instance
        assert isinstance(inner, protocol_models.AutomationActionResult)
        assert inner.created_automation_id == scheduled_task.id

    @pytest.mark.asyncio
    async def test_execute_unsupported_automation_configuration_records_failure_in_provider(self):
        dca = protocol_models.DCAConfiguration(
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
        strat_ref = _default_strategy_reference()
        create_payload = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=_automation_configuration(
                name="unsupported-automation",
                strategy_reference=strat_ref,
                account_id="acc-1",
            ),
        )
        user_action = _user_action_with_context(action_id="ua-dca-exec", payload=create_payload)
        executor = create_automation_executor.CreateAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        stored = _stored_strategy_matching_reference(strat_ref, dca)
        with mock.patch(_ACCOUNT_PROVIDER_INSTANCE_PATCH) as account_mock, mock.patch(
            _STRATEGY_PROVIDER_INSTANCE_PATCH,
        ) as strategy_mock:
            account_mock.return_value.get_item.return_value = _minimal_exchange_account(account_id="acc-1")
            strategy_mock.return_value.get_item.return_value = stored
            with pytest.raises(node_errors.UnsupportedAutomationConfigurationTypeError):
                await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="automation",
            expect_error_details=True,
            expected_error_message=protocol_models.AutomationActionResultErrorMessage.INVALID_CONFIGURATION,
        )
