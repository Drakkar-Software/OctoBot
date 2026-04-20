class HedgingEngineError(Exception):
    pass


class HedgingConfigurationError(HedgingEngineError):
    pass


class HedgingExecutionError(HedgingEngineError):
    pass


class MissingHedgingFundsError(HedgingExecutionError):
    pass


class HedgingAlreadyCountedFillAmountError(HedgingExecutionError):
    pass


class HedgingPriceNotSetError(HedgingExecutionError):
    pass


class HedgingOrderCreationError(HedgingExecutionError):
    pass


class InactiveOrdersNotEnabledError(HedgingOrderCreationError):
    pass


class TooSmallHedgingOrderError(HedgingOrderCreationError):
    pass


class TooLargeHedgingOrderError(HedgingOrderCreationError):
    pass


class HedgingEngineReachedMaxToleratedVolatility(HedgingEngineError):
    pass


class HedgingSymbolNotRegisteredError(HedgingConfigurationError):
    pass


class HedgingExchangeConflictError(HedgingConfigurationError):
    pass


class HedgingProfitThresholdTooHighError(HedgingConfigurationError):
    pass


class HedgingExchangeNotInReferencePriceExchangesError(HedgingConfigurationError):
    pass
