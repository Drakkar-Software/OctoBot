#  Drakkar-Software OctoBot-Evaluators
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
import time

import pytest
from octobot_commons.constants import MINUTE_TO_SECONDS, START_PENDING_EVAL_NOTE

from octobot_commons.enums import TimeFramesMinutes, TimeFrames

from octobot_evaluators.matrix.matrix import Matrix
from octobot_evaluators.matrix.matrix_manager import get_tentacle_path, get_tentacle_value_path, \
    get_tentacle_nodes, get_tentacles_value_nodes, get_matrix_default_value_path, set_tentacle_value, \
    get_tentacle_value, get_tentacle_node, get_available_symbols, \
    is_tentacle_value_valid, is_tentacles_values_valid, get_evaluations_by_evaluator, get_available_time_frames, \
    delete_tentacle_node
from octobot_evaluators.errors import UnsetTentacleEvaluation
from octobot_evaluators.matrix.matrices import Matrices


@pytest.mark.asyncio
async def test_set_tentacle_value():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)
    set_tentacle_value(matrix.matrix_id, tentacle_type="TA", tentacle_value=0, tentacle_path=["test-path"])
    assert matrix.get_node_at_path(["test-path"]).node_value == 0

    set_tentacle_value(matrix.matrix_id, tentacle_type="TA", tentacle_value="value", tentacle_path=
    get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA", exchange_name="binance"))
    assert matrix.get_node_at_path(
        get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA", exchange_name="binance")).node_value == "value"
    Matrices.instance().del_matrix(matrix.matrix_id)


@pytest.mark.asyncio
async def test_get_tentacle_value():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)
    assert not get_tentacle_value(matrix.matrix_id, tentacle_path=["Test-TA"])

    matrix.matrix.get_or_create_node(path=["Test-TA"])
    matrix.set_node_value(value_type="TA", value_path=["Test-TA"], value=0)
    assert get_tentacle_value(matrix.matrix_id, tentacle_path=["Test-TA"]) == 0

    matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA"))
    matrix.set_node_value(value_type="TA", value_path=get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA"),
                          value="test")
    assert get_tentacle_value(matrix.matrix_id, tentacle_path=get_tentacle_path(tentacle_type="TA",
                                                                                tentacle_name="Test-TA")) == "test"
    Matrices.instance().del_matrix(matrix.matrix_id)


def test_get_matrix_default_value_path():
    assert get_matrix_default_value_path(tentacle_type="TA", tentacle_name="Test-TA", exchange_name="binance") == \
           get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA", exchange_name="binance")
    assert get_matrix_default_value_path(tentacle_type="TA", tentacle_name="Test-TA",
                                         symbol="ETH", time_frame="1h") == \
           get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA") + \
           get_tentacle_value_path(symbol="ETH", time_frame="1h")
    assert get_matrix_default_value_path(tentacle_type="TA", tentacle_name="Test-TA",
                                         symbol="ETH", exchange_name="bitmex") == \
           get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA", exchange_name="bitmex") + \
           get_tentacle_value_path(symbol="ETH")


def test_get_tentacle_path():
    assert get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA", exchange_name="binance") == ["binance", "TA",
                                                                                                       "Test-TA"]
    assert get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA") == ["TA", "Test-TA"]
    assert get_tentacle_path(exchange_name="binance", tentacle_name="Test-TA") == ["binance", "Test-TA"]
    assert get_tentacle_path(tentacle_name="Test-TA") == ["Test-TA"]


def test_get_tentacle_value_path():
    assert get_tentacle_value_path() == []
    assert get_tentacle_value_path(symbol="BTC") == ["BTC"]
    assert get_tentacle_value_path(time_frame="1m") == ["1m"]
    assert get_tentacle_value_path(symbol="ETH", time_frame="1h") == ["ETH", "1h"]


