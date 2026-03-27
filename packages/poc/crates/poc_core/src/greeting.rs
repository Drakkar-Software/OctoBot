pub const VERSION: &str = "0.1.0";

pub fn greet(name: &str) -> String {
    format!("Hello, {name}!")
}

pub fn add(a: i64, b: i64) -> i64 {
    a + b
}

pub fn fibonacci(n: u32) -> u64 {
    if n <= 1 {
        return n as u64;
    }
    let (mut a, mut b) = (0u64, 1u64);
    for _ in 2..=n {
        let tmp = a + b;
        a = b;
        b = tmp;
    }
    b
}
