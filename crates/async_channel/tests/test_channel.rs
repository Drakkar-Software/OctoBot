use std::collections::HashMap;

use async_channel::channels::channel::{Channel, ConsumerEntry, FilterValue, check_filters};
use async_channel::enums::ChannelConsumerPriorityLevels;
use async_channel::constants::CHANNEL_WILDCARD;

// ── Channel basics ───────────────────────────────────────────────────

#[test]
fn test_channel_new() {
    let ch = Channel::new("Test");
    assert_eq!(ch.name, "Test");
    assert!(ch.is_paused);
    assert!(!ch.is_synchronized);
}

#[test]
fn test_derive_name() {
    assert_eq!(Channel::derive_name("TestChannel"), "Test");
    assert_eq!(Channel::derive_name("FooBar"), "FooBar");
}

// ── Consumer management ──────────────────────────────────────────────

#[test]
fn test_add_remove_consumer() {
    let mut ch = Channel::new("T");
    ch.add_consumer(ConsumerEntry { priority_level: 0, filters: HashMap::new() });
    assert_eq!(ch.consumer_count(), 1);
    ch.remove_consumer(0);
    assert_eq!(ch.consumer_count(), 0);
}

#[test]
fn test_get_consumers_count() {
    let mut ch = Channel::new("T");
    assert_eq!(ch.get_consumers_count(), 0);
    ch.add_consumer(ConsumerEntry { priority_level: 0, filters: HashMap::new() });
    assert_eq!(ch.get_consumers_count(), 1);
}

#[test]
fn test_prioritized_consumers() {
    let mut ch = Channel::new("T");
    ch.add_consumer(ConsumerEntry { priority_level: 0, filters: HashMap::new() });
    ch.add_consumer(ConsumerEntry { priority_level: 2, filters: HashMap::new() });
    ch.add_consumer(ConsumerEntry { priority_level: 1, filters: HashMap::new() });
    assert_eq!(ch.get_prioritized_consumer_indices(1), vec![0, 2]);
}

// ── Producer management ──────────────────────────────────────────────

#[test]
fn test_unregister_producer() {
    let mut ch = Channel::new("T");
    assert_eq!(ch.producer_count(), 0);
    ch.register_producer();
    ch.register_producer();
    assert_eq!(ch.producer_count(), 2);
    ch.unregister_producer();
    assert_eq!(ch.producer_count(), 1);
    ch.unregister_producer();
    assert_eq!(ch.producer_count(), 0);
    ch.unregister_producer();
    assert_eq!(ch.producer_count(), 0);
}

#[test]
fn test_set_internal_producer() {
    let mut ch = Channel::new("T");
    assert!(!ch.has_internal_producer());
    ch.set_internal_producer();
    assert!(ch.has_internal_producer());
    ch.set_internal_producer();
    assert!(ch.has_internal_producer());
}

#[test]
fn test_get_internal_producer_or_create() {
    let mut ch = Channel::new("T");
    assert!(!ch.get_internal_producer_or_create());
    assert!(ch.has_internal_producer());
    assert!(ch.get_internal_producer_or_create());
}

#[test]
fn test_flush_noop() {
    let mut ch = Channel::new("T");
    ch.flush();
}

// ── Filter matching (check_filters) ──────────────────────────────────

#[test]
fn test_check_filters_empty() {
    assert!(check_filters(&HashMap::new(), &HashMap::new()));
}

#[test]
fn test_check_filters_match() {
    let mut cf = HashMap::new();
    cf.insert("k".into(), FilterValue::Single("v".into()));
    let mut ef = HashMap::new();
    ef.insert("k".into(), "v".into());
    assert!(check_filters(&cf, &ef));
}

#[test]
fn test_check_filters_wildcard() {
    let mut cf = HashMap::new();
    cf.insert("k".into(), FilterValue::Single(CHANNEL_WILDCARD.into()));
    let mut ef = HashMap::new();
    ef.insert("k".into(), "anything".into());
    assert!(check_filters(&cf, &ef));
}

#[test]
fn test_check_filters_no_match() {
    let mut cf = HashMap::new();
    cf.insert("k".into(), FilterValue::Single("v".into()));
    let mut ef = HashMap::new();
    ef.insert("k".into(), "other".into());
    assert!(!check_filters(&cf, &ef));
}

