class PikoError(Exception):
    """Base class for all Piko client errors."""


class ConnectionClosed(PikoError):
    """Raised when an operation is attempted on a closed connection."""


class RetryableError(PikoError):
    """Wraps an underlying error to indicate it can be retried."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code
