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

    def append_new_transactions_deduped(self, transactions: list[dict]) -> bool:
        tx_id_key = octobot_trading.enums.ExchangeConstantsTransactionColumns.TXID.value
        known_txids = {
            transaction[tx_id_key]
            for transaction in self.transactions
            if tx_id_key in transaction
        }
        added = False
        for transaction in transactions:
            tx_id = transaction.get(tx_id_key)
            if tx_id is None or tx_id in known_txids:
                continue
            known_txids.add(tx_id)
            self.transactions.append(dict(transaction))
            added = True
        return added

    def merge_transactions_from_account_elements(self, other: "AccountElements") -> bool:
        """Append transactions from ``other`` excluding tx ids already on ``self``."""
        return self.append_new_transactions_deduped(other.transactions)

    def _sync_transactions(self, transactions: list[dict]) -> bool:
        return self.append_new_transactions_deduped(transactions)
