#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import pytest

from octobot_agents.utils.extractor import (
    extract_json_from_content,
    extract_json_between_braces,
    extract_json_from_markdown,
    extract_json_from_xml_tags,
    preprocess_json_content,
)


def test_preprocess_json_content_strips_fences():
    content = """```json
    {"key": "value"}
    ```"""
    assert preprocess_json_content(content) == '{"key": "value"}'


def test_extract_json_from_content_direct_json():
    content = '{"key": "value", "num": 1}'
    assert extract_json_from_content(content) == {"key": "value", "num": 1}


def test_extract_json_from_content_markdown_json():
    content = """```json
    {"key": "value"}
    ```"""
    assert extract_json_from_content(content) == {"key": "value"}


def test_extract_json_between_braces():
    content = "prefix {\"key\": \"value\"} suffix"
    assert extract_json_between_braces(content) == {"key": "value"}

def test_extract_json_between_braces_with_braces_in_text():
    content = "prefix {not json} {\"key\": \"value\"} suffix"
    assert extract_json_between_braces(content) == {"key": "value"}


def test_extract_json_from_markdown():
    content = """```json
    {"key": "value"}
    ```"""
    assert extract_json_from_markdown(content) == {"key": "value"}

def test_extract_json_from_content_prefixed_markdown():
    content = """Error parsing JSON from response ```json
    {"key": "value"}
    ```"""
    assert extract_json_from_content(content) == {"key": "value"}

def test_extract_json_from_content_single_quoted_payload():
    content = "'Error parsing JSON from response ```json\\n{\"key\": \"value\"}\\n```'"
    assert extract_json_from_content(content) == {"key": "value"}

def test_extract_json_from_content_fenced_with_suffix():
    content = """Error parsing JSON from response
```json
{"key": "value"}
```
--- 
Extra text after fence."""
    assert extract_json_from_content(content) == {"key": "value"}


def test_extract_json_from_xml_tags():
    content = "<final_answer>{\"key\": \"value\"}</final_answer>"
    assert extract_json_from_xml_tags(content) == {"key": "value"}


def test_extract_json_from_content_invalid():
    assert extract_json_from_content("not json") is None
