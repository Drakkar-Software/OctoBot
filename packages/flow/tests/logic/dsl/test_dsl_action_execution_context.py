import mock
import pytest

import octobot_commons.errors
import octobot_trading.enums
import octobot_trading.errors

import octobot_flow.entities
import octobot_flow.enums
import octobot_flow.logic.dsl.dsl_action_execution_context


_PORTFOLIO_NEGATIVE_VALUE_ERROR_MESSAGE = (
    "Trying to update BTC with -0.00074 but quantity was 0.00068"
)
_DISABLED_FUNDS_TRANSFER_ERROR_MESSAGE = "Funds transfer is disabled"
_MISSING_MINIMAL_EXCHANGE_TRADE_VOLUME_MESSAGE = "Order volume below exchange minimum"
_MISSING_FUNDS_MESSAGE = "Insufficient funds for order"
_AUTHENTICATION_ERROR_MESSAGE = "Invalid API credentials"
_UNSUPPORTED_HEDGE_CONTRACT_MESSAGE = "Hedge mode is not supported for this contract"
_INVALID_POSITION_SIDE_MESSAGE = "Invalid position side for this order"
_EXCHANGE_ACCOUNT_SYMBOL_PERMISSION_MESSAGE = "Symbol is not allowed on this account"
_INVALID_PARAMETER_FORMAT_MESSAGE = "Invalid signal parameter format"
_NOT_SUPPORTED_STOP_LOSS_ORDER_MESSAGE = "STOP_LOSS orders are not supported on binance"
_NOT_SUPPORTED_BUY_MARKET_ORDER_MESSAGE = "BUY_MARKET orders are not supported on binance"
_BLOCKCHAIN_WALLET_ERROR_MESSAGE = "Blockchain wallet connection failed"
_GENERIC_EXCEPTION_MESSAGE = "Unexpected DSL execution failure"
_FAILED_REQUEST_ERROR_MESSAGE = "Exchange API request failed"


class TestDslActionExecutionReraisesRecallablePostponeErrors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "raised_exception,expected_exception_type",
        [
            pytest.param(
                octobot_trading.errors.MissingFunds(_MISSING_FUNDS_MESSAGE),
                octobot_trading.errors.MissingFunds,
                id="missing_funds",
            ),
            pytest.param(
                octobot_trading.errors.FailedRequest(_FAILED_REQUEST_ERROR_MESSAGE),
                octobot_trading.errors.FailedRequest,
                id="failed_request",
            ),
            pytest.param(
                octobot_trading.errors.PortfolioNegativeValueError(
                    _PORTFOLIO_NEGATIVE_VALUE_ERROR_MESSAGE
                ),
                octobot_trading.errors.PortfolioNegativeValueError,
                id="portfolio_negative_value_error",
            ),
            pytest.param(
                octobot_trading.errors.AuthenticationError(_AUTHENTICATION_ERROR_MESSAGE),
                octobot_trading.errors.AuthenticationError,
                id="authentication_error",
            ),
            pytest.param(
                octobot_trading.errors.MissingMinimalExchangeTradeVolume(
                    _MISSING_MINIMAL_EXCHANGE_TRADE_VOLUME_MESSAGE
                ),
                octobot_trading.errors.MissingMinimalExchangeTradeVolume,
                id="missing_minimal_exchange_trade_volume",
            ),
        ],
    )
    async def test_reraises_when_action_is_recallable(
        self,
        raised_exception,
        expected_exception_type,
    ):
        class StubExecutor:
            @octobot_flow.logic.dsl.dsl_action_execution_context.dsl_action_execution
            async def execute_action(self, action, **_kwargs):
                raise raised_exception

        action = octobot_flow.entities.DSLScriptActionDetails(
            id="copy_1",
            dsl_script="copy_exchange_account()",
        )
        stub_executor = StubExecutor()

        with mock.patch(
            "octobot_flow.logic.dsl.dsl_action_execution_context._should_postpone_recallable_trading_error",
            return_value=True,
        ):
            with pytest.raises(expected_exception_type) as raised_error:
                await stub_executor.execute_action(action)

        assert str(raised_error.value) == str(raised_exception)
        assert action.error_status is None
        assert action.error_message is None