#[test]
fn test_check_filters_list() {
    let mut cf = HashMap::new();
    cf.insert("k".into(), FilterValue::List(vec!["a".into(), "b".into()]));
    let mut ef = HashMap::new();
    ef.insert("k".into(), "b".into());
    assert!(check_filters(&cf, &ef));
    ef.insert("k".into(), "c".into());
    assert!(!check_filters(&cf, &ef));
}

#[test]
fn test_get_filtered_consumer_indices() {
    let mut ch = Channel::new("T");

    let mut f0 = HashMap::new();
    f0.insert("symbol".into(), FilterValue::Single("BTC".into()));
    ch.add_consumer(ConsumerEntry { priority_level: 0, filters: f0 });

    let mut f1 = HashMap::new();
    f1.insert("symbol".into(), FilterValue::Single("ETH".into()));
    ch.add_consumer(ConsumerEntry { priority_level: 0, filters: f1 });

    let mut f2 = HashMap::new();
    f2.insert("symbol".into(), FilterValue::Single(CHANNEL_WILDCARD.into()));
    ch.add_consumer(ConsumerEntry { priority_level: 0, filters: f2 });

    let mut f3 = HashMap::new();
    f3.insert("symbol".into(), FilterValue::List(vec!["BTC".into(), "SOL".into()]));
    ch.add_consumer(ConsumerEntry { priority_level: 0, filters: f3 });

    let mut ef = HashMap::new();
    ef.insert("symbol".into(), "BTC".into());
    assert_eq!(ch.get_filtered_consumer_indices(&ef), vec![0, 2, 3]);

    ef.insert("symbol".into(), "ETH".into());
    assert_eq!(ch.get_filtered_consumer_indices(&ef), vec![1, 2]);

    ef.insert("symbol".into(), "DOGE".into());
    assert_eq!(ch.get_filtered_consumer_indices(&ef), vec![2]);

    let empty: HashMap<String, String> = HashMap::new();
    assert_eq!(ch.get_filtered_consumer_indices(&empty), vec![0, 1, 2, 3]);
}

/// Mirrors test_new_consumer_with_expected_wildcard_filters
#[test]
fn test_check_filters_with_expected_wildcard() {
    let wc = CHANNEL_WILDCARD;
    // Consumer has test_key=1, test_key_2=abc
    let mut cf = HashMap::new();
    cf.insert("test_key".into(), FilterValue::Single("1".into()));
    cf.insert("test_key_2".into(), FilterValue::Single("abc".into()));

    // Exact match
    let mut ef = HashMap::new();
    ef.insert("test_key".into(), "1".into());
    ef.insert("test_key_2".into(), "abc".into());
    assert!(check_filters(&cf, &ef));

    // Extra key not present → no match
    ef.insert("test_key_3".into(), "45".into());
    assert!(!check_filters(&cf, &ef));

    // Extra key with wildcard → match (wildcard in expected means "don't care")
    ef.insert("test_key_3".into(), wc.into());
    assert!(check_filters(&cf, &ef));

    // Wrong value for key → no match
    let mut ef2 = HashMap::new();
    ef2.insert("test_key".into(), "4".into());
    ef2.insert("test_key_2".into(), "bc".into());
    assert!(!check_filters(&cf, &ef2));

    // Wildcard in expected for test_key_2 → match if test_key matches
    let mut ef3 = HashMap::new();
    ef3.insert("test_key".into(), "1".into());
    ef3.insert("test_key_2".into(), wc.into());
    assert!(check_filters(&cf, &ef3));

    // Wildcard in expected for test_key → match if test_key_2 matches
    let mut ef4 = HashMap::new();
    ef4.insert("test_key".into(), wc.into());
    ef4.insert("test_key_2".into(), "abc".into());
    assert!(check_filters(&cf, &ef4));

    // Both wildcards → match
    let mut ef5 = HashMap::new();
    ef5.insert("test_key".into(), wc.into());
    ef5.insert("test_key_2".into(), wc.into());
    assert!(check_filters(&cf, &ef5));
}

