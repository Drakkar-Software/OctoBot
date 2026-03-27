use poc_core::greeting::{greet, add, fibonacci, VERSION};

#[test]
fn test_version() {
    assert_eq!(VERSION, "0.1.0");
}

#[test]
fn test_greet() {
    assert_eq!(greet("World"), "Hello, World!");
    assert_eq!(greet(""), "Hello, !");
    assert_eq!(greet("OctoBot"), "Hello, OctoBot!");
}

#[test]
fn test_add() {
    assert_eq!(add(2, 3), 5);
    assert_eq!(add(-1, 1), 0);
    assert_eq!(add(0, 0), 0);
    assert_eq!(add(i64::MAX, 0), i64::MAX);
}

#[test]
fn test_fibonacci() {
    assert_eq!(fibonacci(0), 0);
    assert_eq!(fibonacci(1), 1);
    assert_eq!(fibonacci(2), 1);
    assert_eq!(fibonacci(10), 55);
    assert_eq!(fibonacci(20), 6765);
    assert_eq!(fibonacci(50), 12586269025);
}
