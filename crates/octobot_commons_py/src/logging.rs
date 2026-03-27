use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

/// LOGS_MAX_COUNT mirrors the Python constant.
const LOGS_MAX_COUNT: usize = 1000;

/// Get or initialize the module-level logs_database dict.
fn get_logs_database(py: Python<'_>) -> PyResult<Py<PyDict>> {
    let module = py.import("octobot_commons_rs._core")?;
    match module.getattr("_logs_database") {
        Ok(db) => Ok(db.extract()?),
        Err(_) => {
            let db = PyDict::new(py);
            db.set_item("log_db", PyList::empty(py))?;
            db.set_item("log_new_errors_count", 0)?;
            db.set_item("log_backtesting_errors_count", 0)?;
            let db_py = db.unbind();
            module.setattr("_logs_database", &db_py)?;
            Ok(db_py)
        }
    }
}

#[pyclass(name = "BotLogger", module = "octobot_commons_rs")]
pub struct BotLogger {
    #[pyo3(get)]
    pub logger_name: String,
    logger: Py<PyAny>,
}

#[pymethods]
impl BotLogger {
    #[new]
    #[pyo3(signature = (logger_name="Anonymous"))]
    fn new(py: Python<'_>, logger_name: &str) -> PyResult<Self> {
        let logging = py.import("logging")?;
        let logger = logging.call_method1("getLogger", (logger_name,))?.unbind();
        Ok(Self {
            logger_name: logger_name.to_string(),
            logger,
        })
    }

    fn debug(&self, py: Python<'_>, message: &str) -> PyResult<()> {
        self.logger.call_method1(py, "debug", (message,))?;
        Ok(())
    }

    fn info(&self, py: Python<'_>, message: &str) -> PyResult<()> {
        self.logger.call_method1(py, "info", (message,))?;
        Ok(())
    }

    fn warning(&self, py: Python<'_>, message: &str) -> PyResult<()> {
        self.logger.call_method1(py, "warning", (message,))?;
        Ok(())
    }

    #[pyo3(signature = (message, skip_post_callback=false))]
    fn error(&self, py: Python<'_>, message: &str, skip_post_callback: bool) -> PyResult<()> {
        self.logger.call_method1(py, "error", (message,))?;
        self.publish_log_if_necessary(py, message, 40)?;
        if !skip_post_callback {
            self.post_callback_if_necessary(py, None, Some(message))?;
        }
        Ok(())
    }

    #[pyo3(signature = (exc, publish_error_if_necessary=true, error_message=None, skip_post_callback=false))]
    fn exception(
        &self,
        py: Python<'_>,
        exc: &Bound<'_, PyAny>,
        publish_error_if_necessary: bool,
        error_message: Option<&str>,
        skip_post_callback: bool,
    ) -> PyResult<()> {
        let exc_str = exc.str()?.extract::<String>()?;
        let msg = error_message.unwrap_or(&exc_str);
        self.logger.call_method1(py, "exception", (msg,))?;
        if publish_error_if_necessary {
            self.publish_log_if_necessary(py, msg, 40)?;
        }
        if !skip_post_callback {
            self.post_callback_if_necessary(py, Some(exc), error_message)?;
        }
        Ok(())
    }

    fn critical(&self, py: Python<'_>, message: &str) -> PyResult<()> {
        self.logger.call_method1(py, "critical", (message,))?;
        Ok(())
    }

    fn fatal(&self, py: Python<'_>, message: &str) -> PyResult<()> {
        self.logger.call_method1(py, "fatal", (message,))?;
        Ok(())
    }

    fn disable(&self, py: Python<'_>, disabled: bool) -> PyResult<()> {
        self.logger.setattr(py, "disabled", disabled)?;
        Ok(())
    }
}

