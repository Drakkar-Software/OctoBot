class OctobotCopyError(Exception):
    """
    Parent class for all octobot copy errors
    """


class RebalanceError(OctobotCopyError):
    """
    Parent class for all rebalance errors
    """


class RebalanceAborted(RebalanceError):
    """
    Raised when a rebalance is aborted
    """
