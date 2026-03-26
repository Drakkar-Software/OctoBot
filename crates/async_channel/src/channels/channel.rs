use std::future::Future;

use crate::constants::CHANNEL_WILDCARD;
use crate::enums::ChannelConsumerPriorityLevels;
use std::collections::HashMap;

// ── Filter types ───────────────────────────────────────────────────────────

#[derive(Clone, Debug)]
pub enum FilterValue {
    Single(String),
    List(Vec<String>),
}

/// Check if a consumer's filters match the expected filters.
pub fn check_filters(
    consumer_filters: &HashMap<String, FilterValue>,
    expected_filters: &HashMap<String, String>,
) -> bool {
    if expected_filters.is_empty() {
        return true;
    }
    for (key, expected) in expected_filters {
        if expected == CHANNEL_WILDCARD {
            continue;
        }
        match consumer_filters.get(key) {
            Some(FilterValue::Single(v)) => {
                if v != expected && v != CHANNEL_WILDCARD {
                    return false;
                }
            }
            Some(FilterValue::List(vals)) => {
                if !vals.iter().any(|v| v == expected || v == CHANNEL_WILDCARD) {
                    return false;
                }
            }
            None => return false,
        }
    }
    true
}

// ── Channel ────────────────────────────────────────────────────────────────

#[derive(Clone, Debug)]
pub struct ConsumerEntry {
    pub priority_level: i64,
    pub filters: HashMap<String, FilterValue>,
}

pub struct Channel {
    pub name: String,
    pub chan_id: Option<String>,
    pub is_paused: bool,
    pub is_synchronized: bool,
    consumers: Vec<ConsumerEntry>,
    producer_count: usize,
    has_internal_producer: bool,
}