/// Mirrors test_new_consumer_with_consumer_wildcard_filters
#[test]
fn test_check_filters_with_consumer_wildcard() {
    let wc = CHANNEL_WILDCARD;
    // Consumer has test_key=1, test_key_2=abc, test_key_3=*
    let mut cf = HashMap::new();
    cf.insert("test_key".into(), FilterValue::Single("1".into()));
    cf.insert("test_key_2".into(), FilterValue::Single("abc".into()));
    cf.insert("test_key_3".into(), FilterValue::Single(wc.into()));

    // Match on first two keys
    let mut ef = HashMap::new();
    ef.insert("test_key".into(), "1".into());
    ef.insert("test_key_2".into(), "abc".into());
    assert!(check_filters(&cf, &ef));

    // test_key_3 with any value → match (consumer has wildcard)
    ef.insert("test_key_3".into(), "45".into());
    assert!(check_filters(&cf, &ef));

    // Just test_key → match
    let mut ef2 = HashMap::new();
    ef2.insert("test_key".into(), "1".into());
    assert!(check_filters(&cf, &ef2));

    // test_key_3 with any value alone → match (consumer wildcard)
    let mut ef3 = HashMap::new();
    ef3.insert("test_key_3".into(), "e".into());
    assert!(check_filters(&cf, &ef3));

    // Wrong test_key, wildcard test_key_2 → no match
    let mut ef4 = HashMap::new();
    ef4.insert("test_key".into(), "3".into());
    ef4.insert("test_key_2".into(), wc.into());
    assert!(!check_filters(&cf, &ef4));

    // Wildcard expected test_key, wrong test_key_2 → no match
    let mut ef5 = HashMap::new();
    ef5.insert("test_key".into(), wc.into());
    ef5.insert("test_key_2".into(), "a".into());
    assert!(!check_filters(&cf, &ef5));
}

