import octobot_commons.dsl_interpreter
import octobot_commons.errors
import octobot_commons.logging
import octobot_commons.constants
import octobot_trading.errors
import octobot_trading.enums

import octobot_flow.entities
import octobot_flow.enums
import octobot_flow.logic.dsl.action_error_util


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
        except octobot_trading.errors.MissingMinimalExchangeTradeVolume as err:
            octobot_commons.logging.get_logger("action_execution").exception(err, True, f"Missing minimal exchange trade volume error: {err}")
            return _dsl_action_error_call_result(
                action,
                octobot_flow.enums.ActionErrorStatus.INVALID_ORDER.value,
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
        except Exception as err:
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
