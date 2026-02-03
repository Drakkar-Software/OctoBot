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
import pytest
from mock import patch
import octobot_evaluators.evaluators.evaluator_factory as evaluator_factory
from octobot_commons.enums import TimeFrames
import octobot_commons.symbols
import octobot_commons.tentacles_management as tentacles_management


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def symbols_by_crypto_currencies():
    return {"Bitcoin": ["BTC/USD", "BTC/USDT"], "Ethereum": ["ETH/BTC"]}


@pytest.fixture
def symbols():
    return ["BTC/USD", "BTC/USDT", "ETH/BTC"]


@pytest.fixture
def time_frames():
    return [TimeFrames.THREE_DAYS, TimeFrames.ONE_HOUR]


async def test_create_evaluators_no_wild_card(symbols_by_crypto_currencies, symbols, time_frames):
    evaluators = await _create_evaluators(EvaluatorNoWildCard, symbols_by_crypto_currencies, symbols, time_frames)
    assert len(evaluators) == 6

    # one eval per time frame per symbol (1 symbols)
    assert len([e for e in evaluators if e.cryptocurrency == "ETH"]) == len(time_frames) * 1
    # one eval per time frame per symbol (2 symbols)
    assert len([e for e in evaluators if e.cryptocurrency == "BTC"]) == len(time_frames) * 2

    # right crypto-currency name
    assert all([e.cryptocurrency_name == "Ethereum" for e in evaluators if e.cryptocurrency == "ETH"])
    assert all([e.cryptocurrency_name == "Bitcoin" for e in evaluators if e.cryptocurrency == "BTC"])

    # right crypto-currency
    assert all([e.cryptocurrency == "ETH" for e in evaluators if e.symbol == "ETH/BTC"])
    assert all([e.cryptocurrency == "BTC" for e in evaluators if e.symbol in ["BTC/USD", "BTC/USDT"]])

    # right symbol
    assert all([e.symbol == "ETH/BTC" for e in evaluators if e.cryptocurrency == "ETH"])
    assert all([e.symbol in ["BTC/USD", "BTC/USDT"] for e in evaluators if e.cryptocurrency == "BTC"])
    # all symbols taken into account
    assert len(set([e.symbol for e in evaluators if e.cryptocurrency == "BTC"])) == 2
    assert len(set([e.symbol for e in evaluators if e.cryptocurrency == "ETH"])) == 1

    # valid time frames
    assert all([e.time_frame in time_frames for e in evaluators])
    # all time frames taken into account
    assert len(set([e.time_frame for e in evaluators if e.symbol == "BTC/USD"])) == 2
    assert len(set([e.time_frame for e in evaluators if e.symbol == "BTC/USDT"])) == 2
    assert len(set([e.time_frame for e in evaluators if e.symbol == "ETH/BTC"])) == 2


async def test_create_evaluators_wild_card(symbols_by_crypto_currencies, symbols, time_frames):
    evaluators = await _create_evaluators(EvaluatorWildCard, symbols_by_crypto_currencies, symbols, time_frames)

    # only one wild card evaluator created
    assert len(evaluators) == 1
    assert evaluators[0].cryptocurrency is evaluators[0].cryptocurrency_name is evaluators[0].symbol is \
        evaluators[0].time_frame is None


async def test_create_evaluators_no_cc_wild_card(symbols_by_crypto_currencies, symbols, time_frames):
    evaluators = await _create_evaluators(EvaluatorNoCCWildCard, symbols_by_crypto_currencies, symbols, time_frames)

    # only difference is the cryptocurrency attribute
    assert len(evaluators) == 2
    assert evaluators[0].cryptocurrency_name is evaluators[0].symbol is evaluators[0].time_frame is None
    assert sorted([e.cryptocurrency for e in evaluators]) == sorted(["BTC", "ETH"])


async def test_create_evaluators_no_cc_name_wild_card(symbols_by_crypto_currencies, symbols, time_frames):
    evaluators = await _create_evaluators(EvaluatorNoCCNameWildCard, symbols_by_crypto_currencies, symbols, time_frames)

    # only one wild card evaluator created since EvaluatorNoCCNameWildCard is crypto-currency wild card
    assert len(evaluators) == 1
    assert evaluators[0].cryptocurrency is evaluators[0].cryptocurrency_name is evaluators[0].symbol is \
        evaluators[0].time_frame is None


