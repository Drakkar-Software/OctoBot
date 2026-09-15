import dataclasses
import typing

import octobot_commons.dataclasses
import octobot_commons.dsl_interpreter


@dataclasses.dataclass
class RefreshExchangeBotsAuthenticatedDataDetails:
    # todo update this when global view refresh trigger is implemented
    exchange_community_internal_name: str
    exchange_id: str
    exchange_account_id: typing.Optional[str]
    to_recall_bot_id: typing.Optional[str] = None
    update_account_status: bool = False
    ignored_exchange_account_ids: typing.Optional[set[str]] = None


@dataclasses.dataclass
class NextIterationDetails(octobot_commons.dataclasses.FlexibleDataclass):
    instant_trigger: bool = False
    unclearable_trade_exchange_order_ids: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class PostIterationActionsDetails(octobot_commons.dataclasses.MinimizableDataclass):
    stop_automation: bool = False
    configuration_update: typing.Optional[str] = None
    updated_exchange_account_elements: typing.Optional[dict] = None
    postpone_execution: bool = False
    postpone_reason: typing.Optional[str] = None
    raisable_error: typing.Optional[str] = None
    trigger_global_view_refresh: bool = False
    trigger_global_view_refresh_args: typing.Optional[RefreshExchangeBotsAuthenticatedDataDetails] = None
    next_iteration_details: typing.Optional[NextIterationDetails] = None

    def has_automation_actions(self) -> bool:
        return bool(self.stop_automation)

    @classmethod
    def post_iteration_clear(cls, post_iteration_payload: dict) -> None:
        post_iteration_payload.pop("updated_exchange_account_elements", None)

    @classmethod
    def post_iteration_clear_from_action_result(cls, action_result: dict) -> None:
        """
        Remove merge-consumed PostIteration fields from persisted action-result dicts.
        Mutates ``action_result`` in place (top-level and recall-nested blobs).
        """
        post_iter_name = cls.__name__
        # Top-level PostIteration (e.g. stop_automation / update_automation_configuration).
        top_level_payload = action_result.get(post_iter_name)
        if isinstance(top_level_payload, dict):
            cls.post_iteration_clear(top_level_payload)
        # Nested PostIteration inside a re-calling operator recall payload (e.g. run_octobot_process).
        if not octobot_commons.dsl_interpreter.ReCallingOperatorResult.is_re_calling_operator_result(
            action_result
        ):
            return
        recall_wrapper = octobot_commons.dsl_interpreter.ReCallingOperatorResult.from_dict(
            action_result[octobot_commons.dsl_interpreter.ReCallingOperatorResult.__name__]
        )
        inner_last_result = recall_wrapper.last_execution_result
        if not isinstance(inner_last_result, dict):
            return
        nested_payload = inner_last_result.get(post_iter_name)
        if isinstance(nested_payload, dict):
            cls.post_iteration_clear(nested_payload)

    def should_cancel_iteration(self) -> bool:
        # cancelled if global view refresh is triggered, otherwise proceed 
        # with next iteration required steps
        return self.trigger_global_view_refresh