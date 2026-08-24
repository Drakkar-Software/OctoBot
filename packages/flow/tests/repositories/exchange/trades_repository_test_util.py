import octobot_trading.api as trading_api_module
import octobot_trading.constants as trading_constants
import octobot_trading.exchange_channel as exchange_channel_module
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.personal_data as trading_personal_data


async def ensure_trades_channel(exchange_manager) -> None:
    try:
        trading_api_module.get_channel_updater(exchange_manager, trading_constants.TRADES_CHANNEL)
        return
    except KeyError:
        pass
    try:
        exchange_channel_module.get_chan(trading_constants.TRADES_CHANNEL, exchange_manager.id)
    except KeyError:
        await trading_exchanges.create_exchange_channels(exchange_manager)
    await trading_exchanges.create_producers(
        exchange_manager,
        [trading_personal_data.TradesUpdater],
        start_producers=False,
    )