impl BotLogger {
    fn publish_log_if_necessary(&self, py: Python<'_>, message: &str, level: i32) -> PyResult<()> {
        if level < 30 {
            // Only WARNING and above
            return Ok(());
        }
        let db = get_logs_database(py)?;
        let db_bound = db.bind(py);
        let log_list = db_bound.get_item("log_db")?.unwrap();
        let log_list = log_list.cast::<PyList>()?;
        if log_list.len() >= LOGS_MAX_COUNT {
            // Remove oldest
            log_list.del_item(0)?;
        }
        let entry = PyDict::new(py);
        entry.set_item("source", &self.logger_name)?;
        entry.set_item("message", message)?;
        entry.set_item("level", level)?;
        log_list.append(entry)?;

        // Increment error count
        if level >= 40 {
            let count: i64 = db_bound
                .get_item("log_new_errors_count")?
                .map(|v| v.extract().unwrap_or(0))
                .unwrap_or(0);
            db_bound.set_item("log_new_errors_count", count + 1)?;
        }
        Ok(())
    }

    fn post_callback_if_necessary(
        &self,
        py: Python<'_>,
        _exception: Option<&Bound<'_, PyAny>>,
        _error_message: Option<&str>,
    ) -> PyResult<()> {
        // Call registered error notifiers
        let module = py.import("octobot_commons_rs._core")?;
        if let Ok(callbacks) = module.getattr("_error_notifier_callbacks") {
            if let Ok(list) = callbacks.cast::<PyList>() {
                for cb in list.iter() {
                    let _ = cb.call0();
                }
            }
        }
        Ok(())
    }
}

#[pyfunction]
#[pyo3(signature = (logger_name="Anonymous"))]
pub fn get_logger(py: Python<'_>, logger_name: &str) -> PyResult<BotLogger> {
    BotLogger::new(py, logger_name)
}

#[pyfunction]
pub fn set_global_logger_level(py: Python<'_>, level: i32) -> PyResult<()> {
    let logging = py.import("logging")?;
    let root_logger = logging.call_method0("getLogger")?;
    root_logger.call_method1("setLevel", (level,))?;
    Ok(())
}

#[pyfunction]
pub fn get_global_logger_level(py: Python<'_>) -> PyResult<i32> {
    let logging = py.import("logging")?;
    let root_logger = logging.call_method0("getLogger")?;
    root_logger.call_method0("getEffectiveLevel")?.extract()
}

#[pyfunction]
pub fn get_logger_level_per_handler(py: Python<'_>) -> PyResult<Vec<i32>> {
    let logging = py.import("logging")?;
    let root_logger = logging.call_method0("getLogger")?;
    let handlers = root_logger.getattr("handlers")?;
    let handlers = handlers.cast::<PyList>()?;
    let mut levels = Vec::new();
    for handler in handlers.iter() {
        if let Ok(level) = handler.getattr("level") {
            if let Ok(l) = level.extract::<i32>() {
                levels.push(l);
            }
        }
    }
    Ok(levels)
}

#[pyfunction]
pub fn set_logging_level(py: Python<'_>, logger_names: Vec<String>, level: i32) -> PyResult<()> {
    let logging = py.import("logging")?;
    for name in &logger_names {
        let logger = logging.call_method1("getLogger", (name,))?;
        logger.call_method1("setLevel", (level,))?;
    }
    Ok(())
}

#[pyfunction]
#[pyo3(signature = (counter="log_new_errors_count"))]
pub fn get_errors_count(py: Python<'_>, counter: &str) -> PyResult<i64> {
    let db = get_logs_database(py)?;
    let db_bound = db.bind(py);
    Ok(db_bound
        .get_item(counter)?
        .map(|v| v.extract().unwrap_or(0))
        .unwrap_or(0))
}

#[pyfunction]
#[pyo3(signature = (counter="log_new_errors_count"))]
pub fn reset_errors_count(py: Python<'_>, counter: &str) -> PyResult<()> {
    let db = get_logs_database(py)?;
    db.bind(py).set_item(counter, 0)?;
    Ok(())
}

#[pyfunction]
pub fn get_backtesting_errors_count(py: Python<'_>) -> PyResult<i64> {
    get_errors_count(py, "log_backtesting_errors_count")
}

#[pyfunction]
pub fn reset_backtesting_errors(py: Python<'_>) -> PyResult<()> {
    reset_errors_count(py, "log_backtesting_errors_count")
}

