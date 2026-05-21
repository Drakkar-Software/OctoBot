import typing
import dataclasses
import enum
import uuid
import json

import octobot_commons.constants as commons_constants
import octobot_commons.symbols
import octobot_commons.profiles.profile_data as profiles_import
import octobot_commons.dataclasses
import octobot_commons.configuration
import octobot_trading.blockchain_wallets as blockchain_wallets
import octobot_trading.blockchain_wallets.simulator.blockchain_wallet_simulator as blockchain_wallets_simulator
import octobot_trading.exchanges.util.exchange_data as exchange_data_import
import octobot_trading.enums as trading_enums
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
    BLOCKCHAIN_WALLET_INIT = "blockchain_wallet_init"
    WITHDRAW = "withdraw"
    DEPOSIT = "deposit"
    TRANSFER = "transfer"
    LOOP_UNTIL_BLOCKCHAIN_BALANCE = "loop_until_blockchain_balance"
    LOOP_UNTIL_ORDER_CLOSED = "loop_until_order_closed"


CONTENT_KEY = "CONTENT"

# dependency::<action_id>::<k1>::<k2>::... — path into that action's result (dict keys and list indices as digit strings)
DEPENDENCY_SEPARATOR = "::"
DEPENDENCY_IDENTIFIER = "dependency"
PARAM_DEPENDENCY_IDENTIFIER = "param_dependency"
DEPENDENCY_PARAM_PREFIX = f"{DEPENDENCY_IDENTIFIER}{DEPENDENCY_SEPARATOR}"
PARAM_DEPENDENCY_PREFIX = f"{PARAM_DEPENDENCY_IDENTIFIER}{DEPENDENCY_SEPARATOR}"


# Returned by _resolve_param_dependency_string_value when the target field is still a param_dependency string.
_PARAM_DEPENDENCY_RESOLUTION_DEFERRED = object()


