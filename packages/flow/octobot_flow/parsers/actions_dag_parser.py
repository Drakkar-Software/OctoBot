import typing
import dataclasses
import enum
import uuid

import octobot_commons.constants as commons_constants
import octobot_commons.symbols
import octobot_commons.profiles.profile_data as profiles_import
import octobot_commons.dataclasses
import octobot_trading.blockchain_wallets as blockchain_wallets
import octobot_trading.blockchain_wallets.simulator.blockchain_wallet_simulator as blockchain_wallets_simulator
import octobot_trading.util.test_tools.exchange_data as exchange_data_import
import octobot_flow.errors
import octobot_flow.entities
import octobot_flow.enums

import tentacles.Trading.Mode.trading_view_signals_trading_mode.actions_params as actions_params
import tentacles.Trading.Mode.trading_view_signals_trading_mode.trading_view_signals_trading as trading_view_signals_trading
import tentacles.Trading.Mode.trading_view_signals_trading_mode.tradingview_signal_to_dsl_translator as tradingview_signal_to_dsl_translator

def key_val_to_dict(key_val: str) -> dict:
    return trading_view_signals_trading.TradingViewSignalsTradingMode.parse_signal_data(key_val, None, None, None, [])


class ActionType(enum.Enum):
    WAIT = "wait"
    TRADE = "trade"
    CANCEL = "cancel"
    WITHDRAW = "withdraw"
    DEPOSIT = "deposit"
    TRANSFER = "transfer"