@pytest.mark.asyncio
async def test_get_tentacle_nodes_on_root():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)
    created_node_1 = matrix.matrix.get_or_create_node(
        get_tentacle_path(tentacle_type="NO_TYPE", tentacle_name="Test-TA"))
    created_node_2 = matrix.matrix.get_or_create_node(
        get_tentacle_path(exchange_name="binance", tentacle_name="Test-TA-2"))
    created_node_3 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_name="Test-TA-3"))
    assert get_tentacle_nodes(matrix.matrix_id) == [matrix.get_node_at_path(get_tentacle_path(tentacle_type="NO_TYPE")),
                                                    matrix.get_node_at_path(get_tentacle_path(exchange_name="binance")),
                                                    created_node_3]

    assert get_tentacle_nodes(matrix.matrix_id, tentacle_type="TA") == []
    assert get_tentacle_nodes(matrix.matrix_id, exchange_name="bitfinex") == []
    assert get_tentacle_nodes(matrix.matrix_id, tentacle_type="NO_TYPE") == [created_node_1]
    assert get_tentacle_nodes(matrix.matrix_id, exchange_name="binance") == [created_node_2]
    Matrices.instance().del_matrix(matrix.matrix_id)


@pytest.mark.asyncio
async def test_get_tentacle_nodes_on_tentacle_type():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)
    created_node_1 = matrix.matrix.get_or_create_node(
        get_tentacle_path(tentacle_type="NO_TYPE", tentacle_name="Test-TA"))
    created_node_2 = matrix.matrix.get_or_create_node(
        get_tentacle_path(tentacle_type="TEST_TYPE", tentacle_name="Test-TA-2"))

    assert get_tentacle_nodes(matrix.matrix_id, tentacle_type="TA") == []
    assert get_tentacle_nodes(matrix.matrix_id, tentacle_type="NO_TYPE") == [created_node_1]
    assert get_tentacle_nodes(matrix.matrix_id, tentacle_type="TEST_TYPE") == [created_node_2]
    Matrices.instance().del_matrix(matrix.matrix_id)


@pytest.mark.asyncio
async def test_get_tentacle_nodes_on_exchange_name_and_tentacle_type():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)
    created_node_1 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="NO_TYPE",
                                                                        tentacle_name="Test-TA",
                                                                        exchange_name="binance"))
    created_node_2 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TEST_TYPE",
                                                                        tentacle_name="Test-TA-2",
                                                                        exchange_name="binance"))
    assert get_tentacle_nodes(matrix.matrix_id, exchange_name="binance") == [
        matrix.get_node_at_path(get_tentacle_path(exchange_name="binance",
                                                  tentacle_type="NO_TYPE")),
        matrix.get_node_at_path(get_tentacle_path(exchange_name="binance",
                                                  tentacle_type="TEST_TYPE"))]
    assert get_tentacle_nodes(matrix.matrix_id, exchange_name="binance", tentacle_type="NO_TYPE") == [created_node_1]
    assert get_tentacle_nodes(matrix.matrix_id, exchange_name="binance", tentacle_type="TEST_TYPE") == [created_node_2]
    assert get_tentacle_nodes(matrix.matrix_id, exchange_name="bitfinex") == []
    Matrices.instance().del_matrix(matrix.matrix_id)


@pytest.mark.asyncio
async def test_get_tentacle_nodes_on_exchange_name():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)
    created_node_1 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_name="Test-TA",
                                                                        exchange_name="binance"))
    created_node_2 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_name="Test-TA-2",
                                                                        exchange_name="binance"))

    assert get_tentacle_nodes(matrix.matrix_id, exchange_name="bitfinex") == []
    assert get_tentacle_nodes(matrix.matrix_id, tentacle_type="NO_TYPE") == []
    assert get_tentacle_nodes(matrix.matrix_id, exchange_name="binance") == [created_node_1, created_node_2]
    Matrices.instance().del_matrix(matrix.matrix_id)


@pytest.mark.asyncio
async def test_get_tentacle_nodes_on_multiple_tentacle_type():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)
    created_node_1 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA"))
    created_node_2 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA-2"))
    created_node_3 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA-3"))
    assert get_tentacle_nodes(matrix.matrix_id, tentacle_type="TA") == [created_node_1, created_node_2, created_node_3]
    Matrices.instance().del_matrix(matrix.matrix_id)


@pytest.mark.asyncio
async def test_get_tentacle_nodes_on_multiple_tentacle_type_and_exchange_name():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)
    created_node_1 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA",
                                                                        tentacle_name="Test-TA",
                                                                        exchange_name="binance"))
    created_node_2 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA",
                                                                        tentacle_name="Test-TA-2",
                                                                        exchange_name="binance"))
    created_node_3 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA",
                                                                        tentacle_name="Test-TA-3",
                                                                        exchange_name="binance"))
    assert get_tentacle_nodes(matrix.matrix_id, exchange_name="binance", tentacle_type="TA") == [created_node_1,
                                                                                                 created_node_2,
                                                                                                 created_node_3]
    Matrices.instance().del_matrix(matrix.matrix_id)


