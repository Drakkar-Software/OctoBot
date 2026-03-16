import dataclasses
import typing

import octobot_commons.dataclasses


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
    postpone_execution: bool = False
    postpone_reason: typing.Optional[str] = None
    raisable_error: typing.Optional[str] = None
    trigger_global_view_refresh: bool = False
    trigger_global_view_refresh_args: typing.Optional[RefreshExchangeBotsAuthenticatedDataDetails] = None
    next_iteration_details: typing.Optional[NextIterationDetails] = None

    def has_automation_actions(self) -> bool:
        return bool(self.stop_automation)

    def should_cancel_iteration(self) -> bool:
        # cancelled if global view refresh is triggered, otherwise proceed 
        # with next iteration required steps
        return self.trigger_global_view_refresh