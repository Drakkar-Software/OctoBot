#  Drakkar-Software OctoBot
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

from tools.logging.logging_util import get_logger
from abc import *
from queue import Queue
from ccxt import InsufficientFunds

from config import INIT_EVAL_NOTE
from tools.notifications import EvaluatorNotification


class AbstractTradingModeDecider:
    __metaclass__ = ABCMeta

    def __init__(self, trading_mode, symbol_evaluator, exchange):
        self.trading_mode = trading_mode
        self.symbol_evaluator = symbol_evaluator
        self.config = symbol_evaluator.get_config()
        self.final_eval = INIT_EVAL_NOTE
        self.state = None
        self.keep_running = True
        self.exchange = exchange
        self.symbol = symbol_evaluator.get_symbol()
        self.is_computing = False
        self.logger = get_logger(self.__class__.__name__)

        self.notifier = EvaluatorNotification(self.config)
        self.queue = Queue()

    # create real and/or simulating orders in trader instances
    async def create_final_state_orders(self, evaluator_notification, creator_key):
        # simulated trader
        await self.create_order_if_possible(evaluator_notification,
                                            self.symbol_evaluator.get_trader_simulator(self.exchange),
                                            creator_key)

        # real trader
        await self.create_order_if_possible(evaluator_notification,
                                            self.symbol_evaluator.get_trader(self.exchange),
                                            creator_key)

    async def cancel_symbol_open_orders(self):
        cancel_loaded_orders = self.get_should_cancel_loaded_orders()

        real_trader = self.symbol_evaluator.get_trader(self.exchange)
        if real_trader.is_enabled():
            await real_trader.cancel_open_orders(self.symbol, cancel_loaded_orders)

        trader_simulator = self.symbol_evaluator.get_trader_simulator(self.exchange)
        if trader_simulator.is_enabled():
            await trader_simulator.cancel_open_orders(self.symbol, cancel_loaded_orders)

    def activate_deactivate_strategies(self, strategy_list, activate):
        for strategy in strategy_list:
            if strategy not in self.trading_mode.get_strategy_instances_by_classes(self.symbol):
                raise KeyError("{} not in trading mode's strategy instances.".format(strategy))

        strategy_instances_list = [self.trading_mode.get_strategy_instances_by_classes(self.symbol)[strategy_class]
                                   for strategy_class in strategy_list]

        self.symbol_evaluator.activate_deactivate_strategies(strategy_instances_list, self.exchange, activate)

    def get_state(self):
        return self.state

    def get_final_eval(self):
        return self.final_eval

    async def finalize(self):
        # reset previous note
        self.final_eval = INIT_EVAL_NOTE

        try:
            self.set_final_eval()
            await self.create_state()
        except Exception as e:
            self.logger.error("Error when finalizing: {0}".format(e))
            self.logger.exception(e)

    def stop(self):
        self.keep_running = False

    # called by cancel_symbol_open_orders => return true if OctoBot should cancel all orders for a symbol including
    # orders already existing when OctoBot started up
    @classmethod
    @abstractmethod
    def get_should_cancel_loaded_orders(cls):
        raise NotImplementedError("get_should_cancel_loaded_orders not implemented")

    # called first by finalize => when any notification appears
    @abstractmethod
    def set_final_eval(self):
        raise NotImplementedError("_set_final_eval not implemented")

    # called after _set_final_eval by finalize => when any notification appears
    @abstractmethod
    def create_state(self):
        raise NotImplementedError("_create_state not implemented")

    # for each trader call the creator to check if order creation is possible and create it
    async def create_order_if_possible(self, evaluator_notification, trader, creator_key):
        if trader.is_enabled():
            with trader.get_portfolio() as pf:
                order_creator = self.trading_mode.get_creator(self.symbol, creator_key)
                if await order_creator.can_create_order(self.symbol, self.exchange, self.state, pf):
                    new_orders = None
                    try:
                        new_orders = await order_creator.create_new_order(
                            self.final_eval,
                            self.symbol,
                            self.exchange,
                            trader,
                            pf,
                            self.state)
                    except InsufficientFunds:
                        if not trader.get_simulate():
                            try:
                                # second chance: force portfolio update and retry
                                trader.force_refresh_portfolio(pf)
                                trader.force_refresh_orders(pf)
                                new_orders = await order_creator.create_new_order(
                                    self.final_eval,
                                    self.symbol,
                                    self.exchange,
                                    trader,
                                    pf,
                                    self.state)
                            except InsufficientFunds as e:
                                self.logger.error(f"Failed to create order on second attempt : {e})")

                    self._push_order_notification_if_possible(new_orders, evaluator_notification)

    @staticmethod
    def _push_order_notification_if_possible(order_list, notification):
        if order_list:
            for order in order_list:
                order.get_order_notifier().notify(notification)


class AbstractTradingModeDeciderWithBot(AbstractTradingModeDecider):
    __metaclass__ = ABCMeta

    def __init__(self, trading_mode, symbol_evaluator, exchange, trader, creators):
        super().__init__(trading_mode, symbol_evaluator, exchange)
        self.trader = trader
        self.creators = creators

    @classmethod
    @abstractmethod
    def get_should_cancel_loaded_orders(cls):
        raise NotImplementedError("get_should_cancel_loaded_orders not implemented")

    @abstractmethod
    def set_final_eval(self):
        raise NotImplementedError("_set_final_eval not implemented")

    @abstractmethod
    def create_state(self):
        raise NotImplementedError("_create_state not implemented")

    def get_creators(self):
        return self.creators

    def get_trader(self):
        return self.trader
