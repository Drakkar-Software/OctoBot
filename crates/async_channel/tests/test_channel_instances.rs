use async_channel::channels::channel_instances::{ChannelInstances, ChannelRef};

fn fresh() -> ChannelInstances {
    ChannelInstances::new()
}

#[test]
fn test_set_get_del_chan() {
    let mut ci = fresh();
    ci.set_chan("Test", ChannelRef { name: "Test".into() })
        .unwrap();
    assert!(ci.get_chan("Test").is_some());

    // Duplicate should fail
    assert!(ci
        .set_chan("Test", ChannelRef { name: "Test".into() })
        .is_err());

    ci.del_chan("Test");
    assert!(ci.get_chan("Test").is_none());
}

#[test]
fn test_id_channels() {
    let mut ci = fresh();
    ci.set_chan_at_id("id1", "Test", ChannelRef { name: "Test".into() })
        .unwrap();
    assert!(ci.get_chan_at_id("id1", "Test").is_some());
    assert!(ci.get_channels("id1").is_some());

    ci.del_chan_at_id("id1", "Test");
    assert!(ci.get_chan_at_id("id1", "Test").is_none());

    ci.set_chan_at_id("id2", "A", ChannelRef { name: "A".into() })
        .unwrap();
    ci.del_channel_container("id2");
    assert!(ci.get_channels("id2").is_none());
}

/// Mirrors test_set_chan_at_id_already_exist
#[test]
fn test_set_chan_at_id_already_exists() {
    let mut ci = fresh();
    ci.set_chan_at_id("id1", "Ch", ChannelRef { name: "Ch".into() }).unwrap();
    let result = ci.set_chan_at_id("id1", "Ch", ChannelRef { name: "Ch".into() });
    assert!(result.is_err());
    assert!(result.unwrap_err().contains("already exists"));
}

/// Mirrors test_del_channel_container_not_exist_does_not_raise
#[test]
fn test_del_channel_container_not_exist() {
    let mut ci = fresh();
    // Should not panic
    ci.del_channel_container("nonexistent");
}

/// Mirrors test_get_channels_not_exist
#[test]
fn test_get_channels_not_exist() {
    let ci = fresh();
    assert!(ci.get_channels("nonexistent").is_none());
}

/// Mirrors test_get_channels (6 channels across 3 containers)
#[test]
fn test_get_channels_multiple_containers() {
    let mut ci = fresh();
    // Container "id1": 2 channels
    ci.set_chan_at_id("id1", "A", ChannelRef { name: "A".into() }).unwrap();
    ci.set_chan_at_id("id1", "B", ChannelRef { name: "B".into() }).unwrap();
    // Container "id2": 3 channels
    ci.set_chan_at_id("id2", "C", ChannelRef { name: "C".into() }).unwrap();
    ci.set_chan_at_id("id2", "D", ChannelRef { name: "D".into() }).unwrap();
    ci.set_chan_at_id("id2", "E", ChannelRef { name: "E".into() }).unwrap();
    // Container "id3": 1 channel
    ci.set_chan_at_id("id3", "F", ChannelRef { name: "F".into() }).unwrap();

    let id1 = ci.get_channels("id1").unwrap();
    assert_eq!(id1.len(), 2);
    assert!(id1.contains_key("A"));
    assert!(id1.contains_key("B"));

    let id2 = ci.get_channels("id2").unwrap();
    assert_eq!(id2.len(), 3);

    let id3 = ci.get_channels("id3").unwrap();
    assert_eq!(id3.len(), 1);
    assert!(id3.contains_key("F"));
}