async def test_create_evaluators_no_cc_name_and_no_cc_wild_card(symbols_by_crypto_currencies, symbols, time_frames):
    evaluators = await _create_evaluators(EvaluatorNoCCNameNoCCWildCard, symbols_by_crypto_currencies,
                                          symbols, time_frames)

    # only differences are the cryptocurrency and cryptocurrency_name attribute
    assert len(evaluators) == 2
    assert evaluators[0].symbol is evaluators[0].time_frame is None
    assert sorted([e.cryptocurrency for e in evaluators]) == sorted(["BTC", "ETH"])
    assert sorted([e.cryptocurrency_name for e in evaluators]) == sorted(["Bitcoin", "Ethereum"])


async def test_create_evaluators_no_symbol_wild_card(symbols_by_crypto_currencies, symbols, time_frames):
    evaluators = await _create_evaluators(EvaluatorNoSymbolWildCard, symbols_by_crypto_currencies, symbols, time_frames)

    # only difference is the symbol attribute
    assert len(evaluators) == 3
    assert evaluators[0].cryptocurrency is evaluators[0].cryptocurrency_name is evaluators[0].time_frame is None
    assert [e.symbol for e in evaluators] == symbols


async def test_create_evaluators_no_time_frame_wild_card(symbols_by_crypto_currencies, symbols, time_frames):
    evaluators = await _create_evaluators(EvaluatorNoTimeFrameWildCard, symbols_by_crypto_currencies,
                                          symbols, time_frames)

    # only difference is the time_frame attribute
    assert len(evaluators) == 2
    assert evaluators[0].cryptocurrency is evaluators[0].cryptocurrency_name is evaluators[0].symbol is None
    assert [e.time_frame for e in evaluators] == time_frames


async def test_create_evaluators_no_cc_name_no_symbol_wild_card(symbols_by_crypto_currencies, symbols, time_frames):
    evaluators = await _create_evaluators(EvaluatorNoCCNameSymbolWildCard, symbols_by_crypto_currencies,
                                          symbols, time_frames)

    # only difference is the symbol attribute since no crypto-currency wildcard name requires also no
    # cryptocurrency wildcard
    assert len(evaluators) == 3
    assert evaluators[0].cryptocurrency is evaluators[0].cryptocurrency_name is evaluators[0].time_frame is None
    assert [e.symbol for e in evaluators] == symbols


async def test_create_evaluators_no_cc_time_frame_wild_card(symbols_by_crypto_currencies, symbols, time_frames):
    evaluators = await _create_evaluators(EvaluatorNoCCTimeFrameWildCard, symbols_by_crypto_currencies,
                                          symbols, time_frames)

    # only differences are on cryptocurrency and time frame attributes
    assert len(evaluators) == 4
    assert evaluators[0].symbol is evaluators[0].cryptocurrency_name is None
    assert sorted(list(set(e.cryptocurrency for e in evaluators))) == sorted(["ETH", "BTC"])
    tfs = set(e.time_frame for e in evaluators)
    assert len(tfs) == 2
    assert all(tf in time_frames for tf in tfs)


async def test_create_evaluators_no_symbol_time_frame_wild_card(symbols_by_crypto_currencies, symbols, time_frames):
    evaluators = await _create_evaluators(EvaluatorNoSymbolTimeFrameWildCard, symbols_by_crypto_currencies,
                                          symbols, time_frames)

    # only differences are on symbol and time frame attributes
    assert len(evaluators) == 6
    assert evaluators[0].cryptocurrency is evaluators[0].cryptocurrency_name is None
    assert sorted(list(set(e.symbol for e in evaluators))) == sorted(symbols)
    tfs = set(e.time_frame for e in evaluators)
    assert len(tfs) == 2
    assert all(tf in time_frames for tf in tfs)