class TestDslActionExecutionMapsNonRecallablePostponeErrors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "raised_exception,expected_error_status",
        [
            pytest.param(
                octobot_trading.errors.MissingFunds(_MISSING_FUNDS_MESSAGE),
                octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS,
                id="missing_funds",
            ),
            pytest.param(
                octobot_trading.errors.FailedRequest(_FAILED_REQUEST_ERROR_MESSAGE),
                octobot_flow.enums.ActionErrorStatus.INTERNAL_ERROR,
                id="failed_request",
            ),
            pytest.param(
                octobot_trading.errors.PortfolioNegativeValueError(
                    _PORTFOLIO_NEGATIVE_VALUE_ERROR_MESSAGE
                ),
                octobot_flow.enums.ActionErrorStatus.INTERNAL_ERROR,
                id="portfolio_negative_value_error",
            ),
            pytest.param(
                octobot_trading.errors.AuthenticationError(_AUTHENTICATION_ERROR_MESSAGE),
                octobot_flow.enums.ActionErrorStatus.AUTHENTICATION_ERROR,
                id="authentication_error",
            ),
            pytest.param(
                octobot_trading.errors.MissingMinimalExchangeTradeVolume(
                    _MISSING_MINIMAL_EXCHANGE_TRADE_VOLUME_MESSAGE
                ),
                octobot_flow.enums.ActionErrorStatus.INVALID_ORDER,
                id="missing_minimal_exchange_trade_volume",
            ),
        ],
    )
    async def test_maps_to_action_error_when_not_recallable(
        self,
        raised_exception,
        expected_error_status,
    ):
        class StubExecutor:
            @octobot_flow.logic.dsl.dsl_action_execution_context.dsl_action_execution
            async def execute_action(self, action, **_kwargs):
                raise raised_exception

        action = octobot_flow.entities.DSLScriptActionDetails(
            id="action_1",
            dsl_script="True",
            resolved_dsl_script="True",
        )
        stub_executor = StubExecutor()

        with mock.patch(
            "octobot_flow.logic.dsl.dsl_action_execution_context._should_postpone_recallable_trading_error",
            return_value=False,
        ):
            await stub_executor.execute_action(action)

        assert action.error_status == expected_error_status.value
        assert action.error_message == str(raised_exception)


class TestDslActionExecutionMapsCaughtException:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "raised_exception,expected_error_status",
        [
            pytest.param(
                octobot_trading.errors.DisabledFundsTransferError(_DISABLED_FUNDS_TRANSFER_ERROR_MESSAGE),
                octobot_flow.enums.ActionErrorStatus.DISABLED_FUNDS_TRANSFER_ERROR,
                id="disabled_funds_transfer",
            ),
            pytest.param(
                octobot_trading.errors.MissingMinimalExchangeTradeVolume(
                    _MISSING_MINIMAL_EXCHANGE_TRADE_VOLUME_MESSAGE
                ),
                octobot_flow.enums.ActionErrorStatus.INVALID_ORDER,
                id="missing_minimal_exchange_trade_volume",
            ),
            pytest.param(
                octobot_trading.errors.UnsupportedHedgeContractError(_UNSUPPORTED_HEDGE_CONTRACT_MESSAGE),
                octobot_flow.enums.ActionErrorStatus.UNSUPPORTED_HEDGE_POSITION,
                id="unsupported_hedge_contract",
            ),
            pytest.param(
                octobot_trading.errors.InvalidPositionSide(_INVALID_POSITION_SIDE_MESSAGE),
                octobot_flow.enums.ActionErrorStatus.UNSUPPORTED_HEDGE_POSITION,
                id="invalid_position_side",
            ),
            pytest.param(
                octobot_trading.errors.ExchangeAccountSymbolPermissionError(
                    _EXCHANGE_ACCOUNT_SYMBOL_PERMISSION_MESSAGE
                ),
                octobot_flow.enums.ActionErrorStatus.SYMBOL_INCOMPATIBLE_WITH_ACCOUNT,
                id="exchange_account_symbol_permission",
            ),
            pytest.param(
                octobot_commons.errors.InvalidParameterFormatError(_INVALID_PARAMETER_FORMAT_MESSAGE),
                octobot_flow.enums.ActionErrorStatus.INVALID_SIGNAL_FORMAT,
                id="invalid_parameter_format",
            ),
            pytest.param(
                octobot_trading.errors.NotSupportedOrderTypeError(
                    _NOT_SUPPORTED_STOP_LOSS_ORDER_MESSAGE,
                    octobot_trading.enums.TraderOrderType.STOP_LOSS,
                ),
                octobot_flow.enums.ActionErrorStatus.UNSUPPORTED_STOP_ORDER,
                id="not_supported_order_type_stop_loss",
            ),
            pytest.param(
                octobot_trading.errors.NotSupportedOrderTypeError(
                    _NOT_SUPPORTED_BUY_MARKET_ORDER_MESSAGE,
                    octobot_trading.enums.TraderOrderType.BUY_MARKET,
                ),
                octobot_flow.enums.ActionErrorStatus.INVALID_ORDER,
                id="not_supported_order_type_buy_market",
            ),
            pytest.param(
                octobot_trading.errors.BlockchainWalletError(_BLOCKCHAIN_WALLET_ERROR_MESSAGE),
                octobot_flow.enums.ActionErrorStatus.BLOCKCHAIN_WALLET_ERROR,
                id="blockchain_wallet",
            ),
            pytest.param(
                RuntimeError(_GENERIC_EXCEPTION_MESSAGE),
                octobot_flow.enums.ActionErrorStatus.INTERNAL_ERROR,
                id="generic_exception",
            ),
        ],
    )
    async def test_maps_caught_exception_to_action_error_status(
        self,
        raised_exception,
        expected_error_status,
    ):
        class StubExecutor:
            @octobot_flow.logic.dsl.dsl_action_execution_context.dsl_action_execution
            async def execute_action(self, action, **_kwargs):
                raise raised_exception

        action = octobot_flow.entities.DSLScriptActionDetails(
            id="action_1",
            dsl_script="True",
            resolved_dsl_script="True",
        )
        stub_executor = StubExecutor()

        await stub_executor.execute_action(action)

        assert action.error_status == expected_error_status.value
        assert action.error_message == str(raised_exception)