@dataclasses.dataclass
class ActionsDAGParserParams(octobot_commons.dataclasses.FlexibleDataclass):
    ACTIONS: list[str] = dataclasses.field(default_factory=list)
    AUTOMATION_ID: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4()))
    EXCHANGE_TO: typing.Optional[str] = None
    API_KEY: typing.Optional[str] = None
    API_SECRET: typing.Optional[str] = None
    SIMULATED_PORTFOLIO: typing.Optional[dict[str, float]] = None
    ORDER_SIDE: typing.Optional[str] = None
    ORDER_SYMBOL: typing.Optional[str] = None
    ORDER_AMOUNT: typing.Optional[float] = None
    ORDER_PRICE: typing.Optional[float] = None
    ORDER_STOP_PRICE: typing.Optional[float] = None
    ORDER_TAG: typing.Optional[str] = None
    ORDER_REDUCE_ONLY: typing.Optional[bool] = None
    ORDER_TYPE: typing.Optional[str] = None
    EXCHANGE_FROM: typing.Optional[str] = None
    MIN_DELAY: typing.Optional[float] = None
    MAX_DELAY: typing.Optional[float] = None
    BLOCKCHAIN_FROM: typing.Optional[str] = None
    BLOCKCHAIN_FROM_AMOUNT: typing.Optional[float] = None
    BLOCKCHAIN_FROM_ASSET: typing.Optional[str] = None
    BLOCKCHAIN_FROM_ADDRESS: typing.Optional[str] = None
    BLOCKCHAIN_FROM_MNEMONIC_SEED: typing.Optional[str] = None
    BLOCKCHAIN_FROM_BLOCK_HEIGHT: typing.Optional[int] = None
    BLOCKCHAIN_FROM_SECRET_VIEW_KEY: typing.Optional[str] = None
    BLOCKCHAIN_FROM_SECRET_SPEND_KEY: typing.Optional[str] = None
    BLOCKCHAIN_FROM_PRIVATE_KEY: typing.Optional[str] = None
    BLOCKCHAIN_TO: typing.Optional[str] = None
    BLOCKCHAIN_TO_ASSET: typing.Optional[str] = None
    BLOCKCHAIN_TO_AMOUNT: typing.Optional[float] = None
    BLOCKCHAIN_TO_ADDRESS: typing.Optional[str] = None
    BLOCKCHAIN_TO_MNEMONIC_SEED: typing.Optional[str] = None
    BLOCKCHAIN_TO_BLOCK_HEIGHT: typing.Optional[int] = None
    BLOCKCHAIN_TO_SECRET_VIEW_KEY: typing.Optional[str] = None
    BLOCKCHAIN_TO_SECRET_SPEND_KEY: typing.Optional[str] = None
    BLOCKCHAIN_TO_PRIVATE_KEY: typing.Optional[str] = None

    def __post_init__(self):
        if self.ACTIONS and isinstance(self.ACTIONS, str):
            # action is a string, convert it to a list
            self.ACTIONS = self.ACTIONS.split(",")
        self.validate()

    def validate(self):
        if self.EXCHANGE_TO and self.EXCHANGE_FROM:
            if self.EXCHANGE_TO != self.EXCHANGE_FROM:
                raise octobot_flow.errors.InvalidAutomationActionError("EXCHANGE_TO and EXCHANGE_FROM must be the same")

    def get_reference_market(self) -> typing.Optional[str]:
        if self.ORDER_SYMBOL:
            parsed_symbol = octobot_commons.symbols.parse_symbol(self.ORDER_SYMBOL)
            return parsed_symbol.quote
        return None

    def has_next_schedule(self) -> bool:
        return self.MIN_DELAY is not None or self.MAX_DELAY is not None

    def _get_next_schedule_delay(self) -> tuple[float, float]:
        if self.MIN_DELAY is None and self.MAX_DELAY is None:
            return 0, 0
        if self.MIN_DELAY is not None and self.MAX_DELAY is None:
            return self.MIN_DELAY, self.MIN_DELAY # type: ignore
        if self.MIN_DELAY is None and self.MAX_DELAY is not None:
            return self.MAX_DELAY, self.MAX_DELAY # type: ignore
        return self.MIN_DELAY, self.MAX_DELAY # type: ignore

    def get_exchange_internal_name(self) -> typing.Optional[str]:
        if self.EXCHANGE_TO or self.EXCHANGE_FROM:
            return (self.EXCHANGE_TO or self.EXCHANGE_FROM).lower() # type: ignore
        return None

    def get_blockchain_and_wallet_descriptors_from_wallet_details(
        self
    ) -> dict[str, typing.Any]:
        if (
            not self.BLOCKCHAIN_FROM or
            not self.BLOCKCHAIN_FROM_ASSET or
            not self.BLOCKCHAIN_FROM_AMOUNT
        ):
            raise octobot_flow.errors.InvalidAutomationActionError(
                f"BLOCKCHAIN_FROM, BLOCKCHAIN_FROM_ASSET, BLOCKCHAIN_FROM_ADDRESS and BLOCKCHAIN_FROM_AMOUNT "
                f"must be provided for a blockchain from wallet"
            )
        if not (
            # sending details
            not self.BLOCKCHAIN_FROM_PRIVATE_KEY 
            or not self.BLOCKCHAIN_FROM_MNEMONIC_SEED
            or not (
                self.BLOCKCHAIN_FROM_SECRET_VIEW_KEY
                and self.BLOCKCHAIN_FROM_SECRET_SPEND_KEY
            )
        ):
            raise octobot_flow.errors.InvalidAutomationActionError(
                f"BLOCKCHAIN_FROM_PRIVATE_KEY, BLOCKCHAIN_FROM_MNEMONIC_SEED, BLOCKCHAIN_FROM_SECRET_VIEW_KEY "
                f"or BLOCKCHAIN_FROM_SECRET_SPEND_KEY must be provided for a blockchain from wallet"
            )
        blockchain, blockchain_descriptor_specific_config, wallet_descriptor_specific_config = self.get_blockchain_and_specific_configs(self.BLOCKCHAIN_FROM)
        return {
            "blockchain_descriptor": blockchain_wallets.BlockchainDescriptor(
                blockchain=blockchain,
                network=self.BLOCKCHAIN_FROM,
                native_coin_symbol=self.BLOCKCHAIN_FROM_ASSET,
                specific_config=blockchain_descriptor_specific_config,
            ),
            "wallet_descriptor": blockchain_wallets.WalletDescriptor(
                address=self.BLOCKCHAIN_FROM_ADDRESS,
                private_key=self.BLOCKCHAIN_FROM_PRIVATE_KEY,
                mnemonic_seed=self.BLOCKCHAIN_FROM_MNEMONIC_SEED,
                specific_config=wallet_descriptor_specific_config,
            )
        }
    
    def get_blockchain_to_wallet_details(
        self
    ) -> blockchain_wallets.BlockchainWalletParameters:
        if (
            not self.BLOCKCHAIN_TO or 
            not self.BLOCKCHAIN_TO_ADDRESS
        ):
            raise octobot_flow.errors.InvalidAutomationActionError(
                f"BLOCKCHAIN_TO, BLOCKCHAIN_TO_ADDRESS and BLOCKCHAIN_TO_ASSET must be provided for a blockchain to wallet"
            )
        if not (
            self.BLOCKCHAIN_TO_ADDRESS
            and not self.BLOCKCHAIN_TO_PRIVATE_KEY 
            and not self.BLOCKCHAIN_TO_MNEMONIC_SEED
            and not self.BLOCKCHAIN_TO_SECRET_VIEW_KEY
        ):
            raise octobot_flow.errors.InvalidAutomationActionError(
                f"BLOCKCHAIN_TO_ADDRESS, BLOCKCHAIN_TO_PRIVATE_KEY, BLOCKCHAIN_TO_MNEMONIC_SEED "
                f"or BLOCKCHAIN_TO_SECRET_VIEW_KEY must be provided for a blockchain to wallet"
            )
        blockchain, blockchain_descriptor_specific_config, wallet_descriptor_specific_config = self.get_blockchain_and_specific_configs(self.BLOCKCHAIN_TO)
        return blockchain_wallets.BlockchainWalletParameters(
            blockchain_descriptor=blockchain_wallets.BlockchainDescriptor(
                blockchain=blockchain,
                network=self.BLOCKCHAIN_TO,
                native_coin_symbol=self.BLOCKCHAIN_TO_ASSET,
                specific_config=blockchain_descriptor_specific_config,
            ),
            wallet_descriptor=blockchain_wallets.WalletDescriptor(
                address=self.BLOCKCHAIN_TO_ADDRESS,
                specific_config=wallet_descriptor_specific_config,
            )
        )

    def get_blockchain_and_specific_configs(
        self, blockchain: str
    ) -> tuple[str, dict, dict]:
        blockchain_wallet_class = blockchain_wallets.get_blockchain_wallet_class_by_blockchain()[blockchain.lower()]
        simulator_config = {
            blockchain_wallets_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: {
                self.BLOCKCHAIN_FROM_ASSET: self.BLOCKCHAIN_FROM_AMOUNT,
            }
        }
        specific_config = self._create_generic_blockchain_wallet_specific_config(blockchain)
        all_config = {**simulator_config, **specific_config}
        return (
            blockchain_wallet_class.BLOCKCHAIN, 
            blockchain_wallet_class.create_blockchain_descriptor_specific_config(**all_config), 
            blockchain_wallet_class.create_wallet_descriptor_specific_config(**all_config),
        )

    def _create_generic_blockchain_wallet_specific_config(self, blockchain: str) -> dict:
        is_blockchain_from = blockchain == self.BLOCKCHAIN_FROM
        prefix = "BLOCKCHAIN_FROM_" if is_blockchain_from else "BLOCKCHAIN_TO_"
        return {
            key.replace(prefix, "").lower(): value
            for key, value in dataclasses.asdict(self).items()
            if key.startswith(prefix)
        }

