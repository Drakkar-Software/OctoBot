import mock
import pytest

pytest.importorskip("octobot_flow")

import octobot_flow.entities.signals.signal_exchange_context as signal_exchange_context_module
import octobot_flow.errors as flow_errors
import octobot_flow.parsers.signal_script_resolver as signal_script_resolver
import octobot_trading.enums as trading_enums

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.signal_priority_action as signal_priority_action_module
import octobot_node.scheduler.user_actions.user_actions_executor.automation.signal_priority_action_builder as signal_priority_action_builder


USER_ACTION_ID = "ua-signal-priority"
AUTOMATION_ID = "00000000-0000-4000-8000-000000000099"
USER_ID = "0xwallet"

SIGNAL_SCRIPT = "SYMBOL=BTC/USDC\nSIGNAL=buy\nVOLUME=0.01"
SIGNAL_BUY_KEYVAL = SIGNAL_SCRIPT
RESOLVED_DSL = "market('buy', 'BTC/USDC', 0.01)"

EXCHANGE_CONTEXT = signal_exchange_context_module.SignalExchangeContext(
    exchange_name="binance",
    exchange_type=trading_enums.ExchangeTypes.SPOT,
    reference_market="USDT",
    ignore_exchange_key=True,
)


def _build_payload(signal_payload):
    return signal_priority_action_builder.build_signal_priority_actions(
        user_action_id=USER_ACTION_ID,
        automation_id=AUTOMATION_ID,
        user_id=USER_ID,
        signal_payload=signal_payload,
    )


@pytest.fixture
def mock_exchange_context_loader():
    with mock.patch.object(
        signal_priority_action_builder,
        "_load_signal_exchange_context",
        new=mock.AsyncMock(return_value=EXCHANGE_CONTEXT),
    ) as loader_mock:
        yield loader_mock


class TestBuildSignalPriorityActionsNormalizePayload:
    @pytest.mark.asyncio
    async def test_list_of_two_scripts(self, mock_exchange_context_loader):
        with mock.patch.object(
            signal_script_resolver,
            "resolve_signal_script",
            side_effect=[RESOLVED_DSL, RESOLVED_DSL],
        ) as resolve_mock:
            actions = await _build_payload(
                [{"script": SIGNAL_SCRIPT}, {"script": SIGNAL_SCRIPT}],
            )

        assert len(actions) == 2
        assert actions[0].id == f"action_signal_priority_{USER_ACTION_ID}_0"
        assert actions[1].id == f"action_signal_priority_{USER_ACTION_ID}_1"
        assert resolve_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_actions_wrapper(self, mock_exchange_context_loader):
        with mock.patch.object(
            signal_script_resolver,
            "resolve_signal_script",
            return_value=RESOLVED_DSL,
        ) as resolve_mock:
            actions = await _build_payload(
                {"actions": [{"script": SIGNAL_SCRIPT}, {"script": SIGNAL_SCRIPT}]},
            )

        assert len(actions) == 2
        assert resolve_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_single_signal_dict_wrapped(self, mock_exchange_context_loader):
        with mock.patch.object(
            signal_script_resolver,
            "resolve_signal_script",
            return_value=RESOLVED_DSL,
        ):
            actions = await _build_payload({"script": SIGNAL_SCRIPT})

        assert len(actions) == 1

    @pytest.mark.asyncio
    async def test_empty_list_raises(self):
        with pytest.raises(node_errors.InvalidUserActionPayloadError):
            await _build_payload([])

    @pytest.mark.asyncio
    async def test_non_dict_list_item_raises(self):
        with pytest.raises(node_errors.InvalidUserActionPayloadError):
            await _build_payload(["not-a-dict"])


