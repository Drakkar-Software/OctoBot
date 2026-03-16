import octobot_commons.dsl_interpreter
import octobot_commons.errors
import octobot_commons.logging
import octobot_trading.errors
import octobot_trading.enums

import octobot_flow.entities
import octobot_flow.enums


def dsl_action_execution(func):
    async def _action_execution_error_handler_wrapper(
        self, action: octobot_flow.entities.DSLScriptActionDetails
    ):
        try:
            call_result: octobot_commons.dsl_interpreter.DSLCallResult = await func(self, action)
            if call_result.succeeded():
                action.complete(result=call_result.result)
            else:
                action.complete(error_status=call_result.error)
        except octobot_trading.errors.DisabledFundsTransferError as err:
            action.complete(error_status=octobot_flow.enums.ActionErrorStatus.DISABLED_FUNDS_TRANSFER_ERROR.value)
        except octobot_trading.errors.MissingMinimalExchangeTradeVolume as err:
            action.complete(error_status=octobot_flow.enums.ActionErrorStatus.INVALID_ORDER.value)
        except (octobot_trading.errors.UnsupportedHedgeContractError, octobot_trading.errors.InvalidPositionSide) as err:
            action.complete(error_status=octobot_flow.enums.ActionErrorStatus.UNSUPPORTED_HEDGE_POSITION.value)
        except octobot_trading.errors.ExchangeAccountSymbolPermissionError as err:
            action.complete(error_status=octobot_flow.enums.ActionErrorStatus.SYMBOL_INCOMPATIBLE_WITH_ACCOUNT.value)
        except octobot_commons.errors.InvalidParameterFormatError as err:
            action.complete(error_status=octobot_flow.enums.ActionErrorStatus.INVALID_SIGNAL_FORMAT.value)
        except octobot_trading.errors.NotSupportedOrderTypeError as err:
            if err.order_type == octobot_trading.enums.TraderOrderType.STOP_LOSS:
                action.complete(error_status=octobot_flow.enums.ActionErrorStatus.UNSUPPORTED_STOP_ORDER.value)
            else:
                action.complete(error_status=octobot_flow.enums.ActionErrorStatus.INVALID_ORDER.value)
        except octobot_trading.errors.BlockchainWalletError as err:
            action.complete(error_status=octobot_flow.enums.ActionErrorStatus.BLOCKCHAIN_WALLET_ERROR.value)
        except Exception as err:
            octobot_commons.logging.get_logger("action_execution").exception(
                err, True, f"Failed to interpret DSL script '{action.get_summary()}' for action: {action.id}: {err}"
            )
            action.complete(error_status=octobot_flow.enums.ActionErrorStatus.INTERNAL_ERROR.value)
    return _action_execution_error_handler_wrapper
