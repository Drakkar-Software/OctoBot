import octobot_commons.logging as commons_logging
import octobot_trading.errors as trading_errors

import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import

logger = commons_logging.get_logger("TransactionsRepository")


class TransactionsRepository(base_exchange_repository_import.BaseExchangeRepository):

    async def fetch_deposits(self, since: int = None, limit: int = None) -> list[dict]:
        try:
            return await self.exchange_manager.exchange.get_deposits(since=since, limit=limit)
        except trading_errors.NotSupported:
            return []
        except trading_errors.AuthenticationError as error:
            logger.warning(
                "Skipping deposits fetch for %s: %s",
                self.exchange_manager.exchange_name,
                error,
            )
            return []

    async def fetch_withdrawals(self, since: int = None, limit: int = None) -> list[dict]:
        try:
            return await self.exchange_manager.exchange.get_withdrawals(since=since, limit=limit)
        except trading_errors.NotSupported:
            return []
        except trading_errors.AuthenticationError as error:
            logger.warning(
                "Skipping withdrawals fetch for %s: %s",
                self.exchange_manager.exchange_name,
                error,
            )
            return []