/// Mirrors test_new_consumer_with_multiple_consumer_filtering
/// Tests get_filtered_consumer_indices with 23 consumers and various filter combos.
#[test]
fn test_check_filters_multiple_consumers() {
    let wc = CHANNEL_WILDCARD.to_string();
    let mut ch = Channel::new("T");

    // Helper to build filter maps
    fn s(v: &str) -> FilterValue { FilterValue::Single(v.to_string()) }
    fn l(v: &[&str]) -> FilterValue { FilterValue::List(v.iter().map(|x| x.to_string()).collect()) }

    let consumer_filters: Vec<HashMap<String, FilterValue>> = vec![
        // 0: A=1, B=2, C=*
        HashMap::from([("A".into(), s("1")), ("B".into(), s("2")), ("C".into(), s(&wc))]),
        // 1: A=False, B=BBBB, C=*
        HashMap::from([("A".into(), s("False")), ("B".into(), s("BBBB")), ("C".into(), s(&wc))]),
        // 2: A=3, B=*, C=*
        HashMap::from([("A".into(), s("3")), ("B".into(), s(&wc)), ("C".into(), s(&wc))]),
        // 3: A=*, B=*, C=*
        HashMap::from([("A".into(), s(&wc)), ("B".into(), s(&wc)), ("C".into(), s(&wc))]),
        // 4: A=*, B=2, C=1
        HashMap::from([("A".into(), s(&wc)), ("B".into(), s("2")), ("C".into(), s("1"))]),
        // 5: A=True, B=*, C=*
        HashMap::from([("A".into(), s("True")), ("B".into(), s(&wc)), ("C".into(), s(&wc))]),
        // 6: A=None, B=None, C=*
        HashMap::from([("A".into(), s("None")), ("B".into(), s("None")), ("C".into(), s(&wc))]),
        // 7: A=PPP, B=1, C=*, D=5
        HashMap::from([("A".into(), s("PPP")), ("B".into(), s("1")), ("C".into(), s(&wc)), ("D".into(), s("5"))]),
        // 8: A=*, B=2, C=ABC
        HashMap::from([("A".into(), s(&wc)), ("B".into(), s("2")), ("C".into(), s("ABC"))]),
        // 9: A=*, B=True, C=*
        HashMap::from([("A".into(), s(&wc)), ("B".into(), s("True")), ("C".into(), s(&wc))]),
        // 10: A=*, B=6, C=*, D=*
        HashMap::from([("A".into(), s(&wc)), ("B".into(), s("6")), ("C".into(), s(&wc)), ("D".into(), s(&wc))]),
        // 11: A=*, B=*, C=*, D=*
        HashMap::from([("A".into(), s(&wc)), ("B".into(), s(&wc)), ("C".into(), s(&wc)), ("D".into(), s(&wc))]),
        // 12: A=None, B=False, C=LLLL, D=*
        HashMap::from([("A".into(), s("None")), ("B".into(), s("False")), ("C".into(), s("LLLL")), ("D".into(), s(&wc))]),
        // 13: A=None, B=None, C=*, D=None
        HashMap::from([("A".into(), s("None")), ("B".into(), s("None")), ("C".into(), s(&wc)), ("D".into(), s("None"))]),
        // 14: A=*, B=2, C=*, D=None
        HashMap::from([("A".into(), s(&wc)), ("B".into(), s("2")), ("C".into(), s(&wc)), ("D".into(), s("None"))]),
        // 15: A=*, B=[2,3,4,5,6], C=*, D=None
        HashMap::from([("A".into(), s(&wc)), ("B".into(), l(&["2","3","4","5","6"])), ("C".into(), s(&wc)), ("D".into(), s("None"))]),
        // 16: A=*, B=[A,5,G], C=*, D=None
        HashMap::from([("A".into(), s(&wc)), ("B".into(), l(&["A","5","G"])), ("C".into(), s(&wc)), ("D".into(), s("None"))]),
        // 17: A=[1,2,3], B=2, C=*, D=*
        HashMap::from([("A".into(), l(&["1","2","3"])), ("B".into(), s("2")), ("C".into(), s(&wc)), ("D".into(), s(&wc))]),
        // 18: A=[A,B,C], B=2, C=*, D=*
        HashMap::from([("A".into(), l(&["A","B","C"])), ("B".into(), s("2")), ("C".into(), s(&wc)), ("D".into(), s(&wc))]),
        // 19: A=*, B=[2], C=*, D=*
        HashMap::from([("A".into(), s(&wc)), ("B".into(), l(&["2"])), ("C".into(), s(&wc)), ("D".into(), s(&wc))]),
        // 20: A=*, B=[B], C=*, D=*
        HashMap::from([("A".into(), s(&wc)), ("B".into(), l(&["B"])), ("C".into(), s(&wc)), ("D".into(), s(&wc))]),
        // 21: A=18, B=[A,B,C], C=[---,9,#], D=*
        HashMap::from([("A".into(), s("18")), ("B".into(), l(&["A","B","C"])), ("C".into(), l(&["---","9","#"])), ("D".into(), s(&wc))]),
        // 22: A=[9,18], B=[B,C,D], C=[---,9,#,@,{], D=[P,__str__]
        HashMap::from([("A".into(), l(&["9","18"])), ("B".into(), l(&["B","C","D"])), ("C".into(), l(&["---","9","#","@","{"])), ("D".into(), l(&["P","__str__"]))]),
    ];

    for f in &consumer_filters {
        ch.add_consumer(ConsumerEntry { priority_level: 0, filters: f.clone() });
    }

    // Empty filter → all match
    let empty: HashMap<String, String> = HashMap::new();
    assert_eq!(ch.get_filtered_consumer_indices(&empty).len(), 23);

    // A=18, B=A, C=# → 3, 11, 16, 21
    let mut ef = HashMap::new();
    ef.insert("A".into(), "18".into());
    ef.insert("B".into(), "A".into());
    ef.insert("C".into(), "#".into());
    assert_eq!(ch.get_filtered_consumer_indices(&ef), vec![3, 11, 16, 21]);

    // A=18, B=C, C=#, D=None → 11, 21
    let mut ef2 = HashMap::new();
    ef2.insert("A".into(), "18".into());
    ef2.insert("B".into(), "C".into());
    ef2.insert("C".into(), "#".into());
    ef2.insert("D".into(), "None".into());
    assert_eq!(ch.get_filtered_consumer_indices(&ef2), vec![11, 21]);

    // A=18, B=C, C=^, D=None → 11 only (^ not in any list)
    let mut ef3 = HashMap::new();
    ef3.insert("A".into(), "18".into());
    ef3.insert("B".into(), "C".into());
    ef3.insert("C".into(), "^".into());
    ef3.insert("D".into(), "None".into());
    assert_eq!(ch.get_filtered_consumer_indices(&ef3), vec![11]);

    // A=18, B=C, C=#, D=__str__ → 11, 21, 22
    let mut ef4 = HashMap::new();
    ef4.insert("A".into(), "18".into());
    ef4.insert("B".into(), "C".into());
    ef4.insert("C".into(), "#".into());
    ef4.insert("D".into(), "__str__".into());
    assert_eq!(ch.get_filtered_consumer_indices(&ef4), vec![11, 21, 22]);
}

