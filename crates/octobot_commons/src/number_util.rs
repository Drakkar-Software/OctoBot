pub fn round_into_str_with_max_digits(number: f64, digits_count: usize) -> String {
    let rounded = (number * 10f64.powi(digits_count as i32)).round() / 10f64.powi(digits_count as i32);
    format!("{:.prec$}", rounded, prec = digits_count)
}

pub fn round_into_float_with_max_digits(number: f64, digits_count: usize) -> f64 {
    round_into_str_with_max_digits(number, digits_count)
        .parse()
        .unwrap_or(number)
}

pub fn get_digits_count(value: f64) -> i64 {
    value.log10().abs().round() as i64
}