@dataclasses.dataclass
class ActionsDAGParserParams(octobot_commons.dataclasses.MinimizableDataclass):
    ACTIONS: list[str] = dataclasses.field(default_factory=list)
    AUTOMATION_ID: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4()))
    EXCHANGE_TO: typing.Optional[str] = None
    API_KEY: typing.Optional[str] = None
    API_SECRET: typing.Optional[str] = None
    SIMULATED_PORTFOLIO: typing.Optional[dict[str, float]] = dataclasses.field(default_factory=dict)
    ORDER_SIDE: typing.Optional[str] = None
    ORDER_SYMBOL: typing.Optional[str] = None
    ORDER_AMOUNT: typing.Optional[float] = None
    ORDER_PRICE: typing.Optional[float] = None
    ORDER_STOP_PRICE: typing.Optional[float] = None
    ORDER_TAG: typing.Optional[str] = None
    ORDER_REDUCE_ONLY: typing.Optional[bool] = None
    ORDER_TYPE: typing.Optional[str] = None
    ORDER_EXTRA_PARAMS: typing.Optional[dict] = None
    ORDER_EXCHANGE_ID: typing.Optional[str] = None
    EXCHANGE_FROM: typing.Optional[str] = None
    MIN_DELAY: typing.Optional[float] = None
    MAX_DELAY: typing.Optional[float] = None
    BLOCKCHAIN_INIT_FILENAME: typing.Optional[str] = None
    BLOCKCHAIN_INIT_PASSWORD: typing.Optional[str] = None
    BLOCKCHAIN_INIT_PORT: typing.Optional[int] = None
    BLOCKCHAIN_INIT_CLOSE_WALLET_ON_EXIT: typing.Optional[bool] = False
    BLOCKCHAIN_FROM: typing.Optional[str] = None
    BLOCKCHAIN_FROM_AMOUNT: typing.Optional[float] = None
    BLOCKCHAIN_FROM_ASSET: typing.Optional[str] = None
    BLOCKCHAIN_FROM_ADDRESS: typing.Optional[str] = None
    BLOCKCHAIN_FROM_MNEMONIC_SEED: typing.Optional[str] = None
    BLOCKCHAIN_FROM_BLOCK_HEIGHT: typing.Union[int, str, None] = None
    BLOCKCHAIN_FROM_SECRET_VIEW_KEY: typing.Optional[str] = None
    BLOCKCHAIN_FROM_SECRET_SPEND_KEY: typing.Optional[str] = None
    BLOCKCHAIN_FROM_PRIVATE_KEY: typing.Optional[str] = None
    BLOCKCHAIN_FROM_FILENAME: typing.Optional[str] = None
    BLOCKCHAIN_FROM_PASSWORD: typing.Optional[str] = None
    BLOCKCHAIN_FROM_PORT: typing.Optional[int] = None
    BLOCKCHAIN_TO: typing.Optional[str] = None
    BLOCKCHAIN_TO_ASSET: typing.Optional[str] = None
    BLOCKCHAIN_TO_AMOUNT: typing.Optional[float] = None
    BLOCKCHAIN_TO_ADDRESS: typing.Optional[str] = None
    BLOCKCHAIN_TO_MNEMONIC_SEED: typing.Optional[str] = None
    BLOCKCHAIN_TO_BLOCK_HEIGHT: typing.Union[int, str, None] = None
    BLOCKCHAIN_TO_SECRET_VIEW_KEY: typing.Optional[str] = None
    BLOCKCHAIN_TO_SECRET_SPEND_KEY: typing.Optional[str] = None
    BLOCKCHAIN_TO_PRIVATE_KEY: typing.Optional[str] = None
    BLOCKCHAIN_BALANCE_ADDRESS: typing.Optional[str] = None
    BLOCKCHAIN_BALANCE_AMOUNT: typing.Optional[str] = None
    BLOCKCHAIN_BALANCE_ASSET: typing.Optional[str] = None
    BLOCKCHAIN_BALANCE: typing.Optional[str] = None
    LOOP_INTERVAL: typing.Optional[float] = None
    LOOP_TIMEOUT: typing.Optional[float] = None
    LOOP_MAX_ATTEMPTS: typing.Optional[int] = None
    CONTENT: typing.Optional[dict] = None

    def __post_init__(self):
        if self.ACTIONS and isinstance(self.ACTIONS, str):
            # action is a string, convert it to a list
            self.ACTIONS = self.ACTIONS.split(",") # pylint: disable=no-member
        if isinstance(self.ORDER_EXTRA_PARAMS, str):
            self.ORDER_EXTRA_PARAMS = json.loads(self.ORDER_EXTRA_PARAMS)
        if isinstance(self.SIMULATED_PORTFOLIO, str):
            self.SIMULATED_PORTFOLIO = json.loads(self.SIMULATED_PORTFOLIO)
        self._resolve_param_dependencies()
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
        self, 
        descriptors_overrides: typing.Optional[dict[str, typing.Any]] = None
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
        blockchain, blockchain_descriptor_specific_config, wallet_descriptor_specific_config = self.get_blockchain_and_specific_configs(
            self.BLOCKCHAIN_FROM, descriptors_overrides
        )
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
    
    def get_blockchain_and_wallet_descriptors_to_wallet_details(
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
    
    def get_blockchain_and_wallet_descriptors_for_balance_check(
        self
    ) -> blockchain_wallets.BlockchainWalletParameters:
        if (
            not self.BLOCKCHAIN_BALANCE or 
            not self.BLOCKCHAIN_BALANCE_ADDRESS or
            not self.BLOCKCHAIN_BALANCE_ASSET
        ):
            raise octobot_flow.errors.InvalidAutomationActionError(
                f"BLOCKCHAIN_BALANCE, BLOCKCHAIN_BALANCE_ADDRESS and BLOCKCHAIN_BALANCE_ASSET must be provided for a blockchain to wallet"
            )
        blockchain, blockchain_descriptor_specific_config, wallet_descriptor_specific_config = self.get_blockchain_and_specific_configs(self.BLOCKCHAIN_BALANCE)
        return blockchain_wallets.BlockchainWalletParameters(
            blockchain_descriptor=blockchain_wallets.BlockchainDescriptor(
                blockchain=blockchain,
                network=self.BLOCKCHAIN_BALANCE,
                native_coin_symbol=self.BLOCKCHAIN_BALANCE_ASSET,
                specific_config=blockchain_descriptor_specific_config,
            ),
            wallet_descriptor=blockchain_wallets.WalletDescriptor(
                address=self.BLOCKCHAIN_BALANCE_ADDRESS,
                specific_config=wallet_descriptor_specific_config,
            )
        )

    def get_blockchain_and_specific_configs(
        self,
        blockchain: str,
        descriptors_overrides: typing.Optional[dict[str, typing.Any]] = None
    ) -> tuple[str, dict, dict]:
        try:
            blockchain_wallet_class = blockchain_wallets.get_blockchain_wallet_class_by_blockchain()[blockchain.lower()]
        except KeyError as err:
            raise octobot_flow.errors.InvalidAutomationActionError(
                f"Invalid blockchain: {blockchain}"
            ) from err
        simulator_config = {
            blockchain_wallets_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: {
                self.BLOCKCHAIN_FROM_ASSET: self.BLOCKCHAIN_FROM_AMOUNT,
            }
        }
        specific_config = self._create_generic_blockchain_wallet_specific_config(blockchain)
        all_config = {**simulator_config, **specific_config}
        if descriptors_overrides:
            all_config.update(descriptors_overrides)
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

    def _resolve_param_dependencies(self) -> None:
        valid_field_names = frozenset(self.get_field_names())
        field_list = dataclasses.fields(self)
        max_rounds = len(field_list) + 1
        for _ in range(max_rounds):
            progressed = False
            for field in field_list:
                value = getattr(self, field.name)
                if isinstance(value, dict):
                    if self._resolve_param_dependencies_in_mapping(
                        value, valid_field_names, field.name
                    ):
                        progressed = True
                    continue
                if not isinstance(value, str) or not value.startswith(PARAM_DEPENDENCY_PREFIX):
                    continue
                resolved_value = _resolve_param_dependency_string_value(
                    self, value, valid_field_names, f"field {field.name!r}"
                )
                if resolved_value is _PARAM_DEPENDENCY_RESOLUTION_DEFERRED:
                    continue
                object.__setattr__(self, field.name, resolved_value)
                progressed = True
            if not progressed:
                break
        for field in field_list:
            value = getattr(self, field.name)
            if isinstance(value, str) and value.startswith(PARAM_DEPENDENCY_PREFIX):
                raise octobot_flow.errors.InvalidAutomationActionError(
                    f"Unresolved param_dependency cycle or chain for field {field.name!r}: {value!r}"
                )
            if isinstance(value, dict) and self._mapping_contains_unresolved_param_dependency(value):
                raise octobot_flow.errors.InvalidAutomationActionError(
                    f"Unresolved param_dependency cycle or chain inside field {field.name!r}"
                )

    def _resolve_param_dependencies_in_mapping(
        self,
        mapping: dict,
        valid_field_names: frozenset[str],
        context_path: str,
    ) -> bool:
        """
        Replace param_dependency::... string values inside a dict (recursively).
        Returns True if at least one value was resolved this pass.
        """
        progressed = False
        for key, entry_value in mapping.items():
            entry_path = f"{context_path}[{key!r}]"
            if isinstance(entry_value, dict):
                if self._resolve_param_dependencies_in_mapping(
                    entry_value, valid_field_names, entry_path
                ):
                    progressed = True
            elif isinstance(entry_value, str) and entry_value.startswith(PARAM_DEPENDENCY_PREFIX):
                resolved_value = _resolve_param_dependency_string_value(
                    self, entry_value, valid_field_names, entry_path
                )
                if resolved_value is _PARAM_DEPENDENCY_RESOLUTION_DEFERRED:
                    continue
                mapping[key] = resolved_value
                progressed = True
        return progressed

    @staticmethod
    def _mapping_contains_unresolved_param_dependency(mapping: dict) -> bool:
        for entry_value in mapping.values():
            if isinstance(entry_value, dict):
                if ActionsDAGParserParams._mapping_contains_unresolved_param_dependency(entry_value):
                    return True
            elif isinstance(entry_value, str) and entry_value.startswith(PARAM_DEPENDENCY_PREFIX):
                return True
        return False

class ActionsDAGParser:
    def __init__(self, params: dict):
        if content := params.get(CONTENT_KEY):
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    raise octobot_flow.errors.InvalidAutomationActionError(
                        f"Invalid json value in {CONTENT_KEY} column: {content}"
                    )
            params = {**params, **content}
        self.params: ActionsDAGParserParams = ActionsDAGParserParams.from_dict(params)
        self.blockchain_param_index = 0

    def parse(self) -> octobot_flow.entities.ActionsDAG:
        init_action = self._create_init_action(
            self.params.AUTOMATION_ID,
            self.params.get_exchange_internal_name(),
            self.params.API_KEY,
            self.params.API_SECRET,
            self.params.SIMULATED_PORTFOLIO,
            self.params.to_dict(include_default_values=False),
        )
        actions_dag = octobot_flow.entities.ActionsDAG([init_action])
        self._parse_generic_actions(actions_dag)
        return actions_dag

    def _parse_generic_actions(self, actions_dag: octobot_flow.entities.ActionsDAG) -> None:
        latest_action = actions_dag.get_executable_actions()[0]
        previous_action_needs_if_error_wallet_cleanup = False
        for index, action_name in enumerate(self.params.ACTIONS):
            new_action = self._create_generic_action(action_name, index + 1)
            if previous_action_needs_if_error_wallet_cleanup and isinstance(
                new_action, octobot_flow.entities.DSLScriptActionDetails
            ):
                self._wrap_dsl_script_with_wallet_cleanup_if_error(new_action)
            new_action.add_dependency(latest_action.id)
            actions_dag.add_action(new_action)
            latest_action = new_action
            previous_action_needs_if_error_wallet_cleanup = (
                action_name == ActionType.BLOCKCHAIN_WALLET_INIT.value
                and self.params.BLOCKCHAIN_INIT_CLOSE_WALLET_ON_EXIT is not True
            )

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
            case ActionType.BLOCKCHAIN_WALLET_INIT.value:
                return self._create_blockchain_wallet_init_action(index)
            case ActionType.LOOP_UNTIL_BLOCKCHAIN_BALANCE.value:
                return self._create_loop_until_blockchain_balance_action(index)
            case ActionType.LOOP_UNTIL_ORDER_CLOSED.value:
                return self._create_loop_until_order_closed_action(index)
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
        if self.params.ORDER_EXTRA_PARAMS:
            for extra_param, value in self.params.ORDER_EXTRA_PARAMS.items():
                order_details[f"{trading_view_signals_trading.TradingViewSignalsTradingMode.PARAM_PREFIX_KEY}{extra_param}"] = value
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

    def _wallet_init_details_for_translate(
        self,
        *,
        close_wallet_override: typing.Optional[bool] = None,
    ) -> dict:
        self._ensure_params(
            ["BLOCKCHAIN_FROM_ASSET", "BLOCKCHAIN_FROM"],
            "blockchain_wallet_init",
        )
        resolved_close = (
            self.params.BLOCKCHAIN_INIT_CLOSE_WALLET_ON_EXIT
            if close_wallet_override is None
            else close_wallet_override
        )
        descriptors_overrides = {
            "filename": self.params.BLOCKCHAIN_INIT_FILENAME,
            "password": self.params.BLOCKCHAIN_INIT_PASSWORD,
            "port": self.params.BLOCKCHAIN_INIT_PORT,
            "close_wallet_on_exit": resolved_close,
        }
        return dataclasses.asdict(
            actions_params.BlockchainWalletInitParams(
                **self.params.get_blockchain_and_wallet_descriptors_from_wallet_details(
                    descriptors_overrides
                )
            )
        )

    def _translate_blockchain_wallet_init_signal(self, details: dict) -> str:
        parsed_signal = {
            trading_view_signals_trading.TradingViewSignalsTradingMode.SIGNAL_KEY:
                trading_view_signals_trading.TradingViewSignalsTradingMode.BLOCKCHAIN_WALLET_INIT_SIGNAL,
            **details,
        }
        dsl_script = tradingview_signal_to_dsl_translator.TradingViewSignalToDSLTranslator.translate_signal(
            parsed_signal
        )
        if dsl_script == tradingview_signal_to_dsl_translator.UNKNOWN_SIGNAL_RESULT:
            raise octobot_flow.errors.InvalidAutomationActionError(
                f"Invalid signal: {trading_view_signals_trading.TradingViewSignalsTradingMode.BLOCKCHAIN_WALLET_INIT_SIGNAL}"
                f"({details})"
            )
        return dsl_script

    def _build_blockchain_wallet_init_dsl(self, *, force_close_wallet_on_exit: bool) -> str:
        # force_close_wallet_on_exit: recovery path uses True so the wallet is closed on error.
        details = self._wallet_init_details_for_translate(
            close_wallet_override=True if force_close_wallet_on_exit else None,
        )
        return self._translate_blockchain_wallet_init_signal(details)

    def _wrap_dsl_script_with_wallet_cleanup_if_error(
        self,
        dsl_action: octobot_flow.entities.DSLScriptActionDetails,
    ) -> None:
        # Step: wrap the primary DSL so a failing step runs a matching init with close_wallet_on_exit=True.
        primary_script = dsl_action.dsl_script
        if not primary_script:
            raise octobot_flow.errors.InvalidAutomationActionError(
                "Cannot wrap empty dsl_script with if_error wallet cleanup"
            )
        recovery_script = self._build_blockchain_wallet_init_dsl(force_close_wallet_on_exit=True)
        dsl_action.dsl_script = (
            f"if_error(value=({primary_script}), on_error={json.dumps(recovery_script)})"
        )

    def _create_blockchain_wallet_init_action(self, index: int) -> octobot_flow.entities.AbstractActionDetails:
        blockchain_wallet_init_details = self._wallet_init_details_for_translate()
        return self.create_dsl_script_from_tv_format_action_details(
            f"action_blockchain_wallet_init_{index}",
            trading_view_signals_trading.TradingViewSignalsTradingMode.BLOCKCHAIN_WALLET_INIT_SIGNAL,
            blockchain_wallet_init_details,
        )
    
    def _create_transfer_action(
        self, index: int
    ) -> octobot_flow.entities.AbstractActionDetails:
        self._ensure_params(
            ["BLOCKCHAIN_FROM_ASSET", "BLOCKCHAIN_FROM_AMOUNT", "BLOCKCHAIN_FROM", "BLOCKCHAIN_TO_ADDRESS"],
            "transfer",
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

    def _get_loop_params(self) -> tuple[typing.Optional[float], typing.Optional[float], int]:
        loop_interval, loop_timeout, loop_max_attempts = (
            self.params.LOOP_INTERVAL, self.params.LOOP_TIMEOUT, self.params.LOOP_MAX_ATTEMPTS
        )
        if not loop_interval:
            raise octobot_flow.errors.InvalidAutomationActionError(
                "LOOP_INTERVAL must be provided for the loop_until action"
            )
        return loop_interval, loop_timeout, loop_max_attempts # type: ignore

    def _create_loop_until_order_closed_action(self, index: int) -> octobot_flow.entities.AbstractActionDetails:
        loop_interval, loop_timeout, loop_max_attempts = self._get_loop_params()
        self._ensure_params(
            ["ORDER_EXCHANGE_ID", "ORDER_SYMBOL"],
            "loop_until_order_closed",
        )
        if not self.params.get_exchange_internal_name():
            raise octobot_flow.errors.InvalidAutomationActionError(
                "EXCHANGE_TO or EXCHANGE_FROM must be provided for the loop_until_order_closed action"
            )
        # force the use of keyword form for the exchange_order_id parameter to resolve the dependency
        fetch_order = f"fetch_order('{self.params.ORDER_SYMBOL}', exchange_order_id='{self.params.ORDER_EXCHANGE_ID}')"
        selector = (
            f"value_if({fetch_order}, "
            f"\"get({commons_constants.LOCAL_VALUE_PLACEHOLDER}, 'status', '{trading_enums.OrderStatus.OPEN.value}') "
            f"!= '{trading_enums.OrderStatus.OPEN.value}'\")"
        )
        dsl_script = (
            f"loop_until({selector}, "
            f"{loop_interval}, timeout={loop_timeout}, max_attempts={loop_max_attempts}, "
            f"return_remaining_time=True)"
        )
        action_id = f"action_loop_until_order_closed_{index}"
        params = {"exchange_order_id": self.params.ORDER_EXCHANGE_ID, "symbol": self.params.ORDER_SYMBOL}
        return self._create_dsl_action_with_dependencies_if_any(action_id, dsl_script, params)

    def _create_loop_until_blockchain_balance_action(self, index: int) -> octobot_flow.entities.AbstractActionDetails:
        loop_interval, loop_timeout, loop_max_attempts = self._get_loop_params()
        amount, asset = self.params.BLOCKCHAIN_BALANCE_AMOUNT, self.params.BLOCKCHAIN_BALANCE_ASSET
        if not amount or not asset:
            raise octobot_flow.errors.InvalidAutomationActionError(
                "BLOCKCHAIN_BALANCE_AMOUNT and BLOCKCHAIN_BALANCE_ASSET must be provided for the wait_for_blockchain_balance action"
            )
        blockchain_params = self.params.get_blockchain_and_wallet_descriptors_for_balance_check()
        wallet_params = dataclasses.asdict(blockchain_params)
        wallet_check = tradingview_signal_to_dsl_translator.TradingViewSignalToDSLTranslator.translate_keyword_and_params(
            "blockchain_wallet_balance",
            wallet_params,
            {"asset": asset},
        )
        dsl_script = (
            f"loop_until(value_if({wallet_check}, ' >= {float(amount)}'), "
            f"{loop_interval}, timeout={loop_timeout}, max_attempts={loop_max_attempts}, "
            f"return_remaining_time=True)"
        )
        action_id = f"action_loop_until_blockchain_balance_{index}"
        return self._create_dsl_action_with_dependencies_if_any(action_id, dsl_script, wallet_params)

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

    def _get_empty_exchange_api_key(self) -> str:
        return octobot_commons.configuration.encrypt("").decode()

    def _create_init_action(
        self,
        automation_id: str,
        exchange_internal_name: typing.Optional[str],
        api_key: typing.Optional[str],
        api_secret: typing.Optional[str],
        simulated_portfolio: typing.Optional[dict[str, float]],
        result: dict,
    ) -> octobot_flow.entities.AbstractActionDetails:
        formatted_simulated_portfolio = {
            asset: {
                commons_constants.PORTFOLIO_TOTAL: value,
                commons_constants.PORTFOLIO_AVAILABLE: value,
            }
            for asset, value in simulated_portfolio.items()
        }
        automation_details = octobot_flow.entities.AutomationDetails(
            metadata=octobot_flow.entities.AutomationMetadata(
                automation_id=automation_id,
            ),
            exchange_account_elements=octobot_flow.entities.ExchangeAccountElements(
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
                # use empty key to simulate the exchange without an account
                api_key=api_key or ("" if simulated_portfolio else self._get_empty_exchange_api_key()),
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
            result=result,
        )

    def _collect_dependency_refs_from_details(
        self, details: dict
    ) -> list[tuple[str, str, tuple[str, ...], str]]:
        """
        Find dependency::... references in string param values.
        Returns (dsl_parameter_name, dependency_action_id, result_path_keys, source_literal).
        """
        refs: list[tuple[str, str, tuple[str, ...], str]] = []
        for key, value in details.items():
            if isinstance(value, dict):
                refs.extend(self._collect_dependency_refs_from_details(value))
            if not isinstance(value, str):
                continue
            parsed = _parse_dependency_param_value(value)
            if not parsed:
                continue
            dep_action_id, result_path = parsed
            dsl_key = (
                trading_view_signals_trading.TradingViewSignalsTradingMode.TRADINGVIEW_TO_DSL_PARAM.get(
                    key, key.lower() if isinstance(key, str) else str(key).lower()
                )
            )
            refs.append((dsl_key, dep_action_id, result_path, value))
        return refs

    def _inject_dependency_placeholders_in_dsl_script(
        self, dsl_script: str, refs: list[tuple[str, str, tuple[str, ...], str]]
    ) -> str:
        """
        Turn dependency:: references in the translated DSL into UNRESOLVED_PARAMETER placeholders
        and use keyword form when the value was emitted as a positional argument.
        """
        result = dsl_script
        placeholder = commons_constants.UNRESOLVED_PARAMETER_PLACEHOLDER
        for dsl_key, _, __, source_literal in refs:
            literal_repr = repr(source_literal)
            kw_form = f"{dsl_key}={literal_repr}"
            kw_placeholder = f"{dsl_key}={placeholder}"
            if kw_form in result:
                result = result.replace(kw_form, kw_placeholder)
            elif literal_repr in result:
                count = result.count(literal_repr)
                if count != 1:
                    raise octobot_flow.errors.InvalidAutomationActionError(
                        f"Ambiguous dependency literal {literal_repr} ({count} occurrences) in DSL: {dsl_script}"
                    )
                result = result.replace(literal_repr, placeholder, 1)
            else:
                raise octobot_flow.errors.InvalidAutomationActionError(
                    f"Dependency value for DSL parameter {dsl_key!r} ({source_literal!r}) not found in script: {dsl_script}"
                )
        return result

    def create_dsl_script_from_tv_format_action_details(
        self, action_id: str, signal: str, details: dict
    ) -> octobot_flow.entities.DSLScriptActionDetails:
        dsl_script = tradingview_signal_to_dsl_translator.TradingViewSignalToDSLTranslator.translate_signal(
            {**{trading_view_signals_trading.TradingViewSignalsTradingMode.SIGNAL_KEY: signal}, **details}
        )
        if dsl_script == tradingview_signal_to_dsl_translator.UNKNOWN_SIGNAL_RESULT:
            raise octobot_flow.errors.InvalidAutomationActionError(
                f"Invalid signal: {signal}({details}) (action {action_id})"
            )
        return self._create_dsl_action_with_dependencies_if_any(action_id, dsl_script, details)

    def _create_dsl_action_with_dependencies_if_any(
        self, action_id:str, dsl_script: str, details: dict
    ) -> octobot_flow.entities.DSLScriptActionDetails:
        dependency_refs = self._collect_dependency_refs_from_details(details)
        if dependency_refs:
            dsl_script = self._inject_dependency_placeholders_in_dsl_script(dsl_script, dependency_refs)
        action = octobot_flow.entities.DSLScriptActionDetails(
            id=action_id,
            dsl_script=dsl_script,
        )
        for dsl_key, dep_action_id, result_path, _ in dependency_refs:
            action.add_dependency(dep_action_id, dsl_key, list(result_path))
        return action

    def create_configured_action_details(
        self, action_id: str,
        action: octobot_flow.enums.ActionType,
        config: dict,
        result: typing.Optional[dict] = None
    ) -> octobot_flow.entities.ConfiguredActionDetails:
        return octobot_flow.entities.ConfiguredActionDetails(
            id=action_id,
            action=action.value,
            config=config,
            result=result,
        )


def _parse_dependency_param_value(
    value: str,
) -> typing.Optional[tuple[str, tuple[str, ...]]]:
    if not isinstance(value, str) or not value.startswith(DEPENDENCY_PARAM_PREFIX):
        return None
    parts = value.split(DEPENDENCY_SEPARATOR)
    if len(parts) < 3 or parts[0] != DEPENDENCY_IDENTIFIER or not parts[1]:
        return None
    path_keys = tuple(parts[2:])
    if not path_keys or any(not segment for segment in path_keys):
        return None
    return parts[1], path_keys


def _canonical_param_dependency_field_name(
    target_name: str,
    valid_field_names: frozenset[str],
) -> typing.Optional[str]:
    """
    Map a param_dependency target token to the canonical ActionsDAGParserParams field name.
    Matching is case-insensitive; returns the dataclass field name (typically UPPER_CASE).
    """
    if target_name in valid_field_names:
        return target_name
    target_lower = target_name.lower()
    for field_name in valid_field_names:
        if field_name.lower() == target_lower:
            return field_name
    return None


def _resolve_param_dependency_string_value(
    params: typing.Any,
    raw_value: str,
    valid_field_names: frozenset[str],
    context_for_errors: str,
) -> typing.Any:
    """
    Resolve a param_dependency::... string against params fields.
    Returns _PARAM_DEPENDENCY_RESOLUTION_DEFERRED if the target is not ready yet (still a dependency string).
    Otherwise returns the resolved value (may be None).
    """
    if not isinstance(raw_value, str) or not raw_value.startswith(PARAM_DEPENDENCY_PREFIX):
        return None
    target_name = raw_value[len(PARAM_DEPENDENCY_PREFIX):]
    if not target_name or DEPENDENCY_SEPARATOR in target_name:
        target_name = None
    if target_name is None:
        raise octobot_flow.errors.InvalidAutomationActionError(
            f"Invalid param_dependency value ({context_for_errors}): {raw_value!r}"
        )
    canonical_name = _canonical_param_dependency_field_name(target_name, valid_field_names)
    if canonical_name is None:
        raise octobot_flow.errors.InvalidAutomationActionError(
            f"param_dependency target {target_name!r} is not a valid "
            f"ActionsDAGParserParams field (referenced from {context_for_errors})"
        )
    resolved_value = getattr(params, canonical_name)
    if isinstance(resolved_value, str) and resolved_value.startswith(PARAM_DEPENDENCY_PREFIX):
        return _PARAM_DEPENDENCY_RESOLUTION_DEFERRED
    return resolved_value
