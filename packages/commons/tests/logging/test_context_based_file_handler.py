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

import octobot_commons.logging.context_based_file_handler as context_based_file_handler


@pytest.fixture
def temp_info_logs_and_cleanup_folder():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = logging.getLogger()
        original_level = root.level
        root.setLevel(logging.INFO)
        yield tmpdir
        root.setLevel(original_level)
        for handler in root.handlers[:]:
            if isinstance(handler, context_based_file_handler.ContextBasedFileHandler):
                handler.close()
                root.removeHandler(handler)


def test_context_based_file_handler_writes_to_file_when_provider_returns_name(temp_info_logs_and_cleanup_folder):
    file_name_provider = mock.Mock(return_value="my_context")
    handler = context_based_file_handler.ContextBasedFileHandler(
        temp_info_logs_and_cleanup_folder, file_name_provider
    )
    handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(handler)

    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.INFO)
    logger.info("test message")

    handler.flush()
    log_path = os.path.join(temp_info_logs_and_cleanup_folder, "my_context.log")
    with open(log_path, encoding="utf-8") as f:
        content = f.read()
    assert "test message" in content


def test_context_based_file_handler_does_not_write_when_provider_returns_none(temp_info_logs_and_cleanup_folder):
    file_name_provider = mock.Mock(return_value=None)
    handler = context_based_file_handler.ContextBasedFileHandler(
        temp_info_logs_and_cleanup_folder, file_name_provider
    )
    handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(handler)

    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.INFO)
    logger.info("test message")

    handler.flush()
    assert not os.listdir(temp_info_logs_and_cleanup_folder)


def test_context_based_file_handler_creates_multiple_files_for_different_contexts(
    temp_info_logs_and_cleanup_folder,
):
    contexts = []

    def rotating_provider():
        return contexts[0] if contexts else None

    handler = context_based_file_handler.ContextBasedFileHandler(
        temp_info_logs_and_cleanup_folder, rotating_provider
    )
    handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(handler)
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.INFO)

    contexts.append("ctx_a")
    logger.info("message a")
    handler.flush()

    contexts[0] = "ctx_b"
    logger.info("message b")
    handler.flush()

    files = sorted(os.listdir(temp_info_logs_and_cleanup_folder))
    assert files == ["ctx_a.log", "ctx_b.log"]

    with open(f"{temp_info_logs_and_cleanup_folder}/ctx_a.log", encoding="utf-8") as f:
        assert "message a" in f.read()
    with open(f"{temp_info_logs_and_cleanup_folder}/ctx_b.log", encoding="utf-8") as f:
        assert "message b" in f.read()


def test_context_based_file_handler_removes_oldest_when_max_handlers_reached(temp_info_logs_and_cleanup_folder):
    with mock.patch.object(
        context_based_file_handler,
        "MAX_CONTEXT_BASED_FILE_HANDLERS_PER_CATEGORY",
        3,
    ):
        contexts = []

        def rotating_provider():
            return contexts[0] if contexts else None

        handler = context_based_file_handler.ContextBasedFileHandler(
            temp_info_logs_and_cleanup_folder, rotating_provider
        )
        handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(handler)
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.INFO)

        contexts.append("ctx_1")
        logger.info("msg 1")
        handler.flush()

        contexts[0] = "ctx_2"
        logger.info("msg 2")
        handler.flush()

        contexts[0] = "ctx_3"
        logger.info("msg 3")
        handler.flush()

        contexts[0] = "ctx_4"
        logger.info("msg 4")
        handler.flush()

        assert len(handler._custom_handlers) == 3
        assert "ctx_1" not in handler._custom_handlers
        assert "ctx_2" in handler._custom_handlers
        assert "ctx_3" in handler._custom_handlers
        assert "ctx_4" in handler._custom_handlers


def test_add_context_based_file_handler_adds_handler_to_root_logger(temp_info_logs_and_cleanup_folder):
    file_name_provider = mock.Mock(return_value=None)
    root = logging.getLogger()
    initial_count = len(root.handlers)

    context_based_file_handler.add_context_based_file_handler(
        temp_info_logs_and_cleanup_folder, file_name_provider
    )

    assert len(root.handlers) == initial_count + 1
    added = root.handlers[-1]
    assert isinstance(added, context_based_file_handler.ContextBasedFileHandler)


def test_context_based_file_handler_creates_logs_folder_if_missing(temp_info_logs_and_cleanup_folder):
    nested = f"{temp_info_logs_and_cleanup_folder}/nested/logs"
    file_name_provider = mock.Mock(return_value="ctx")
    handler = context_based_file_handler.ContextBasedFileHandler(
        nested, file_name_provider
    )
    handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(handler)

    assert os.path.isdir(nested)
    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    logger.info("msg")
    handler.flush()
    assert os.path.isfile(f"{nested}/ctx.log")
