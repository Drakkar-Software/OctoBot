import os
import contextlib
import decimal
import pytest

import async_channel.util as channel_util
import octobot_commons.constants as commons_constants
import octobot_commons.tests.test_config as test_config
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_backtesting.api as backtesting_api
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.api as trading_api
import octobot_trading.personal_data
import octobot_trading.exchanges
import octobot_trading.enums as trading_enums

import tentacles.Trading.Mode.simple_market_making_trading_mode.advanced_order_book_distribution as advanced_order_book_distribution
import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging.hedging_engine as hedging_engine_import

import tests.test_utils.config as test_utils_config
import tests.test_utils.test_exchanges as test_exchanges


SYMBOL = "BTC/USDT"
PRICE = 1000


@contextlib.asynccontextmanager
async def exchange_manager_context():
    tentacles_manager_api.reload_tentacle_info()
    exchange_manager = None
    try:
        config = test_config.load_test_config()
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]["USDT"] = 1000
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO][
            "BTC"] = 10
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO].update({})
        exchange_manager = test_exchanges.get_test_exchange_manager(config, "binance")
        exchange_manager.tentacles_setup_config = test_utils_config.load_test_tentacles_config()

        # use backtesting not to spam exchanges apis
        exchange_manager.is_simulated = True
        exchange_manager.is_backtesting = True
        exchange_manager.use_cached_markets = False
        backtesting = await backtesting_api.initialize_backtesting(
            config,
            exchange_ids=[exchange_manager.id],
            matrix_id=None,
            data_files=[
                os.path.join(test_config.TEST_CONFIG_FOLDER, "AbstractExchangeHistoryCollector_1586017993.616272.data")])
        exchange_manager.exchange = octobot_trading.exchanges.ExchangeSimulator(exchange_manager.config,
                                                                exchange_manager,
                                                                backtesting)
        await exchange_manager.exchange.initialize()
        for exchange_channel_class_type in [exchanges_channel.ExchangeChannel, exchanges_channel.TimeFrameExchangeChannel]:
            await channel_util.create_all_subclasses_channel(exchange_channel_class_type, exchanges_channel.set_chan,
                                                            exchange_manager=exchange_manager)

        trader = octobot_trading.exchanges.TraderSimulator(config, exchange_manager)
        await trader.initialize()

        # set BTC/USDT price at 1000 USDT
        if SYMBOL not in exchange_manager.client_symbols:
            exchange_manager.client_symbols.append(SYMBOL)
        trading_api.force_set_mark_price(exchange_manager, SYMBOL, PRICE)

        yield exchange_manager
    finally:
        if exchange_manager:
            for importer in backtesting_api.get_importers(exchange_manager.exchange.backtesting):
                await backtesting_api.stop_importer(importer)
            await exchange_manager.exchange.backtesting.stop()
            await exchange_manager.stop()


def create_hedging_fill(
    trading_exchange_manager,
    order_exchange_id,
    symbol=SYMBOL,
    side=trading_enums.TradeOrderSide.BUY,
    filled_price=decimal.Decimal("1000"),
    hedging_price=decimal.Decimal("1001"),
    locally_filled_amount=decimal.Decimal("0.1"),
    filled_time=1234567890.0,
    hedging_order=None,
    is_locked=True,
):
    """Helper function to create a HedgingFill instance for testing."""
    order = {
        trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: order_exchange_id,
        trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: symbol,
        trading_enums.ExchangeConstantsOrderColumns.SIDE.value: side,
        trading_enums.ExchangeConstantsOrderColumns.PRICE.value: filled_price,
    }
    fill_trade = hedging_engine_import.HedgingEngine.fill_trade_factory(
        trading_exchange_manager, order, locally_filled_amount, filled_time
    )
    return hedging_engine_import.HedgingFill(
        fill_trade=fill_trade,
        hedging_price=hedging_price,
        hedging_order=hedging_order,
        is_locked=is_locked,
    )


def create_hedging_order(exchange_manager, exchange_order_id, order_group=None):
    """Helper function to create a real Order instance for testing."""
    order = octobot_trading.personal_data.Order(exchange_manager.trader)
    order.exchange_order_id = exchange_order_id
    order.order_group = order_group
    return order


@pytest.fixture
def order_book_distribution():
    return advanced_order_book_distribution.AdvancedOrderBookDistribution(
        bids_count=10,
        asks_count=10,
        min_spread=decimal.Decimal("4"),
        max_spread=decimal.Decimal("40"),
        target_cumulated_volume_percent=decimal.Decimal("2"),
        daily_trading_volume_percent=decimal.Decimal("1"),
        price_distribution=advanced_order_book_distribution.OrdersDistribution.LINEAR,
        funds_distribution=advanced_order_book_distribution.FundsDistribution.VALLEY,
        max_base_budget=decimal.Decimal("1"),
        max_quote_budget=decimal.Decimal("100"),
        min_base_budget=decimal.Decimal("0.01"),
        min_quote_budget=decimal.Decimal("1"),
    )
