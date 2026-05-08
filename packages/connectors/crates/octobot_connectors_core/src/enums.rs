// Translated from packages/trading/octobot_trading/enums.py
// and packages/trading/octobot_trading/exchanges/connectors/ccxt/enums.py

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TradeOrderSide {
    Buy,
    Sell,
}

impl TradeOrderSide {
    pub fn value(&self) -> &'static str {
        match self {
            Self::Buy => "buy",
            Self::Sell => "sell",
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "buy" => Some(Self::Buy),
            "sell" => Some(Self::Sell),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TradeOrderType {
    Limit,
    Market,
    StopLoss,
    StopLossLimit,
    ConditionalMarket,
    ConditionalLimit,
    TakeProfit,
    TakeProfitLimit,
    TrailingStop,
    TrailingStopLimit,
    LimitMaker,
    Unsupported,
    Unknown,
}

impl TradeOrderType {
    pub fn value(&self) -> &'static str {
        match self {
            Self::Limit => "limit",
            Self::Market => "market",
            Self::StopLoss => "stop_loss",
            Self::StopLossLimit => "stop_loss_limit",
            Self::ConditionalMarket => "stop_market",
            Self::ConditionalLimit => "stop_limit",
            Self::TakeProfit => "take_profit",
            Self::TakeProfitLimit => "take_profit_limit",
            Self::TrailingStop => "trailing_stop",
            Self::TrailingStopLimit => "trailing_stop_limit",
            Self::LimitMaker => "limit_maker",
            Self::Unsupported => "unsupported",
            Self::Unknown => "unknown",
        }
    }
}

/// High-level order types combining side + type (matches TraderOrderType in Python)
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TraderOrderType {
    BuyMarket,
    BuyLimit,
    StopLoss,
    StopLossLimit,
    SellMarket,
    SellLimit,
    TrailingStop,
    TrailingStopLimit,
    TakeProfit,
    TakeProfitLimit,
    Unsupported,
    Unknown,
}

impl TraderOrderType {
    pub fn value(&self) -> &'static str {
        match self {
            Self::BuyMarket => "buy_market",
            Self::BuyLimit => "buy_limit",
            Self::StopLoss => "stop_loss",
            Self::StopLossLimit => "stop_limit",
            Self::SellMarket => "sell_market",
            Self::SellLimit => "sell_limit",
            Self::TrailingStop => "trailing_stop",
            Self::TrailingStopLimit => "trailing_stop_limit",
            Self::TakeProfit => "take_profit",
            Self::TakeProfitLimit => "take_profit_limit",
            Self::Unsupported => "unsupported",
            Self::Unknown => "unknown",
        }
    }

