#  Drakkar-Software OctoBot-Tentacles-Manager
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
import io
import logging

import mock
import pytest

import octobot_tentacles_manager.util.tentacle_processing as tentacle_processing


def _cp1252_logger(name: str) -> logging.Logger:
    cp1252_stream = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    handler = logging.StreamHandler(cp1252_stream)
    logger = logging.getLogger(name)
    logger.handlers = []
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    return logger


class TestDecodeSubprocessOutput:
    def test_unicode_and_ansi_are_safe_for_cp1252_logging(self):
        raw_output = b"\xe2\x8f\xb3 \x1b[36mDone\x1b[39m"
        decoded_output = tentacle_processing._decode_subprocess_output(raw_output)

        decoded_output.encode("cp1252")
        assert "\u23f3" not in decoded_output
        assert "Done" in decoded_output

    def test_plain_ascii_passes_through_unchanged(self):
        raw_output = b"up to date, audited 370 packages"
        decoded_output = tentacle_processing._decode_subprocess_output(raw_output)

        assert decoded_output == "up to date, audited 370 packages"

    def test_utf8_stderr_with_cp1252_logging_handler_replaces_emoji(self):
        raw_output = (
            b"\n> octobot-node@0.0.0 generate-client\n> openapi-ts\n\n"
            b"\xe2\x8f\xb3 \x1b[36mGenerating from\x1b[39m ./openapi.json\n"
            b"\x1b[32m\xf0\x9f\x9a\x80 Done!\x1b[39m Your output is in \x1b[96m./src\\client\x1b[39m\n"
        )
        decoded_output = tentacle_processing._decode_subprocess_output(raw_output)

        decoded_output.encode("cp1252")
        assert "\u23f3" not in decoded_output
        assert "\U0001f680" not in decoded_output
        assert "Generating from" in decoded_output
        assert "Done!" in decoded_output


class TestExecuteTentacleBuild:
    @pytest.mark.asyncio
    async def test_logs_unicode_subprocess_output_on_cp1252_console(self):
        tentacle = mock.Mock()
        tentacle.build_command = ["npm run generate-client"]
        tentacle.name = "node_web_interface"
        tentacle.tentacle_module_path = "."
        emoji_stdout = b"\n> openapi-ts\n\n\xe2\x8f\xb3 \x1b[36mGenerating\x1b[39m\n"

        async def fake_create_subprocess_shell(*_args, **_kwargs):
            process = mock.Mock()
            process.returncode = 0
            process.communicate = mock.AsyncMock(return_value=(emoji_stdout, b""))
            return process

        logger = _cp1252_logger("test_tentacle_build_unicode")
        cp1252_stream = logger.handlers[0].stream

        stderr_stream = mock.Mock(encoding="utf-8")
        with mock.patch.object(
            tentacle_processing.asyncio, "create_subprocess_shell", fake_create_subprocess_shell
        ):
            with mock.patch.object(tentacle_processing.sys, "stderr", stderr_stream):
                await tentacle_processing.execute_tentacle_build(tentacle, logger)

        assert cp1252_stream.buffer.getvalue()

    @pytest.mark.asyncio
    async def test_logs_openapi_ts_emoji_when_stderr_is_utf8_but_handler_is_cp1252(self):
        tentacle = mock.Mock()
        tentacle.build_command = ["npm run generate-client"]
        tentacle.name = "node_web_interface"
        tentacle.tentacle_module_path = "."
        emoji_stdout = (
            b"\n> octobot-node@0.0.0 generate-client\n> openapi-ts\n\n"
            b"\xe2\x8f\xb3 \x1b[36mGenerating from\x1b[39m ./openapi.json\n"
            b"\x1b[32m\xf0\x9f\x9a\x80 Done!\x1b[39m Your output is in \x1b[96m./src\\client\x1b[39m\n"
        )

        async def fake_create_subprocess_shell(*_args, **_kwargs):
            process = mock.Mock()
            process.returncode = 0
            process.communicate = mock.AsyncMock(return_value=(emoji_stdout, b""))
            return process

        logger = _cp1252_logger("test_tentacle_build_openapi_ts_emoji")
        cp1252_stream = logger.handlers[0].stream

        stderr_stream = mock.Mock(encoding="utf-8")
        with mock.patch.object(
            tentacle_processing.asyncio, "create_subprocess_shell", fake_create_subprocess_shell
        ):
            with mock.patch.object(tentacle_processing.sys, "stderr", stderr_stream):
                await tentacle_processing.execute_tentacle_build(tentacle, logger)

        logged_output = cp1252_stream.buffer.getvalue().decode("cp1252")
        assert "\u23f3" not in logged_output
        assert "\U0001f680" not in logged_output
        assert "Generating from" in logged_output
