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

import mock
import pytest

import octobot_commons.logging.capped_file_handler as capped_file_handler


@pytest.fixture
def temp_log_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def _create_handler(
    temp_log_directory: str,
    file_name: str = "test.log",
    max_bytes: int = 512,
    trim_lines_fraction: float = 0.2,
) -> capped_file_handler.CappedFileHandler:
    log_path = os.path.join(temp_log_directory, file_name)
    handler = capped_file_handler.CappedFileHandler(
        log_path,
        max_bytes=max_bytes,
        trim_lines_fraction=trim_lines_fraction,
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.setLevel(logging.INFO)
    return handler


def _emit_message(handler: capped_file_handler.CappedFileHandler, message: str) -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )
    handler.emit(record)


def _read_log_file(handler: capped_file_handler.CappedFileHandler) -> str:
    handler.flush()
    with open(handler.baseFilename, encoding="utf-8") as log_file:
        return log_file.read()


class TestEmit:
    def test_does_not_trim_below_max(self, temp_log_directory):
        handler = _create_handler(temp_log_directory, max_bytes=2048)
        with mock.patch("octobot_commons.logging.capped_file_handler.os.replace") as replace_mock:
            _emit_message(handler, "small message")
            handler.flush()
            replace_mock.assert_not_called()
        handler.close()

    def test_trims_oldest_lines_when_max_reached(self, temp_log_directory):
        log_path = os.path.join(temp_log_directory, "numbered.log")
        numbered_lines = "\n".join(f"line-{line_index}" for line_index in range(1, 11)) + "\n"
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write(numbered_lines)

        handler = _create_handler(temp_log_directory, file_name="numbered.log", max_bytes=60)
        _emit_message(handler, "line-new")
        content = _read_log_file(handler)
        handler.close()
        content_lines = [line for line in content.splitlines() if line]

        assert "line-1" not in content_lines
        assert "line-2" not in content_lines
        assert "line-3" in content_lines
        assert "line-10" in content_lines
        assert "line-new" in content_lines

    def test_continues_writing_after_trim(self, temp_log_directory):
        log_path = os.path.join(temp_log_directory, "continue.log")
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write("\n".join(f"old-{line_index}" for line_index in range(20)) + "\n")

        handler = _create_handler(temp_log_directory, file_name="continue.log", max_bytes=120)
        _emit_message(handler, "after-trim")
        _emit_message(handler, "still-writable")
        content = _read_log_file(handler)
        handler.close()

        assert "after-trim" in content
        assert "still-writable" in content

    def test_second_trim_cycle_works(self, temp_log_directory):
        handler = _create_handler(temp_log_directory, max_bytes=200)
        for message_index in range(40):
            _emit_message(handler, f"cycle-message-{message_index}")
        first_size = os.path.getsize(handler.baseFilename)
        for message_index in range(40, 80):
            _emit_message(handler, f"cycle-message-{message_index}")
        second_size = os.path.getsize(handler.baseFilename)
        handler.close()

        assert second_size <= first_size * 1.1
        assert "cycle-message-79" in _read_log_file(handler)


class TestTrimFile:
    def test_reduces_file_size_to_about_eighty_percent(self, temp_log_directory):
        log_path = os.path.join(temp_log_directory, "size.log")
        lines = "\n".join(f"payload-{line_index}" for line_index in range(50)) + "\n"
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write(lines)
        original_size = os.path.getsize(log_path)

        capped_file_handler._trim_file_bytes(log_path, trim_lines_fraction=0.2)
        trimmed_size = os.path.getsize(log_path)

        assert trimmed_size < original_size
        assert trimmed_size <= original_size * 0.85

    def test_single_line_file_trims_by_bytes(self, temp_log_directory):
        log_path = os.path.join(temp_log_directory, "single.log")
        single_line = "x" * 200
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write(single_line)
        original_size = os.path.getsize(log_path)

        capped_file_handler._trim_file_bytes(log_path, trim_lines_fraction=0.2)
        trimmed_size = os.path.getsize(log_path)

        assert trimmed_size < original_size
        assert trimmed_size == original_size - max(1, int(original_size * 0.2))

    def test_empty_file_is_noop(self, temp_log_directory):
        log_path = os.path.join(temp_log_directory, "empty.log")
        with open(log_path, "w", encoding="utf-8"):
            pass

        capped_file_handler._trim_file_bytes(log_path, trim_lines_fraction=0.2)

        assert os.path.getsize(log_path) == 0

    def test_utf8_multibyte_line_not_split(self, temp_log_directory):
        log_path = os.path.join(temp_log_directory, "utf8.log")
        lines = "\n".join(
            [
                "remove-me",
                "remove-me-too",
                "keep-café",
                "keep-naïve",
            ]
        ) + "\n"
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write(lines)

        capped_file_handler._trim_file_bytes(log_path, trim_lines_fraction=0.5)
        with open(log_path, encoding="utf-8") as log_file:
            content = log_file.read()

        assert "remove-me" not in content
        assert "keep-café" in content
        assert "keep-naïve" in content


class TestSizeCheck:
    def test_getsize_not_called_on_every_emit(self, temp_log_directory):
        handler = _create_handler(temp_log_directory, max_bytes=4096)
        with mock.patch("octobot_commons.logging.capped_file_handler.os.path.getsize") as getsize_mock:
            for message_index in range(20):
                _emit_message(handler, f"under-cap-{message_index}")
            handler.close()

        assert getsize_mock.call_count == 0

    def test_opens_existing_file_with_correct_initial_size(self, temp_log_directory):
        log_path = os.path.join(temp_log_directory, "existing.log")
        existing_lines = "\n".join(f"seed-{line_index}" for line_index in range(30)) + "\n"
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write(existing_lines)

        handler = _create_handler(temp_log_directory, file_name="existing.log", max_bytes=120)
        _emit_message(handler, "trigger-trim")
        content = _read_log_file(handler)
        handler.close()

        assert "seed-0" not in content
        assert "trigger-trim" in content


class TestTrimFailure:
    def test_trim_failure_logs_and_reraises(self, temp_log_directory, caplog):
        log_path = os.path.join(temp_log_directory, "failure.log")
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write("\n".join(f"line-{line_index}" for line_index in range(20)) + "\n")

        handler = _create_handler(temp_log_directory, file_name="failure.log", max_bytes=80)
        with mock.patch(
            "octobot_commons.logging.capped_file_handler.os.replace",
            side_effect=OSError("replace failed"),
        ):
            with caplog.at_level(logging.ERROR):
                with pytest.raises(OSError, match="replace failed"):
                    _emit_message(handler, "overflow")
        handler.close()

        assert "Failed to trim log file" in caplog.text
