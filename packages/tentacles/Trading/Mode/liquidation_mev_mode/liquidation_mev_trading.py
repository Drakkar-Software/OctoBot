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
import asyncio
import decimal

import octobot_commons.enums as commons_enums
import octobot_trading.modes as trading_modes
import octobot_trading.enums as trading_enums
import octobot_trading.lending_protocols as lending_protocols

import tentacles.Trading.Mode.liquidation_mev_mode.liquidation_container as liquidation_container_import
import tentacles.Trading.Mode.liquidation_mev_mode.chain_config as chain_config_import


class LiquidationMEVTradingMode(trading_modes.AbstractTradingMode):
    """
    Monitors DeFi lending protocols for undercollateralized positions
    and executes profitable liquidations on-chain.
    Currently supports Aave V3 on Polygon.
    """

    def init_user_inputs(self, inputs: dict) -> None:
        self.UI.user_input(
            "polling_interval_seconds", commons_enums.UserInputTypes.FLOAT, 10, inputs,
            min_val=1, max_val=3600,
            title="Polling interval: seconds between each scan for liquidatable positions.",
        )
        self.UI.user_input(
            "min_profit_usd", commons_enums.UserInputTypes.FLOAT, 5.0, inputs,
            min_val=0,
            title="Minimum profit: minimum estimated net profit in USD to trigger a liquidation.",
        )
        self.UI.user_input(
            "max_gas_price_gwei", commons_enums.UserInputTypes.FLOAT, 100, inputs,
            min_val=1,
            title="Maximum gas price: maximum gas price in gwei to use for liquidation transactions.",
        )
        self.UI.user_input(
            "min_debt_usd", commons_enums.UserInputTypes.FLOAT, 100.0, inputs,
            min_val=0,
            title="Minimum debt size: minimum debt value in USD to consider a position for liquidation.",
        )
        self.UI.user_input(
            "lending_protocol", commons_enums.UserInputTypes.OPTIONS, "aave_v3_polygon", inputs,
            options=["aave_v3_polygon"],
            title="Lending protocol: the DeFi lending protocol to monitor for liquidation opportunities.",
        )
        self.UI.user_input(
            "chain", commons_enums.UserInputTypes.OPTIONS, "polygon", inputs,
            options=list(chain_config_import.CHAIN_CONFIGS.keys()),
            title="Chain: the blockchain network to operate on.",
        )

    def get_mode_producer_classes(self) -> list:
        return [LiquidationMEVModeProducer]

    def get_mode_consumer_classes(self) -> list:
        return [LiquidationMEVModeConsumer]

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        # Liquidation MEV is not tied to a specific trading pair
        return True

    @staticmethod
    def is_backtestable():
        return False


