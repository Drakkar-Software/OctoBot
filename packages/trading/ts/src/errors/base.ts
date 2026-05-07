// Mirrors octobot_trading/errors.py

export class OctoBotTradingError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "OctoBotTradingError"
  }
}

export class OctoBotExchangeError extends OctoBotTradingError {
  constructor(message: string) {
    super(message)
    this.name = "OctoBotExchangeError"
  }
}

export class MissingFunds extends OctoBotExchangeError {
  constructor(message: string) {
    super(message)
    this.name = "MissingFunds"
  }
}

export class MissingMinimalExchangeTradeVolume extends OctoBotExchangeError {
  constructor(message: string) {
    super(message)
    this.name = "MissingMinimalExchangeTradeVolume"
  }
}

export class OrderCreationError extends OctoBotExchangeError {
  constructor(message: string) {
    super(message)
    this.name = "OrderCreationError"
  }
}

export class UnsupportedOrderTypeError extends OrderCreationError {
  constructor(message: string) {
    super(message)
    this.name = "UnsupportedOrderTypeError"
  }
}

export class MarketClosedError extends OrderCreationError {
  constructor(message: string) {
    super(message)
    this.name = "MarketClosedError"
  }
}

export class OrderEditError extends OctoBotExchangeError {
  constructor(message: string) {
    super(message)
    this.name = "OrderEditError"
  }
}

export class OrderCancelError extends OctoBotExchangeError {
  constructor(message: string) {
    super(message)
    this.name = "OrderCancelError"
  }
}

export class OrderNotFoundOnCancelError extends OrderCancelError {
  constructor(message: string) {
    super(message)
    this.name = "OrderNotFoundOnCancelError"
  }
}

export class NotSupported extends OctoBotTradingError {
  constructor(message: string) {
    super(message)
    this.name = "NotSupported"
  }
}

export class UnSupportedSymbolError extends NotSupported {
  constructor(message: string) {
    super(message)
    this.name = "UnSupportedSymbolError"
  }
}

export class FailedRequest extends OctoBotExchangeError {
  constructor(message: string) {
    super(message)
    this.name = "FailedRequest"
  }
}

export class RetriableFailedRequest extends FailedRequest {
  constructor(message: string) {
    super(message)
    this.name = "RetriableFailedRequest"
  }
}

export class NetworkError extends RetriableFailedRequest {
  constructor(message: string) {
    super(message)
    this.name = "NetworkError"
  }
}

export class RateLimitExceeded extends OctoBotExchangeError {
  constructor(message: string) {
    super(message)
    this.name = "RateLimitExceeded"
  }
}

export class AuthenticationError extends OctoBotExchangeError {
  constructor(message: string) {
    super(message)
    this.name = "AuthenticationError"
  }
}

export class InvalidAPIKeyIPWhitelistError extends AuthenticationError {
  constructor(message: string) {
    super(message)
    this.name = "InvalidAPIKeyIPWhitelistError"
  }
}

export class UnreachableExchange extends OctoBotTradingError {
  constructor(message: string) {
    super(message)
    this.name = "UnreachableExchange"
  }
}

export class ExchangeCompliancyError extends OctoBotExchangeError {
  constructor(message: string) {
    super(message)
    this.name = "ExchangeCompliancyError"
  }
}

export class ExchangeInternalSyncError extends OctoBotExchangeError {
  constructor(message: string) {
    super(message)
    this.name = "ExchangeInternalSyncError"
  }
}

export class AdapterError extends OctoBotTradingError {
  constructor(message: string) {
    super(message)
    this.name = "AdapterError"
  }
}

export class UnexpectedAdapterError extends OctoBotTradingError {
  constructor(message: string) {
    super(message)
    this.name = "UnexpectedAdapterError"
  }
}
