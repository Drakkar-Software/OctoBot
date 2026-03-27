use octobot_commons::errors::*;

#[test]
fn test_commons_error_no_profile_display() {
    let err = CommonsError::NoProfile("test".into());
    assert_eq!(format!("{err}"), "test");
}

#[test]
fn test_config_error_config_display() {
    let err = ConfigError::Config("bad config".into());
    assert_eq!(format!("{err}"), "bad config");
}

#[test]
fn test_config_error_remote_display() {
    let err = ConfigError::Remote("remote error".into());
    assert_eq!(format!("{err}"), "remote error");
}

#[test]
fn test_dsl_interpreter_error_unsupported_operator_display() {
    let err = DSLInterpreterError::UnsupportedOperator("op".into());
    assert_eq!(format!("{err}"), "op");
}

#[test]
fn test_invalid_parameters_error_missing_default_value_display() {
    let err = InvalidParametersError::MissingDefaultValue("x".into());
    assert_eq!(format!("{err}"), "x");
}

#[test]
fn test_commons_error_from_config_error() {
    let cfg_err = ConfigError::Config("cfg".into());
    let commons_err = CommonsError::from(cfg_err);
    assert_eq!(format!("{commons_err}"), "cfg");
}

#[test]
fn test_commons_error_from_dsl_interpreter_error() {
    let dsl_err = DSLInterpreterError::Base("dsl".into());
    let commons_err = CommonsError::from(dsl_err);
    assert_eq!(format!("{commons_err}"), "dsl");
}
