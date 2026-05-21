import typing

import octobot_commons.dsl_interpreter
import octobot_commons.errors

import octobot_flow.enums


ACTION_ERROR_STATUS_VALUES: frozenset[str] = frozenset(
    status.value
    for status in octobot_flow.enums.ActionErrorStatus
    if status.value is not None
)


def default_message_for_status(status: str) -> str:
    return status.replace("_", " ").capitalize()


def _join_error_statement_args(args: tuple[typing.Any, ...]) -> str:
    return ", ".join(str(arg) for arg in args)


def resolve_error_statement(
    err: octobot_commons.errors.ErrorStatementEncountered,
) -> tuple[str, str]:
    if not err.args:
        return (
            octobot_flow.enums.ActionErrorStatus.DSL_EXECUTION_ERROR.value,
            str(err),
        )
    first_argument = err.args[0]
    if isinstance(first_argument, str) and first_argument in ACTION_ERROR_STATUS_VALUES:
        error_status = first_argument
        if len(err.args) > 1:
            error_message = _join_error_statement_args(err.args[1:])
        else:
            error_message = default_message_for_status(error_status)
        return error_status, error_message
    return (
        octobot_flow.enums.ActionErrorStatus.DSL_EXECUTION_ERROR.value,
        _join_error_statement_args(err.args),
    )


def build_dsl_call_result(
    statement: str,
    error_status: str,
    error_message: str,
) -> octobot_commons.dsl_interpreter.DSLCallResult:
    return octobot_commons.dsl_interpreter.DSLCallResult(
        statement=statement,
        error=error_status,
        error_message=error_message,
    )
