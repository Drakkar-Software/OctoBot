from typing import Protocol, runtime_checkable


@runtime_checkable
class Logger(Protocol):
    def debug(self, msg: str, **kwargs) -> None: ...
    def info(self, msg: str, **kwargs) -> None: ...
    def warning(self, msg: str, **kwargs) -> None: ...
    def error(self, msg: str, **kwargs) -> None: ...


class NopLogger:
    """No-op logger used when no logger is configured."""

    def debug(self, msg: str, **kwargs) -> None:
        pass

    def info(self, msg: str, **kwargs) -> None:
        pass

    def warning(self, msg: str, **kwargs) -> None:
        pass

    def error(self, msg: str, **kwargs) -> None:
        pass
