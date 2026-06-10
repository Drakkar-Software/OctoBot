#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.

import octobot_commons.dsl_interpreter as dsl_interpreter_import
import octobot_commons.dsl_interpreter.operator as dsl_interpreter_operator
import octobot_commons.errors as commons_errors
import octobot_commons.logging as common_logging
import octobot_commons.profiles.profile_data as profile_data_import

import octobot_flow.entities
import octobot_flow.errors
import octobot_flow.logic.dsl.dsl_executor as dsl_executor_module


def are_all_actions_process_bound_only(
    profile_data: profile_data_import.ProfileData,
    actions: list[octobot_flow.entities.AbstractActionDetails],
) -> bool:
    """
    True when every action is a DSL script whose top-level operator is process-bound
    (e.g. run_octobot_process). Non-DSL actions and empty lists are not considered eligible to skip
    exchange/copy-trading dependency fetches.
    """
    if not actions:
        return False
    dsl_executor_instance = dsl_executor_module.DSLExecutor(
        profile_data, None, None
    )
    for action in actions:
        if isinstance(action, octobot_flow.entities.ConfiguredActionDetails):
            return False
        if not isinstance(action, octobot_flow.entities.DSLScriptActionDetails):
            return False
        try:
            dsl_executor_instance._interpreter.prepare(action.resolved_dsl_script or action.dsl_script)
        except commons_errors.DSLInterpreterError as err:
            common_logging.get_logger(__name__).info(
                "Process-bound check: DSL script skipped for action %s (%s): %s",
                action.id,
                action.dsl_script,
                err,
            )
            continue
        top_operator = dsl_executor_instance.get_top_operator()
        if not isinstance(top_operator, dsl_interpreter_operator.Operator):
            return False
        if not dsl_interpreter_import.is_process_bound(top_operator):
            return False
    return True
