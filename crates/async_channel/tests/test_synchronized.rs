use async_channel::producer::{Producer, SyncConsumerHandle};

// ── drain_queue ──────────────────────────────────────────────────────

#[tokio::test]
async fn test_drain_queue() {
    let items = std::cell::RefCell::new(vec![3, 2, 1]);
    let mut performed = Vec::new();
    Producer::drain_queue(
        || {
            let empty = items.borrow().is_empty();
            async move { empty }
        },
        || {
            let item = items.borrow_mut().pop();
            async move { item }
        },
        |val| {
            performed.push(val);
            async {}
        },
    )
    .await;
    assert_eq!(performed, vec![1, 2, 3]);
}

#[tokio::test]
async fn test_drain_queue_empty() {
    let mut performed = Vec::new();
    Producer::drain_queue::<i32, _, _, _, _, _, _>(
        || async { true },
        || async { None },
        |val| {
            performed.push(val);
            async {}
        },
    )
    .await;
    assert!(performed.is_empty());
}

// ── synchronized_perform ─────────────────────────────────────────────

#[tokio::test]
async fn test_synchronized_perform_with_join() {
    let consumers = vec![
        SyncConsumerHandle { index: 0 },
        SyncConsumerHandle { index: 1 },
        SyncConsumerHandle { index: 2 },
    ];
    let mut drained = Vec::new();
    let mut joined = Vec::new();
    Producer::synchronized_perform(
        &consumers,
        true,
        5.0,
        |i| {
            drained.push(i);
            async {}
        },
        |i, t| {
            joined.push((i, t));
            async {}
        },
    )
    .await;
    assert_eq!(drained, vec![0, 1, 2]);
    assert_eq!(joined, vec![(0, 5.0), (1, 5.0), (2, 5.0)]);
}

#[tokio::test]
async fn test_synchronized_perform_no_join() {
    let consumers = vec![
        SyncConsumerHandle { index: 0 },
        SyncConsumerHandle { index: 1 },
    ];
    let mut drained = Vec::new();
    let mut joined = Vec::new();
    Producer::synchronized_perform(
        &consumers,
        false,
        1.0,
        |i| {
            drained.push(i);
            async {}
        },
        |i, t| {
            joined.push((i, t));
            async {}
        },
    )
    .await;
    assert_eq!(drained, vec![0, 1]);
    assert!(joined.is_empty());
}

/// Mirrors test_producer_synchronized_perform_consumers_queue_with_one_consumer
#[tokio::test]
async fn test_synchronized_perform_with_one_consumer() {
    let consumers = vec![SyncConsumerHandle { index: 0 }];
    let mut drain_called = false;
    let mut join_called = false;
    Producer::synchronized_perform(
        &consumers,
        true,
        1.0,
        |_| { drain_called = true; async {} },
        |_, _| { join_called = true; async {} },
    )
    .await;
    assert!(drain_called);
    assert!(join_called);
}

/// Mirrors test_producer_synchronized_perform_consumers_queue_with_multiple_consumer
/// Tests that synchronized_perform processes consumers in order by index.
#[tokio::test]
async fn test_synchronized_perform_with_multiple_consumers() {
    let consumers: Vec<SyncConsumerHandle> = (0..5)
        .map(|i| SyncConsumerHandle { index: i })
        .collect();
    let mut drain_order = Vec::new();
    let mut join_order = Vec::new();
    Producer::synchronized_perform(
        &consumers,
        true,
        1.0,
        |i| { drain_order.push(i); async {} },
        |i, _| { join_order.push(i); async {} },
    )
    .await;
    assert_eq!(drain_order, vec![0, 1, 2, 3, 4]);
    assert_eq!(join_order, vec![0, 1, 2, 3, 4]);
}

// ── is_consumers_queue_empty ─────────────────────────────────────────

#[test]
fn test_is_consumers_queue_empty_basic() {
    assert!(Producer::is_consumers_queue_empty(&[], 1));
    assert!(Producer::is_consumers_queue_empty(&[(0, true), (1, true)], 1));
    assert!(!Producer::is_consumers_queue_empty(&[(0, false)], 1));
    // prio > max → considered empty
    assert!(Producer::is_consumers_queue_empty(&[(2, false)], 1));
}

/// Mirrors test_is_consumers_queue_empty_with_one_consumer
#[test]
fn test_is_consumers_queue_empty_with_one_consumer() {
    // One consumer at priority 0, queue not empty
    let data = vec![(0, false)];
    assert!(!Producer::is_consumers_queue_empty(&data, 1));
    assert!(!Producer::is_consumers_queue_empty(&data, 2));
    // After draining
    let data = vec![(0, true)];
    assert!(Producer::is_consumers_queue_empty(&data, 1));
    assert!(Producer::is_consumers_queue_empty(&data, 2));
}

/// Mirrors test_is_consumers_queue_empty_with_multiple_consumers
/// 5 consumers: 2 at prio 1, 2 at prio 2, 1 at prio 3
#[test]
fn test_is_consumers_queue_empty_with_multiple_consumers() {
    // All queues non-empty
    let all_full = vec![(1, false), (1, false), (2, false), (2, false), (3, false)];
    assert!(!Producer::is_consumers_queue_empty(&all_full, 1));
    assert!(!Producer::is_consumers_queue_empty(&all_full, 2));
    assert!(!Producer::is_consumers_queue_empty(&all_full, 3));

    // After draining priority <= 1
    let after_level1 = vec![(1, true), (1, true), (2, false), (2, false), (3, false)];
    assert!(Producer::is_consumers_queue_empty(&after_level1, 1));
    assert!(!Producer::is_consumers_queue_empty(&after_level1, 2));
    assert!(!Producer::is_consumers_queue_empty(&after_level1, 3));

    // After draining priority <= 2
    let after_level2 = vec![(1, true), (1, true), (2, true), (2, true), (3, false)];
    assert!(Producer::is_consumers_queue_empty(&after_level2, 1));
    assert!(Producer::is_consumers_queue_empty(&after_level2, 2));
    assert!(!Producer::is_consumers_queue_empty(&after_level2, 3));

    // After draining all
    let all_empty = vec![(1, true), (1, true), (2, true), (2, true), (3, true)];
    assert!(Producer::is_consumers_queue_empty(&all_empty, 3));
}
