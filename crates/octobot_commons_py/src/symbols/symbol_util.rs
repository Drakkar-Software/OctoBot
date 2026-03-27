use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;

use crate::symbols::symbol::PySymbol;
use octobot_commons::symbols::symbol_util;

#[pyfunction]
pub fn parse_symbol(symbol_str: &str) -> PySymbol {
    PySymbol::new(symbol_str)
}

#[pyfunction]
pub fn parse_symbols(symbol_strs: Vec<String>) -> Vec<PySymbol> {
    symbol_strs.iter().map(|s| PySymbol::new(s)).collect()
}

#[pyfunction]
pub fn merge_symbol(symbol_str: &str) -> String {
    symbol_util::merge_symbol(symbol_str)
}

#[pyfunction]
#[pyo3(signature = (symbol_str, separator=None))]
pub fn is_symbol(symbol_str: &str, separator: Option<&str>) -> bool {
    symbol_util::is_symbol(symbol_str, separator)
}

#[pyfunction]
#[allow(clippy::too_many_arguments)]
#[pyo3(signature = (base, quote, settlement_asset=None, identifier=None, strike_price=None, option_type=None, market_separator=None, settlement_separator=None, option_separator=None))]
pub fn merge_currencies(
    base: &str,
    quote: &str,
    settlement_asset: Option<&str>,
    identifier: Option<&str>,
    strike_price: Option<&str>,
    option_type: Option<&str>,
    market_separator: Option<&str>,
    settlement_separator: Option<&str>,
    option_separator: Option<&str>,
) -> String {
    symbol_util::merge_currencies(
        base,
        quote,
        settlement_asset,
        identifier,
        strike_price,
        option_type,
        market_separator,
        settlement_separator,
        option_separator,
    )
}

#[pyfunction]
#[pyo3(signature = (symbol_str, symbol_separator="/", new_symbol_separator=None, should_uppercase=false, should_lowercase=false, with_settlement_asset=false))]
pub fn convert_symbol(
    symbol_str: &str,
    symbol_separator: &str,
    new_symbol_separator: Option<&str>,
    should_uppercase: bool,
    should_lowercase: bool,
    with_settlement_asset: bool,
) -> String {
    symbol_util::convert_symbol(
        symbol_str,
        symbol_separator,
        new_symbol_separator,
        should_uppercase,
        should_lowercase,
        with_settlement_asset,
    )
}

#[pyfunction]
pub fn is_usd_like_coin(coin: &str) -> bool {
    symbol_util::is_usd_like_coin(coin)
}

#[pyfunction]
pub fn get_most_common_usd_like_symbol(pairs: Vec<String>) -> PyResult<String> {
    let refs: Vec<&str> = pairs.iter().map(String::as_str).collect();
    symbol_util::get_most_common_usd_like_symbol(&refs)
        .map_err(|e| PyValueError::new_err(e.to_string()))
}

pub fn register(m: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse_symbol, m)?)?;
    m.add_function(wrap_pyfunction!(parse_symbols, m)?)?;
    m.add_function(wrap_pyfunction!(merge_symbol, m)?)?;
    m.add_function(wrap_pyfunction!(is_symbol, m)?)?;
    m.add_function(wrap_pyfunction!(merge_currencies, m)?)?;
    m.add_function(wrap_pyfunction!(convert_symbol, m)?)?;
    m.add_function(wrap_pyfunction!(is_usd_like_coin, m)?)?;
    m.add_function(wrap_pyfunction!(get_most_common_usd_like_symbol, m)?)?;
    Ok(())
}
