import octobot_flow.entities
import octobot_flow.repositories.community as trading_signals_channel


async def subscribe_internal_trading_signal_consumer() -> None:
    """
    Propagates trading signals from the internal trading signal channel to running automations.
    Signals can from from a local signal emitter or from send_internal_trading_signal
    """
    async def _on_internal_trading_signal(trading_signal: octobot_flow.entities.TradingSignal) -> None:
        print(trading_signal)

    channel = await trading_signals_channel.get_or_create_internal_trading_signal_channel()
    await channel.new_consumer(_on_internal_trading_signal)


async def send_internal_trading_signal(trading_signal: octobot_flow.entities.TradingSignal) -> None:
    """
    Broadcasts a trading signal to the internal trading signal channel.
    """
    await trading_signals_channel.send_internal_trading_signal(trading_signal)
