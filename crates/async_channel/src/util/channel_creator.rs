use std::future::Future;

/// Create and initialize a channel: instantiate, register, set synchronized, start.
pub async fn create_channel_instance<C, SF, STF, SFut>(
    create: impl FnOnce() -> C,
    set_chan: impl FnOnce(&C),
    _is_synchronized: bool,
    set_synchronized: SF,
    start: STF,
) -> C
where
    SF: FnOnce(&C),
    STF: FnOnce() -> SFut,
    SFut: Future<Output = ()>,
{
    let channel = create();
    set_chan(&channel);
    set_synchronized(&channel);
    start().await;
    channel
}

/// Create channel instances for all subclasses.
pub async fn create_all_subclasses_channel<F, Fut>(
    subclass_count: usize,
    mut create_one: F,
) where
    F: FnMut(usize) -> Fut,
    Fut: Future<Output = ()>,
{
    for i in 0..subclass_count {
        create_one(i).await;
    }
}
