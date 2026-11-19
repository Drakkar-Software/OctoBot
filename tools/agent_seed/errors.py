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


class AutomationIdConflictError(AgentSeedError):
    pass


class AgentSeedPortInUseError(AgentSeedError):
    pass


class AgentSeedNodeStopError(AgentSeedError):
    pass


class AgentSeedSchedulerSqliteConfigError(AgentSeedError):
    pass
