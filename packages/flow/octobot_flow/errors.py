class OctobotFlowError(Exception):
    """parent class for all octobot flow errors"""

class ConfigurationError(OctobotFlowError):
    """an error related to the configuration of the bot"""

class ExchangeError(OctobotFlowError):
    """an error related to the bot's communication with the exchange"""

class AutomationActionError(OctobotFlowError):
    """an error related to an automation action execution"""

class DSLExecutorError(OctobotFlowError):
    """raise when a DSL executor error occurs"""

class ExchangeAccountInitializationError(ExchangeError):
    """raise when an exchange account initialization fails"""

class InitializationRunFailedError(ConfigurationError):
    """raise when an initialization run fails"""


class NoExchangeAccountDetailsError(ConfigurationError):
    """raise when no exchange account details are available"""


class AutomationValidationError(ConfigurationError):
    """raise when an automation configuration or state is invalid"""


class UnsupportedActionTypeError(AutomationActionError):
    """raise when an unsupported action type is encountered"""


class UnsupportedConfiguredActionTypeError(UnsupportedActionTypeError):
    """raise when an unsupported configured action type is encountered"""



class InvalidAutomationActionError(ConfigurationError):
    """raise when an automation action is invalid"""


class InvalidConfigurationActionError(ConfigurationError):
    """raise when a configuration action is invalid"""


class NoProfileDataError(ConfigurationError):
    """raise when no profile data is available"""


class NoAutomationError(ConfigurationError):
    """raise when a automations state does not contain any automation"""


class CommunityError(ConfigurationError):
    """an error related to the community authentication of the bot"""


class CommunityAuthenticationRequiredError(CommunityError):
    """raise when community authentication is required"""


class UnresolvedDSLScriptError(AutomationActionError):
    """raise when a DSL script is not resolved"""


class ActionDependencyError(AutomationActionError):
    """raise when an action dependency is invalid"""


class AutomationDAGResetError(AutomationActionError):
    """raise when a DAG reset fails"""


class ActionDependencyNotFoundError(ActionDependencyError):
    """raise when an action dependency is not found"""


class MissingDSLExecutorDependencyError(DSLExecutorError):
    """raise when a DSL executor dependency is missing"""
