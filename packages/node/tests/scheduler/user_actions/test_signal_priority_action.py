import octobot_node.scheduler.user_actions.signal_priority_action as signal_priority_action_module


class TestSignalPriorityActionSerialization:
    def test_to_dict_from_dict_round_trip(self):
        priority_action = signal_priority_action_module.SignalPriorityAction(
            id="action_1",
            dsl_script="noop()",
            await_execution_result=False,
        )
        round_tripped = signal_priority_action_module.SignalPriorityAction.from_dict(
            priority_action.to_dict(include_default_values=False),
        )
        assert round_tripped.id == "action_1"
        assert round_tripped.dsl_script == "noop()"
        assert round_tripped.await_execution_result is False

    def test_default_await_execution_result_is_true(self):
        priority_action = signal_priority_action_module.SignalPriorityAction(
            id="action_2",
            dsl_script="market('buy', 'BTC/USDC', 0.01)",
        )
        assert priority_action.await_execution_result is True
        assert "await_execution_result" not in priority_action.to_dict(include_default_values=False)
