# pylint: disable=C0415, W0603, W1508, R0913, C0103
#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import logging
import os
import typing

import octobot_commons.logging.capped_file_handler as capped_file_handler


MAX_CONTEXT_BASED_FILE_HANDLERS_PER_CATEGORY = 30
DEFAULT_CONTEXT_BASED_FILE_FORMATTER = "%(asctime)s %(levelname)-8s %(name)-20s %(message)s"


def add_context_based_file_handler(
    logs_folder: str,
    file_name_provider: typing.Callable[[], typing.Optional[str]],
    max_file_bytes: int | None = None,
    trim_lines_fraction: float = 0.2,
) -> None:
    """
    Add the ContextBasedFileHandler to the root logger. Logs will
    additionally be written to a file named after the file name provided by the file_name_provider.
    """
    logging.getLogger().addHandler(
        ContextBasedFileHandler(
            logs_folder,
            file_name_provider,
            max_file_bytes=max_file_bytes,
            trim_lines_fraction=trim_lines_fraction,
        )
    )


class ContextBasedFileHandler(logging.Handler):
    """
    Logging handler that writes logs to specific files when the
    context is set. The log file name is the file name provided by the file_name_provider.
    """
    def __init__(
        self,
        logs_folder: str,
        file_name_provider: typing.Callable[[], typing.Optional[str]],
        max_file_bytes: int | None = None,
        trim_lines_fraction: float = 0.2,
    ):
        super().__init__()
        self._custom_handlers: dict[str, logging.FileHandler] = {}
        self._file_name_provider = file_name_provider
        self._logs_folder = logs_folder
        self._max_file_bytes = max_file_bytes
        self._trim_lines_fraction = trim_lines_fraction
        os.makedirs(self._logs_folder, exist_ok=True)

    def emit(self, record: logging.LogRecord) -> None:
        if file_name := self._file_name_provider():
            if file_name not in self._custom_handlers:
                if len(self._custom_handlers) >= MAX_CONTEXT_BASED_FILE_HANDLERS_PER_CATEGORY:
                    self._remove_oldest_handler()
                self._custom_handlers[file_name] = self._create_file_handler(file_name)
            self._custom_handlers[file_name].emit(record)

    def close(self) -> None:
        for file_handler in self._custom_handlers.values():
            file_handler.close()
        super().close()

    def _remove_oldest_handler(self) -> None:
        oldest_key = next(iter(self._custom_handlers))
        oldest_handler = self._custom_handlers.pop(oldest_key)
        logging.getLogger().removeHandler(oldest_handler)
        oldest_handler.close()

    def _create_file_handler(self, file_name: str) -> logging.FileHandler:
        log_path = os.path.join(self._logs_folder, f"{file_name}.log")
        if self._max_file_bytes is not None:
            file_handler = capped_file_handler.CappedFileHandler(
                log_path,
                max_bytes=self._max_file_bytes,
                trim_lines_fraction=self._trim_lines_fraction,
                mode="a",
                encoding="utf-8",
            )
        else:
            file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
        file_handler.setLevel(self.level)
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, logging.FileHandler) and handler.formatter:
                # reuse the user configured formatter
                file_handler.setFormatter(handler.formatter)
                break
        else:
            # default formatter
            file_handler.setFormatter(logging.Formatter(DEFAULT_CONTEXT_BASED_FILE_FORMATTER))
        return file_handler
