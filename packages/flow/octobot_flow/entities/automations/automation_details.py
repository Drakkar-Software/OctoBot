import dataclasses
import typing

import octobot_commons.dataclasses

import octobot_flow.entities.automations.execution_details as execution_details_import
import octobot_flow.entities.accounts.reference_exchange_account_elements as reference_exchange_account_elements_import
import octobot_flow.entities.accounts.client_exchange_account_elements as client_exchange_account_elements_import
import octobot_flow.entities.actions.actions_dag as actions_dag_import
import octobot_flow.entities.accounts.account_elements as account_elements_import
import octobot_flow.entities.automations.post_iteration_actions_details as post_iteration_actions_details_import


@dataclasses.dataclass
class AutomationMetadata(octobot_commons.dataclasses.MinimizableDataclass):
    automation_id: str = dataclasses.field(default="", repr=True)


@dataclasses.dataclass
class AutomationDetails(octobot_commons.dataclasses.MinimizableDataclass, octobot_commons.dataclasses.UpdatableDataclass):
    """
    Defines an automation made of:
    - An actions DAG defining the actions to be executed as DSL or configured actions
      This actions DAG also defines bot strategies in the form of a keyword with parameters
    - Reference exchange account elements if relevant => ideal strategy exchange state, shared to others
    - Client's local exchange account elements if relevant ((sub)portfolio, orders, positions, trades, ...)
    - Extra accounts elements if any (blockchain wallets, etc.)
    - Current and previous execution details
    - Post actions if any (local to an iteration)
    """

    metadata: AutomationMetadata = dataclasses.field(default_factory=AutomationMetadata, repr=True)
    actions_dag: actions_dag_import.ActionsDAG = dataclasses.field(default_factory=actions_dag_import.ActionsDAG, repr=True)
    reference_exchange_account_elements: typing.Optional[reference_exchange_account_elements_import.ReferenceExchangeAccountElements] = dataclasses.field(default=None, repr=True)
    client_exchange_account_elements: typing.Optional[client_exchange_account_elements_import.ClientExchangeAccountElements] = dataclasses.field(default=None, repr=True)
    extra_accounts: list[account_elements_import.AccountElements] = dataclasses.field(default_factory=list, repr=True)
    execution: execution_details_import.ExecutionDetails = dataclasses.field(default_factory=execution_details_import.ExecutionDetails, repr=False)
    post_actions: post_iteration_actions_details_import.PostIterationActionsDetails = dataclasses.field(default_factory=post_iteration_actions_details_import.PostIterationActionsDetails, repr=False)

    def __post_init__(self):
        if self.metadata and isinstance(self.metadata, dict):
            self.metadata = AutomationMetadata.from_dict(self.metadata)
        if self.execution and isinstance(self.execution, dict):
            self.execution = execution_details_import.ExecutionDetails.from_dict(self.execution)
        if self.reference_exchange_account_elements and isinstance(self.reference_exchange_account_elements, dict):
            self.reference_exchange_account_elements = reference_exchange_account_elements_import.ReferenceExchangeAccountElements.from_dict(self.reference_exchange_account_elements)
        if self.client_exchange_account_elements and isinstance(self.client_exchange_account_elements, dict):
            self.client_exchange_account_elements = client_exchange_account_elements_import.ClientExchangeAccountElements.from_dict(self.client_exchange_account_elements)
        if self.extra_accounts and isinstance(self.extra_accounts[0], dict):
            self.extra_accounts = [
                account_elements_import.AccountElements.from_dict(account)
                for account in self.extra_accounts
            ]
        if self.post_actions and isinstance(self.post_actions, dict):
            self.post_actions = post_iteration_actions_details_import.PostIterationActionsDetails.from_dict(self.post_actions)

    def get_exchange_account_elements(self, as_reference_account: bool) -> typing.Union[
        reference_exchange_account_elements_import.ReferenceExchangeAccountElements, client_exchange_account_elements_import.ClientExchangeAccountElements
    ]:
        return (
            self.reference_exchange_account_elements
            if as_reference_account else self.client_exchange_account_elements
        ) # type: ignore

    def runs_on_reference_exchange_account_first(self) -> bool:
        return False # TODO return True when the automation should run on the reference exchange account first and then copied by the client
