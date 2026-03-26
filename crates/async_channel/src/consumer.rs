use std::future::Future;

use crate::enums::ChannelConsumerPriorityLevels;

pub struct Consumer {
    pub should_stop: bool,
    pub priority_level: i64,
}

impl Consumer {
    pub fn new(priority_level: i64) -> Self {
        Self {
            should_stop: false,
            priority_level,
        }
    }

    pub fn with_defaults() -> Self {
        Self::new(ChannelConsumerPriorityLevels::High.value())
    }

    /// Return a human-readable display name for a consumer.
    /// Mirrors Python `Consumer.__str__`.
    pub fn display_name(class_name: &str, callback_name: &str) -> String {
        format!("{class_name} with callback: {callback_name}")
    }

    /// No-op base `perform` stub. Mirrors the Python `Consumer.perform`
    /// which simply calls the callback. In pure Rust the callback is
    /// runtime-specific, so this is a placeholder.
    pub async fn perform(&self) {
        // no-op
    }

    pub fn start(&mut self) {
        self.should_stop = false;
    }

    pub fn stop(&mut self) {
        self.should_stop = true;
    }

    pub fn should_consume(&self) -> bool {
        !self.should_stop
    }

    /// No-op stub. Task management is runtime-specific; in pure Rust this is a
    /// placeholder so that call-sites compile.
    pub fn create_task(&self) {
        // no-op: task creation depends on the async runtime
    }

    /// Initialize and optionally create a task for this consumer.
    /// Calls `start()` and, when `with_task` is true, calls `create_task()`.
    pub async fn run(&mut self, with_task: bool) {
        self.start();
        if with_task {
            self.create_task();
        }
    }

    /// No-op base implementation. Supervised consumers override this to wait
    /// for any in-progress `perform` call to finish.
    pub async fn join(&self, _timeout: f64) {
        // no-op in base consumer
    }

    /// No-op base implementation. Supervised consumers override this to wait
    /// for the entire queue to finish processing.
    pub async fn join_queue(&self) {
        // no-op in base consumer
    }

    /// Run the consume loop. Caller provides the async operations as closures:
    /// - `get_data`: awaits next item from queue
    /// - `perform`: processes the item
    /// - `on_cancelled`: called on cancellation
    /// - `on_error`: called on other errors
    /// - `consume_ends`: called after each cycle (finally block)
    ///
    /// The loop runs indefinitely until `get_data` returns
    /// `ConsumeError::Closed`. Stop signalling is the caller's responsibility
    /// (e.g. via the `get_data` closure checking a flag and returning `Closed`).
    pub async fn consume_loop<T, E, GF, PF, EF>(
        &self,
        mut get_data: impl FnMut() -> GF,
        mut perform: impl FnMut(T) -> PF,
        mut on_cancelled: impl FnMut(),
        mut on_error: impl FnMut(E),
        mut consume_ends: impl FnMut() -> EF,
    ) where
        GF: Future<Output = Result<T, ConsumeError<E>>>,
        PF: Future<Output = Result<(), ConsumeError<E>>>,
        EF: Future<Output = ()>,
    {
        loop {
            let data = match get_data().await {
                Ok(d) => d,
                Err(ConsumeError::Cancelled) => {
                    on_cancelled();
                    consume_ends().await;
                    continue;
                }
                Err(ConsumeError::Closed) => break,
                Err(ConsumeError::Other(e)) => {
                    on_error(e);
                    consume_ends().await;
                    continue;
                }
            };
            match perform(data).await {
                Ok(()) => {}
                Err(ConsumeError::Cancelled) => on_cancelled(),
                Err(ConsumeError::Other(e)) => on_error(e),
                Err(ConsumeError::Closed) => {}
            }
            consume_ends().await;
        }
    }
}

pub enum ConsumeError<E> {
    Cancelled,
    Closed,
    Other(E),
}

/// Supervised consumer state: tracks whether a perform is in progress.
pub struct SupervisedState {
    is_idle: std::sync::atomic::AtomicBool,
}

impl SupervisedState {
    pub fn new() -> Self {
        Self {
            is_idle: std::sync::atomic::AtomicBool::new(true),
        }
    }

    pub fn is_idle(&self) -> bool {
        self.is_idle.load(std::sync::atomic::Ordering::SeqCst)
    }

    pub fn mark_busy(&self) {
        self.is_idle
            .store(false, std::sync::atomic::Ordering::SeqCst);
    }

    pub fn mark_idle(&self) {
        self.is_idle
            .store(true, std::sync::atomic::Ordering::SeqCst);
    }

    /// Wrap a perform call: clear idle before, set idle after (even on error).
    pub async fn supervised_perform<T, E, F, Fut>(
        &self,
        data: T,
        mut perform: F,
    ) -> Result<(), E>
    where
        F: FnMut(T) -> Fut,
        Fut: Future<Output = Result<(), E>>,
    {
        self.mark_busy();
        let result = perform(data).await;
        self.mark_idle();
        result
    }
}

impl Default for SupervisedState {
    fn default() -> Self {
        Self::new()
    }
}

/// An InternalConsumer is a Consumer whose callback is declared internally.
/// In pure Rust this is an empty marker struct that wraps a `Consumer`.
pub struct InternalConsumer {
    pub consumer: Consumer,
}

impl InternalConsumer {
    pub fn new() -> Self {
        Self {
            consumer: Consumer::with_defaults(),
        }
    }
}

impl Default for InternalConsumer {
    fn default() -> Self {
        Self::new()
    }
}