@pytest.mark.asyncio
async def test_get_tentacle_nodes_mixed():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)
    created_node_1 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA",
                                                                        tentacle_name="Test-TA",
                                                                        exchange_name="binance"))
    created_node_2 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA",
                                                                        tentacle_name="Test-TA-2",
                                                                        exchange_name="bitfinex"))
    created_node_3 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA",
                                                                        tentacle_name="Test-TA-3",
                                                                        exchange_name="binance"))
    created_node_4 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TEST-TYPE",
                                                                        tentacle_name="Test-TA-4",
                                                                        exchange_name="binance"))
    created_node_5 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TEST-TYPE",
                                                                        tentacle_name="Test-TA-5",
                                                                        exchange_name="bitfinex"))
    created_node_6 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TEST-TYPE",
                                                                        tentacle_name="Test-TA-6"))
    created_node_7 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_name="Test-TA-7",
                                                                        exchange_name="bitfinex"))
    created_node_8 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_name="Test-TA-8"))
    created_node_9 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_name="Test-TA-9",
                                                                        exchange_name="binance"))
    assert get_tentacle_nodes(matrix.matrix_id, exchange_name="binance", tentacle_type="TA") == [created_node_1,
                                                                                                 created_node_3]
    assert get_tentacle_nodes(matrix.matrix_id, exchange_name="binance", tentacle_type="TEST-TYPE") == [created_node_4]

    assert get_tentacle_nodes(matrix.matrix_id, exchange_name="bitfinex", tentacle_type="TEST-TYPE") == [created_node_5]

    assert get_tentacle_nodes(matrix.matrix_id, exchange_name="bitfinex") == [
        matrix.get_node_at_path(get_tentacle_path(exchange_name="bitfinex", tentacle_type="TA")),
        matrix.get_node_at_path(get_tentacle_path(exchange_name="bitfinex", tentacle_type="TEST-TYPE")),
        created_node_7]

    assert get_tentacle_nodes(matrix.matrix_id, tentacle_type="TEST-TYPE") == [created_node_6]

    assert get_tentacle_nodes(matrix.matrix_id, exchange_name="binance") == [
        matrix.get_node_at_path(get_tentacle_path(exchange_name="binance", tentacle_type="TA")),
        matrix.get_node_at_path(get_tentacle_path(exchange_name="binance", tentacle_type="TEST-TYPE")),
        created_node_9]
    Matrices.instance().del_matrix(matrix.matrix_id)


@pytest.mark.asyncio
async def test_get_tentacles_value_nodes_with_symbol():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)
    created_node = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA"))
    created_node_2 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA-2"))
    btc_node = matrix.matrix.get_or_create_node(get_tentacle_value_path(symbol="BTC"), starting_node=created_node)
    eth_node = matrix.matrix.get_or_create_node(get_tentacle_value_path(symbol="ETH"), starting_node=created_node)
    btc_node_2 = matrix.matrix.get_or_create_node(get_tentacle_value_path(symbol="BTC"), starting_node=created_node_2)
    assert get_tentacles_value_nodes(matrix.matrix_id, tentacle_nodes=[created_node, created_node_2],
                                     symbol="BTC") == [btc_node, btc_node_2]
    assert get_tentacles_value_nodes(matrix.matrix_id, tentacle_nodes=[created_node, created_node_2],
                                     symbol="ETH") == [eth_node]
    Matrices.instance().del_matrix(matrix.matrix_id)


@pytest.mark.asyncio
async def test_get_tentacles_value_nodes_with_time_frame():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)
    assert get_tentacle_value_path(time_frame="1m") == ["1m"]
    created_node = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA"))
    created_node_2 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA-2"))
    m_node = matrix.matrix.get_or_create_node(get_tentacle_value_path(time_frame="1m"), starting_node=created_node)
    h_node = matrix.matrix.get_or_create_node(get_tentacle_value_path(time_frame="1h"), starting_node=created_node)
    h_node_2 = matrix.matrix.get_or_create_node(get_tentacle_value_path(time_frame="1h"), starting_node=created_node_2)
    assert get_tentacles_value_nodes(matrix.matrix_id, tentacle_nodes=[created_node, created_node_2],
                                     time_frame="1h") == [h_node, h_node_2]
    assert get_tentacles_value_nodes(matrix.matrix_id, tentacle_nodes=[created_node, created_node_2],
                                     symbol="1m") == [m_node]
    Matrices.instance().del_matrix(matrix.matrix_id)