async def _create_evaluators(evaluator_parent_class, symbols_by_crypto_currencies, symbols, time_frames):
    crypto_currency_name_by_crypto_currencies = {}
    symbols_by_crypto_currency_tickers = {}
    for name, symbol_list in symbols_by_crypto_currencies.items():
        ticker = octobot_commons.symbols.parse_symbol(symbol_list[0]).base
        crypto_currency_name_by_crypto_currencies[ticker] = name
        symbols_by_crypto_currency_tickers[ticker] = symbol_list
    with patch("octobot_evaluators.evaluators.evaluator_factory.create_evaluator", new=_mocked_create_evaluator), \
            patch("octobot_commons.tentacles_management.get_all_classes_from_parent",
                  new=_mocked_get_all_classes_from_parent):
        return await evaluator_factory.create_evaluators(
            evaluator_parent_class=evaluator_parent_class,
            tentacles_setup_config=None,
            matrix_id="",
            exchange_name="",
            bot_id="",
            crypto_currency_name_by_crypto_currencies=crypto_currency_name_by_crypto_currencies,
            symbols_by_crypto_currency_tickers=symbols_by_crypto_currency_tickers,
            symbols=symbols,
            time_frames=time_frames
        )


def _mocked_get_all_classes_from_parent(evaluator_parent_class):
    return [evaluator_parent_class]


async def _mocked_create_evaluator(evaluator_class,
                                   tentacles_setup_config: object,
                                   matrix_id: str,
                                   exchange_name: str,
                                   bot_id: str,
                                   cryptocurrency: str = None,
                                   cryptocurrency_name: str = None,
                                   symbol: str = None,
                                   time_frame=None,
                                   relevant_evaluators=None,
                                   all_symbols_by_crypto_currencies=None,
                                   time_frames=None,
                                   real_time_time_frames=None,
                                   evaluator_configuration=None):
    return evaluator_class(cryptocurrency, cryptocurrency_name, symbol, time_frame, all_symbols_by_crypto_currencies)


class EvaluatorWildCard(tentacles_management.AbstractTentacle):
    def __init__(self, cryptocurrency, cryptocurrency_name, symbol, time_frame, all_symbols_by_crypto_currencies):
        self.cryptocurrency = cryptocurrency
        self.cryptocurrency_name = cryptocurrency_name
        self.symbol = symbol
        self.time_frame = time_frame
        self.all_symbols_by_crypto_currencies = all_symbols_by_crypto_currencies

    @classmethod
    def get_is_cryptocurrency_name_wildcard(cls):
        return True

    @classmethod
    def get_is_symbol_wildcard(cls):
        return True

    @classmethod
    def get_is_time_frame_wildcard(cls):
        return True


    @classmethod
    def get_is_cryptocurrencies_wildcard(cls):
        return True


class EvaluatorNoCCWildCard(EvaluatorWildCard):
    @classmethod
    def get_is_cryptocurrencies_wildcard(cls):
        return False


class EvaluatorNoCCNameWildCard(EvaluatorWildCard):
    @classmethod
    def get_is_cryptocurrency_name_wildcard(cls):
        return False


class EvaluatorNoSymbolWildCard(EvaluatorWildCard):
    @classmethod
    def get_is_symbol_wildcard(cls):
        return False


class EvaluatorNoTimeFrameWildCard(EvaluatorWildCard):
    @classmethod
    def get_is_time_frame_wildcard(cls):
        return False


class EvaluatorNoCCNameNoCCWildCard(EvaluatorNoCCNameWildCard, EvaluatorNoCCWildCard):
    pass


class EvaluatorNoCCNameSymbolWildCard(EvaluatorNoCCNameWildCard, EvaluatorNoSymbolWildCard):
    pass


class EvaluatorNoCCTimeFrameWildCard(EvaluatorNoCCWildCard, EvaluatorNoTimeFrameWildCard):
    pass


class EvaluatorNoSymbolTimeFrameWildCard(EvaluatorNoSymbolWildCard, EvaluatorNoTimeFrameWildCard):
    pass


class EvaluatorNoWildCard(EvaluatorNoCCWildCard, EvaluatorNoCCNameWildCard,
                          EvaluatorNoSymbolWildCard, EvaluatorNoTimeFrameWildCard):
    def __init__(self, *args):
        super().__init__(*args)
