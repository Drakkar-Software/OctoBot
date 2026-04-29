import dataclasses
import typing

import octobot_commons.dataclasses
import octobot_trading.exchanges.util.exchange_data as exchange_data_import
import octobot_trading.enums
import octobot_flow.enums



@dataclasses.dataclass
class AccountElements(octobot_commons.dataclasses.MinimizableDataclass, octobot_commons.dataclasses.UpdatableDataclass):
    """
    Defines the ideal exchange account state of an automation. Only contains sharable data
    """
    name: typing.Optional[str] = None
    portfolio: exchange_data_import.PortfolioDetails = dataclasses.field(default_factory=exchange_data_import.PortfolioDetails)
    transactions: list[dict] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if self.portfolio and isinstance(self.portfolio, dict):
            self.portfolio = exchange_data_import.PortfolioDetails.from_dict(self.portfolio)

    def sync_from_transactions(self, transactions: list[dict]) -> list[octobot_flow.enums.ChangedElements]:
        changed_elements = []
        if self._sync_transactions(transactions):
            changed_elements.append(octobot_flow.enums.ChangedElements.TRANSACTIONS)
        return changed_elements
    
    def _sync_transactions(self, transactions: list[dict]) -> bool:
        previous_transactions_ids = {
            transaction[octobot_trading.enums.ExchangeConstantsTransactionColumns.TXID.value]
            for transaction in self.transactions
        }
        added_transactions = [
            transaction
            for transaction in transactions
            if transaction[octobot_trading.enums.ExchangeConstantsTransactionColumns.TXID.value] not in previous_transactions_ids
        ]
        self.transactions.extend(added_transactions)
        return bool(added_transactions)
