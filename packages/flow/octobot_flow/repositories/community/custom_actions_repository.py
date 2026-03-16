import octobot.community

import octobot_flow.entities


class CustomActionsRepository:
    def __init__(self, authenticator: octobot.community.CommunityAuthentication):
        self.authenticator: octobot.community.CommunityAuthentication = authenticator

    async def fetch_custom_actions(
        self, 
        user_action_history_ids: list[str], 
        select_pending_user_actions_only: bool
    ) -> list[octobot_flow.entities.AbstractActionDetails]:
        raise NotImplementedError("TODO: fetch_custom_actions")

    async def fetch_signals(
        self, signal_history_ids: list[str], select_pending_signals_only: bool
    ) -> list[octobot_flow.entities.AbstractActionDetails]:
        raise NotImplementedError("TODO: fetch_signals")

    async def update_custom_actions_history(self, actions: list[octobot_flow.entities.AbstractActionDetails]):
        raise NotImplementedError("TODO: update_custom_actions_history")
