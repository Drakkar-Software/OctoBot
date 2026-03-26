use std::collections::HashMap;
use std::sync::{Arc, Mutex, OnceLock};

/// Singleton container for named channel metadata.
///
/// Stores channel entries by name and optionally by (chan_id, name) pairs.
pub struct ChannelInstances {
    pub channels: HashMap<String, ChannelRef>,
    pub id_channels: HashMap<String, HashMap<String, ChannelRef>>,
}

/// Opaque reference to a channel. In pure Rust this wraps a channel name;
/// the PyO3 layer replaces this with a Python object reference.
#[derive(Clone, Debug)]
pub struct ChannelRef {
    pub name: String,
}

impl ChannelInstances {
    pub fn new() -> Self {
        ChannelInstances {
            channels: HashMap::new(),
            id_channels: HashMap::new(),
        }
    }

    pub fn set_chan(&mut self, name: &str, chan: ChannelRef) -> Result<(), String> {
        if self.channels.contains_key(name) {
            return Err(format!("Channel {} already exists.", name));
        }
        self.channels.insert(name.to_string(), chan);
        Ok(())
    }

    pub fn get_chan(&self, name: &str) -> Option<&ChannelRef> {
        self.channels.get(name)
    }

    pub fn del_chan(&mut self, name: &str) {
        self.channels.remove(name);
    }

    pub fn set_chan_at_id(
        &mut self,
        chan_id: &str,
        name: &str,
        chan: ChannelRef,
    ) -> Result<(), String> {
        let id_map = self
            .id_channels
            .entry(chan_id.to_string())
            .or_default();
        if id_map.contains_key(name) {
            return Err(format!("Channel {} already exists.", name));
        }
        id_map.insert(name.to_string(), chan);
        Ok(())
    }

    pub fn get_channels(&self, chan_id: &str) -> Option<&HashMap<String, ChannelRef>> {
        self.id_channels.get(chan_id)
    }

    pub fn get_chan_at_id(&self, chan_id: &str, name: &str) -> Option<&ChannelRef> {
        self.id_channels.get(chan_id)?.get(name)
    }

    pub fn del_chan_at_id(&mut self, chan_id: &str, name: &str) {
        if let Some(id_map) = self.id_channels.get_mut(chan_id) {
            id_map.remove(name);
        }
    }

    pub fn del_channel_container(&mut self, chan_id: &str) {
        self.id_channels.remove(chan_id);
    }
}

impl Default for ChannelInstances {
    fn default() -> Self {
        Self::new()
    }
}

/// Global singleton instance.
static INSTANCE: OnceLock<Arc<Mutex<ChannelInstances>>> = OnceLock::new();

pub fn instance() -> Arc<Mutex<ChannelInstances>> {
    INSTANCE
        .get_or_init(|| Arc::new(Mutex::new(ChannelInstances::new())))
        .clone()
}
