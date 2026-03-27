use std::collections::HashMap;

use async_channel::channels::channel::Channel;
use async_channel::channels::channel_instances::{self, ChannelRef};
use async_channel::enums::ChannelConsumerPriorityLevels;

// ---------------------------------------------------------------------------
// EvaluatorChannel
// ---------------------------------------------------------------------------

/// Evaluator-specific channel that wraps a base `Channel` and adds a
/// `matrix_id` field. Mirrors `evaluators/channel/evaluator_channel.py`.
pub struct EvaluatorChannel {
    pub channel: Channel,
    pub matrix_id: String,
}

impl EvaluatorChannel {
    pub fn new(matrix_id: String) -> Self {
        Self {
            channel: Channel::new(""),
            matrix_id,
        }
    }

    /// Return filtered consumer indices, excluding `origin_consumer_index`
    /// when it is `Some`. This mirrors the Python override that removes the
    /// origin consumer from the result list.
    pub fn get_consumer_from_filters(
        &self,
        consumer_filters: &HashMap<String, String>,
        origin_consumer_index: Option<usize>,
    ) -> Vec<usize> {
        let base = self.channel.get_filtered_consumer_indices(consumer_filters);
        match origin_consumer_index {
            Some(origin) => base.into_iter().filter(|&i| i != origin).collect(),
            None => base,
        }
    }

    /// Default priority level for evaluator channel consumers.
    pub fn default_priority_level() -> i64 {
        ChannelConsumerPriorityLevels::Medium.value()
    }
}

// ---------------------------------------------------------------------------
// Module-level helpers – operate on the ChannelInstances singleton using
// `id_channels` keyed by `matrix_id`.
// ---------------------------------------------------------------------------

/// Register `chan` under `name` inside the `matrix_id` id-channel container.
pub fn set_chan(chan: ChannelRef, name: &str, matrix_id: &str) -> Result<(), String> {
    let inst = channel_instances::instance();
    let mut guard = inst.lock().map_err(|e| e.to_string())?;
    guard.set_chan_at_id(matrix_id, name, chan)
}

/// Return a clone of the channels map for the given `matrix_id`.
pub fn get_evaluator_channels(
    matrix_id: &str,
) -> Result<HashMap<String, ChannelRef>, String> {
    let inst = channel_instances::instance();
    let guard = inst.lock().map_err(|e| e.to_string())?;
    Ok(guard
        .get_channels(matrix_id)
        .cloned()
        .unwrap_or_default())
}

/// Remove the entire channel container for `matrix_id`.
pub fn del_evaluator_channel_container(matrix_id: &str) -> Result<(), String> {
    let inst = channel_instances::instance();
    let mut guard = inst.lock().map_err(|e| e.to_string())?;
    guard.del_channel_container(matrix_id);
    Ok(())
}

/// Retrieve a single channel reference by `chan_name` within `matrix_id`.
pub fn get_chan(chan_name: &str, matrix_id: &str) -> Result<Option<ChannelRef>, String> {
    let inst = channel_instances::instance();
    let guard = inst.lock().map_err(|e| e.to_string())?;
    Ok(guard.get_chan_at_id(matrix_id, chan_name).cloned())
}

/// Remove a single channel by `chan_name` within `matrix_id`.
pub fn del_chan(chan_name: &str, matrix_id: &str) -> Result<(), String> {
    let inst = channel_instances::instance();
    let mut guard = inst.lock().map_err(|e| e.to_string())?;
    guard.del_chan_at_id(matrix_id, chan_name);
    Ok(())
}