@pytest.mark.asyncio
async def test_get_tentacles_value_nodes_with_symbol_and_time_frame():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)
    assert get_tentacle_value_path(symbol="ETH", time_frame="1h") == ["ETH", "1h"]

    created_node = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA"))
    created_node_2 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA-2"))
    created_node_3 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA-3"))
    btc_h_node = matrix.matrix.get_or_create_node(get_tentacle_value_path(symbol="BTC", time_frame="1h"),
                                                  starting_node=created_node)
    btc_m_node = matrix.matrix.get_or_create_node(get_tentacle_value_path(symbol="BTC", time_frame="1m"),
                                                  starting_node=created_node_2)
    eth_h_node = matrix.matrix.get_or_create_node(get_tentacle_value_path(symbol="ETH", time_frame="1h"),
                                                  starting_node=created_node_3)
    eth_m_node = matrix.matrix.get_or_create_node(get_tentacle_value_path(symbol="ETH", time_frame="1m"),
                                                  starting_node=created_node_2)
    eth_d_node = matrix.matrix.get_or_create_node(get_tentacle_value_path(symbol="ETH", time_frame="1d"),
                                                  starting_node=created_node)
    ltc_h_node = matrix.matrix.get_or_create_node(get_tentacle_value_path(symbol="LTC", time_frame="1h"),
                                                  starting_node=created_node_2)
    assert get_tentacles_value_nodes(matrix.matrix_id, tentacle_nodes=[created_node, created_node_2, created_node_3],
                                     symbol="BTC", time_frame="1h") == [btc_h_node]
    assert get_tentacles_value_nodes(matrix.matrix_id, tentacle_nodes=[created_node, created_node_2, created_node_3],
                                     symbol="BTC") == [
               matrix.get_node_at_path(get_tentacle_value_path(symbol="BTC"), starting_node=created_node),
               matrix.get_node_at_path(get_tentacle_value_path(symbol="BTC"), starting_node=created_node_2)]
    assert get_tentacles_value_nodes(matrix.matrix_id, tentacle_nodes=[created_node, created_node_3],
                                     symbol="BTC") == [
               matrix.get_node_at_path(get_tentacle_value_path(symbol="BTC"), starting_node=created_node)]
    assert get_tentacles_value_nodes(matrix.matrix_id, tentacle_nodes=[created_node, created_node_3],
                                     symbol="BTC", time_frame="1m") == []
    assert get_tentacles_value_nodes(matrix.matrix_id, tentacle_nodes=[created_node_3],
                                     symbol="BTC") == []
    assert get_tentacles_value_nodes(matrix.matrix_id, tentacle_nodes=[created_node, created_node_2, created_node_3],
                                     symbol="ETH") == [
               matrix.get_node_at_path(get_tentacle_value_path(symbol="ETH"), starting_node=created_node),
               matrix.get_node_at_path(get_tentacle_value_path(symbol="ETH"), starting_node=created_node_2),
               matrix.get_node_at_path(get_tentacle_value_path(symbol="ETH"), starting_node=created_node_3)]
    Matrices.instance().del_matrix(matrix.matrix_id)


