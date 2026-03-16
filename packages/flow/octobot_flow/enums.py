import enum


class LastTriggerReason(enum.Enum):
    SCHEDULED = "scheduled"
    CUSTOM_ACTION = "custom_action"
    SIGNAL = "signal"
    CONFIGURATION_UPDATE = "configuration_update"
    UNDEFINED = None


class DegradedStateReasons(enum.Enum):
    INVALID_EXCHANGE_CREDENTIALS = "invalid_exchange_credentials"
    MISSING_API_KEY_TRADING_RIGHTS = "missing_api_key_trading_rights"
    MISSING_STRATEGY_MINIMAL_FUNDS = "missing_strategy_minimal_funds"
    WORKFLOW_INIT_ERROR = "workflow_init_error"
    UNDEFINED = None


class ChangedElements(enum.Enum):
    ORDERS = "orders"
    TRADES = "trades"
    PORTFOLIO = "portfolio"
    POSITIONS = "positions"


class ActionType(enum.Enum):
    APPLY_CONFIGURATION = "apply_configuration"
    UNKNOWN = "unknown"


class ActionErrorStatus(enum.Enum):
    NO_ERROR = None
    NOT_ENOUGH_FUNDS = "not_enough_funds"
    MISSING_SYMBOL = "missing_symbol"
    SYMBOL_INCOMPATIBLE_WITH_ACCOUNT = "symbol_incompatible_with_account"
    ORDER_NOT_FOUND = "order_not_found"
    INVALID_ORDER = "invalid_order"
    INVALID_CONFIG = "invalid_config"
    INVALID_SIGNAL_FORMAT = "invalid_signal_format"
    UNSUPPORTED_STOP_ORDER = "unsupported_stop_order"
    INCOMPATIBLE_TRADING_TYPE = "incompatible_trading_type"
    UNSUPPORTED_HEDGE_POSITION = "unsupported_hedge_position"
    INTERNAL_ERROR = "internal_error"
    BLOCKCHAIN_WALLET_ERROR = "blockchain_wallet_error"
    DISABLED_FUNDS_TRANSFER_ERROR = "disabled_funds_transfer_error"
    UNSUPPORTED_ACTION_TYPE = "unsupported_action_type"
