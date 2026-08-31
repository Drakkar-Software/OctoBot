# pylint: disable=C0103
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
import tempfile

_MODULE_LOGGER = logging.getLogger(__name__)

_SIZE_CHECK_WRITE_THRESHOLD = 64 * 1024


def _count_lines(data: bytes) -> int:
    if not data:
        return 0
    line_count = data.count(b"\n")
    if not data.endswith(b"\n"):
        line_count += 1
    return line_count


def _find_trim_offset(data: bytes, trim_lines_fraction: float) -> int:
    if not data:
        return 0
    total_lines = _count_lines(data)
    if total_lines == 0:
        return 0
    lines_to_remove = max(1, int(total_lines * trim_lines_fraction))
    removed_lines = 0
    for index, byte in enumerate(data):
        if byte == ord("\n"):
            removed_lines += 1
            if removed_lines >= lines_to_remove:
                return index + 1
    return max(1, int(len(data) * trim_lines_fraction))


def _trim_file_bytes(log_path: str, trim_lines_fraction: float) -> None:
    with open(log_path, "rb") as log_file:
        data = log_file.read()
    if not data:
        return
    trim_offset = _find_trim_offset(data, trim_lines_fraction)
    remainder = data[trim_offset:]
    log_directory = os.path.dirname(log_path)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=log_directory) as temp_file:
        temp_path = temp_file.name
        temp_file.write(remainder)
    os.replace(temp_path, log_path)


class CappedFileHandler(logging.FileHandler):
    """
    FileHandler that trims the oldest lines from a log file when it exceeds max_bytes.
    """
    def __init__(
        self,
        filename: str,
        max_bytes: int,
        trim_lines_fraction: float = 0.2,
        mode: str = "a",
        encoding: str | None = "utf-8",
    ):
        super().__init__(filename, mode=mode, encoding=encoding)
        self._max_bytes = max_bytes
        self._trim_lines_fraction = trim_lines_fraction
        self._size_check_threshold = min(
            _SIZE_CHECK_WRITE_THRESHOLD,
            max(1, self._max_bytes // 4),
        )
        self._approx_bytes = os.path.getsize(filename) if os.path.exists(filename) else 0
        self._bytes_since_size_check = 0
        if self._approx_bytes >= self._max_bytes:
            self._bytes_since_size_check = self._size_check_threshold

    def emit(self, record: logging.LogRecord) -> None:
        try:
            formatted_message = self.format(record)
            encoding = self.encoding or "utf-8"
            written_bytes = (
                len(formatted_message.encode(encoding))
                + len(self.terminator.encode(encoding))
            )
            super().emit(record)
            self._approx_bytes += written_bytes
            self._bytes_since_size_check += written_bytes
        except Exception:
            self.handleError(record)
            return
        if (
            self._approx_bytes >= self._max_bytes
            and self._bytes_since_size_check >= self._size_check_threshold
        ):
            self._maybe_trim()

    def _maybe_trim(self) -> None:
        self.flush()
        self._bytes_since_size_check = 0
        actual_size = os.path.getsize(self.baseFilename)
        self._approx_bytes = actual_size
        if actual_size < self._max_bytes:
            return
        if self.stream:
            self.stream.close()
            self.stream = None
        try:
            _trim_file_bytes(self.baseFilename, self._trim_lines_fraction)
        except Exception:
            _MODULE_LOGGER.exception("Failed to trim log file %s", self.baseFilename)
            raise
        self.stream = self._open()
        self._approx_bytes = os.path.getsize(self.baseFilename)
