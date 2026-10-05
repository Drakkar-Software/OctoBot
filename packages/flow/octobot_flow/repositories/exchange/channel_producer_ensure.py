import octobot_trading.exchange_channel as exchange_channel_module
import octobot_trading.exchanges as trading_exchanges


def exchange_has_registered_channels(exchange_manager) -> bool:
    try:
        registered_channels = exchange_channel_module.get_exchange_channels(exchange_manager.id)
    except KeyError:
        return False
    return bool(registered_channels)


def channel_has_producer(exchange_manager, channel_name: str) -> bool:
    try:
        channel = exchange_channel_module.get_chan(channel_name, exchange_manager.id)
    except KeyError:
        return False
    return bool(channel.get_producers())


async def ensure_temporary_channel_producer(
    exchange_manager,
    channel_name: str,
    updater_class: type,
    *,
    create_all_channels_if_missing: bool = True,
) -> None:
    if create_all_channels_if_missing and not exchange_has_registered_channels(exchange_manager):
        await trading_exchanges.create_exchange_channels(exchange_manager)
    if channel_has_producer(exchange_manager, channel_name):
        return
    await trading_exchanges.create_producers(
        exchange_manager,
        [updater_class],
        start_producers=False,
    )