class TestBuildSignalPriorityActionsResolve:
    @pytest.mark.asyncio
    async def test_signal_dict_without_script_wrapper(self, mock_exchange_context_loader):
        signal_dict = {"SYMBOL": "BTC/USDC", "SIGNAL": "buy", "VOLUME": 0.01}
        with mock.patch.object(
            signal_script_resolver,
            "resolve_signal_script",
            return_value=RESOLVED_DSL,
        ) as resolve_mock:
            actions = await _build_payload([signal_dict])

        resolve_mock.assert_called_once_with(
            signal_dict,
            exchange_name=EXCHANGE_CONTEXT.exchange_name,
            exchange_type=EXCHANGE_CONTEXT.exchange_type,
            reference_market=EXCHANGE_CONTEXT.reference_market,
            ignore_exchange_key=True,
        )
        assert len(actions) == 1

    @pytest.mark.asyncio
    async def test_legacy_passthrough(self, mock_exchange_context_loader):
        legacy_action = {"id": "x", "dsl_script": "stop_automation()", "await_execution_result": False}
        with mock.patch.object(
            signal_script_resolver,
            "resolve_signal_script",
        ) as resolve_mock:
            actions = await _build_payload([legacy_action])

        assert actions == [signal_priority_action_module.SignalPriorityAction.from_dict(legacy_action)]
        resolve_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_passes_through_await_execution_result(self, mock_exchange_context_loader):
        with mock.patch.object(
            signal_script_resolver,
            "resolve_signal_script",
            return_value=RESOLVED_DSL,
        ):
            actions = await _build_payload(
                [{"script": SIGNAL_SCRIPT, "await_execution_result": False}],
            )

        assert actions[0].await_execution_result is False

    @pytest.mark.asyncio
    async def test_mixed_resolve_and_passthrough(self, mock_exchange_context_loader):
        legacy_action = {"id": "legacy", "dsl_script": "stop_automation()"}
        with mock.patch.object(
            signal_script_resolver,
            "resolve_signal_script",
            return_value=RESOLVED_DSL,
        ) as resolve_mock:
            actions = await _build_payload(
                [{"script": SIGNAL_SCRIPT}, legacy_action],
            )

        assert len(actions) == 2
        resolve_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_id_when_script_and_id(self, mock_exchange_context_loader):
        with mock.patch.object(
            signal_script_resolver,
            "resolve_signal_script",
            return_value=RESOLVED_DSL,
        ):
            actions = await _build_payload([{"id": "custom", "script": SIGNAL_SCRIPT}])

        assert actions[0].id == "custom"


class TestBuildSignalPriorityActionsFailFast:
    @pytest.mark.asyncio
    async def test_second_signal_invalid_aborts_batch(self, mock_exchange_context_loader):
        with mock.patch.object(
            signal_script_resolver,
            "resolve_signal_script",
            side_effect=[
                RESOLVED_DSL,
                flow_errors.InvalidAutomationActionError("invalid"),
            ],
        ) as resolve_mock:
            with pytest.raises(node_errors.InvalidUserActionPayloadError):
                await _build_payload(
                    [{"script": SIGNAL_SCRIPT}, {"script": "bad"}],
                )

        assert resolve_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_resolver_error_wrapped(self, mock_exchange_context_loader):
        with mock.patch.object(
            signal_script_resolver,
            "resolve_signal_script",
            side_effect=flow_errors.InvalidAutomationActionError("bad signal"),
        ):
            with pytest.raises(node_errors.InvalidUserActionPayloadError, match="bad signal"):
                await _build_payload([{"script": SIGNAL_SCRIPT}])


class TestBuildSignalPriorityActionsExchangeContext:
    @pytest.mark.asyncio
    async def test_no_active_automation_raises(self):
        with mock.patch.object(
            signal_priority_action_builder,
            "_load_signal_exchange_context",
            new=mock.AsyncMock(
                side_effect=node_errors.ActiveAutomationWorkflowNotFoundError("missing"),
            ),
        ):
            with pytest.raises(node_errors.ActiveAutomationWorkflowNotFoundError):
                await _build_payload([{"script": SIGNAL_SCRIPT}])


class TestBuildSignalPriorityActionsResolverIntegration:
    @pytest.mark.asyncio
    async def test_signal_script_resolved_via_real_resolver(self, mock_exchange_context_loader):
        actions = await _build_payload([{"script": SIGNAL_BUY_KEYVAL}])

        assert len(actions) == 1
        assert isinstance(actions[0], signal_priority_action_module.SignalPriorityAction)
        dsl_script = actions[0].dsl_script
        assert "market" in dsl_script
        assert "buy" in dsl_script
        assert "BTC/USDC" in dsl_script
