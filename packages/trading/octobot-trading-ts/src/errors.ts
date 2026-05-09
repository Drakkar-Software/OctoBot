// Drakkar-Software OctoBot-Trading
// LGPL-3.0
//
// Typed error hierarchy mirroring octobot_trading/errors.py. Only the errors that
// can be raised from the in-scope REST + WebSocket + adapters surface are included.
// Pattern follows the repo's "no string-based error classification" rule from
// CLAUDE.md — callers narrow with `instanceof`.

export class OctoBotTradingError extends Error {
  constructor(message?: string) {
    super(message);
    this.name = new.target.name;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class OctoBotExchangeError extends OctoBotTradingError {}
export class MissingFunds extends OctoBotExchangeError {}
export class MissingMinimalExchangeTradeVolume extends OctoBotExchangeError {}
export class ExchangeProxyError extends OctoBotExchangeError {}
export class RetriableExchangeProxyError extends ExchangeProxyError {}

export class OrderCreationError extends OctoBotExchangeError {}
export class UnsupportedOrderTypeError extends OrderCreationError {}
export class UntradableSymbolError extends OrderCreationError {}
export class MaxOpenOrderReachedForSymbolError extends OrderCreationError {}
export class MarketClosedError extends OrderCreationError {}

export class OrderEditError extends OctoBotExchangeError {}
export class OrderCancelError extends OctoBotExchangeError {}
export class ExchangeOrderCancelError extends OrderCancelError {}
export class OrderNotFoundOnCancelError extends ExchangeOrderCancelError {}

export class UnexpectedExchangeSideOrderStateError extends OctoBotTradingError {}
export class OpenOrderError extends UnexpectedExchangeSideOrderStateError {}
export class FilledOrderError extends UnexpectedExchangeSideOrderStateError {}
export class CancellingOrderError extends UnexpectedExchangeSideOrderStateError {}
export class ClosedOrderError extends UnexpectedExchangeSideOrderStateError {}

export class NotSupported extends OctoBotTradingError {}
export class NotSupportedOrderTypeError extends NotSupported {}
export class UnSupportedSymbolError extends NotSupported {}

export class FailedRequest extends OctoBotExchangeError {}
export class RetriableFailedRequest extends FailedRequest {}
export class NetworkError extends RetriableFailedRequest {}
export class FailedMarketStatusRequest extends RetriableFailedRequest {}

export class RateLimitExceeded extends OctoBotExchangeError {}
export class UnavailableOrderTypeForMarketError extends OctoBotExchangeError {}

export class AuthenticationError extends OctoBotExchangeError {}
export class InvalidAPIKeyIPWhitelistError extends AuthenticationError {}

export class ExchangeInternalSyncError extends OctoBotExchangeError {}
export class ExchangeCompliancyError extends OctoBotExchangeError {}
export class ExchangeMaxOrdersForMarketReachedError extends OctoBotExchangeError {}
export class ExchangeAccountSymbolPermissionError extends OctoBotExchangeError {}
export class ExchangeClosedPositionError extends OctoBotExchangeError {}
export class ExchangeOrderInstantTriggerError extends OctoBotExchangeError {}

export class StoppedExchangeManagerError extends OctoBotTradingError {}
export class UnreachableExchange extends OctoBotTradingError {}
export class InvalidArgumentError extends OctoBotTradingError {}
export class AdapterError extends OctoBotTradingError {}
export class UnexpectedAdapterError extends OctoBotTradingError {}
export class InitializingError extends OctoBotTradingError {}
