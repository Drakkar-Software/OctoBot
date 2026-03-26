use async_channel::producer::Producer;

// ── Lifecycle ────────────────────────────────────────────────────────

#[test]
fn test_producer_new() {
    let p = Producer::new();
    assert!(!p.should_stop);
    assert!(!p.is_running);
}

#[test]
fn test_producer_lifecycle() {
    let mut p = Producer::new();
    p.start_running();
    assert!(p.is_running);
    p.pause();
    assert!(!p.is_running);
    p.stop();
    assert!(p.should_stop);
    assert!(!p.is_running);
}

#[test]
fn test_create_task() {
    let mut p = Producer::new();
    assert!(!p.is_running);
    p.create_task();
    assert!(p.is_running);
}

#[test]
fn test_resume_noop() {
    let mut p = Producer::new();
    p.start_running();
    assert!(p.is_running);
    p.resume();
    assert!(p.is_running);

    let mut p2 = Producer::new();
    assert!(!p2.is_running);
    p2.resume();
    assert!(!p2.is_running);
}

// ── No-op stubs ──────────────────────────────────────────────────────

#[test]
fn test_send_noop() {
    let p = Producer::new();
    p.send();
}

#[tokio::test]
async fn test_push_noop() {
    let p = Producer::new();
    p.push().await;
}

#[tokio::test]
async fn test_start_noop() {
    let p = Producer::new();
    p.start().await;
}

#[tokio::test]
async fn test_perform_noop() {
    let p = Producer::new();
    p.perform().await;
}

#[tokio::test]
async fn test_modify_noop() {
    let p = Producer::new();
    p.modify().await;
}

// ── Async orchestration ──────────────────────────────────────────────

#[tokio::test]
async fn test_wait_for_processing() {
    let mut joined = Vec::new();
    Producer::wait_for_processing(3, |i| {
        joined.push(i);
        async {}
    })
    .await;
    assert_eq!(joined, vec![0, 1, 2]);
}

#[tokio::test]
async fn test_run_not_synchronized() {
    let mut p = Producer::new();
    let mut registered = false;
    let mut task_created = false;
    p.run(
        || async { registered = true },
        || { task_created = true },
        false,
    )
    .await;
    assert!(registered);
    assert!(task_created);
}

#[tokio::test]
async fn test_run_synchronized() {
    let mut p = Producer::new();
    let mut registered = false;
    let mut task_created = false;
    p.run(
        || async { registered = true },
        || { task_created = true },
        true,
    )
    .await;
    assert!(registered);
    assert!(!task_created);
}

#[tokio::test]
async fn test_send_to_all() {
    let mut sent = Vec::new();
    Producer::send_to_all(4, |i| {
        sent.push(i);
        async {}
    })
    .await;
    assert_eq!(sent, vec![0, 1, 2, 3]);
}

#[tokio::test]
async fn test_send_to_all_zero() {
    let mut sent = Vec::new();
    Producer::send_to_all(0, |i| {
        sent.push(i);
        async {}
    })
    .await;
    assert!(sent.is_empty());
}