    pub fn ccxt_type(&self) -> &'static str {
        match self {
            Self::BuyLimit | Self::SellLimit | Self::StopLossLimit
            | Self::TakeProfitLimit | Self::TrailingStopLimit => "limit",
            _ => "market",
        }
    }

    pub fn ccxt_side(&self) -> &'static str {
        match self {
            Self::BuyMarket | Self::BuyLimit => "buy",
            Self::SellMarket | Self::SellLimit => "sell",
            Self::StopLoss | Self::StopLossLimit | Self::TakeProfit
            | Self::TakeProfitLimit | Self::TrailingStop | Self::TrailingStopLimit => "sell",
            _ => "buy",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum OrderStatus {
    PendingCreation,
    Open,
    PartiallyFilled,
    Filled,
    Canceled,
    PendingCancel,
    Closed,
    Expired,
    Rejected,
    Unknown,
}

impl OrderStatus {
    pub fn value(&self) -> &'static str {
        match self {
            Self::PendingCreation => "pending_creation",
            Self::Open => "open",
            Self::PartiallyFilled => "partially_filled",
            Self::Filled => "filled",
            Self::Canceled => "canceled",
            Self::PendingCancel => "canceling",
            Self::Closed => "closed",
            Self::Expired => "expired",
            Self::Rejected => "rejected",
            Self::Unknown => "unknown",
        }
    }

    pub fn is_closed(&self) -> bool {
        matches!(self, Self::Filled | Self::Canceled | Self::Closed | Self::Expired | Self::Rejected)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ExchangeTypes {
    Spot,
    Future,
    Margin,
    Option,
    Unknown,
}

impl ExchangeTypes {
    pub fn value(&self) -> &'static str {
        match self {
            Self::Spot => "spot",
            Self::Future => "future",
            Self::Margin => "margin",
            Self::Option => "option",
            Self::Unknown => "unknown",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum AccountTypes {
    Cash,
    Margin,
    Future,
    Swap,
    Option,
}

impl AccountTypes {
    pub fn value(&self) -> &'static str {
        match self {
            Self::Cash => "cash",
            Self::Margin => "margin",
            Self::Future => "future",
            Self::Swap => "swap",
            Self::Option => "option",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PositionSide {
    Long,
    Short,
    Both,
    Unknown,
}

impl PositionSide {
    pub fn value(&self) -> &'static str {
        match self {
            Self::Long => "long",
            Self::Short => "short",
            Self::Both => "both",
            Self::Unknown => "unknown",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PositionStatus {
    Liquidating,
    Liquidated,
    Open,
    Adl,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PositionMode {
    Hedge,
    OneWay,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum MarginType {
    Cross,
    Isolated,
}

impl MarginType {
    pub fn value(&self) -> &'static str {
        match self {
            Self::Cross => "cross",
            Self::Isolated => "isolated",
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "cross" => Some(Self::Cross),
            "isolated" => Some(Self::Isolated),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ContractTradingTypes {
    Linear,
    Inverse,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum FutureContractType {
    InversePerpetual,
    LinearPerpetual,
    InverseExpirable,
    LinearExpirable,
}

impl FutureContractType {
    pub fn value(&self) -> &'static str {
        match self {
            Self::InversePerpetual => "inverse_perpetual",
            Self::LinearPerpetual => "linear_perpetual",
            Self::InverseExpirable => "inverse_expirable",
            Self::LinearExpirable => "linear_expirable",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TakeProfitStopLossMode {
    Full,
    Partial,
}

/// Time frames — mirrors octobot_commons.enums.TimeFrames
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TimeFrame {
    OneMinute,
    ThreeMinutes,
    FiveMinutes,
    FifteenMinutes,
    ThirtyMinutes,
    OneHour,
    TwoHours,
    FourHours,
    SixHours,
    EightHours,
    TwelveHours,
    OneDay,
    ThreeDays,
    OneWeek,
    OneMonth,
}

impl TimeFrame {
    pub fn to_ccxt_value(&self) -> &'static str {
        match self {
            Self::OneMinute => "1m",
            Self::ThreeMinutes => "3m",
            Self::FiveMinutes => "5m",
            Self::FifteenMinutes => "15m",
            Self::ThirtyMinutes => "30m",
            Self::OneHour => "1h",
            Self::TwoHours => "2h",
            Self::FourHours => "4h",
            Self::SixHours => "6h",
            Self::EightHours => "8h",
            Self::TwelveHours => "12h",
            Self::OneDay => "1d",
            Self::ThreeDays => "3d",
            Self::OneWeek => "1w",
            Self::OneMonth => "1M",
        }
    }

    pub fn to_seconds(&self) -> i64 {
        match self {
            Self::OneMinute => 60,
            Self::ThreeMinutes => 180,
            Self::FiveMinutes => 300,
            Self::FifteenMinutes => 900,
            Self::ThirtyMinutes => 1800,
            Self::OneHour => 3600,
            Self::TwoHours => 7200,
            Self::FourHours => 14400,
            Self::SixHours => 21600,
            Self::EightHours => 28800,
            Self::TwelveHours => 43200,
            Self::OneDay => 86400,
            Self::ThreeDays => 259200,
            Self::OneWeek => 604800,
            Self::OneMonth => 2592000,
        }
    }

    pub fn from_ccxt_value(s: &str) -> Option<Self> {
        match s {
            "1m" => Some(Self::OneMinute),
            "3m" => Some(Self::ThreeMinutes),
            "5m" => Some(Self::FiveMinutes),
            "15m" => Some(Self::FifteenMinutes),
            "30m" => Some(Self::ThirtyMinutes),
            "1h" => Some(Self::OneHour),
            "2h" => Some(Self::TwoHours),
            "4h" => Some(Self::FourHours),
            "6h" => Some(Self::SixHours),
            "8h" => Some(Self::EightHours),
            "12h" => Some(Self::TwelveHours),
            "1d" => Some(Self::OneDay),
            "3d" => Some(Self::ThreeDays),
            "1w" => Some(Self::OneWeek),
            "1M" => Some(Self::OneMonth),
            _ => None,
        }
    }
}

/// CCXT-specific column enums (mirrors ccxt/enums.py)

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum ExchangeOrderCcxtUnifiedParams {
    ReduceOnly,
    StopLossPrice,
    TakeProfitPrice,
    StopPrice,
    TriggerDirection,
    TriggerPrice,
    StopLoss,
    TakeProfit,
    TrailingPercent,
    TrailingAmount,
    TrailingTriggerPrice,
}

impl ExchangeOrderCcxtUnifiedParams {
    pub fn value(&self) -> &'static str {
        match self {
            Self::ReduceOnly => "reduceOnly",
            Self::StopLossPrice => "stopLossPrice",
            Self::TakeProfitPrice => "takeProfitPrice",
            Self::StopPrice => "stopPrice",
            Self::TriggerDirection => "triggerDirection",
            Self::TriggerPrice => "triggerPrice",
            Self::StopLoss => "stopLoss",
            Self::TakeProfit => "takeProfit",
            Self::TrailingPercent => "trailingPercent",
            Self::TrailingAmount => "trailingAmount",
            Self::TrailingTriggerPrice => "trailingTriggerPrice",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum ExchangeMarginTypes {
    Isolated,
    Cross,
}

impl ExchangeMarginTypes {
    pub fn value(&self) -> &'static str {
        match self {
            Self::Isolated => "isolated",
            Self::Cross => "cross",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum OrderFetchParams {
    Stop,
}

impl OrderFetchParams {
    pub fn value(&self) -> &'static str {
        match self {
            Self::Stop => "stop",
        }
    }
}

/// Supported exchange elements (mirrors ExchangeSupportedElements)
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum ExchangeSupportedElements {
    UnsupportedOrders,
    SupportedBundledOrders,
}

impl ExchangeSupportedElements {
    pub fn value(&self) -> &'static str {
        match self {
            Self::UnsupportedOrders => "unsupported_orders",
            Self::SupportedBundledOrders => "supported_bundled_orders",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_trade_order_side_roundtrip() {
        assert_eq!(TradeOrderSide::from_str("buy"), Some(TradeOrderSide::Buy));
        assert_eq!(TradeOrderSide::from_str("sell"), Some(TradeOrderSide::Sell));
        assert_eq!(TradeOrderSide::Buy.value(), "buy");
        assert_eq!(TradeOrderSide::Sell.value(), "sell");
    }

    #[test]
    fn test_time_frame_seconds() {
        assert_eq!(TimeFrame::OneHour.to_seconds(), 3600);
        assert_eq!(TimeFrame::OneDay.to_seconds(), 86400);
    }

    #[test]
    fn test_order_status_closed() {
        assert!(OrderStatus::Filled.is_closed());
        assert!(OrderStatus::Canceled.is_closed());
        assert!(!OrderStatus::Open.is_closed());
    }
}
