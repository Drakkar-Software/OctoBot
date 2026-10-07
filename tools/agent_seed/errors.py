#  Demo-only agent seed typed errors.


class AgentSeedError(Exception):
    pass


class AutomationLifecycleError(AgentSeedError):
    pass


class AutomationNameLostError(AutomationLifecycleError):
    pass