class LiquidationMEVModeProducer(trading_modes.AbstractTradingModeProducer):
    """
    Monitors lending protocol positions for liquidation opportunities.
    Runs a background polling loop (following DCA mode pattern) and
    ignores evaluator matrix signals (following Arbitrage mode pattern).
    """

    def __init__(self, channel, config, trading_mode, exchange_manager):
        super().__init__(channel, config, trading_mode, exchange_manager)
        self._monitoring_task: asyncio.Task = None
        self._active_liquidations: list[liquidation_container_import.LiquidationContainer] = []

    def on_reload_config(self):
        self.polling_interval = self.trading_mode.trading_config.get(
            "polling_interval_seconds", 10
        )
        self.min_profit_usd = decimal.Decimal(str(
            self.trading_mode.trading_config.get("min_profit_usd", 5.0)
        ))
        self.max_gas_price_gwei = self.trading_mode.trading_config.get(
            "max_gas_price_gwei", 100
        )
        self.min_debt_usd = decimal.Decimal(str(
            self.trading_mode.trading_config.get("min_debt_usd", 100.0)
        ))
        self.lending_protocol_name = self.trading_mode.trading_config.get(
            "lending_protocol", "aave_v3_polygon"
        )
        self.chain_name = self.trading_mode.trading_config.get("chain", "polygon")

    async def inner_start(self) -> None:
        """
        Start the liquidation monitoring loop.
        Follows the DCA mode pattern of creating a background task in inner_start().
        """
        await super().inner_start()
        self.logger.info(
            f"Starting liquidation MEV monitoring on {self.chain_name} "
            f"using {self.lending_protocol_name} protocol. "
            f"Polling every {self.polling_interval}s, "
            f"min profit: ${self.min_profit_usd}, min debt: ${self.min_debt_usd}"
        )
        self._monitoring_task = asyncio.create_task(
            self._poll_liquidation_opportunities()
        )

    def get_channels_registration(self):
        # No channel subscriptions needed - we use our own polling loop
        return []

    async def set_final_eval(
        self, matrix_id: str, cryptocurrency: str, symbol: str,
        time_frame, trigger_source: str
    ):
        # Ignore evaluator matrix signals (same pattern as ArbitrageModeProducer)
        pass

    async def _poll_liquidation_opportunities(self):
        """
        Main monitoring loop. Periodically scans for liquidatable positions.

        TODO: Implement the following steps:
        1. Create blockchain wallet instance via _create_blockchain_wallet()
        2. Create lending protocol instance via lending_protocols.create_lending_protocol()
        3. Loop:
           a. async with wallet.open():
                positions = await protocol.get_liquidatable_positions(self.min_debt_usd)
           b. For each position:
              - Check gas price <= max_gas_price_gwei
              - estimate = await protocol.estimate_liquidation_profit(position, ...)
              - If estimate.net_profit_usd >= self.min_profit_usd:
                  - Check no active liquidation for same borrower+debt
                  - Create LiquidationContainer
                  - await self._trigger_liquidation(container)
           c. await asyncio.sleep(self.polling_interval)
        4. Handle exceptions gracefully, log errors, continue loop
        """
        try:
            while True:
                try:
                    await self._scan_for_opportunities()
                except NotImplementedError:
                    self.logger.warning(
                        "Lending protocol methods are not yet implemented. "
                        "Liquidation monitoring is running in stub mode."
                    )
                except Exception as e:
                    self.logger.exception(
                        e, True,
                        f"Error scanning for liquidation opportunities: {e}"
                    )
                await asyncio.sleep(self.polling_interval)
        except asyncio.CancelledError:
            self.logger.info("Liquidation monitoring task cancelled")

    async def _scan_for_opportunities(self):
        """
        Scan for liquidatable positions and trigger liquidations for profitable ones.

        TODO: Implement:
        1. wallet = self._create_blockchain_wallet()
        2. async with wallet.open():
             protocol = lending_protocols.create_lending_protocol(
                 self.lending_protocol_name, wallet)
             positions = await protocol.get_liquidatable_positions(self.min_debt_usd)
        3. For each position, estimate profit and trigger if profitable
        """
        raise NotImplementedError(
            "_scan_for_opportunities is not yet implemented. "
            "See _poll_liquidation_opportunities docstring for full implementation plan."
        )

    async def _trigger_liquidation(
        self, container: liquidation_container_import.LiquidationContainer
    ):
        """
        Submit a liquidation opportunity for execution by the consumer.
        Follows the ArbitrageModeProducer._create_arbitrage_initial_order pattern.
        """
        data = {
            LiquidationMEVModeConsumer.LIQUIDATION_CONTAINER_KEY: container,
        }
        self._active_liquidations.append(container)
        self.logger.info(
            f"Liquidation opportunity detected: borrower={container.borrower_address[:10]}..., "
            f"debt={container.debt_asset}, collateral={container.collateral_asset}, "
            f"estimated profit=${container.estimated_profit_usd}"
        )
        await self.submit_trading_evaluation(
            cryptocurrency=self.trading_mode.cryptocurrency,
            symbol=self.trading_mode.symbol,
            time_frame=None,
            state=trading_enums.EvaluatorStates.NEUTRAL,
            data=data,
        )

    def _create_blockchain_wallet(self):
        """
        Create an EVMBlockchainWallet instance for the configured chain.
        Follows the Polymarket exchange connector pattern (polymarket_exchange.py:74-96).

        TODO: Implement:
        1. import tentacles.Trading.Blockchain_wallet.evm.evm_blockchain_wallet as evm_wallet
        2. chain_config = chain_config_import.CHAIN_CONFIGS[self.chain_name]
        3. parameters = BlockchainWalletParameters(
               blockchain_descriptor=BlockchainDescriptor(
                   blockchain=evm_wallet.EVMBlockchainWallet.BLOCKCHAIN,
                   network=evm_wallet.POLYGON_MAINNET_CONFIG.network,
                   specific_config={
                       evm_wallet.EVMBlockchainSpecificConfigurationKeys.RPC_URL.value:
                           chain_config.default_rpc_url,
                   },
               ),
               wallet_descriptor=WalletDescriptor(
                   private_key=os.environ.get("MEV_WALLET_PRIVATE_KEY"),
               ),
           )
        4. return evm_wallet.EVMBlockchainWallet(parameters)
        """
        raise NotImplementedError(
            "_create_blockchain_wallet is not yet implemented. "
            "See docstring for implementation steps."
        )

    @classmethod
    def get_should_cancel_loaded_orders(cls) -> bool:
        return False

    async def stop(self):
        if self._monitoring_task is not None and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        if self.trading_mode is not None:
            self.trading_mode.flush_trading_mode_consumers()
        await super().stop()