// ── Pause/resume logic ───────────────────────────────────────────────

#[test]
fn test_should_pause_with_no_consumers() {
    let mut ch = Channel::new("T");
    ch.is_paused = false;
    assert!(ch.should_pause_producers());
}

#[test]
fn test_should_pause_when_already_paused() {
    let ch = Channel::new("T"); // is_paused = true by default
    assert!(!ch.should_pause_producers());
}

/// Mirrors test_should_pause_producers_with_priority_consumers
#[test]
fn test_should_pause_with_priority_consumers() {
    let mut ch = Channel::new("T");
    ch.is_paused = false;
    ch.add_consumer(ConsumerEntry {
        priority_level: ChannelConsumerPriorityLevels::High.value(),
        filters: HashMap::new(),
    });
    ch.add_consumer(ConsumerEntry {
        priority_level: ChannelConsumerPriorityLevels::Medium.value(),
        filters: HashMap::new(),
    });
    ch.add_consumer(ConsumerEntry {
        priority_level: ChannelConsumerPriorityLevels::Optional.value(),
        filters: HashMap::new(),
    });
    // Should NOT pause because HIGH and MEDIUM consumers exist
    assert!(!ch.should_pause_producers());
}

/// Mirrors test_should_pause_producers_with_optional_consumers
#[test]
fn test_should_pause_with_optional_consumers() {
    let mut ch = Channel::new("T");
    ch.is_paused = false;
    for _ in 0..3 {
        ch.add_consumer(ConsumerEntry {
            priority_level: ChannelConsumerPriorityLevels::Optional.value(),
            filters: HashMap::new(),
        });
    }
    // Should pause: all consumers are OPTIONAL
    assert!(ch.should_pause_producers());
}

#[test]
fn test_should_resume_with_no_consumers() {
    let mut ch = Channel::new("T");
    ch.is_paused = true;
    assert!(!ch.should_resume_producers());
}

#[test]
fn test_should_resume_when_already_resumed() {
    let mut ch = Channel::new("T");
    ch.is_paused = false;
    ch.add_consumer(ConsumerEntry {
        priority_level: ChannelConsumerPriorityLevels::High.value(),
        filters: HashMap::new(),
    });
    assert!(!ch.should_resume_producers());
}

/// Mirrors test_should_resume_producers_with_priority_consumers
#[test]
fn test_should_resume_with_priority_consumers() {
    let mut ch = Channel::new("T");
    ch.is_paused = true;
    ch.add_consumer(ConsumerEntry {
        priority_level: ChannelConsumerPriorityLevels::High.value(),
        filters: HashMap::new(),
    });
    ch.add_consumer(ConsumerEntry {
        priority_level: ChannelConsumerPriorityLevels::Medium.value(),
        filters: HashMap::new(),
    });
    ch.add_consumer(ConsumerEntry {
        priority_level: ChannelConsumerPriorityLevels::Optional.value(),
        filters: HashMap::new(),
    });
    assert!(ch.should_resume_producers());
}

/// Mirrors test_should_resume_producers_with_optional_consumers
#[test]
fn test_should_resume_with_optional_consumers() {
    let mut ch = Channel::new("T");
    ch.is_paused = true;
    for _ in 0..3 {
        ch.add_consumer(ConsumerEntry {
            priority_level: ChannelConsumerPriorityLevels::Optional.value(),
            filters: HashMap::new(),
        });
    }
    assert!(!ch.should_resume_producers());
}

#[test]
fn test_should_pause_with_priorities() {
    assert!(!Channel::should_pause_with_priorities(true, &[0]));
    assert!(Channel::should_pause_with_priorities(false, &[]));
    let opt = ChannelConsumerPriorityLevels::Optional.value();
    assert!(Channel::should_pause_with_priorities(false, &[opt, opt + 1]));
    let high = ChannelConsumerPriorityLevels::High.value();
    assert!(!Channel::should_pause_with_priorities(false, &[high]));
    assert!(!Channel::should_pause_with_priorities(false, &[high, opt]));
}

#[test]
fn test_should_resume_with_priorities() {
    assert!(!Channel::should_resume_with_priorities(false, &[0]));
    assert!(!Channel::should_resume_with_priorities(true, &[]));
    let high = ChannelConsumerPriorityLevels::High.value();
    assert!(Channel::should_resume_with_priorities(true, &[high]));
    let opt = ChannelConsumerPriorityLevels::Optional.value();
    assert!(!Channel::should_resume_with_priorities(true, &[opt, opt + 1]));
    assert!(Channel::should_resume_with_priorities(true, &[high, opt]));
}

