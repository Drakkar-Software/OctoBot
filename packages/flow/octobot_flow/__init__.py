import octobot_commons.logging

_import_tentacles = False
try:
    import tentacles
    _import_tentacles = True
except ImportError:
    octobot_commons.logging.get_logger("octobot_flow").info(
        "tentacles is not installed, tentacles operators will not be available"
    )

if _import_tentacles:
    from octobot_flow.jobs.automation_job import AutomationJob
    from octobot_flow.entities import (
        AbstractActionDetails,
        parse_action_details,
        AutomationState,
        ActionsDAG,
    )


    __all__ = [
        "AutomationJob",
        "AbstractActionDetails",
        "parse_action_details",
        "ActionsDAG",
        "AutomationState",
    ]