class LiquidationMEVModeConsumer(trading_modes.AbstractTradingModeConsumer):
    """
    Executes liquidation transactions on-chain.
    Receives LiquidationContainer from the producer and handles
    the blockchain transaction lifecycle.
    """
    LIQUIDATION_CONTAINER_KEY = "liquidation"

    def __init__(self, trading_mode):
        super().__init__(trading_mode)
        self.completed_liquidations: list[liquidation_container_import.LiquidationContainer] = []

    async def create_new_orders(self, symbol, final_note, state, **kwargs):
        data = kwargs.get(self.CREATE_ORDER_DATA_PARAM, {})
        container = data.get(self.LIQUIDATION_CONTAINER_KEY)
        if container is not None:
            await self._execute_liquidation(container)

    async def _execute_liquidation(
        self, container: liquidation_container_import.LiquidationContainer
    ):
        """
        Execute a liquidation transaction on-chain.

        TODO: Implement the following steps:
        1. Update container status to EXECUTING
        2. Create wallet instance via producer's _create_blockchain_wallet()
        3. Create lending protocol instance via factory
        4. async with wallet.open():
             a. Build liquidation tx:
                tx_data = await protocol.build_liquidation_tx(
                    container related position,
                    container.debt_asset,
                    container.debt_to_cover,
                    container.collateral_asset)
             b. Send transaction:
                tx_hash = await wallet.build_and_send_contract_tx(
                    tx_data["to"], tx_data["abi"], tx_data["function"], ...)
             c. Wait for receipt:
                receipt = await wallet.wait_for_receipt(tx_hash)
             d. Check receipt status:
                if receipt["status"] == 1:
                    container.status = COMPLETED
                    container.tx_hash = tx_hash
                else:
                    container.status = FAILED
                    container.error = "Transaction reverted"
        5. Log results
        6. Move container to completed_liquidations
        """
        container.status = liquidation_container_import.LiquidationStatus.EXECUTING
        try:
            # Stub: actual implementation follows the steps above
            raise NotImplementedError(
                "_execute_liquidation is not yet implemented. "
                "See docstring for implementation steps."
            )
        except NotImplementedError:
            container.status = liquidation_container_import.LiquidationStatus.FAILED
            container.error = "Liquidation execution not yet implemented"
            self.logger.warning(
                f"Liquidation execution not yet implemented for "
                f"borrower={container.borrower_address[:10]}..."
            )
        except Exception as e:
            container.status = liquidation_container_import.LiquidationStatus.FAILED
            container.error = str(e)
            self.logger.exception(
                e, True,
                f"Error executing liquidation for "
                f"borrower={container.borrower_address[:10]}...: {e}"
            )
        finally:
            self.completed_liquidations.append(container)
