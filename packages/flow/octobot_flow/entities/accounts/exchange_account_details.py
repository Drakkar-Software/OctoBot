import dataclasses
import typing
import decimal

import octobot_commons.dataclasses
import octobot_commons.profiles.profile_data as profile_data_import
import octobot_trading.exchanges.util.exchange_data as exchange_data_import
import octobot_flow.entities.accounts.portfolio_asset_holdings as portfolio_asset_holdings_import


@dataclasses.dataclass
class ExchangeAccountPortfolio(octobot_commons.dataclasses.MinimizableDataclass, octobot_commons.dataclasses.UpdatableDataclass):
    content: list[portfolio_asset_holdings_import.PortfolioAssetHolding] = dataclasses.field(default_factory=list)
    unit: str = ""


@dataclasses.dataclass
class ExchangeAccountDetails(octobot_commons.dataclasses.MinimizableDataclass):
    exchange_details: profile_data_import.ExchangeData = dataclasses.field(
        default_factory=profile_data_import.ExchangeData, repr=True
    )
    auth_details: exchange_data_import.ExchangeAuthDetails = dataclasses.field(default_factory=exchange_data_import.ExchangeAuthDetails, repr=False)
    portfolio: ExchangeAccountPortfolio = dataclasses.field(default_factory=ExchangeAccountPortfolio, repr=True)

    def to_minimal_exchange_data(self, portfolio: typing.Optional[dict[str, dict[str, decimal.Decimal]]]) -> exchange_data_import.ExchangeData:
        exchange_data = exchange_data_import.ExchangeData(
            exchange_details=exchange_data_import.ExchangeDetails(
                name=self.exchange_details.internal_name, # type: ignore
            ),
            auth_details=self.auth_details,
        )
        if portfolio:
            exchange_data.portfolio_details.content = portfolio # type: ignore
        return exchange_data

    def is_simulated(self) -> bool:
        return not (
            self.auth_details.api_key
            or self.auth_details.api_secret
            or self.auth_details.api_password
            or self.auth_details.access_token
            or self.auth_details.encrypted
        )

    def __post_init__(self):
        if self.portfolio and isinstance(self.portfolio, dict):
            self.portfolio = ExchangeAccountPortfolio.from_dict(self.portfolio)
        if self.exchange_details and isinstance(self.exchange_details, dict):
            self.exchange_details = profile_data_import.ExchangeData.from_dict(self.exchange_details)
        if self.auth_details and isinstance(self.auth_details, dict):
            self.auth_details = exchange_data_import.ExchangeAuthDetails.from_dict(self.auth_details)