class ActionsDAGParser:
    def __init__(self, params: dict):
        self.params: ActionsDAGParserParams = ActionsDAGParserParams.from_dict(params)
        self.blockchain_param_index = 0

    def parse(self) -> octobot_flow.entities.ActionsDAG:
        init_action = self._create_init_action(
            self.params.AUTOMATION_ID,
            self.params.get_exchange_internal_name(),
            self.params.API_KEY,
            self.params.API_SECRET,
            self.params.SIMULATED_PORTFOLIO,
        )
        actions_dag = octobot_flow.entities.ActionsDAG([init_action])
        self._parse_generic_actions(actions_dag)
        return actions_dag

    def _parse_generic_actions(self, actions_dag: octobot_flow.entities.ActionsDAG) -> None:
        latest_action = actions_dag.get_executable_actions()[0]
        for index, action in enumerate(self.params.ACTIONS):
            new_action = self._create_generic_action(action, index + 1)
            new_action.add_dependency(latest_action.id)
            actions_dag.add_action(new_action)
            latest_action = new_action

    def _create_generic_action(
        self, action: str, index: int
    ) -> octobot_flow.entities.AbstractActionDetails:
        match action:
            case ActionType.TRADE.value:
                return self._create_order_action(index)
            case ActionType.CANCEL.value:
                return self._create_cancel_action(index)
            case ActionType.WITHDRAW.value:
                return self._create_withdraw_action(index)
            case ActionType.DEPOSIT.value:
                return self._create_deposit_action(index)
            case ActionType.TRANSFER.value:
                return self._create_transfer_action(index)
            case ActionType.WAIT.value:
                return self._create_wait_action(index)
            case _:
                raise ValueError(
                    f"Unknown action: {action}"
                )
    
    def _create_order_action(self, index: int) -> octobot_flow.entities.AbstractActionDetails:
        self._ensure_params(
            ["ORDER_SYMBOL", "ORDER_AMOUNT", "ORDER_TYPE"],
            "trade",
        )
        parsed_symbol = octobot_commons.symbols.parse_symbol(self.params.ORDER_SYMBOL)
        if self.params.ORDER_SIDE:
            signal = self.params.ORDER_SIDE.lower()
        elif parsed_symbol.base == self.params.BLOCKCHAIN_FROM_ASSET and parsed_symbol.quote == self.params.BLOCKCHAIN_TO_ASSET: # type: ignore
            # sell the first blockchain asset to get the second one
            signal = trading_view_signals_trading.TradingViewSignalsTradingMode.SELL_SIGNAL
        elif parsed_symbol.base == self.params.BLOCKCHAIN_TO_ASSET and parsed_symbol.quote == self.params.BLOCKCHAIN_FROM_ASSET: # type: ignore
            # buy the second blockchain asset to get the first one
            signal = trading_view_signals_trading.TradingViewSignalsTradingMode.BUY_SIGNAL
        else:
            raise octobot_flow.errors.InvalidAutomationActionError(
                f"Invalid order symbol: {self.params.ORDER_SYMBOL}: symbol must contain the 2 "
                f"blockchain assets to determine the side of the order"
            )
        order_details = {
            trading_view_signals_trading.TradingViewSignalsTradingMode.EXCHANGE_KEY: self.params.get_exchange_internal_name(),
            trading_view_signals_trading.TradingViewSignalsTradingMode.SYMBOL_KEY: self.params.ORDER_SYMBOL,
            trading_view_signals_trading.TradingViewSignalsTradingMode.VOLUME_KEY: self.params.ORDER_AMOUNT,
            trading_view_signals_trading.TradingViewSignalsTradingMode.ORDER_TYPE_SIGNAL: self.params.ORDER_TYPE,
        }
        if self.params.ORDER_PRICE:
            order_details[trading_view_signals_trading.TradingViewSignalsTradingMode.PRICE_KEY] = self.params.ORDER_PRICE
        if self.params.ORDER_STOP_PRICE:
            order_details[trading_view_signals_trading.TradingViewSignalsTradingMode.STOP_PRICE_KEY] = self.params.ORDER_STOP_PRICE
        if self.params.ORDER_TAG:
            order_details[trading_view_signals_trading.TradingViewSignalsTradingMode.TAG_KEY] = self.params.ORDER_TAG
        if self.params.ORDER_REDUCE_ONLY:
            order_details[trading_view_signals_trading.TradingViewSignalsTradingMode.REDUCE_ONLY_KEY] = self.params.ORDER_REDUCE_ONLY
        return self.create_dsl_script_from_tv_format_action_details(
            f"action_trade_{index}", signal, order_details,
        )
    
    def _create_cancel_action(self, index: int) -> octobot_flow.entities.AbstractActionDetails:
        self._ensure_params(
            ["ORDER_SYMBOL"],
            "cancel",
        )
        cancel_details = {
            trading_view_signals_trading.TradingViewSignalsTradingMode.SYMBOL_KEY: self.params.ORDER_SYMBOL,
        }
        if self.params.ORDER_SIDE:
            cancel_details[trading_view_signals_trading.TradingViewSignalsTradingMode.SIDE_PARAM_KEY] = self.params.ORDER_SIDE.lower()
        if self.params.ORDER_TAG:
            cancel_details[trading_view_signals_trading.TradingViewSignalsTradingMode.TAG_KEY] = self.params.ORDER_TAG
        return self.create_dsl_script_from_tv_format_action_details(
            f"action_cancel_{index}",
            trading_view_signals_trading.TradingViewSignalsTradingMode.CANCEL_SIGNAL,
            cancel_details,
        )
    
    def _create_withdraw_action(
        self, index: int
    ) -> octobot_flow.entities.AbstractActionDetails:
        self._ensure_params(
            ["BLOCKCHAIN_TO_ASSET", "BLOCKCHAIN_TO", "BLOCKCHAIN_TO_ADDRESS"],
            "withdraw",
        )
        withdraw_details = actions_params.WithdrawFundsParams(
            asset=self.params.BLOCKCHAIN_TO_ASSET,
            network=self.params.BLOCKCHAIN_TO,
            address=self.params.BLOCKCHAIN_TO_ADDRESS,
        )
        if self.params.BLOCKCHAIN_TO_AMOUNT:
            withdraw_details.amount = self.params.BLOCKCHAIN_TO_AMOUNT
        return self.create_dsl_script_from_tv_format_action_details(
            f"action_withdraw_{index}",
            trading_view_signals_trading.TradingViewSignalsTradingMode.WITHDRAW_FUNDS_SIGNAL,
            dataclasses.asdict(withdraw_details),
        )
    
    def _create_deposit_action(
        self, index: int
    ) -> octobot_flow.entities.AbstractActionDetails:
        self._ensure_params(
            ["BLOCKCHAIN_FROM_ASSET", "BLOCKCHAIN_FROM_AMOUNT", "BLOCKCHAIN_FROM", "EXCHANGE_TO"],
            "deposit",
        )
        deposit_details = actions_params.TransferFundsParams(
            asset=self.params.BLOCKCHAIN_FROM_ASSET,
            amount=self.params.BLOCKCHAIN_FROM_AMOUNT,
            address=None,
            destination_exchange=self.params.EXCHANGE_TO,
            **self.params.get_blockchain_and_wallet_descriptors_from_wallet_details(),
        )
        return self.create_dsl_script_from_tv_format_action_details(
            f"action_deposit_{index}",
            trading_view_signals_trading.TradingViewSignalsTradingMode.TRANSFER_FUNDS_SIGNAL,
            dataclasses.asdict(deposit_details),
        )
    
    def _create_transfer_action(
        self, index: int
    ) -> octobot_flow.entities.AbstractActionDetails:
        self._ensure_params(
            ["BLOCKCHAIN_FROM_ASSET", "BLOCKCHAIN_FROM_AMOUNT", "BLOCKCHAIN_FROM", "BLOCKCHAIN_TO_ADDRESS"],
            "transfer",
        )
        if self.params.BLOCKCHAIN_TO != self.params.BLOCKCHAIN_FROM:
            raise octobot_flow.errors.InvalidAutomationActionError(
                f"BLOCKCHAIN_TO and BLOCKCHAIN_FROM must be the same for a transfer action"
            )
        transfer_details = actions_params.TransferFundsParams(
            asset=self.params.BLOCKCHAIN_FROM_ASSET,
            amount=self.params.BLOCKCHAIN_FROM_AMOUNT,
            address=self.params.BLOCKCHAIN_TO_ADDRESS,
            **self.params.get_blockchain_and_wallet_descriptors_from_wallet_details(),
        )
        return self.create_dsl_script_from_tv_format_action_details(
            f"action_transfer_{index}",
            trading_view_signals_trading.TradingViewSignalsTradingMode.TRANSFER_FUNDS_SIGNAL,
            dataclasses.asdict(transfer_details),
        )

    def _create_wait_action(self, index: int) -> octobot_flow.entities.AbstractActionDetails:
        if not self.params.has_next_schedule():
            raise octobot_flow.errors.InvalidAutomationActionError(
                f"{ActionType.WAIT.value} action requires at least a MIN_DELAY"
            )
        min_delay, max_delay = self.params._get_next_schedule_delay()
        max_delay_str = f", {max_delay}" if max_delay and max_delay != min_delay else ""
        dsl_script = f"wait({min_delay}{max_delay_str}, return_remaining_time=True)"
        return octobot_flow.entities.DSLScriptActionDetails(
            id=f"action_wait_{index}",
            dsl_script=dsl_script,
        )

    def _ensure_params(self, keys: list[str], action: str) -> None:
        missing_keys = []
        for key in keys:
            if not getattr(self.params, key):
                missing_keys.append(key)
        if missing_keys:
            raise octobot_flow.errors.InvalidAutomationActionError(
                f"Missing keys: {', '.join(missing_keys)} (required: {', '.join(keys)}) "
                f"for a {action} action"
            )
    
    def _create_init_action(
        self,
        automation_id: str,
        exchange_internal_name: typing.Optional[str],
        api_key: typing.Optional[str],
        api_secret: typing.Optional[str],
        simulated_portfolio: typing.Optional[dict[str, float]],
    ) -> octobot_flow.entities.AbstractActionDetails:
        formatted_simulated_portfolio = {
            asset: {
                commons_constants.PORTFOLIO_TOTAL: value,
                commons_constants.PORTFOLIO_AVAILABLE: value,
            }
            for asset, value in simulated_portfolio.items()
        } if simulated_portfolio else None
        must_wait = bool(self.params.ACTIONS and self.params.ACTIONS[0] == ActionType.WAIT.value)
        automation_details = octobot_flow.entities.AutomationDetails(
            metadata=octobot_flow.entities.AutomationMetadata(
                automation_id=automation_id,
            ),
            client_exchange_account_elements=octobot_flow.entities.ClientExchangeAccountElements(
                portfolio=exchange_data_import.PortfolioDetails(
                    content=formatted_simulated_portfolio,
                )
            ),
        )
        exchange_account_details = octobot_flow.entities.ExchangeAccountDetails(
            exchange_details=profiles_import.ExchangeData(
                internal_name=exchange_internal_name,
            ),
            auth_details=exchange_data_import.ExchangeAuthDetails(
                api_key=api_key or "",
                api_secret=api_secret or "",
            ),
        ) if exchange_internal_name else None
        automation_state = octobot_flow.entities.AutomationState(
            automation=automation_details,
            exchange_account_details=exchange_account_details,
        )
        return self.create_configured_action_details(
            "action_init",
            octobot_flow.enums.ActionType.APPLY_CONFIGURATION,
            automation_state.to_dict(include_default_values=False),
        )

    def create_dsl_script_from_tv_format_action_details(
        self, action_id: str, signal: str, details: dict
    ) -> octobot_flow.entities.DSLScriptActionDetails:
        dsl_script = tradingview_signal_to_dsl_translator.TradingViewSignalToDSLTranslator.translate_signal(
            {**{trading_view_signals_trading.TradingViewSignalsTradingMode.SIGNAL_KEY: signal}, **details}
        )
        return octobot_flow.entities.DSLScriptActionDetails(
            id=action_id,
            dsl_script=dsl_script,
        )

    def create_configured_action_details(
        self, action_id: str, action: octobot_flow.enums.ActionType, config: dict
    ) -> octobot_flow.entities.ConfiguredActionDetails:
        return octobot_flow.entities.ConfiguredActionDetails(
            id=action_id,
            action=action.value,
            config=config,
        )
