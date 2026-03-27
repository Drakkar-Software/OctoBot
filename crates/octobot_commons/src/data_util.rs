pub fn mean(number_list: &[f64]) -> f64 {
    if number_list.is_empty() {
        return 0.0;
    }
    number_list.iter().sum::<f64>() / number_list.len() as f64
}