@pytest.mark.asyncio
async def test_get_tentacles_value_nodes_mixed():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)

    created_node = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA"))
    created_node_2 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA-2"))
    created_node_3 = matrix.matrix.get_or_create_node(get_tentacle_path(tentacle_type="TA", tentacle_name="Test-TA-3"))
    btc_h_node = matrix.matrix.get_or_create_node(get_tentacle_value_path(symbol="BTC", time_frame="1h"),
                                                  starting_node=created_node)
    btc_node = matrix.matrix.get_or_create_node(get_tentacle_value_path(symbol="BTC"), starting_node=created_node_2)
    eth_node = matrix.matrix.get_or_create_node(get_tentacle_value_path(symbol="ETH"), starting_node=created_node_3)
    eth_m_node = matrix.matrix.get_or_create_node(get_tentacle_value_path(symbol="ETH", time_frame="1m"),
                                                  starting_node=created_node_2)
    eth_d_node = matrix.matrix.get_or_create_node(get_tentacle_value_path(symbol="ETH", time_frame="1d"),
                                                  starting_node=created_node)
    ltc_h_node = matrix.matrix.get_or_create_node(get_tentacle_value_path(symbol="LTC", time_frame="1h"),
                                                  starting_node=created_node_2)

    assert get_tentacles_value_nodes(matrix.matrix_id, tentacle_nodes=[created_node, created_node_2, created_node_3],
                                     symbol="BTC", time_frame="1h") == [btc_h_node]
    assert get_tentacles_value_nodes(matrix.matrix_id, tentacle_nodes=[created_node, created_node_2, created_node_3],
                                     symbol="BTC") == [
               matrix.get_node_at_path(get_tentacle_value_path(symbol="BTC"), starting_node=created_node),
               matrix.get_node_at_path(get_tentacle_value_path(symbol="BTC"), starting_node=created_node_2)]
    assert get_tentacles_value_nodes(matrix.matrix_id, tentacle_nodes=[created_node, created_node_3],
                                     symbol="BTC") == [
               matrix.get_node_at_path(get_tentacle_value_path(symbol="BTC"), starting_node=created_node)]
    assert get_tentacles_value_nodes(matrix.matrix_id, tentacle_nodes=[created_node, created_node_3],
                                     symbol="BTC", time_frame="1m") == []
    assert get_tentacles_value_nodes(matrix.matrix_id, tentacle_nodes=[created_node_3],
                                     symbol="BTC") == []
    assert get_tentacles_value_nodes(matrix.matrix_id, tentacle_nodes=[created_node, created_node_2, created_node_3],
                                     symbol="ETH") == [
               matrix.get_node_at_path(get_tentacle_value_path(symbol="ETH"), starting_node=created_node),
               matrix.get_node_at_path(get_tentacle_value_path(symbol="ETH"), starting_node=created_node_2),
               matrix.get_node_at_path(get_tentacle_value_path(symbol="ETH"), starting_node=created_node_3)]
    Matrices.instance().del_matrix(matrix.matrix_id)


def test_delete_tentacle_node():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)

    evaluator_1_path = get_matrix_default_value_path(tentacle_type="TA", tentacle_name="Test-TA",
                                                     cryptocurrency="BTC",
                                                     symbol="BTC/USD",
                                                     time_frame="1m")
    evaluator_2_path = get_matrix_default_value_path(tentacle_type="TA", tentacle_name="Test-TA",
                                                     cryptocurrency="BTC",
                                                     symbol="BTC/USD",
                                                     time_frame="1h")

    # simulate AbstractEvaluator.initialize()
    set_tentacle_value(matrix.matrix_id, evaluator_1_path, "TA", None)
    set_tentacle_value(matrix.matrix_id, evaluator_2_path, "TA", None)

    assert delete_tentacle_node(matrix.matrix_id, ["non_existing"]) is None

    # deleted: returned the deleted node
    assert delete_tentacle_node(matrix.matrix_id, evaluator_2_path) is not None

    # already deleted
    assert delete_tentacle_node(matrix.matrix_id, evaluator_2_path) is None



