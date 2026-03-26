use async_channel::consumer::{Consumer, ConsumeError, SupervisedState, InternalConsumer};
use async_channel::enums::ChannelConsumerPriorityLevels;

// ── Consumer basics ──────────────────────────────────────────────────

#[test]
fn test_consumer_new() {
    let c = Consumer::new(0);
    assert!(!c.should_stop);
    assert_eq!(c.priority_level, 0);
    assert!(c.should_consume());
}

#[test]
fn test_consumer_start_stop() {
    let mut c = Consumer::with_defaults();
    c.stop();
    assert!(c.should_stop);
    assert!(!c.should_consume());
    c.start();
    assert!(!c.should_stop);
    assert!(c.should_consume());
}

#[test]
fn test_display_name() {
    let name = Consumer::display_name("MyConsumer", "on_data");
    assert_eq!(name, "MyConsumer with callback: on_data");
}

#[test]
fn test_create_task_noop() {
    let c = Consumer::new(0);
    c.create_task();
}

#[tokio::test]
async fn test_perform_noop() {
    let c = Consumer::new(0);
    c.perform().await;
}

#[tokio::test]
async fn test_run_with_task() {
    let mut c = Consumer::new(0);
    c.stop();
    assert!(c.should_stop);
    c.run(true).await;
    assert!(!c.should_stop);
}

#[tokio::test]
async fn test_run_without_task() {
    let mut c = Consumer::new(0);
    c.stop();
    c.run(false).await;
    assert!(!c.should_stop);
}

#[tokio::test]
async fn test_join_noop() {
    let c = Consumer::new(0);
    c.join(1.0).await;
}

#[tokio::test]
async fn test_join_queue_noop() {
    let c = Consumer::new(0);
    c.join_queue().await;
}

// ── Consume loop ─────────────────────────────────────────────────────

#[tokio::test]
async fn test_consume_loop_stops() {
    let c = Consumer::new(0);
    let mut call_count = 0u32;
    c.consume_loop(
        || {
            call_count += 1;
            async { Err::<i32, _>(ConsumeError::<()>::Closed) }
        },
        |_| async { Ok(()) },
        || {},
        |_| {},
        || async {},
    )
    .await;
    assert_eq!(call_count, 1);
}

#[tokio::test]
async fn test_consume_loop_cancelled() {
    let c = Consumer::new(0);
    let mut cancelled_count = 0u32;
    let mut ends_count = 0u32;
    let mut iteration = 0u32;
    c.consume_loop(
        || {
            iteration += 1;
            async move {
                if iteration == 1 {
                    Err::<i32, _>(ConsumeError::<()>::Cancelled)
                } else {
                    Err(ConsumeError::Closed)
                }
            }
        },
        |_| async { Ok(()) },
        || { cancelled_count += 1; },
        |_| {},
        || { ends_count += 1; async {} },
    )
    .await;
    assert_eq!(cancelled_count, 1);
    assert_eq!(ends_count, 1); // consume_ends called after cancellation
}

#[tokio::test]
async fn test_consume_loop_error() {
    let c = Consumer::new(0);
    let mut error_count = 0u32;
    let mut ends_count = 0u32;
    let mut iteration = 0u32;
    c.consume_loop(
        || {
            iteration += 1;
            async move {
                if iteration == 1 {
                    Err::<i32, _>(ConsumeError::Other("boom"))
                } else {
                    Err(ConsumeError::Closed)
                }
            }
        },
        |_| async { Ok(()) },
        || {},
        |e: &str| { assert_eq!(e, "boom"); error_count += 1; },
        || { ends_count += 1; async {} },
    )
    .await;
    assert_eq!(error_count, 1);
    assert_eq!(ends_count, 1);
}

#[tokio::test]
async fn test_consume_loop_perform_error() {
    let c = Consumer::new(0);
    let mut error_count = 0u32;
    let mut ends_count = 0u32;
    let mut iteration = 0u32;
    c.consume_loop(
        || {
            iteration += 1;
            async move {
                if iteration == 1 {
                    Ok::<i32, ConsumeError<&str>>(42)
                } else {
                    Err(ConsumeError::Closed)
                }
            }
        },
        |_| async { Err::<(), _>(ConsumeError::Other("perform failed")) },
        || {},
        |_e| { error_count += 1; },
        || { ends_count += 1; async {} },
    )
    .await;
    assert_eq!(error_count, 1);
    assert_eq!(ends_count, 1);
}

// ── SupervisedState ──────────────────────────────────────────────────

#[test]
fn test_supervised_state() {
    let s = SupervisedState::new();
    assert!(s.is_idle());
    s.mark_busy();
    assert!(!s.is_idle());
    s.mark_idle();
    assert!(s.is_idle());
}

#[tokio::test]
async fn test_supervised_perform() {
    let s = SupervisedState::new();
    assert!(s.is_idle());
    let result = s
        .supervised_perform(42, |data| async move {
            assert_eq!(data, 42);
            Ok::<(), ()>(())
        })
        .await;
    assert!(result.is_ok());
    assert!(s.is_idle());
}

#[tokio::test]
async fn test_supervised_perform_error() {
    let s = SupervisedState::new();
    let result = s
        .supervised_perform(1, |_| async { Err::<(), _>("fail") })
        .await;
    assert!(result.is_err());
    // Must be idle even after error
    assert!(s.is_idle());
}

// ── InternalConsumer ─────────────────────────────────────────────────

#[test]
fn test_internal_consumer_new() {
    let ic = InternalConsumer::new();
    assert!(!ic.consumer.should_stop);
    assert_eq!(
        ic.consumer.priority_level,
        ChannelConsumerPriorityLevels::High.value()
    );
}

#[test]
fn test_internal_consumer_default() {
    let ic = InternalConsumer::default();
    assert!(!ic.consumer.should_stop);
}
