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

import typing
from datetime import datetime

import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_evaluators.enums as evaluators_enums
from octobot_evaluators import matrix
from octobot_evaluators.matrix.channel.matrix import MatrixChannel
import octobot_evaluators.api as evaluators_api
import octobot_commons.evaluators_util as evaluators_util
import octobot_evaluators.constants as evaluators_constants
import octobot_trading.api as trading_api
import octobot_services.api.services as services_api
import octobot_agents.constants as agents_constants
import octobot_commons.constants as common_constants

from tentacles.Trading.Mode.ai_trading_mode import ai_index_distribution
from tentacles.Trading.Mode.index_trading_mode import index_trading
from tentacles.Trading.Mode.ai_trading_mode.team import TradingAgentTeam
from tentacles.Trading.Mode.ai_trading_mode.deep_agent_team import DeepAgentTradingTeam

# Data keys
STRATEGY_DATA_KEY = "strategy_data"
CRYPTO_STRATEGY_DATA_KEY = "crypto_strategy_data"
GLOBAL_STRATEGY_DATA_KEY = "global_strategy_data"
AI_INSTRUCTIONS_KEY = "ai_instructions"


class AIIndexTradingModeProducer(index_trading.IndexTradingModeProducer):
    def __init__(self, channel, config, trading_mode, exchange_manager):
        super().__init__(channel, config, trading_mode, exchange_manager)
        self._global_strategy_data = {}
        self._crypto_strategy_data = {}  # {cryptocurrency: strategy_data}
        self.time_frame_filter = commons_constants.CONFIG_WILDCARD

    def get_channels_registration(self):
        """
        Override parent to register on MATRIX_CHANNEL instead of candle channels.
        AI trading mode should only trade based on AI evaluator results (strategy evaluations),
        not on candle events directly.
        """
        return [
            self.TOPIC_TO_CHANNEL_NAME[commons_enums.ActivationTopics.EVALUATION_CYCLE.value]
        ]

    async def set_final_eval(
        self,
        matrix_id: str,
        cryptocurrency: typing.Optional[str],
        symbol: typing.Optional[str],
        time_frame,
        trigger_source: str,
    ) -> None:
        self._global_strategy_data = self._collect_global_strategy_data(matrix_id)
        self._crypto_strategy_data = self._collect_crypto_strategy_data(matrix_id)
        if self._global_strategy_data and self._crypto_strategy_data:
            await self._trigger_crypto_analysis(cryptocurrency, symbol, time_frame)

    def _collect_global_strategy_data(self, matrix_id: str) -> dict:
        strategy_data = {}
        strategy_type = evaluators_enums.EvaluatorMatrixTypes.STRATEGIES.value
        tentacle_nodes = matrix.get_tentacle_nodes(
            matrix_id=matrix_id,
            exchange_name=self.exchange_name,
            tentacle_type=strategy_type,
        )
        # Get global strategy nodes (cryptocurrency=None)
        for evaluated_strategy_node in matrix.get_tentacles_value_nodes(
            matrix_id,
            tentacle_nodes,
            cryptocurrency=None,
            symbol=None,
            time_frame=None,
        ):
            eval_note = evaluators_api.get_value(evaluated_strategy_node)
            note_description = evaluators_api.get_description(evaluated_strategy_node)
            if not note_description:
                continue
            is_valid = evaluators_util.check_valid_eval_note(
                eval_note,
                evaluators_api.get_type(evaluated_strategy_node),
                evaluators_constants.EVALUATOR_EVAL_DEFAULT_TYPE,
            )
            if not is_valid and not (
                eval_note == common_constants.START_PENDING_EVAL_NOTE
                and note_description == agents_constants.DEFAULT_AGENT_RESULT
            ):
                continue
            note_metadata = evaluators_api.get_metadata(evaluated_strategy_node)

            if strategy_type not in strategy_data:
                strategy_data[strategy_type] = []

            strategy_data[strategy_type].append(
                {
                    "eval_note": eval_note,
                    "description": note_description,
                    "metadata": note_metadata,
                    MatrixChannel.CRYPTOCURRENCY_KEY: None,
                    MatrixChannel.SYMBOL_KEY: None,
                    "evaluation_type": "global",
                }
            )

        return strategy_data

    def _collect_crypto_strategy_data(
        self,
        matrix_id: str
    ) -> dict:
        strategy_data = {}
        strategy_type = evaluators_enums.EvaluatorMatrixTypes.STRATEGIES.value
        tentacle_nodes = matrix.get_tentacle_nodes(
            matrix_id=matrix_id,
            exchange_name=self.exchange_name,
            tentacle_type=strategy_type,
        )
        try:
            indexed_coins = list(self.trading_mode.indexed_coins)
        except Exception:
            indexed_coins = []

        for cryptocurrency in indexed_coins:
            try:
                symbols = matrix.get_available_symbols(
                    matrix_id,
                    self.exchange_name,
                    strategy_type,
                    cryptocurrency,
                )
            except Exception:
                symbols = []
            if not symbols:
                symbols = [None]

            for symbol in symbols:
                try:
                    if symbol is None:
                        time_frames = [None]
                    else:
                        time_frames = matrix.get_available_time_frames(
                            matrix_id,
                            self.exchange_name,
                            strategy_type,
                            cryptocurrency,
                            symbol,
                        )
                except Exception:
                    time_frames = []
                if not time_frames:
                    time_frames = [None]

                for time_frame in time_frames:
                    for evaluated_strategy_node in matrix.get_tentacles_value_nodes(
                        matrix_id,
                        tentacle_nodes,
                        cryptocurrency=cryptocurrency,
                        symbol=symbol,
                        time_frame=time_frame,
                    ):
                        eval_note = evaluators_api.get_value(evaluated_strategy_node)
                        note_description = evaluators_api.get_description(evaluated_strategy_node)
                        if not note_description:
                            continue
                        is_valid = evaluators_util.check_valid_eval_note(
                            eval_note,
                            evaluators_api.get_type(evaluated_strategy_node),
                            evaluators_constants.EVALUATOR_EVAL_DEFAULT_TYPE,
                        )
                        if not is_valid and not (
                            eval_note == common_constants.START_PENDING_EVAL_NOTE
                            and note_description == agents_constants.DEFAULT_AGENT_RESULT
                        ):
                            continue
                        note_metadata = evaluators_api.get_metadata(evaluated_strategy_node)

                        if cryptocurrency not in strategy_data:
                            strategy_data[cryptocurrency] = {strategy_type: []}
                        elif strategy_type not in strategy_data[cryptocurrency]:
                            strategy_data[cryptocurrency][strategy_type] = []

                        strategy_data[cryptocurrency][strategy_type].append(
                            {
                                "eval_note": eval_note,
                                "description": note_description,
                                "metadata": note_metadata,
                                MatrixChannel.CRYPTOCURRENCY_KEY: cryptocurrency,
                                MatrixChannel.SYMBOL_KEY: symbol,
                                MatrixChannel.TIME_FRAME_KEY: time_frame,
                                "evaluation_type": "crypto_specific",
                            }
                        )

        return strategy_data

    def _has_filtered_global_strategy_data(self) -> bool:
        strategy_type = evaluators_enums.EvaluatorMatrixTypes.STRATEGIES.value
        try:
            entries = self._global_strategy_data.get(strategy_type, [])
        except Exception:
            return False
        for entry in entries:
            try:
                if entry.get(MatrixChannel.CRYPTOCURRENCY_KEY) is None:
                    return True
            except Exception:
                continue
        return False

    def _has_filtered_crypto_strategy_data(self, indexed_coins: list[str]) -> bool:
        strategy_type = evaluators_enums.EvaluatorMatrixTypes.STRATEGIES.value
        for coin in indexed_coins:
            try:
                strategy_data = self._crypto_strategy_data.get(coin, {})
                entries = strategy_data.get(strategy_type, [])
            except Exception:
                return False
            has_entries = False
            for entry in entries:
                try:
                    if entry.get(MatrixChannel.CRYPTOCURRENCY_KEY) is not None:
                        has_entries = True
                        break
                except Exception:
                    continue
            if not has_entries:
                return False
        return True

    def _collect_all_strategy_data(
        self, matrix_id: str, cryptocurrency: str, symbol: str, time_frame=None
    ) -> dict:
        """
        Legacy method: Collect all strategy data (both global and crypto-specific).
        Kept for backwards compatibility.
        """
        strategy_data = {}
        strategy_type = evaluators_enums.EvaluatorMatrixTypes.STRATEGIES.value
        tentacle_nodes = matrix.get_tentacle_nodes(
            matrix_id=matrix_id,
            exchange_name=self.exchange_name,
            tentacle_type=strategy_type,
        )
        for evaluated_strategy_node in matrix.get_tentacles_value_nodes(
            matrix_id,
            tentacle_nodes,
            cryptocurrency=cryptocurrency,
            symbol=symbol,
            time_frame=time_frame,
        ):
            eval_note = evaluators_api.get_value(evaluated_strategy_node)
            note_description = evaluators_api.get_description(evaluated_strategy_node)
            if not note_description:
                continue
            is_valid = evaluators_util.check_valid_eval_note(
                eval_note,
                evaluators_api.get_type(evaluated_strategy_node),
                evaluators_constants.EVALUATOR_EVAL_DEFAULT_TYPE,
            )
            if not is_valid and not (
                eval_note == common_constants.START_PENDING_EVAL_NOTE
                and note_description == agents_constants.DEFAULT_AGENT_RESULT
            ):
                continue
            note_metadata = evaluators_api.get_metadata(evaluated_strategy_node)

            if strategy_type not in strategy_data:
                strategy_data[strategy_type] = []

            strategy_data[strategy_type].append(
                {
                    "eval_note": eval_note,
                    "description": note_description,
                    "metadata": note_metadata,
                    MatrixChannel.CRYPTOCURRENCY_KEY: cryptocurrency,
                    MatrixChannel.SYMBOL_KEY: symbol,
                }
            )

        return strategy_data

    async def _trigger_crypto_analysis(
        self,
        cryptocurrency: typing.Optional[str],
        symbol: typing.Optional[str],
        time_frame,
    ):       
        # TODO Check if all cryptocurrencies have been analyzed

        # Only run the full agent team when we have data for all tracked coins
        if not self.trading_mode.indexed_coins:
            self.logger.debug("No indexed coins configured, skipping agent analysis.")
            return
        
        # Check if we have crypto strategy data for all indexed coins (exclude reference market)
        reference_market = self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
        indexed_coins = [coin for coin in self.trading_mode.indexed_coins if coin != reference_market]

        if not self._has_filtered_global_strategy_data():
            self.logger.debug("Waiting for filtered global strategy data.")
            return

        if not self._has_filtered_crypto_strategy_data(indexed_coins):
            self.logger.debug(
                "Waiting for filtered crypto strategy data. Have: %s Need: %s",
                list(self._crypto_strategy_data.keys()),
                indexed_coins,
            )
            return
        
        # TODO check if all coins are ready        
        self.logger.debug("All strategy data collected. Running AI agents...")
        
        try:
            await self._run_agents()
        except Exception as e:
            self.logger.exception(f"Error running AI agents: {e}")
    
    async def _run_agents(self):
        """
        Run AI agents using TradingAgentTeam to analyze portfolio and generate distribution decisions.
        
        The team orchestrates:
        1. Signal agent - analyzes all cryptocurrencies and synthesizes signals
        2. Risk agent - evaluates portfolio risk based on signals
        3. Distribution agent - makes final allocation decisions
        """        
        ai_service = await self._get_ai_service()
        if ai_service is None:
            self.logger.error("Failed to create AI service. Check AI configuration.")
            return
        
        # Build state
        state = self._build_agent_state()
        
        self.logger.debug("Running TradingAgentTeam for portfolio distribution analysis...")
        
        # Create and run the team based on use_deep_agent config
        use_deep_agent = self.trading_mode.config.get(AIIndexTradingMode.USE_DEEP_AGENT_KEY, False)
        if use_deep_agent:
            # Deep agents require langchain service explicitly
            team_class = DeepAgentTradingTeam
            # Get langchain service for deep agents
            from tentacles.Services.Services_bases.langchain_service.langchain import LangChainService
            langchain_service = await services_api.get_service(
                LangChainService,
                is_backtesting=self.exchange_manager.is_backtesting
            )
            team = team_class(ai_service=langchain_service or ai_service)
        else:
            team_class = TradingAgentTeam
            team = team_class(ai_service=ai_service)
        
        try:
            distribution_output = await team.run_with_state(state)
        except Exception as e:
            self.logger.exception(f"TradingAgentTeam execution failed: {e}")
            return

        # Structured logging of debate/judge outputs when present
        try:
            debate_state = team.last_debate_state
        except AttributeError:
            debate_state = None
        if debate_state:
            if self.trading_mode.log_ai_decisions:
                self.logger.info(
                    "Debate state: %s",
                    str(debate_state),
                )
            self.logger.debug(
                "Debate history (%s entries), judge decisions (%s entries)",
                len(debate_state.get("debate_history", [])),
                len(debate_state.get("judge_decisions", [])),
            )
            for entry in debate_state.get("judge_decisions", []):
                self.logger.debug(
                    "Judge round %s: decision=%s reasoning=%s",
                    entry.get("round"),
                    entry.get("decision"),
                    (entry.get("reasoning") or "")[:200],
                )

        if distribution_output is None:
            self.logger.warning("Agent team returned no distribution output.")
            return
        
        self.logger.info(
            f"TradingAgentTeam completed. Urgency: {distribution_output.rebalance_urgency}"
        )
        self.logger.info(f"AI Reasoning: {distribution_output.reasoning}")
        for dist in distribution_output.distributions:
            self.logger.info(
                f"  {dist.asset}: {dist.percentage:.1f}% ({dist.action}) - {dist.explanation}"
            )
        
        # Convert to AI instructions and trigger rebalance
        ai_instructions = distribution_output.get_ai_instructions()
        
        if ai_instructions and distribution_output.rebalance_urgency != "none":
            self.logger.info(f"Triggering rebalance with {len(ai_instructions)} instructions")
            await self._submit_trading_evaluation(ai_instructions)
        else:
            if distribution_output.rebalance_urgency == "none":
                self.logger.info("No rebalance triggered (urgency is 'none')")
            else:
                self.logger.info("No rebalance triggered (no instructions)")
    
    def _build_agent_state(self) -> dict:
        """
        Build the state dictionary for agent execution.
        """
        portfolio_state = self._build_portfolio_state()
        orders_state = self._build_orders_state()
        current_distribution = self._build_current_distribution()

        # Get all traded symbols from exchange manager
        traded_symbols = trading_api.get_trading_symbols(self.exchange_manager, include_additional_pairs=True)
        # Extract both base and quote currencies (cryptocurrencies) from symbols
        traded_cryptocurrencies = list(set(
            currency for symbol in traded_symbols 
            for currency in [symbol.base, symbol.quote]
        ))
        # Combine with indexed_coins to ensure all configured coins are included
        indexed_cryptocurrencies = list(self.trading_mode.indexed_coins) if self.trading_mode.indexed_coins else []
        # Merge and deduplicate
        cryptocurrencies = list(set(traded_cryptocurrencies + indexed_cryptocurrencies))
        
        reference_market = self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
        
        return {
            "global_strategy_data": self._global_strategy_data,
            "crypto_strategy_data": self._crypto_strategy_data,
            "cryptocurrencies": cryptocurrencies,
            "reference_market": reference_market,
            "portfolio": portfolio_state,
            "orders": orders_state,
            "current_distribution": current_distribution,
            "signal_outputs": {"signals": {}},
            "risk_output": None,
            "signal_synthesis": None,
            "distribution_output": None,
            "exchange_name": self.exchange_name,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def _build_portfolio_state(self) -> dict:
        """Build portfolio state from exchange manager."""
        portfolio = trading_api.get_portfolio(self.exchange_manager)
        reference_market = trading_api.get_portfolio_reference_market(self.exchange_manager)
        
        holdings = {}
        holdings_value = {}
        total_value = 0
        
        for asset, amount in portfolio.items():
            if hasattr(amount, 'total'):
                holdings[asset] = float(amount.total)
            elif isinstance(amount, dict):
                holdings[asset] = float(amount.get('total', 0))
            else:
                holdings[asset] = float(amount)
        
        # Get portfolio value
        try:
            portfolio_value_holder = self.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder
            total_value = float(portfolio_value_holder.get_traded_assets_holdings_value(reference_market))
        except Exception:
            total_value = 0
        
        # Get available balance
        try:
            available_balance = float(
                self.exchange_manager.exchange_personal_data.portfolio_manager.portfolio
                .get_currency_portfolio(reference_market).available
            )
        except Exception:
            available_balance = 0
        
        return {
            "holdings": holdings,
            "holdings_value": holdings_value,
            "total_value": total_value,
            "reference_market": reference_market,
            "available_balance": available_balance,
        }
    
    def _build_orders_state(self) -> dict:
        """Build orders state from exchange manager."""
        try:
            open_orders = trading_api.get_open_orders(self.exchange_manager)
            orders_list = [
                {
                    "symbol": order.symbol,
                    "side": order.side.value if hasattr(order.side, 'value') else str(order.side),
                    "type": order.order_type.value if hasattr(order.order_type, 'value') else str(order.order_type),
                    "amount": float(order.origin_quantity),
                    "price": float(order.origin_price) if order.origin_price else None,
                    "status": order.status.value if hasattr(order.status, 'value') else str(order.status),
                }
                for order in open_orders
            ]
        except Exception:
            orders_list = []
        
        return {
            "open_orders": orders_list,
            "pending_orders": [],
            "recent_trades": [],
        }
    
    def _build_current_distribution(self) -> dict:
        """Build current distribution from trading mode."""
        if not hasattr(self.trading_mode, 'ratio_per_asset') or not self.trading_mode.ratio_per_asset:
            return {}
        
        return {
            asset: float(data.get(index_trading.index_distribution.DISTRIBUTION_VALUE, 0))
            for asset, data in self.trading_mode.ratio_per_asset.items()
        }
    
    async def _get_ai_service(self):
        ai_service = await services_api.get_ai_service(
            is_backtesting=self.exchange_manager.is_backtesting
        )
        if not ai_service:
            self.logger.error("AIService not available, cannot perform AI analysis")
            return None
        return ai_service
    
    async def _submit_trading_evaluation(self, ai_instructions: list):
        """
        Submit AI instructions to trigger portfolio rebalancing.
        """
        ai_index_distribution.apply_ai_instructions(
            self.trading_mode, ai_instructions
        )
        await self.ensure_index()


class AIIndexTradingModeConsumer(index_trading.IndexTradingModeConsumer):
    @classmethod
    def get_should_cancel_loaded_orders(cls):
        return True


class AIIndexTradingMode(index_trading.IndexTradingMode):
    MODE_PRODUCER_CLASSES = [AIIndexTradingModeProducer]
    MODE_CONSUMER_CLASSES = [AIIndexTradingModeConsumer]

    # AI-specific config keys
    MODEL_KEY = "model"
    TEMPERATURE_KEY = "temperature"
    MAX_TOKENS_KEY = "max_tokens"
    LOG_AI_DECISIONS_KEY = "log_ai_decisions"
    USE_DEEP_AGENT_KEY = "use_deep_agent"

    async def single_exchange_process_health_check(self, chained_orders, tickers):
        return []

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Initialize user inputs for AI configuration.
        """
        super().init_user_inputs(inputs)

        # AI Model Configuration
        self.UI.user_input(
            self.MODEL_KEY,
            commons_enums.UserInputTypes.TEXT,
            inputs.get(self.MODEL_KEY),
            inputs,
            title="LLM model to use for AI strategy.",
        )

        self.UI.user_input(
            self.TEMPERATURE_KEY,
            commons_enums.UserInputTypes.FLOAT,
            inputs.get(self.TEMPERATURE_KEY),
            inputs,
            min_val=0.0,
            max_val=1.0,
            title="Temperature for AI randomness (0.0 = deterministic, 1.0 = creative).",
        )

        self.UI.user_input(
            self.MAX_TOKENS_KEY,
            commons_enums.UserInputTypes.INT,
            inputs.get(self.MAX_TOKENS_KEY),
            inputs,
            min_val=500,
            max_val=4000,
            title="Maximum tokens for AI response.",
        )

        self.UI.user_input(
            self.LOG_AI_DECISIONS_KEY,
            commons_enums.UserInputTypes.BOOLEAN,
            inputs.get(self.LOG_AI_DECISIONS_KEY),
            inputs,
            title="Log debate/judge decisions at INFO (verbose).",
        )

        self.UI.user_input(
            self.USE_DEEP_AGENT_KEY,
            commons_enums.UserInputTypes.BOOLEAN,
            inputs.get(self.USE_DEEP_AGENT_KEY, False),
            inputs,
            title="Use Deep Agent implementation (requires deepagents package). Default: use traditional AI agent.",
        )