@pytest.mark.asyncio
async def test_is_tentacle_value_valid():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)

    evaluator_1_path = get_matrix_default_value_path(tentacle_type="TA", tentacle_name="Test-TA",
                                                     cryptocurrency="BTC",
                                                     symbol="BTC/USD",
                                                     time_frame="1m")
    evaluator_2_path = get_matrix_default_value_path(tentacle_type="TA", tentacle_name="Test-TA",
                                                     cryptocurrency="BTC",
                                                     symbol="BTC/USD",
                                                     time_frame="1h")

    # simulate AbstractEvaluator.initialize()
    set_tentacle_value(matrix.matrix_id, evaluator_1_path, "TA", None)
    set_tentacle_value(matrix.matrix_id, evaluator_2_path, "TA", None)

    get_tentacle_node(matrix.matrix_id, evaluator_1_path).node_value_time = time.time()
    assert is_tentacle_value_valid(matrix.matrix_id, evaluator_1_path)
    assert not is_tentacle_value_valid(matrix.matrix_id, evaluator_2_path)

    set_tentacle_value(matrix.matrix_id, evaluator_2_path, "TA", None, timestamp=100)
    assert not is_tentacle_value_valid(matrix.matrix_id, evaluator_2_path)

    set_tentacle_value(matrix.matrix_id, evaluator_2_path, "TA", None,
                       timestamp=time.time() - TimeFramesMinutes[TimeFrames.ONE_HOUR] * 2 * MINUTE_TO_SECONDS)
    assert not is_tentacle_value_valid(matrix.matrix_id, evaluator_2_path)

    set_tentacle_value(matrix.matrix_id, evaluator_2_path, "TA", None,
                       timestamp=time.time() - TimeFramesMinutes[TimeFrames.ONE_HOUR] * MINUTE_TO_SECONDS)
    assert is_tentacle_value_valid(matrix.matrix_id, evaluator_2_path)

    # test non existing node
    with pytest.raises(KeyError):
        is_tentacle_value_valid(matrix.matrix_id, evaluator_2_path + ["other"])

    # test delta
    set_tentacle_value(matrix.matrix_id, evaluator_2_path, "TA", None,
                       timestamp=time.time() - TimeFramesMinutes[TimeFrames.ONE_HOUR] * MINUTE_TO_SECONDS - 10)
    assert not is_tentacle_value_valid(matrix.matrix_id, evaluator_2_path)

    # test delta
    set_tentacle_value(matrix.matrix_id, evaluator_2_path, "TA", None,
                       timestamp=time.time() - TimeFramesMinutes[TimeFrames.ONE_HOUR] * MINUTE_TO_SECONDS - 9)
    assert is_tentacle_value_valid(matrix.matrix_id, evaluator_2_path)

    # test modified delta
    set_tentacle_value(matrix.matrix_id, evaluator_2_path, "TA", None,
                       timestamp=time.time() - TimeFramesMinutes[TimeFrames.ONE_HOUR] * MINUTE_TO_SECONDS - 29)
    assert is_tentacle_value_valid(matrix.matrix_id, evaluator_2_path, delta=30)

    # test modified delta
    set_tentacle_value(matrix.matrix_id, evaluator_2_path, "TA", None,
                       timestamp=time.time() - TimeFramesMinutes[TimeFrames.ONE_HOUR] * MINUTE_TO_SECONDS - 31)
    assert not is_tentacle_value_valid(matrix.matrix_id, evaluator_2_path, delta=30)

    Matrices.instance().del_matrix(matrix.matrix_id)


@pytest.mark.asyncio
async def test_is_tentacles_values_valid():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)

    evaluator_1_path = get_matrix_default_value_path(tentacle_type="TA", tentacle_name="Test-TA",
                                                     cryptocurrency="BTC",
                                                     symbol="BTC/USD",
                                                     time_frame="1m")
    evaluator_2_path = get_matrix_default_value_path(tentacle_type="TA", tentacle_name="Test-TA",
                                                     cryptocurrency="BTC",
                                                     symbol="BTC/USD",
                                                     time_frame="1h")

    # simulate AbstractEvaluator.initialize()
    set_tentacle_value(matrix.matrix_id, evaluator_1_path, "TA", None)
    set_tentacle_value(matrix.matrix_id, evaluator_2_path, "TA", None)

    assert not is_tentacles_values_valid(matrix.matrix_id, [evaluator_1_path, evaluator_2_path])

    set_tentacle_value(matrix.matrix_id, evaluator_1_path, "TA", None,
                       timestamp=time.time() - TimeFramesMinutes[TimeFrames.ONE_MINUTE] * 2 * MINUTE_TO_SECONDS)
    set_tentacle_value(matrix.matrix_id, evaluator_2_path, "TA", None,
                       timestamp=time.time() - TimeFramesMinutes[TimeFrames.ONE_HOUR] * 2 * MINUTE_TO_SECONDS)
    assert not is_tentacles_values_valid(matrix.matrix_id, [evaluator_1_path, evaluator_2_path])

    set_tentacle_value(matrix.matrix_id, evaluator_1_path, "TA", None,
                       timestamp=time.time() - TimeFramesMinutes[TimeFrames.ONE_MINUTE] * MINUTE_TO_SECONDS)
    assert not is_tentacles_values_valid(matrix.matrix_id, [evaluator_1_path, evaluator_2_path])

    set_tentacle_value(matrix.matrix_id, evaluator_2_path, "TA", None,
                       timestamp=time.time() - TimeFramesMinutes[TimeFrames.ONE_HOUR] * MINUTE_TO_SECONDS)
    assert is_tentacles_values_valid(matrix.matrix_id, [evaluator_1_path, evaluator_2_path])
    Matrices.instance().del_matrix(matrix.matrix_id)


