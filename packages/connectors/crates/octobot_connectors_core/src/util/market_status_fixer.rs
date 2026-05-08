// Market status fixer.
// Translated from packages/trading/octobot_trading/exchanges/util/exchange_market_status_fixer.py
// and packages/trading/octobot_trading/exchanges/util/exchange_market_status.py

use crate::types::{MarketLimits, MarketPrecision, MarketStatus};

// ---- Column key constants (mirrors ExchangeConstantsMarketStatusColumns) ----

pub const LIMITS_AMOUNT_MIN: &str = "min";
pub const LIMITS_AMOUNT_MAX: &str = "max";
pub const LIMITS_PRICE_MIN: &str = "min";
pub const LIMITS_PRICE_MAX: &str = "max";
pub const LIMITS_COST_MIN: &str = "min";
pub const LIMITS_COST_MAX: &str = "max";

// ---- Validation helpers (mirrors is_ms_valid) ----

/// Returns true if the value is finite, non-NaN, and > 0 (or >= 0 if zero_valid).
pub fn is_ms_valid(value: Option<f64>, zero_valid: bool) -> bool {
    match value {
        None => false,
        Some(v) if v.is_nan() || v.is_infinite() => false,
        Some(v) => if zero_valid { v >= 0.0 } else { v > 0.0 },
    }
}

/// Checks all values in a limit dict are valid.
pub fn check_market_status_values(values: &[Option<f64>], zero_valid: bool) -> bool {
    values.iter().all(|&v| is_ms_valid(v, zero_valid))
}

// ---- Amount / cost cross-calculation ----

/// Derive missing amount limits from cost and price limits.
/// Mirrors calculate_amounts(market_limit).
pub fn calculate_amounts(limits: &mut MarketLimits) {
    // max amount from max cost / max price
    if !is_ms_valid(limits.amount_max, false) {
        if let (Some(cost_max), Some(price_max)) = (limits.cost_max, limits.price_max) {
            if is_ms_valid(Some(cost_max), false) && is_ms_valid(Some(price_max), false) {
                limits.amount_max = Some(cost_max / price_max);
            }
        }
    }
    // min amount from min cost / min price
    if !is_ms_valid(limits.amount_min, false) {
        if let (Some(cost_min), Some(price_min)) = (limits.cost_min, limits.price_min) {
            if is_ms_valid(Some(cost_min), false) && is_ms_valid(Some(price_min), false) {
                limits.amount_min = Some(cost_min / price_min);
            }
        }
    }
}

/// Derive missing cost limits from amount and price limits.
/// Mirrors calculate_costs(market_limit).
pub fn calculate_costs(limits: &mut MarketLimits) {
    if !is_ms_valid(limits.cost_max, false) {
        if let (Some(amount_max), Some(price_max)) = (limits.amount_max, limits.price_max) {
            if is_ms_valid(Some(amount_max), false) && is_ms_valid(Some(price_max), false) {
                limits.cost_max = Some(amount_max * price_max);
            }
        }
    }
    if !is_ms_valid(limits.cost_min, false) {
        if let (Some(amount_min), Some(price_min)) = (limits.amount_min, limits.price_min) {
            if is_ms_valid(Some(amount_min), false) && is_ms_valid(Some(price_min), false) {
                limits.cost_min = Some(amount_min * price_min);
            }
        }
    }
}

/// Set invalid price limits to None.
/// Mirrors update_prices(market_limit).
pub fn update_prices(limits: &mut MarketLimits) {
    if !is_ms_valid(limits.price_max, false) {
        limits.price_max = None;
    }
    if !is_ms_valid(limits.price_min, false) {
        limits.price_min = None;
    }
}

/// Run all limit fixes in the correct order.
/// Mirrors fix_market_status_limits_from_current_data(market_limit).
pub fn fix_limits_from_current_data(limits: &mut MarketLimits) {
    let cost_values = [limits.cost_min, limits.cost_max];
    if !check_market_status_values(&cost_values, false) {
        calculate_costs(limits);
    }
    let amount_values = [limits.amount_min, limits.amount_max];
    if !check_market_status_values(&amount_values, false) {
        calculate_amounts(limits);
    }
    let price_values = [limits.price_min, limits.price_max];
    if !check_market_status_values(&price_values, false) {
        update_prices(limits);
    }
    // Ensure cost_min is at least 0
    if !is_ms_valid(limits.cost_min, true) {
        limits.cost_min = Some(0.0);
    }
}

// ---- ExchangeMarketStatusFixer constants (mirrors class constants) ----

pub const LIMIT_PRICE_MULTIPLIER: f64 = 1000.0;
pub const LIMIT_COST_MULTIPLIER: f64 = 1.0;

// Attenuation factors for calculated limits
pub const LIMIT_AMOUNT_MAX_SUP_ATTENUATION: f64 = 8.0;
pub const LIMIT_AMOUNT_MAX_MINUS_3_ATTENUATION: f64 = 8.0;
pub const LIMIT_AMOUNT_MIN_ATTENUATION: f64 = 3.0;
pub const LIMIT_AMOUNT_MIN_SUP_ATTENUATION: f64 = 1.0;

