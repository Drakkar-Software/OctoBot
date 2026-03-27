use pyo3::prelude::*;

use octobot_commons::symbols::symbol::Symbol;

#[pyclass(name = "Symbol", module = "octobot_commons_rs", from_py_object)]
#[derive(Clone)]
pub struct PySymbol {
    inner: Symbol,
}

#[pymethods]
impl PySymbol {
    #[new]
    #[pyo3(signature = (symbol_str))]
    pub fn new(symbol_str: &str) -> Self {
        Self {
            inner: Symbol::new(symbol_str),
        }
    }

    #[getter]
    fn symbol_str(&self) -> &str {
        &self.inner.symbol_str
    }

    #[getter]
    fn base(&self) -> Option<&str> {
        self.inner.base.as_deref()
    }

    #[getter]
    fn quote(&self) -> Option<&str> {
        self.inner.quote.as_deref()
    }

    #[getter]
    fn settlement_asset(&self) -> Option<&str> {
        self.inner.settlement_asset.as_deref()
    }

    #[getter]
    fn identifier(&self) -> Option<&str> {
        self.inner.identifier.as_deref()
    }

    #[getter]
    fn strike_price(&self) -> Option<&str> {
        self.inner.strike_price.as_deref()
    }

    #[getter]
    fn option_type(&self) -> Option<&str> {
        self.inner.option_type.as_deref()
    }

    fn base_and_quote(&self) -> (Option<&str>, Option<&str>) {
        self.inner.base_and_quote()
    }

    #[pyo3(signature = (market_separator=None, settlement_separator=None, option_separator=None))]
    fn merged_str_symbol(
        &self,
        market_separator: Option<&str>,
        settlement_separator: Option<&str>,
        option_separator: Option<&str>,
    ) -> String {
        self.inner
            .merged_str_symbol(market_separator, settlement_separator, option_separator)
    }

    #[pyo3(signature = (market_separator=None))]
    fn merged_str_base_and_quote_only_symbol(
        &self,
        market_separator: Option<&str>,
    ) -> String {
        self.inner
            .merged_str_base_and_quote_only_symbol(market_separator)
    }

    fn is_perpetual_future(&self) -> bool {
        self.inner.is_perpetual_future()
    }

    fn is_future(&self) -> bool {
        self.inner.is_future()
    }

    fn is_option(&self) -> bool {
        self.inner.is_option()
    }

    fn is_spot(&self) -> bool {
        self.inner.is_spot()
    }

    fn is_linear(&self) -> bool {
        self.inner.is_linear()
    }

    fn is_inverse(&self) -> bool {
        self.inner.is_inverse()
    }

    fn is_put_option(&self) -> bool {
        self.inner.is_put_option()
    }

    fn is_call_option(&self) -> bool {
        self.inner.is_call_option()
    }

    fn does_expire(&self) -> bool {
        self.inner.does_expire()
    }

    fn __str__(&self) -> String {
        self.inner.to_string()
    }

    fn __repr__(&self) -> String {
        format!("Symbol(\"{}\")", self.inner.symbol_str)
    }

    fn __eq__(&self, other: &PySymbol) -> bool {
        self.inner == other.inner
    }

    fn __hash__(&self) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        self.inner.symbol_str.hash(&mut hasher);
        hasher.finish()
    }
}

pub fn register(m: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {
    m.add_class::<PySymbol>()?;
    Ok(())
}