@pytest.mark.asyncio
async def test_get_evaluations_by_evaluator():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)

    evaluator_1_path = get_matrix_default_value_path(tentacle_type="TA",
                                                     exchange_name="kraken",
                                                     tentacle_name="RSI",
                                                     cryptocurrency="BTC",
                                                     symbol="BTC/USD",
                                                     time_frame="1m")
    evaluator_2_path = get_matrix_default_value_path(tentacle_type="TA",
                                                     exchange_name="kraken",
                                                     tentacle_name="ADX",
                                                     cryptocurrency="BTC",
                                                     symbol="BTC/USD",
                                                     time_frame="1m")
    evaluator_3_path = get_matrix_default_value_path(tentacle_type="TA",
                                                     exchange_name="kraken",
                                                     tentacle_name="ADX",
                                                     cryptocurrency="BTC",
                                                     symbol="BTC/USD",
                                                     time_frame="1h")

    # simulate AbstractEvaluator.initialize()
    set_tentacle_value(matrix.matrix_id, evaluator_1_path, "TA", 1)
    set_tentacle_value(matrix.matrix_id, evaluator_2_path, "TA", -0.5)
    set_tentacle_value(matrix.matrix_id, evaluator_3_path, "TA", 0)

    assert get_evaluations_by_evaluator(matrix.matrix_id,
                                        tentacle_type="TA",
                                        exchange_name="kraken",
                                        cryptocurrency="BTC",
                                        symbol="BTC/USD",
                                        time_frame="1m") == {
               "RSI": get_tentacle_node(matrix.matrix_id, evaluator_1_path),
               "ADX": get_tentacle_node(matrix.matrix_id, evaluator_2_path)
           }

    # set invalid value to not to add this value in result dict
    set_tentacle_value(matrix.matrix_id, evaluator_2_path, "TA", START_PENDING_EVAL_NOTE)
    with pytest.raises(UnsetTentacleEvaluation):
        get_evaluations_by_evaluator(matrix.matrix_id,
                                     tentacle_type="TA",
                                     exchange_name="kraken",
                                     cryptocurrency="BTC",
                                     symbol="BTC/USD",
                                     time_frame="1m",
                                     allow_missing=False)
    assert get_evaluations_by_evaluator(matrix.matrix_id,
                                        tentacle_type="TA",
                                        exchange_name="kraken",
                                        cryptocurrency="BTC",
                                        symbol="BTC/USD",
                                        time_frame="1m",
                                        allow_missing=True) == {
               "RSI": get_tentacle_node(matrix.matrix_id, evaluator_1_path)
           }
    assert get_evaluations_by_evaluator(matrix.matrix_id,
                                        tentacle_type="TA",
                                        exchange_name="kraken",
                                        cryptocurrency="BTC",
                                        symbol="BTC/USD",
                                        time_frame="1m",
                                        allow_missing=True,
                                        allowed_values=[START_PENDING_EVAL_NOTE]) == {
               "RSI": get_tentacle_node(matrix.matrix_id, evaluator_1_path),
               "ADX": get_tentacle_node(matrix.matrix_id, evaluator_2_path)
           }

    # invalid path
    assert get_evaluations_by_evaluator(matrix.matrix_id,
                                        tentacle_type="TA_invalid",
                                        exchange_name="kraken",
                                        cryptocurrency="BTC",
                                        symbol="BTC/USD",
                                        time_frame="1m",
                                        allow_missing=True,
                                        allowed_values=[START_PENDING_EVAL_NOTE]) == {}


