use octobot_commons::list_util::*;

#[test]
fn test_flatten_list_i32() {
    let input = vec![vec![1, 2, 3], vec![4, 5, 6], vec![7, 8]];
    assert_eq!(flatten_list(input), vec![1, 2, 3, 4, 5, 6, 7, 8]);
}

#[test]
fn test_flatten_list_string() {
    let input = vec![
        vec!["a".to_string(), "b".to_string(), "c".to_string()],
        vec!["d".to_string(), "e".to_string()],
    ];
    assert_eq!(
        flatten_list(input),
        vec!["a", "b", "c", "d", "e"]
            .into_iter()
            .map(String::from)
            .collect::<Vec<String>>()
    );
}

#[test]
fn test_flatten_list_empty() {
    let input: Vec<Vec<i32>> = vec![];
    let expected: Vec<i32> = vec![];
    assert_eq!(flatten_list(input), expected);
}

#[test]
fn test_flatten_list_single_inner() {
    let input = vec![vec![42]];
    assert_eq!(flatten_list(input), vec![42]);
}

#[test]
fn test_deduplicate_integers() {
    let input = vec![1, 2, 3, 1, 2, 5];
    let result = deduplicate(&input);
    assert_eq!(result.len(), 4);
    assert!(result.contains(&1));
    assert!(result.contains(&2));
    assert!(result.contains(&3));
    assert!(result.contains(&5));
}

#[test]
fn test_deduplicate_strings() {
    let input = vec![
        "a".to_string(),
        "b".to_string(),
        "a".to_string(),
        "c".to_string(),
        "b".to_string(),
    ];
    let result = deduplicate(&input);
    assert_eq!(result.len(), 3);
    assert!(result.contains(&"a".to_string()));
    assert!(result.contains(&"b".to_string()));
    assert!(result.contains(&"c".to_string()));
}

#[test]
fn test_deduplicate_empty() {
    let input: Vec<i32> = vec![];
    assert_eq!(deduplicate(&input), Vec::<i32>::new());
}

#[test]
fn test_deduplicate_no_duplicates() {
    let input = vec![1, 2, 3, 4, 5];
    let mut result = deduplicate(&input);
    result.sort();
    assert_eq!(result, vec![1, 2, 3, 4, 5]);
}

#[test]
fn test_deduplicate_all_same() {
    let input = vec![7, 7, 7, 7];
    assert_eq!(deduplicate(&input), vec![7]);
}
