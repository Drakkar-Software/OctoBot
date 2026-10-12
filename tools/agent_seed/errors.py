#  Demo-only agent seed typed errors.


class AgentSeedError(Exception):
    pass


class AutomationLifecycleError(AgentSeedError):
    pass


class AutomationNameLostError(AutomationLifecycleError):
    pass


class AgentSeedNodeStartupTimeoutError(AgentSeedError):
    pass


class AgentSeedClearNotInitializedError(AgentSeedError):
    pass


class GridAutomationIdConflictError(AgentSeedError):
    pass
