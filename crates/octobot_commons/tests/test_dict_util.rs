use octobot_commons::dict_util::*;
use serde_json::json;

#[test]
fn test_find_nested_value() {
    assert_eq!(
        find_nested_value(&json!({"a": 1, "b": 2}), "b", &[]),
        Some(json!(2))
    );
    assert_eq!(
        find_nested_value(&json!({"a": 1, "b": 2}), "c", &[]),
        None
    );
    assert_eq!(
        find_nested_value(&json!({"a": 1, "b": {"c": 5, "d": "e"}}), "d", &[]),
        Some(json!("e"))
    );
    assert_eq!(
        find_nested_value(
            &json!({"a": 1, "b": {"c": 5, "d": {"f": [1, 2, 3]}}}),
            "f",
            &[]
        ),
        Some(json!([1, 2, 3]))
    );
    assert_eq!(
        find_nested_value(
            &json!({"a": {"e": 7}, "b": {"c": {"t": 5}, "d": {"f": [1, 2, 3], "y": 1}}}),
            "y",
            &[]
        ),
        Some(json!(1))
    );

    let complex_dict = json!({
        "a": {"e": 7},
        "b": {
            "c": {
                "t": [
                    {
                        "ab": [8, 9, 10],
                        "cd": {
                            "4": 4,
                            "5": 5,
                            "6": [7, 8, 9, {"abc": "def", "zyx": "zxv"}]
                        }
                    },
                    {"up": "pa", "123": 1234}
                ]
            },
            "d": {"f": [1, 2, 3], "y": 1}
        }
    });
    assert_eq!(
        find_nested_value(&complex_dict, "abc", &[]),
        Some(json!("def"))
    );
    assert_eq!(
        find_nested_value(&complex_dict, "5", &[]),
        Some(json!(5))
    );
    assert_eq!(
        find_nested_value(&complex_dict, "123", &[]),
        Some(json!(1234))
    );
}

#[test]
fn test_check_and_merge_values_from_reference() {
    let mut current_dict = json!({"b": 5, "d": 1});
    let ref_dict = json!({"a": 1, "b": 2, "c": 3, "d": 4});
    let exception_list = vec!["d"];
    check_and_merge_values_from_reference(&mut current_dict, &ref_dict, &exception_list, None);
    assert_eq!(current_dict, json!({"a": 1, "b": 5, "c": 3, "d": 1}));
}

#[test]
fn test_contains_each_element() {
    assert!(contains_each_element(&json!({}), &json!({})));
    assert!(!contains_each_element(&json!({}), &json!({"1": 1})));
    assert!(contains_each_element(&json!({"1": 1}), &json!({"1": 1})));
    assert!(contains_each_element(&json!({"1": 1, "2": 2}), &json!({"1": 1})));
    assert!(!contains_each_element(&json!({"1": 1}), &json!({"1": 1, "2": 2})));
    assert!(contains_each_element(&json!({"1": 1}), &json!({})));
    assert!(!contains_each_element(&json!({"1": 2}), &json!({"1": 1})));
}

#[test]
fn test_nested_update_dict() {
    let mut base = json!({});
    nested_update_dict(&mut base, &json!({"1": 1, "2": 2}), &[], false);
    assert_eq!(base, json!({"1": 1, "2": 2}));

    let mut base = json!({"1": "aa"});
    nested_update_dict(&mut base, &json!({"1": 1, "2": 2}), &[], false);
    assert_eq!(base, json!({"1": 1, "2": 2}));

    let mut base = json!({"1": []});
    nested_update_dict(&mut base, &json!({"1": 1, "2": 2}), &[], false);
    assert_eq!(base, json!({"1": 1, "2": 2}));

    // ignore_lists=true: existing list values are preserved
    let mut base = json!({"1": []});
    nested_update_dict(&mut base, &json!({"1": 1, "2": 2}), &[], true);
    assert_eq!(base, json!({"1": [], "2": 2}));

    // nested dict with ignore_lists=true
    let mut base = json!({
        "1": [],
        "plop": {"jerome": 0, "michel": 1, "monique": [1]}
    });
    nested_update_dict(
        &mut base,
        &json!({
            "1": 1,
            "2": 2,
            "plop": {"jerome": 0.5, "simon": 3, "monique": [2]}
        }),
        &[],
        true,
    );
    assert_eq!(
        base,
        json!({
            "1": [],
            "2": 2,
            "plop": {"jerome": 0.5, "michel": 1, "monique": [1], "simon": 3}
        })
    );

    // nested dict with ignore_lists=false
    let mut base = json!({
        "1": [],
        "plop": {"jerome": 0, "michel": 1, "monique": [1]}
    });
    nested_update_dict(
        &mut base,
        &json!({
            "1": 1,
            "2": 2,
            "plop": {"jerome": 0.5, "simon": 3, "monique": [2]}
        }),
        &[],
        false,
    );
    assert_eq!(
        base,
        json!({
            "1": 1,
            "2": 2,
            "plop": {"jerome": 0.5, "michel": 1, "monique": [2], "simon": 3}
        })
    );
}
