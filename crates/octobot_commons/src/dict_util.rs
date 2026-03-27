use serde_json::Value;

/// Find a nested value in a JSON object.
///
/// Recursively searches through nested objects and arrays for `field`.
/// `list_indexes` optionally restricts which array element to descend into at
/// each nesting level (consumed left-to-right). When `list_indexes` is empty,
/// every element of every encountered array is explored.
///
/// Returns `Some(value)` when the field is found, `None` otherwise.
pub fn find_nested_value(dict: &Value, field: &str, list_indexes: &[usize]) -> Option<Value> {
    let obj = dict.as_object()?;
    if let Some(val) = obj.get(field) {
        return Some(val.clone());
    }
    for value in obj.values() {
        if value.is_object() {
            if let Some(found) = find_nested_value(value, field, list_indexes) {
                return Some(found);
            }
        } else if value.is_array() {
            if let Some(found) = _find_nested_value_in_list(value, field, list_indexes) {
                return Some(found);
            }
        }
    }
    None
}

/// Search through array elements for a nested field.
///
/// When `list_indexes` is non-empty the first element is used to pick a single
/// array entry and the remaining indexes are forwarded. Otherwise every element
/// is inspected.
fn _find_nested_value_in_list(list: &Value, field: &str, list_indexes: &[usize]) -> Option<Value> {
    let arr = list.as_array()?;
    if let Some((&first, rest)) = list_indexes.split_first() {
        if let Some(item) = arr.get(first) {
            if item.is_object() {
                if let Some(found) = find_nested_value(item, field, rest) {
                    return Some(found);
                }
            }
        }
    } else {
        for item in arr {
            if item.is_object() {
                if let Some(found) = find_nested_value(item, field, list_indexes) {
                    return Some(found);
                }
            }
        }
    }
    None
}

/// Recursively merge `updated` into `base`, keeping existing values in `base`
/// that are not present in `updated`.
///
/// When `base` is an array, every element of the array (or only the element at
/// `list_indexes[0]` when indexes are provided) is updated with `updated`.
/// Set `ignore_lists` to `true` to skip list values entirely.
pub fn nested_update_dict(
    base: &mut Value,
    updated: &Value,
    list_indexes: &[usize],
    ignore_lists: bool,
) {
    if let Some(base_arr) = base.as_array_mut() {
        if ignore_lists {
            return;
        }
        if let Some((&first, rest)) = list_indexes.split_first() {
            if let Some(element) = base_arr.get_mut(first) {
                nested_update_dict(element, updated, rest, ignore_lists);
            }
        } else {
            for element in base_arr.iter_mut() {
                nested_update_dict(element, updated, &[], false);
            }
        }
        return;
    }

    if let (Some(base_obj), Some(updated_obj)) = (base.as_object_mut(), updated.as_object()) {
        for (key, val) in updated_obj {
            if val.is_object() {
                if let Some(existing) = base_obj.get_mut(key) {
                    nested_update_dict(existing, val, list_indexes, ignore_lists);
                } else {
                    base_obj.insert(key.clone(), val.clone());
                }
            } else if ignore_lists
                && base_obj.get(key).is_some_and(|v| v.is_array())
            {
                // list should be ignored
            } else {
                base_obj.insert(key.clone(), val.clone());
            }
        }
    }
}

/// Merge missing keys from `reference` into `current`.
///
/// For every key present in `reference` but absent from `current`, the
/// reference value is inserted. When both sides contain an object for the same
/// key (and that key is not in `exception_list`), the merge recurses.
///
/// `log_fn`, when provided, is called with a descriptive message for every
/// key that is added.
pub fn check_and_merge_values_from_reference(
    current: &mut Value,
    reference: &Value,
    exception_list: &[&str],
    log_fn: Option<&dyn Fn(&str)>,
) {
    let (Some(current_obj), Some(reference_obj)) =
        (current.as_object_mut(), reference.as_object())
    else {
        return;
    };

    for (key, val) in reference_obj {
        if !current_obj.contains_key(key) {
            current_obj.insert(key.clone(), val.clone());
            if let Some(log) = log_fn {
                log(&format!(
                    "Missing {} in configuration, added default value: {}",
                    key, val
                ));
            }
        } else if val.is_object() && !exception_list.contains(&key.as_str()) {
            if let Some(current_child) = current_obj.get_mut(key) {
                check_and_merge_values_from_reference(
                    current_child,
                    val,
                    exception_list,
                    log_fn,
                );
            }
        }
    }
}

