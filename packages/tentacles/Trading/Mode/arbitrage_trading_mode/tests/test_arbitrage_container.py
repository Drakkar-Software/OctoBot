#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import decimal

import octobot_trading.enums as trading_enums
import tentacles.Trading.Mode.arbitrage_trading_mode.arbitrage_container as arbitrage_container_import


def test_is_similar_with_prices_close_to_own_price():
    container = arbitrage_container_import.ArbitrageContainer(decimal.Decimal(90), decimal.Decimal(100),
                                                              trading_enums.EvaluatorStates.LONG)
    # same price and state
    assert container.is_similar(decimal.Decimal(90), trading_enums.EvaluatorStates.LONG)
    # same price but different state
    assert not container.is_similar(decimal.Decimal(90), trading_enums.EvaluatorStates.SHORT)

    # too different prices comparing to own_exchange_price
    for price in (decimal.Decimal(110), decimal.Decimal(200), decimal.Decimal(80),
                  decimal.Decimal(20), decimal.Decimal(0)):
        assert not container.is_similar(price, trading_enums.EvaluatorStates.LONG)
        assert not container.is_similar(price, trading_enums.EvaluatorStates.LONG)

    # similar prices comparing to own_exchange_price
    for price in (decimal.Decimal(str(89.97)), decimal.Decimal(str(90.01))):
        assert container.is_similar(price, trading_enums.EvaluatorStates.LONG)
        assert container.is_similar(price, trading_enums.EvaluatorStates.LONG)


def test_is_similar_with_prices_close_to_own_price_very_low_prices():
    container = arbitrage_container_import.ArbitrageContainer(decimal.Decimal(str(0.00000621)),
                                                              decimal.Decimal(str(0.00000645)),
                                                              trading_enums.EvaluatorStates.LONG)

    # too different prices comparing to own_exchange_price
    for price in (decimal.Decimal(str(0.0000060)), decimal.Decimal(str(0.0000061)), decimal.Decimal(str(0.0000065)),
                  decimal.Decimal(str(0.000007))):
        assert not container.is_similar(price, trading_enums.EvaluatorStates.LONG)
        assert not container.is_similar(price, trading_enums.EvaluatorStates.LONG)

    # similar prices comparing to own_exchange_price
    for price in (decimal.Decimal(str(0.000006196)), decimal.Decimal(str(0.00000620)), decimal.Decimal(str(0.00000646)),
                  decimal.Decimal(str(0.000006463))):
        assert container.is_similar(price, trading_enums.EvaluatorStates.LONG)
        assert container.is_similar(price, trading_enums.EvaluatorStates.LONG)

    container = arbitrage_container_import.ArbitrageContainer(decimal.Decimal(str(0.00000062)),
                                                              decimal.Decimal(str(0.00000064)),
                                                              trading_enums.EvaluatorStates.LONG)

    # too different prices comparing to own_exchange_price
    for price in (decimal.Decimal(str(0.00000060)), decimal.Decimal(str(0.00000061)), decimal.Decimal(str(0.00000065)),
                  decimal.Decimal(str(0.0000007))):
        assert not container.is_similar(price, trading_enums.EvaluatorStates.LONG)
        assert not container.is_similar(price, trading_enums.EvaluatorStates.LONG)

    # similar prices comparing to own_exchange_price
    for price in (decimal.Decimal(str(0.0000006199)), decimal.Decimal(str(0.0000006401))):
        assert container.is_similar(price, trading_enums.EvaluatorStates.LONG)
        assert container.is_similar(price, trading_enums.EvaluatorStates.LONG)


def test_is_similar_with_prices_in_arbitrage_range():
    container = arbitrage_container_import.ArbitrageContainer(decimal.Decimal(90), decimal.Decimal(100),
                                                              trading_enums.EvaluatorStates.LONG)

    for price in range(int(container.own_exchange_price), int(container.target_price)):
        assert container.is_similar(price, trading_enums.EvaluatorStates.LONG)
        assert container.is_similar(price, trading_enums.EvaluatorStates.LONG)

    container = arbitrage_container_import.ArbitrageContainer(decimal.Decimal(100), decimal.Decimal(90),
                                                              trading_enums.EvaluatorStates.SHORT)

    for price in range(int(container.target_price), int(container.own_exchange_price)):
        assert container.is_similar(price, trading_enums.EvaluatorStates.SHORT)
        assert container.is_similar(price, trading_enums.EvaluatorStates.SHORT)


def test_is_expired():
    container = arbitrage_container_import.ArbitrageContainer(decimal.Decimal(90), decimal.Decimal(100),
                                                              trading_enums.EvaluatorStates.LONG)
    assert not container.is_expired(decimal.Decimal(99.99))
    assert container.is_expired(decimal.Decimal(99))

    container = arbitrage_container_import.ArbitrageContainer(decimal.Decimal(100), decimal.Decimal(90),
                                                              trading_enums.EvaluatorStates.SHORT)
    assert not container.is_expired(decimal.Decimal(90.01))
    assert container.is_expired(decimal.Decimal(91))


def test_is_expired_very_low_prices():
    container = arbitrage_container_import.ArbitrageContainer(decimal.Decimal(str(0.00000621)),
                                                              decimal.Decimal(str(0.00000645)),
                                                              trading_enums.EvaluatorStates.LONG)
    assert not container.is_expired(decimal.Decimal(str(0.00000644)))
    assert container.is_expired(decimal.Decimal(str(0.00000643)))

    container = arbitrage_container_import.ArbitrageContainer(decimal.Decimal(str(0.00000062)),
                                                              decimal.Decimal(str(0.00000064)),
                                                              trading_enums.EvaluatorStates.LONG)
    assert not container.is_expired(decimal.Decimal(str(0.000000639)))
    assert container.is_expired(decimal.Decimal(str(0.000000637)))


def test_should_be_discarded_after_order_cancel():
    container = arbitrage_container_import.ArbitrageContainer(90, 100, trading_enums.EvaluatorStates.LONG)
    assert not container.should_be_discarded_after_order_cancel("123")
    container.initial_limit_order_id = "123"
    assert container.should_be_discarded_after_order_cancel("123")
    assert not container.should_be_discarded_after_order_cancel("1234")


def test_is_watching_this_order():
    container = arbitrage_container_import.ArbitrageContainer(90, 100, trading_enums.EvaluatorStates.LONG)
    assert not container.is_watching_this_order("init")
    assert not container.is_watching_this_order("sec")
    assert not container.is_watching_this_order("stop")

    container.initial_limit_order_id = "init"
    assert container.is_watching_this_order("init")
    assert not container.is_watching_this_order("sec")
    assert not container.is_watching_this_order("stop")

    container.secondary_limit_order_id = "sec"
    assert container.is_watching_this_order("init")
    assert container.is_watching_this_order("sec")
    assert not container.is_watching_this_order("stop")

    container.secondary_stop_order_id = "stop"
    assert container.is_watching_this_order("init")
    assert container.is_watching_this_order("sec")
    assert container.is_watching_this_order("stop")

    container.initial_limit_order_id = None
    assert not container.is_watching_this_order("init")
    assert container.is_watching_this_order("sec")
    assert container.is_watching_this_order("stop")

    container.secondary_limit_order_id = None
    assert not container.is_watching_this_order("init")
    assert not container.is_watching_this_order("sec")
    assert container.is_watching_this_order("stop")

    container.secondary_stop_order_id = None
    assert not container.is_watching_this_order("init")
    assert not container.is_watching_this_order("sec")
    assert not container.is_watching_this_order("stop")