#[pyfunction]
pub fn register_error_notifier(py: Python<'_>, callback: Py<PyAny>) -> PyResult<()> {
    let module = py.import("octobot_commons_rs._core")?;
    match module.getattr("_error_notifier_callbacks") {
        Ok(callbacks) => {
            callbacks.cast::<PyList>()?.append(callback)?;
        }
        Err(_) => {
            let list = PyList::new(py, [callback])?;
            module.setattr("_error_notifier_callbacks", list)?;
        }
    }
    Ok(())
}

#[pyfunction]
pub fn register_log_callback(_py: Python<'_>, _callback: Py<PyAny>) -> PyResult<()> {
    // Store the callback for future use
    // Currently a no-op in bridge
    Ok(())
}

#[pyfunction]
pub fn set_error_publication_enabled(_py: Python<'_>, _enabled: bool) -> PyResult<()> {
    Ok(())
}

#[pyfunction]
pub fn set_enable_web_interface_logs(_py: Python<'_>, _enabled: bool) -> PyResult<()> {
    Ok(())
}

#[pyfunction]
#[pyo3(signature = (level, source, message, keep_log=true, call_notifiers=true))]
pub fn add_log(
    py: Python<'_>,
    level: i32,
    source: &str,
    message: &str,
    keep_log: bool,
    call_notifiers: bool,
) -> PyResult<()> {
    if keep_log {
        let db = get_logs_database(py)?;
        let db_bound = db.bind(py);
        let log_list = db_bound.get_item("log_db")?.unwrap();
        let log_list = log_list.cast::<PyList>()?;
        if log_list.len() >= LOGS_MAX_COUNT {
            log_list.del_item(0)?;
        }
        let entry = PyDict::new(py);
        entry.set_item("source", source)?;
        entry.set_item("message", message)?;
        entry.set_item("level", level)?;
        log_list.append(entry)?;
    }
    if call_notifiers && level >= 40 {
        let module = py.import("octobot_commons_rs._core")?;
        if let Ok(callbacks) = module.getattr("_error_notifier_callbacks") {
            if let Ok(list) = callbacks.cast::<PyList>() {
                for cb in list.iter() {
                    let _ = cb.call0();
                }
            }
        }
    }
    Ok(())
}

pub fn register(m: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {
    let py = m.py();

    // Initialize global state
    m.add("_logs_database", {
        let db = PyDict::new(py);
        db.set_item("log_db", PyList::empty(py))?;
        db.set_item("log_new_errors_count", 0)?;
        db.set_item("log_backtesting_errors_count", 0)?;
        db
    })?;
    m.add("_error_notifier_callbacks", PyList::empty(py))?;
    m.add("LOGS_MAX_COUNT", LOGS_MAX_COUNT)?;

    m.add_class::<BotLogger>()?;
    m.add_function(wrap_pyfunction!(get_logger, m)?)?;
    m.add_function(wrap_pyfunction!(set_global_logger_level, m)?)?;
    m.add_function(wrap_pyfunction!(get_global_logger_level, m)?)?;
    m.add_function(wrap_pyfunction!(get_logger_level_per_handler, m)?)?;
    m.add_function(wrap_pyfunction!(set_logging_level, m)?)?;
    m.add_function(wrap_pyfunction!(get_errors_count, m)?)?;
    m.add_function(wrap_pyfunction!(reset_errors_count, m)?)?;
    m.add_function(wrap_pyfunction!(get_backtesting_errors_count, m)?)?;
    m.add_function(wrap_pyfunction!(reset_backtesting_errors, m)?)?;
    m.add_function(wrap_pyfunction!(register_error_notifier, m)?)?;
    m.add_function(wrap_pyfunction!(register_log_callback, m)?)?;
    m.add_function(wrap_pyfunction!(set_error_publication_enabled, m)?)?;
    m.add_function(wrap_pyfunction!(set_enable_web_interface_logs, m)?)?;
    m.add_function(wrap_pyfunction!(add_log, m)?)?;
    Ok(())
}
