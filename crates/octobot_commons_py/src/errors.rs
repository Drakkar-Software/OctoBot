use pyo3::prelude::*;

// Base exceptions
pyo3::create_exception!(octobot_commons_rs, ConfigError, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, RemoteConfigError, ConfigError);
pyo3::create_exception!(octobot_commons_rs, NoProfileError, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, ProfileConflictError, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, ProfileRemovalError, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, ProfileImportError, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, ProfileExportError, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, ProfileMigrationError, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, UninitializedProfile, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, NotSupported, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, MissingExchangeDataError, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, MissingSignalBuilder, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, TentaclesSetupError, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, DisplayTranslatorError, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, EncryptionDecryptionError, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, LogicalOperatorError, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, MissingDataError, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, NoBotDeviceError, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, OperationStoppedError, pyo3::exceptions::PyException);

// DSL interpreter errors
pyo3::create_exception!(octobot_commons_rs, DSLInterpreterError, pyo3::exceptions::PyException);
pyo3::create_exception!(octobot_commons_rs, UnsupportedOperatorError, DSLInterpreterError);
pyo3::create_exception!(octobot_commons_rs, InvalidParametersError, DSLInterpreterError);
pyo3::create_exception!(octobot_commons_rs, MissingDefaultValueError, InvalidParametersError);
pyo3::create_exception!(octobot_commons_rs, InvalidFormatError, InvalidParametersError);
pyo3::create_exception!(octobot_commons_rs, ResolvedParameterNotFoundError, DSLInterpreterError);
pyo3::create_exception!(octobot_commons_rs, ErrorStatementError, DSLInterpreterError);

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let py = m.py();
    m.add("ConfigError", py.get_type::<ConfigError>())?;
    m.add("RemoteConfigError", py.get_type::<RemoteConfigError>())?;
    m.add("NoProfileError", py.get_type::<NoProfileError>())?;
    m.add("ProfileConflictError", py.get_type::<ProfileConflictError>())?;
    m.add("ProfileRemovalError", py.get_type::<ProfileRemovalError>())?;
    m.add("ProfileImportError", py.get_type::<ProfileImportError>())?;
    m.add("ProfileExportError", py.get_type::<ProfileExportError>())?;
    m.add("ProfileMigrationError", py.get_type::<ProfileMigrationError>())?;
    m.add("UninitializedProfile", py.get_type::<UninitializedProfile>())?;
    m.add("NotSupported", py.get_type::<NotSupported>())?;
    m.add("MissingExchangeDataError", py.get_type::<MissingExchangeDataError>())?;
    m.add("MissingSignalBuilder", py.get_type::<MissingSignalBuilder>())?;
    m.add("TentaclesSetupError", py.get_type::<TentaclesSetupError>())?;
    m.add("DisplayTranslatorError", py.get_type::<DisplayTranslatorError>())?;
    m.add("EncryptionDecryptionError", py.get_type::<EncryptionDecryptionError>())?;
    m.add("LogicalOperatorError", py.get_type::<LogicalOperatorError>())?;
    m.add("MissingDataError", py.get_type::<MissingDataError>())?;
    m.add("NoBotDeviceError", py.get_type::<NoBotDeviceError>())?;
    m.add("OperationStoppedError", py.get_type::<OperationStoppedError>())?;
    m.add("DSLInterpreterError", py.get_type::<DSLInterpreterError>())?;
    m.add("UnsupportedOperatorError", py.get_type::<UnsupportedOperatorError>())?;
    m.add("InvalidParametersError", py.get_type::<InvalidParametersError>())?;
    m.add("MissingDefaultValueError", py.get_type::<MissingDefaultValueError>())?;
    m.add("InvalidFormatError", py.get_type::<InvalidFormatError>())?;
    m.add("ResolvedParameterNotFoundError", py.get_type::<ResolvedParameterNotFoundError>())?;
    m.add("ErrorStatementError", py.get_type::<ErrorStatementError>())?;
    Ok(())
}
