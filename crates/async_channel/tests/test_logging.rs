use async_channel::util::logging::{get_logger_name, get_logger};

#[test]
fn test_get_logger_name() {
    assert_eq!(get_logger_name("Consumer"), "async_channel::Consumer");
    assert_eq!(get_logger_name(""), "async_channel");
}

#[test]
fn test_get_logger() {
    assert_eq!(get_logger("Producer"), "async_channel::Producer");
    assert_eq!(get_logger(""), "async_channel");
    assert_eq!(get_logger("Foo"), get_logger_name("Foo"));
}
