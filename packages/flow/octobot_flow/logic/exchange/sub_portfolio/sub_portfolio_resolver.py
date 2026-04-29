import octobot_commons.constants as common_constants

import octobot_flow.entities
import octobot_flow.errors


class SubPortfolioResolver:
    def __init__(self, automation_state: octobot_flow.entities.AutomationState):
        self._automation_state = automation_state

    async def resolve(self):
        # equivalent to serverless global view update
        # 1. identify missing orders #TODO
        # 2. resolve missing orders #TODO
        # 3. resolve (sub)portfolios
        await self._resolve_full_portfolio(self._automation_state.automation)
            # await self._resolve_sub_portfolio(bot_details)

    async def _resolve_sub_portfolio(self, automation: octobot_flow.entities.AutomationDetails):
        # TODO: implement to support sub portfolios
        # for now only uses the global portfolio content
        raise NotImplementedError("SubPortfolioResolver._resolve_sub_portfolio is not implemented")

    async def _resolve_full_portfolio(self, automation: octobot_flow.entities.AutomationDetails):
        if automation.exchange_account_elements is None:
            raise octobot_flow.errors.ExchangeAccountInitializationError(
                "Exchange account elements are required to resolve the portfolio"
            )
        automation.exchange_account_elements.portfolio.content = {
            asset.asset: {
                common_constants.PORTFOLIO_AVAILABLE: asset.available,
                common_constants.PORTFOLIO_TOTAL: asset.total,
            }
            for asset in self._automation_state.exchange_account_details.portfolio.content
            if asset.total > 0
        }
