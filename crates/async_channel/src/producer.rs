use std::future::Future;

pub struct Producer {
    pub should_stop: bool,
    pub is_running: bool,
}

impl Producer {
    pub fn new() -> Self {
        Self {
            should_stop: false,
            is_running: false,
        }
    }

    pub fn start_running(&mut self) {
        self.is_running = true;
    }

    pub fn stop(&mut self) {
        self.should_stop = true;
        self.is_running = false;
    }

    pub fn pause(&mut self) {
        self.is_running = false;
    }

    pub fn resume(&mut self) {
        // is_running is set by the caller if needed
    }

    /// No-op stub. Actual sending requires a runtime-specific queue, so
    /// concrete producers override this.
    pub fn send(&self) {
        // no-op
    }

    /// No-op stub. Push notification that new data should be sent.
    /// Concrete producers override this with actual implementation.
    pub async fn push(&self) {
        // no-op
    }

    /// No-op stub. Should be implemented for producer's non-triggered tasks.
    pub async fn start(&self) {
        // no-op
    }

    /// No-op stub. Should implement producer's non-triggered tasks.
    /// Can be used to force producer to perform tasks.
    pub async fn perform(&self) {
        // no-op
    }

    /// No-op stub. Should be implemented when producer can be modified
    /// during perform().
    pub async fn modify(&self) {
        // no-op
    }

    /// Wait until all consumers have finished processing their queues.
    /// Calls `join_fn` for each consumer index in `0..count`.
    pub async fn wait_for_processing<JF, JFut>(count: usize, mut join_fn: JF)
    where
        JF: FnMut(usize) -> JFut,
        JFut: std::future::Future<Output = ()>,
    {
        for i in 0..count {
            join_fn(i).await;
        }
    }

    /// Orchestration entry point.
    /// - Calls `register_fn` to register this producer on the channel.
    /// - If not synchronized, calls `create_task_fn` to spawn the producer task.
    pub async fn run<RF, RFut, CF>(
        &mut self,
        register_fn: RF,
        create_task_fn: CF,
        is_synchronized: bool,
    ) where
        RF: FnOnce() -> RFut,
        RFut: std::future::Future<Output = ()>,
        CF: FnOnce(),
    {
        register_fn().await;
        if !is_synchronized {
            create_task_fn();
        }
    }

    /// Mark the producer as running. Mirrors the Python `create_task` which
    /// sets `is_running = True` and spawns `start()` into an asyncio task.
    /// In pure Rust the actual task spawn is runtime-specific, so we only
    /// flip the flag here.
    pub fn create_task(&mut self) {
        self.is_running = true;
    }

    /// Send data to N consumers. Caller provides the async put operation per index.
    pub async fn send_to_all<F, Fut>(count: usize, mut send_one: F)
    where
        F: FnMut(usize) -> Fut,
        Fut: std::future::Future<Output = ()>,
    {
        for i in 0..count {
            send_one(i).await;
        }
    }

    /// Drain each consumer's queue synchronously, calling perform for each item.
    pub async fn synchronized_perform<F, Fut, JF, JFut>(
        consumers: &[SyncConsumerHandle],
        join_consumers: bool,
        timeout: f64,
        mut drain_and_perform: F,
        mut join_fn: JF,
    ) where
        F: FnMut(usize) -> Fut,
        Fut: Future<Output = ()>,
        JF: FnMut(usize, f64) -> JFut,
        JFut: Future<Output = ()>,
    {
        for (i, _handle) in consumers.iter().enumerate() {
            drain_and_perform(i).await;
            if join_consumers {
                join_fn(i, timeout).await;
            }
        }
    }

    /// Drain a queue by repeatedly checking emptiness, getting the next item,
    /// and performing on it. Stops when the queue is empty or `get` returns `None`.
    pub async fn drain_queue<T, IsEmpty, IFut, Get, GFut, Perform, PFut>(
        mut is_empty: IsEmpty,
        mut get: Get,
        mut perform: Perform,
    ) where
        IsEmpty: FnMut() -> IFut,
        IFut: Future<Output = bool>,
        Get: FnMut() -> GFut,
        GFut: Future<Output = Option<T>>,
        Perform: FnMut(T) -> PFut,
        PFut: Future<Output = ()>,
    {
        loop {
            if is_empty().await {
                break;
            }
            match get().await {
                Some(data) => perform(data).await,
                None => break,
            }
        }
    }

    pub fn is_consumers_queue_empty(consumer_priorities: &[(i64, bool)], max_priority: i64) -> bool {
        consumer_priorities
            .iter()
            .all(|(prio, empty)| *prio > max_priority || *empty)
    }
}

impl Default for Producer {
    fn default() -> Self {
        Self::new()
    }
}

/// Opaque handle for sync perform operations.
pub struct SyncConsumerHandle {
    pub index: usize,
}