/// Return `true` when `element` (a JSON object) contains every key-value pair
/// from `expected`.
pub fn contains_each_element(element: &Value, expected: &Value) -> bool {
    let (Some(elem_obj), Some(expected_obj)) = (element.as_object(), expected.as_object()) else {
        return false;
    };
    for (key, val) in expected_obj {
        match elem_obj.get(key) {
            Some(existing) if existing == val => {}
            _ => return false,
        }
    }
    true
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    // -- find_nested_value -------------------------------------------------

    #[test]
    fn test_find_top_level() {
        let d = json!({"a": 1, "b": 2});
        assert_eq!(find_nested_value(&d, "a", &[]), Some(json!(1)));
    }

    #[test]
    fn test_find_nested_in_object() {
        let d = json!({"a": {"b": {"c": 42}}});
        assert_eq!(find_nested_value(&d, "c", &[]), Some(json!(42)));
    }

    #[test]
    fn test_find_nested_in_list() {
        let d = json!({"a": [{"x": 1}, {"y": 2}]});
        assert_eq!(find_nested_value(&d, "y", &[]), Some(json!(2)));
    }

    #[test]
    fn test_find_nested_with_list_indexes() {
        let d = json!({"a": [{"x": 1}, {"y": 2}]});
        // index 1 -> {"y": 2}
        assert_eq!(find_nested_value(&d, "y", &[1]), Some(json!(2)));
        // index 0 -> {"x": 1}, "y" not there
        assert_eq!(find_nested_value(&d, "y", &[0]), None);
    }

    #[test]
    fn test_find_not_found() {
        let d = json!({"a": 1});
        assert_eq!(find_nested_value(&d, "z", &[]), None);
    }

    // -- nested_update_dict ------------------------------------------------

    #[test]
    fn test_simple_merge() {
        let mut base = json!({"a": 1, "b": 2});
        let update = json!({"b": 3, "c": 4});
        nested_update_dict(&mut base, &update, &[], false);
        assert_eq!(base, json!({"a": 1, "b": 3, "c": 4}));
    }

    #[test]
    fn test_nested_merge() {
        let mut base = json!({"a": {"x": 1, "y": 2}});
        let update = json!({"a": {"y": 3, "z": 4}});
        nested_update_dict(&mut base, &update, &[], false);
        assert_eq!(base, json!({"a": {"x": 1, "y": 3, "z": 4}}));
    }

    #[test]
    fn test_merge_list_base() {
        let mut base = json!([{"a": 1}, {"a": 2}]);
        let update = json!({"b": 9});
        nested_update_dict(&mut base, &update, &[], false);
        assert_eq!(base, json!([{"a": 1, "b": 9}, {"a": 2, "b": 9}]));
    }

    #[test]
    fn test_merge_ignore_lists() {
        let mut base = json!({"a": [1, 2, 3], "b": 1});
        let update = json!({"a": [4, 5], "b": 2});
        nested_update_dict(&mut base, &update, &[], true);
        assert_eq!(base, json!({"a": [1, 2, 3], "b": 2}));
    }

    // -- check_and_merge_values_from_reference -----------------------------

    #[test]
    fn test_merge_missing_keys() {
        let mut current = json!({"a": 1});
        let reference = json!({"a": 1, "b": 2, "c": 3});
        check_and_merge_values_from_reference(&mut current, &reference, &[], None);
        assert_eq!(current, json!({"a": 1, "b": 2, "c": 3}));
    }

    #[test]
    fn test_merge_with_logging() {
        use std::cell::RefCell;
        let mut current = json!({"a": 1});
        let reference = json!({"a": 1, "b": 2});
        let logged = RefCell::new(Vec::new());
        let log_fn = |msg: &str| logged.borrow_mut().push(msg.to_string());
        check_and_merge_values_from_reference(
            &mut current,
            &reference,
            &[],
            Some(&log_fn),
        );
        assert_eq!(current, json!({"a": 1, "b": 2}));
        let logged = logged.into_inner();
        assert_eq!(logged.len(), 1);
        assert!(logged[0].contains("Missing b"));
    }

    #[test]
    fn test_merge_nested_with_exception() {
        let mut current = json!({"a": {"x": 1}, "b": {"y": 2}});
        let reference = json!({"a": {"x": 1, "z": 3}, "b": {"y": 2, "w": 4}});
        check_and_merge_values_from_reference(&mut current, &reference, &["b"], None);
        // "a" is recursed into, "b" is in exception list so not recursed
        assert_eq!(
            current,
            json!({"a": {"x": 1, "z": 3}, "b": {"y": 2}})
        );
    }

    // -- contains_each_element ---------------------------------------------

    #[test]
    fn test_contains_all() {
        let element = json!({"a": 1, "b": 2, "c": 3});
        let expected = json!({"a": 1, "c": 3});
        assert!(contains_each_element(&element, &expected));
    }

    #[test]
    fn test_contains_mismatch() {
        let element = json!({"a": 1, "b": 2});
        let expected = json!({"a": 99});
        assert!(!contains_each_element(&element, &expected));
    }

    #[test]
    fn test_contains_missing_key() {
        let element = json!({"a": 1});
        let expected = json!({"z": 1});
        assert!(!contains_each_element(&element, &expected));
    }

    #[test]
    fn test_contains_not_objects() {
        assert!(!contains_each_element(&json!(42), &json!({"a": 1})));
        assert!(!contains_each_element(&json!({"a": 1}), &json!(42)));
    }
}
