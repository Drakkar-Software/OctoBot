import dataclasses

import octobot_trading.exchanges
import octobot_trading.api
import octobot_trading.enums as trading_enums

import octobot_flow.enums
import octobot_flow.entities.accounts.reference_exchange_account_elements as reference_exchange_account_elements_import

@dataclasses.dataclass
class ClientExchangeAccountElements(reference_exchange_account_elements_import.ReferenceExchangeAccountElements):
    """
    Defines the local exchange account state of an automation. Contains private data specific to this client.
    """
    trades: list[dict] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        if self.trades and isinstance(self.trades[0], dict):
            self.trades = [
                dict(trade) for trade in self.trades # type: ignore
            ]

    def sync_from_exchange_manager(
        self, exchange_manager: octobot_trading.exchanges.ExchangeManager
    ) -> list[octobot_flow.enums.ChangedElements]:
        changed_elements = super().sync_from_exchange_manager(exchange_manager)
        if self._sync_trades_from_exchange_manager(exchange_manager):
            changed_elements.append(octobot_flow.enums.ChangedElements.TRADES)
        return changed_elements

    def _sync_trades_from_exchange_manager(self, exchange_manager: octobot_trading.exchanges.ExchangeManager) -> bool:
        previous_trades_count = len(self.trades)
        if update_trades := octobot_trading.api.get_trade_history(exchange_manager, as_dict=True):
            current_trade_ids = {
                trade[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_TRADE_ID.value]
                for trade in self.trades
            }
            if new_trades := tuple(
                trade
                for trade in update_trades
                if trade[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_TRADE_ID.value] not in current_trade_ids
            ):
                self.trades.extend(new_trades)
        return previous_trades_count != len(self.trades)
