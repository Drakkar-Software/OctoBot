use std::collections::HashSet;
use std::hash::Hash;

pub fn flatten_list<T>(list_to_flatten: Vec<Vec<T>>) -> Vec<T> {
    list_to_flatten.into_iter().flatten().collect()
}

pub fn deduplicate<T: Eq + Hash + Clone>(elements: &[T]) -> Vec<T> {
    let mut seen = HashSet::new();
    elements
        .iter()
        .filter(|x| seen.insert((*x).clone()))
        .cloned()
        .collect()
}
