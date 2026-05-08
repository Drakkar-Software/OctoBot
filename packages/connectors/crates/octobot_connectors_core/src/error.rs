// Translated from packages/trading/octobot_trading/errors.py

use thiserror::Error;

#[derive(Debug, Error)]
pub enum OctoBotExchangeError {
    #[error("Exchange request failed: {0}")]
    FailedRequest(String),

    #[error("Retriable request failed: {0}")]
    RetriableFailedRequest(String),

    #[error("Network error: {0}")]
    NetworkError(String),

    #[error("Authentication error: {0}")]
    AuthenticationError(String),

    #[error("Invalid API key IP whitelist: {0}")]
    InvalidApiKeyIpWhitelistError(String),

    #[error("Not supported: {0}")]
    NotSupported(String),

    #[error("Missing funds: {0}")]
    MissingFunds(String),

    #[error("Missing minimal exchange trade volume: {0}")]
    MissingMinimalExchangeTradeVolume(String),

    #[error("Unsupported symbol: {0}")]
    UnsupportedSymbolError(String),

    #[error("Order creation error: {0}")]
    OrderCreationError(String),

    #[error("Order cancel error: {0}")]
    OrderCancelError(String),

    #[error("Order not found on cancel: {0}")]
    OrderNotFoundOnCancelError(String),

    #[error("Exchange order cancel error: {0}")]
    ExchangeOrderCancelError(String),

    #[error("Rate limit exceeded: {0}")]
    RateLimitExceeded(String),

    #[error("Exchange internal sync error: {0}")]
    ExchangeInternalSyncError(String),

    #[error("Exchange compliancy error: {0}")]
    ExchangeCompliancyError(String),

    #[error("Exchange max orders for market reached: {0}")]
    ExchangeMaxOrdersForMarketReachedError(String),

    #[error("Unreachable exchange: {0}")]
    UnreachableExchange(String),

    #[error("Exchange proxy error: {0}")]
    ExchangeProxyError(String),

    #[error("Failed market status request: {0}")]
    FailedMarketStatusRequest(String),

    #[error("Disabled funds transfer: {0}")]
    DisabledFundsTransferError(String),

    #[error("Adapter error: {0}")]
    AdapterError(String),

    #[error("Market closed: {0}")]
    MarketClosedError(String),

    #[error("Exchange closed position: {0}")]
    ExchangeClosedPositionError(String),

    #[error("Order not found: {0}")]
    OrderNotFound(String),

    #[error("Permission error: {0}")]
    PermissionError(String),
}

pub type ExchangeResult<T> = Result<T, OctoBotExchangeError>;

impl OctoBotExchangeError {
    /// Returns true if this error is likely transient and can be retried
    pub fn is_retriable(&self) -> bool {
        matches!(
            self,
            Self::RetriableFailedRequest(_)
                | Self::NetworkError(_)
                | Self::RateLimitExceeded(_)
                | Self::ExchangeInternalSyncError(_)
                | Self::UnreachableExchange(_)
        )
    }

    /// Returns true if this is an authentication failure
    pub fn is_auth_error(&self) -> bool {
        matches!(
            self,
            Self::AuthenticationError(_) | Self::InvalidApiKeyIpWhitelistError(_) | Self::PermissionError(_)
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_display() {
        let e = OctoBotExchangeError::AuthenticationError("bad key".into());
        assert!(e.to_string().contains("Authentication error"));
        assert!(e.is_auth_error());
        assert!(!e.is_retriable());
    }

    #[test]
    fn test_retriable() {
        assert!(OctoBotExchangeError::RateLimitExceeded("too many".into()).is_retriable());
        assert!(!OctoBotExchangeError::MissingFunds("no money".into()).is_retriable());
    }
}