// ── Async orchestration ──────────────────────────────────────────────

#[tokio::test]
async fn test_check_producers_state_pause() {
    let mut ch = Channel::new("T");
    ch.is_paused = false;
    let mut paused = false;
    ch.check_producers_state(
        || async { paused = true; },
        || async {},
    )
    .await;
    assert!(paused);
    assert!(ch.is_paused);
}

#[tokio::test]
async fn test_check_producers_state_resume() {
    let mut ch = Channel::new("T");
    ch.is_paused = true;
    ch.add_consumer(ConsumerEntry {
        priority_level: ChannelConsumerPriorityLevels::High.value(),
        filters: HashMap::new(),
    });
    let mut resumed = false;
    ch.check_producers_state(
        || async {},
        || async { resumed = true; },
    )
    .await;
    assert!(resumed);
    assert!(!ch.is_paused);
}

#[tokio::test]
async fn test_for_each_async() {
    let mut called = Vec::new();
    Channel::for_each_async(3, |i| {
        called.push(i);
        async {}
    })
    .await;
    assert_eq!(called, vec![0, 1, 2]);
}

#[tokio::test]
async fn test_start_consumers() {
    let mut started = Vec::new();
    Channel::start_consumers(3, |i| {
        started.push(i);
        async {}
    })
    .await;
    assert_eq!(started, vec![0, 1, 2]);
}

#[tokio::test]
async fn test_stop_all() {
    let mut stopped = Vec::new();
    Channel::stop_all(2, 1, true, |i, kind| {
        stopped.push((i, kind));
        async {}
    })
    .await;
    assert_eq!(stopped, vec![(0, 0), (1, 0), (0, 1), (0, 2)]);
}

#[tokio::test]
async fn test_stop_all_no_internal() {
    let mut stopped = Vec::new();
    Channel::stop_all(1, 1, false, |i, kind| {
        stopped.push((i, kind));
        async {}
    })
    .await;
    assert_eq!(stopped, vec![(0, 0), (0, 1)]);
}

#[tokio::test]
async fn test_run_consumers() {
    let mut runs = Vec::new();
    Channel::run_consumers(2, false, |i, is_sync| {
        runs.push((i, is_sync));
        async {}
    })
    .await;
    assert_eq!(runs, vec![(0, false), (1, false)]);
}

#[tokio::test]
async fn test_run_consumers_synchronized() {
    let mut runs = Vec::new();
    Channel::run_consumers(2, true, |i, is_sync| {
        runs.push((i, is_sync));
        async {}
    })
    .await;
    assert_eq!(runs, vec![(0, true), (1, true)]);
}

#[tokio::test]
async fn test_modify_producers() {
    let mut modified = Vec::new();
    Channel::modify_producers(3, |i| {
        modified.push(i);
        async {}
    })
    .await;
    assert_eq!(modified, vec![0, 1, 2]);
}

#[tokio::test]
async fn test_register_producer_flow_paused() {
    let mut ch = Channel::new("T");
    let initial_count = ch.producer_count();
    let mut pause_called = false;
    ch.register_producer_flow(true, || async {
        pause_called = true;
    })
    .await;
    assert_eq!(ch.producer_count(), initial_count + 1);
    assert!(pause_called);
}

#[tokio::test]
async fn test_register_producer_flow_not_paused() {
    let mut ch = Channel::new("T");
    let mut pause_called = false;
    ch.register_producer_flow(false, || async {
        pause_called = true;
    })
    .await;
    assert_eq!(ch.producer_count(), 1);
    assert!(!pause_called);
}

#[tokio::test]
async fn test_new_consumer_flow() {
    let mut ch = Channel::new("T");
    let mut run_called = false;
    let mut check_called = false;
    let consumer = ch
        .new_consumer_flow(
            42u32,
            ConsumerEntry {
                priority_level: 0,
                filters: HashMap::new(),
            },
            || async {
                run_called = true;
            },
            || async {
                check_called = true;
            },
        )
        .await;
    assert_eq!(consumer, 42u32);
    assert!(run_called);
    assert!(check_called);
    assert_eq!(ch.consumer_count(), 1);
}