@pytest.mark.asyncio
async def test_get_available_time_frames():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)

    evaluator_1_path = get_matrix_default_value_path(tentacle_type="TA",
                                                     exchange_name="kraken",
                                                     tentacle_name="RSI",
                                                     cryptocurrency="BTC",
                                                     symbol="BTC/USD",
                                                     time_frame="1m")
    evaluator_2_path = get_matrix_default_value_path(tentacle_type="TA",
                                                     exchange_name="kraken",
                                                     tentacle_name="ADX",
                                                     cryptocurrency="BTC",
                                                     symbol="BTC/USD",
                                                     time_frame="1m")
    evaluator_3_path = get_matrix_default_value_path(tentacle_type="TA",
                                                     exchange_name="kraken",
                                                     tentacle_name="ADX",
                                                     cryptocurrency="BTC",
                                                     symbol="BTC/USD",
                                                     time_frame="1h")
    evaluator_4_path = get_matrix_default_value_path(tentacle_type="TA",
                                                     exchange_name="kraken",
                                                     tentacle_name="RSI",
                                                     cryptocurrency="BTC",
                                                     symbol="BTC/USD",
                                                     time_frame="1h")

    # simulate AbstractEvaluator.initialize()
    set_tentacle_value(matrix.matrix_id, evaluator_1_path, "TA", 1)
    set_tentacle_value(matrix.matrix_id, evaluator_2_path, "TA", -0.5)
    set_tentacle_value(matrix.matrix_id, evaluator_3_path, "TA", 0)
    set_tentacle_value(matrix.matrix_id, evaluator_4_path, "TA", -1)

    assert get_available_time_frames(matrix.matrix_id,
                                     exchange_name="kraken",
                                     tentacle_type="TA",
                                     cryptocurrency="BTC",
                                     symbol="BTC/USD") == ["1m", "1h"]

    # invalid path
    assert get_available_time_frames(matrix.matrix_id,
                                     exchange_name="kraken",
                                     tentacle_type="TA_invalid",
                                     cryptocurrency="BTC",
                                     symbol="BTC/USD") == []


@pytest.mark.asyncio
async def test_get_available_symbols():
    matrix = Matrix()
    Matrices.instance().add_matrix(matrix)

    evaluator_1_path = get_matrix_default_value_path(tentacle_type="TA",
                                                     exchange_name="kraken",
                                                     tentacle_name="RSI",
                                                     cryptocurrency="BTC",
                                                     symbol="BTC/USD",
                                                     time_frame="1m")
    evaluator_2_path = get_matrix_default_value_path(tentacle_type="TA",
                                                     exchange_name="kraken",
                                                     tentacle_name="RSI",
                                                     cryptocurrency="BTC",
                                                     symbol="BTCX/USDC",
                                                     time_frame="1m")
    evaluator_3_path = get_matrix_default_value_path(tentacle_type="TA",
                                                     exchange_name="kraken",
                                                     tentacle_name="RSI",
                                                     cryptocurrency="BTC",
                                                     symbol="BTCX/USDC",
                                                     time_frame="1h")
    evaluator_4_path = get_matrix_default_value_path(tentacle_type="TA",
                                                     exchange_name="kraken",
                                                     tentacle_name="RSI",
                                                     cryptocurrency="BTC",
                                                     symbol="BTC/USD",
                                                     time_frame="1h")

    # simulate AbstractEvaluator.initialize()
    set_tentacle_value(matrix.matrix_id, evaluator_1_path, "TA", 1)
    set_tentacle_value(matrix.matrix_id, evaluator_2_path, "TA", -0.5)
    set_tentacle_value(matrix.matrix_id, evaluator_3_path, "TA", 0)
    set_tentacle_value(matrix.matrix_id, evaluator_4_path, "TA", -1)

    assert get_available_symbols(matrix.matrix_id,
                                 exchange_name="kraken",
                                 cryptocurrency="BTC") == ["BTC/USD", "BTCX/USDC"]

    # invalid path
    assert get_available_symbols(matrix.matrix_id, exchange_name="invalid_exchange", cryptocurrency="BTC") == []
    assert get_available_symbols(matrix.matrix_id, exchange_name="kraken", cryptocurrency="BTCX") == []
    assert get_available_symbols(matrix.matrix_id, exchange_name="invalid_exchange", cryptocurrency="BTCX") == []

    # now valid using real-time evaluation
    evaluator_5_path = get_matrix_default_value_path(tentacle_type="REAL_TIME",
                                                     exchange_name="kraken",
                                                     tentacle_name="RSI",
                                                     cryptocurrency="BTCX",
                                                     symbol="BTCX/USD",
                                                     time_frame="1h")
    set_tentacle_value(matrix.matrix_id, evaluator_5_path, "REAL_TIME", -1)
    assert get_available_symbols(matrix.matrix_id, exchange_name="kraken", cryptocurrency="BTCX") == ["BTCX/USD"]