/// Fix a market status in-place using the price example and computed limit fallbacks.
/// Mirrors ExchangeMarketStatusFixer.__init__ which calls _fix_typing, _fix_market_status_precision,
/// and _fix_market_status_limits.
///
/// `price_example` is used to derive limits when the market provides none.
pub fn fix_market_status(status: &mut MarketStatus, price_example: Option<f64>) {
    fix_precision(&mut status.precision);
    fix_limits(&mut status.limits, price_example);
}

fn fix_precision(precision: &mut MarketPrecision) {
    // Ensure precision values are valid (positive floats)
    // Mirrors ExchangeMarketStatusFixer._fix_market_status_precision
    if let Some(p) = precision.price {
        if !is_ms_valid(Some(p), false) {
            precision.price = None;
        }
    }
    if let Some(a) = precision.amount {
        if !is_ms_valid(Some(a), false) {
            precision.amount = None;
        }
    }
}

fn fix_limits(limits: &mut MarketLimits, price_example: Option<f64>) {
    fix_limits_from_current_data(limits);
    if let Some(price) = price_example {
        fix_limits_from_price_example(limits, price);
    }
}

/// Fill in completely missing limits from a known current price.
/// Mirrors ExchangeMarketStatusFixer._fix_market_limit_from_price_example
fn fix_limits_from_price_example(limits: &mut MarketLimits, price: f64) {
    if !is_ms_valid(limits.price_max, false) {
        limits.price_max = Some(price * LIMIT_PRICE_MULTIPLIER);
    }
    if !is_ms_valid(limits.price_min, false) {
        limits.price_min = Some(price / LIMIT_PRICE_MULTIPLIER);
    }
    if !is_ms_valid(limits.cost_max, false) {
        limits.cost_max = Some(price * LIMIT_PRICE_MULTIPLIER * LIMIT_COST_MULTIPLIER);
    }
    if !is_ms_valid(limits.cost_min, true) {
        limits.cost_min = Some(0.0);
    }
    if !is_ms_valid(limits.amount_max, false) {
        let log_price = price.log10();
        let attenuation = if log_price >= 0.0 {
            LIMIT_AMOUNT_MAX_SUP_ATTENUATION
        } else {
            LIMIT_AMOUNT_MAX_MINUS_3_ATTENUATION
        };
        limits.amount_max = Some(10_f64.powf(-log_price + attenuation));
    }
    if !is_ms_valid(limits.amount_min, false) {
        let log_price = price.log10();
        let attenuation = if log_price >= 0.0 {
            LIMIT_AMOUNT_MIN_SUP_ATTENUATION
        } else {
            LIMIT_AMOUNT_MIN_ATTENUATION
        };
        limits.amount_min = Some(10_f64.powf(-log_price - attenuation));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_ms_valid() {
        assert!(is_ms_valid(Some(1.0), false));
        assert!(is_ms_valid(Some(0.0), true));
        assert!(!is_ms_valid(Some(0.0), false));
        assert!(!is_ms_valid(None, false));
        assert!(!is_ms_valid(Some(f64::NAN), false));
    }

    #[test]
    fn test_calculate_amounts_from_cost_and_price() {
        let mut limits = MarketLimits {
            amount_min: None,
            amount_max: None,
            price_min: Some(100.0),
            price_max: Some(200.0),
            cost_min: Some(10.0),
            cost_max: Some(1000.0),
        };
        calculate_amounts(&mut limits);
        assert_eq!(limits.amount_min, Some(0.1));   // 10 / 100
        assert_eq!(limits.amount_max, Some(5.0));   // 1000 / 200
    }

    #[test]
    fn test_calculate_costs_from_amount_and_price() {
        let mut limits = MarketLimits {
            amount_min: Some(0.001),
            amount_max: Some(10.0),
            price_min: Some(50000.0),
            price_max: Some(60000.0),
            cost_min: None,
            cost_max: None,
        };
        calculate_costs(&mut limits);
        assert_eq!(limits.cost_max, Some(600000.0));   // 10 * 60000
        assert_eq!(limits.cost_min, Some(50.0));       // 0.001 * 50000
    }

    #[test]
    fn test_fix_limits_from_price_example() {
        let mut limits = MarketLimits::default();
        fix_limits_from_price_example(&mut limits, 50000.0);
        assert!(limits.price_max.is_some());
        assert!(limits.amount_min.is_some());
        assert!(limits.cost_min == Some(0.0) || limits.cost_min.map_or(false, |v| v >= 0.0));
    }

    #[test]
    fn test_fix_limits_from_current_data_sets_cost_min_zero() {
        let mut limits = MarketLimits {
            amount_min: Some(0.001),
            amount_max: Some(10.0),
            price_min: Some(100.0),
            price_max: Some(200.0),
            cost_min: None,
            cost_max: None,
        };
        fix_limits_from_current_data(&mut limits);
        // cost_min should be filled or defaulted to 0
        assert!(limits.cost_min.is_some());
    }
}