impl Channel {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            chan_id: None,
            is_paused: true,
            is_synchronized: false,
            consumers: Vec::new(),
            producer_count: 0,
            has_internal_producer: false,
        }
    }

    pub fn derive_name(class_name: &str) -> String {
        class_name.replace("Channel", "")
    }

    // ── Consumer management ────────────────────────────────────────────

    pub fn add_consumer(&mut self, entry: ConsumerEntry) {
        self.consumers.push(entry);
    }

    pub fn remove_consumer(&mut self, index: usize) {
        if index < self.consumers.len() {
            self.consumers.remove(index);
        }
    }

    pub fn consumer_count(&self) -> usize {
        self.consumers.len()
    }

    pub fn consumers(&self) -> &[ConsumerEntry] {
        &self.consumers
    }

    pub fn get_prioritized_consumer_indices(&self, priority_level: i64) -> Vec<usize> {
        self.consumers
            .iter()
            .enumerate()
            .filter(|(_, c)| c.priority_level <= priority_level)
            .map(|(i, _)| i)
            .collect()
    }

    pub fn get_filtered_consumer_indices(
        &self,
        expected_filters: &HashMap<String, String>,
    ) -> Vec<usize> {
        self.consumers
            .iter()
            .enumerate()
            .filter(|(_, c)| check_filters(&c.filters, expected_filters))
            .map(|(i, _)| i)
            .collect()
    }

    // ── Producer management ────────────────────────────────────────────

    pub fn register_producer(&mut self) {
        self.producer_count += 1;
    }

    pub fn unregister_producer(&mut self) {
        if self.producer_count > 0 {
            self.producer_count -= 1;
        }
    }

    pub fn producer_count(&self) -> usize {
        self.producer_count
    }

    pub fn set_internal_producer(&mut self) {
        self.has_internal_producer = true;
    }

    pub fn has_internal_producer(&self) -> bool {
        self.has_internal_producer
    }

    /// Returns `true` if the internal producer was already set, `false` if it
    /// needs creation. Mirrors the Python `get_internal_producer` create-if-
    /// not-exists pattern.
    pub fn get_internal_producer_or_create(&mut self) -> bool {
        if self.has_internal_producer {
            true
        } else {
            self.has_internal_producer = true;
            false
        }
    }

    // ── State checks ───────────────────────────────────────────────────

    pub fn should_pause_producers(&self) -> bool {
        if self.is_paused {
            return false;
        }
        if self.consumers.is_empty() {
            return true;
        }
        let opt = ChannelConsumerPriorityLevels::Optional.value();
        self.consumers.iter().all(|c| c.priority_level >= opt)
    }

    pub fn should_resume_producers(&self) -> bool {
        if !self.is_paused {
            return false;
        }
        if self.consumers.is_empty() {
            return false;
        }
        let opt = ChannelConsumerPriorityLevels::Optional.value();
        self.consumers.iter().any(|c| c.priority_level < opt)
    }

    /// Static variant of `should_pause_producers` that accepts priority levels
    /// directly instead of reading from internal consumer entries.
    /// Useful for bridge code where consumer priorities live in Python objects.
    pub fn should_pause_with_priorities(is_paused: bool, priorities: &[i64]) -> bool {
        if is_paused {
            return false;
        }
        if priorities.is_empty() {
            return true;
        }
        let opt = ChannelConsumerPriorityLevels::Optional.value();
        priorities.iter().all(|&p| p >= opt)
    }

    /// Static variant of `should_resume_producers` that accepts priority levels
    /// directly instead of reading from internal consumer entries.
    /// Useful for bridge code where consumer priorities live in Python objects.
    pub fn should_resume_with_priorities(is_paused: bool, priorities: &[i64]) -> bool {
        if !is_paused {
            return false;
        }
        if priorities.is_empty() {
            return false;
        }
        let opt = ChannelConsumerPriorityLevels::Optional.value();
        priorities.iter().any(|&p| p < opt)
    }

    // ── Orchestration helpers ──────────────────────────────────────────

    /// Alias for `consumer_count()`. Returns the number of registered consumers.
    pub fn get_consumers_count(&self) -> usize {
        self.consumers.len()
    }

    /// Call `start_fn` for each consumer (by index).
    pub async fn start_consumers<F, Fut>(count: usize, mut start_fn: F)
    where
        F: FnMut(usize) -> Fut,
        Fut: Future<Output = ()>,
    {
        for i in 0..count {
            start_fn(i).await;
        }
    }

    /// Stop each consumer, each producer, and optionally the internal producer.
    /// Calls `stop_fn(index, kind)` where kind is 0 = consumer, 1 = producer,
    /// 2 = internal producer.
    pub async fn stop_all<F, Fut>(
        consumer_count: usize,
        producer_count: usize,
        has_internal: bool,
        mut stop_fn: F,
    ) where
        F: FnMut(usize, u8) -> Fut,
        Fut: Future<Output = ()>,
    {
        for i in 0..consumer_count {
            stop_fn(i, 0).await;
        }
        for i in 0..producer_count {
            stop_fn(i, 1).await;
        }
        if has_internal {
            stop_fn(0, 2).await;
        }
    }

    /// No-op stub. Flush the channel object before stopping.
    /// Concrete implementations can override to clear producer references.
    pub fn flush(&mut self) {
        // no-op in pure Rust
    }

    /// Call `run_fn` for each consumer (by index).
    /// `is_synchronized` is forwarded so the caller can decide whether the
    /// consumer should create a task or not.
    pub async fn run_consumers<F, Fut>(
        count: usize,
        is_synchronized: bool,
        mut run_fn: F,
    ) where
        F: FnMut(usize, bool) -> Fut,
        Fut: Future<Output = ()>,
    {
        for i in 0..count {
            run_fn(i, is_synchronized).await;
        }
    }

    /// Call `modify_fn` for each producer (by index).
    pub async fn modify_producers<F, Fut>(count: usize, mut modify_fn: F)
    where
        F: FnMut(usize) -> Fut,
        Fut: Future<Output = ()>,
    {
        for i in 0..count {
            modify_fn(i).await;
        }
    }

    /// Register a producer and pause it if the channel is currently paused.
    pub async fn register_producer_flow<PF, PFut>(
        &mut self,
        is_paused: bool,
        pause_fn: PF,
    ) where
        PF: FnOnce() -> PFut,
        PFut: Future<Output = ()>,
    {
        self.register_producer();
        if is_paused {
            pause_fn().await;
        }
    }

    // ── Async orchestration ────────────────────────────────────────────

    /// The new_consumer flow: create, add, run, check state.
    pub async fn new_consumer_flow<C, RF, CF, RFut, CFut>(
        &mut self,
        consumer: C,
        entry: ConsumerEntry,
        run_consumer: RF,
        check_producers: CF,
    ) -> C
    where
        RF: FnOnce() -> RFut,
        RFut: Future<Output = ()>,
        CF: FnOnce() -> CFut,
        CFut: Future<Output = ()>,
    {
        self.add_consumer(entry);
        run_consumer().await;
        check_producers().await;
        consumer
    }

    /// Check producers state and call pause/resume as needed.
    pub async fn check_producers_state<PF, RF, PFut, RFut>(
        &mut self,
        pause_all: PF,
        resume_all: RF,
    ) where
        PF: FnOnce() -> PFut,
        PFut: Future<Output = ()>,
        RF: FnOnce() -> RFut,
        RFut: Future<Output = ()>,
    {
        if self.should_pause_producers() {
            self.is_paused = true;
            pause_all().await;
        } else if self.should_resume_producers() {
            self.is_paused = false;
            resume_all().await;
        }
    }

    /// Iterate items and call an async function on each.
    pub async fn for_each_async<F, Fut>(count: usize, mut action: F)
    where
        F: FnMut(usize) -> Fut,
        Fut: Future<Output = ()>,
    {
        for i in 0..count {
            action(i).await;
        }
    }
}
