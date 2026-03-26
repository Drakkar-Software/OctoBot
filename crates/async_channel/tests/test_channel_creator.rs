use async_channel::util::channel_creator::{create_channel_instance, create_all_subclasses_channel};

#[tokio::test]
async fn test_create_channel_instance() {
    let mut started = false;
    let ch = create_channel_instance(
        || "test_channel".to_string(),
        |_| {},
        true,
        |_| {},
        || async { started = true },
    )
    .await;
    assert_eq!(ch, "test_channel");
    assert!(started);
}

#[tokio::test]
async fn test_create_all_subclasses() {
    let mut created = Vec::new();
    create_all_subclasses_channel(3, |i| {
        created.push(i);
        async {}
    })
    .await;
    assert_eq!(created, vec![0, 1, 2]);
}
