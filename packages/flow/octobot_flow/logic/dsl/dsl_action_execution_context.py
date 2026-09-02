import octobot_commons.dsl_interpreter
import octobot_commons.errors
import octobot_commons.logging
import octobot_trading.errors
import octobot_trading.enums

import octobot_copy.errors as copy_errors

import octobot_flow.entities
import octobot_flow.enums
import octobot_flow.logic.dsl.action_error_util
import octobot_flow.logic.dsl.dsl_actions_util as dsl_actions_util_module
import octobot_flow.logic.dsl.dsl_executor as dsl_executor_module


POSTPONE_ON_RECALLABLE_TRADING_ERRORS: tuple[type[Exception], ...] = (
    octobot_trading.errors.MissingFunds,
    octobot_trading.errors.FailedRequest,
    octobot_trading.errors.PortfolioNegativeValueError,
    octobot_trading.errors.AuthenticationError,
    octobot_trading.errors.MissingMinimalExchangeTradeVolume,
)


def _dsl_action_error_call_result(
    action: octobot_flow.entities.DSLScriptActionDetails,
    error_status: str,
    error_message: str,
) -> octobot_commons.dsl_interpreter.DSLCallResult:
    action.complete(error_status=error_status, error_message=error_message)
    return octobot_flow.logic.dsl.action_error_util.build_dsl_call_result(
        action.get_resolved_dsl_script(),
        error_status,
        error_message,
    )


def _should_postpone_recallable_trading_error(
    executor: object,
    action: octobot_flow.entities.DSLScriptActionDetails,
) -> bool:

    if not isinstance(executor, dsl_executor_module.DSLExecutor):
        return False
    return dsl_actions_util_module.is_recallable_dsl_action(executor, action)


def _map_non_recallable_postpone_trading_error(
    action: octobot_flow.entities.DSLScriptActionDetails,
    err: Exception,
) -> octobot_commons.dsl_interpreter.DSLCallResult:
    if isinstance(err, octobot_trading.errors.MissingMinimalExchangeTradeVolume):
        octobot_commons.logging.get_logger("action_execution").exception(
            err, True, f"Missing minimal exchange trade volume error: {err}"
        )
        return _dsl_action_error_call_result(
            action,
            octobot_flow.enums.ActionErrorStatus.INVALID_ORDER.value,
            str(err),
        )
    if isinstance(err, octobot_trading.errors.AuthenticationError):
        return _dsl_action_error_call_result(
            action,
            octobot_flow.enums.ActionErrorStatus.AUTHENTICATION_ERROR.value,
            str(err),
        )
    if isinstance(err, octobot_trading.errors.MissingFunds):
        return _dsl_action_error_call_result(
            action,
            octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value,
            str(err),
        )
    return _dsl_action_error_call_result(
        action,
        octobot_flow.enums.ActionErrorStatus.INTERNAL_ERROR.value,
        str(err),
    )


def dsl_action_execution(func):
    async def _action_execution_error_handler_wrapper(
        self, action: octobot_flow.entities.DSLScriptActionDetails, **kwargs
    ):
        """
        Handle the error of the DSL script execution.
        action.result should only be a value of octobot_flow.enums.ActionErrorStatus.
        """
        try:
            call_result: octobot_commons.dsl_interpreter.DSLCallResult = await func(
                self, action, **kwargs
            )
            if call_result.succeeded():
                action.complete(result=call_result.result)
            else:
                action.complete(
                    error_status=call_result.error,
                    error_message=call_result.error_message,
                )
            return call_result
        except octobot_trading.errors.DisabledFundsTransferError as err:
            return _dsl_action_error_call_result(
                action,
                octobot_flow.enums.ActionErrorStatus.DISABLED_FUNDS_TRANSFER_ERROR.value,
                str(err),
            )
        except (octobot_trading.errors.UnsupportedHedgeContractError, octobot_trading.errors.InvalidPositionSide) as err:
            return _dsl_action_error_call_result(
                action,
                octobot_flow.enums.ActionErrorStatus.UNSUPPORTED_HEDGE_POSITION.value,
                str(err),
            )
        except octobot_trading.errors.ExchangeAccountSymbolPermissionError as err:
            return _dsl_action_error_call_result(
                action,
                octobot_flow.enums.ActionErrorStatus.SYMBOL_INCOMPATIBLE_WITH_ACCOUNT.value,
                str(err),
            )
        except octobot_commons.errors.InvalidParameterFormatError as err:
            return _dsl_action_error_call_result(
                action,
                octobot_flow.enums.ActionErrorStatus.INVALID_SIGNAL_FORMAT.value,
                str(err),
            )
        except octobot_trading.errors.NotSupportedOrderTypeError as err:
            error_status_value = (
                octobot_flow.enums.ActionErrorStatus.UNSUPPORTED_STOP_ORDER.value
                if err.order_type == octobot_trading.enums.TraderOrderType.STOP_LOSS
                else octobot_flow.enums.ActionErrorStatus.INVALID_ORDER.value
            )
            return _dsl_action_error_call_result(action, error_status_value, str(err))
        except octobot_trading.errors.BlockchainWalletError as err:
            octobot_commons.logging.get_logger("action_execution").exception(err, True, f"Blockchain wallet error: {err}")
            return _dsl_action_error_call_result(
                action,
                octobot_flow.enums.ActionErrorStatus.BLOCKCHAIN_WALLET_ERROR.value,
                str(err),
            )
        except POSTPONE_ON_RECALLABLE_TRADING_ERRORS as err:
            if _should_postpone_recallable_trading_error(self, action):
                raise
            return _map_non_recallable_postpone_trading_error(action, err)
        except octobot_trading.errors.OrderDescriptionNotFoundError as err:
            return _dsl_action_error_call_result(
                action,
                octobot_flow.enums.ActionErrorStatus.ORDER_NOT_FOUND.value,
                str(err),
            )
        except copy_errors.OutdatedReferenceAccountError:
            raise
        except Exception as err:
            # swallowed errors: warning: will stop the workflow
            octobot_commons.logging.get_logger("action_execution").exception(
                err,
                True,
                f"Failed to interpret DSL script '{action.get_summary()}' "
                f"for action: {action.id}: {err}"
            )
            return _dsl_action_error_call_result(
                action,
                octobot_flow.enums.ActionErrorStatus.INTERNAL_ERROR.value,
                str(err),
            )
    return _action_execution_error_handler_wrapper
