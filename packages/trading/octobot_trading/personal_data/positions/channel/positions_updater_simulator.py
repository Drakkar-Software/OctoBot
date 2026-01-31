#  Drakkar-Software OctoBot-Trading
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
import octobot_commons.logging as logging
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.personal_data.positions.channel.positions_updater as positions_updater


class PositionsUpdaterSimulator(positions_updater.PositionsUpdater):
    async def start(self):
        if not self._should_run():
            return
        await self.initialize()

    async def initialize(self) -> None:
        """
        Initialize positions and future contracts
        """
        await self.initialize_contracts()
        for pair in self.channel.exchange_manager.exchange_config.traded_symbol_pairs:
            self.channel.exchange_manager.exchange_personal_data.positions_manager.set_initialized_event(pair)
        self.logger = logging.get_logger(f"{self.__class__.__name__}[{self.channel.exchange_manager.exchange.name}]")
        await exchanges_channel.get_chan(constants.MARK_PRICE_CHANNEL, self.channel.exchange_manager.id) \
            .new_consumer(self.handle_mark_price)
        await exchanges_channel.get_chan(constants.FUNDING_CHANNEL, self.channel.exchange_manager.id) \
            .new_consumer(self.handle_funding_rate)

    async def initialize_contracts(self) -> None:
        """
        Initialize exchange FutureContracts required to manage positions
        """
        for pair in self.channel.exchange_manager.exchange_config.traded_symbol_pairs:
            contract = self.channel.exchange_manager.exchange.create_pair_contract(
                pair=pair,
                current_leverage=constants.DEFAULT_SYMBOL_LEVERAGE,
                contract_size=constants.DEFAULT_SYMBOL_CONTRACT_SIZE,
                margin_type=constants.DEFAULT_SYMBOL_MARGIN_TYPE,
                contract_type=
                self.channel.exchange_manager.exchange_config.backtesting_exchange_config.future_contract_type
                if self.channel.exchange_manager.is_backtesting else self._get_contract_type_or_default(pair),
                position_mode=constants.DEFAULT_SYMBOL_POSITION_MODE,
                maintenance_margin_rate=constants.DEFAULT_SYMBOL_MAINTENANCE_MARGIN_RATE,
                maximum_leverage=constants.DEFAULT_SYMBOL_MAX_LEVERAGE)
            if not contract.is_handled_contract():
                self.logger.error(f"Unhandled contract {contract}. This contract can't be traded")
            self.channel.exchange_manager.exchange.set_contract_initialized_event(pair)

    def _get_contract_type_or_default(self, pair):
        try:
            return self.channel.exchange_manager.exchange.get_contract_type(pair)
        except NotImplementedError as e:
            self.logger.error(f"Unimplemented required method: {e}")
        self.logger.error(f"Unknown contract type for {pair} on {self.channel.exchange_manager.exchange_name}. Using "
                          f"{constants.DEFAULT_SYMBOL_FUTURE_CONTRACT_TYPE}")
        return enums.FutureContractType.LINEAR_PERPETUAL

    async def handle_funding_rate(self, exchange: str,
                                  exchange_id: str,
                                  cryptocurrency: str,
                                  symbol: str,
                                  funding_rate,
                                  predicted_funding_rate,
                                  next_funding_time,
                                  timestamp):
        """
        Funding channel consumer callback
        """
        try:
            for symbol_position in self.channel.exchange_manager.exchange_personal_data.positions_manager. \
                    get_symbol_positions(symbol=symbol):
                if not symbol_position.is_idle() and symbol_position.symbol_contract.is_perpetual_contract():
                    async with self.channel.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.lock:
                        await self.channel.exchange_manager.exchange_personal_data.handle_portfolio_update_from_funding(
                            position=symbol_position, funding_rate=funding_rate
                        )
        except Exception as e:
            self.logger.exception(e, True, f"Fail to handle funding rate : {e}")
