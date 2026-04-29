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
import json
import re
import typing


def preprocess_json_content(content: str) -> str:
    if not content:
        return ""
    cleaned = content.strip()
    cleaned = _strip_wrapping_quotes(cleaned)
    if "\\n" in cleaned and "\n" not in cleaned:
        try:
            cleaned = bytes(cleaned, "utf-8").decode("unicode_escape")
        except Exception:
            pass
    fenced = _extract_fenced_content(cleaned)
    return fenced if fenced is not None else cleaned


def extract_json_from_content(content: str) -> typing.Optional[typing.Dict[str, typing.Any]]:
    if not content:
        return None

    cleaned = preprocess_json_content(content)
    parsed = _try_load(cleaned)
    if parsed is not None:
        return parsed

    for candidate in (
        extract_json_between_braces(cleaned),
        extract_json_from_markdown(content),
        extract_json_from_xml_tags(content),
    ):
        if candidate is not None:
            return candidate

    return None


def extract_json_between_braces(content: str) -> typing.Optional[typing.Dict[str, typing.Any]]:
    if not content:
        return None
    start = 0
    while True:
        json_str = _find_first_json_object(content, start_index=start)
        if not json_str:
            return None
        parsed = _try_load(json_str)
        if parsed is not None:
            return parsed
        next_pos = content.find("{", start + 1)
        if next_pos == -1:
            return None
        start = next_pos


def extract_json_from_markdown(content: str) -> typing.Optional[typing.Dict[str, typing.Any]]:
    matches = re.findall(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
    for match in matches:
        parsed = _try_load(match.strip())
        if parsed is not None:
            return parsed
    return None


def extract_json_from_xml_tags(content: str) -> typing.Optional[typing.Dict[str, typing.Any]]:
    matches = re.findall(r"<[^>]+>(.*?)</[^>]+>", content, re.DOTALL)
    for match in matches:
        match_str = match.strip()
        parsed = _try_load(match_str)
        if parsed is not None:
            return parsed
        parsed = extract_json_between_braces(match_str)
        if parsed is not None:
            return parsed
    return None


def _try_load(content: str) -> typing.Optional[typing.Dict[str, typing.Any]]:
    try:
        return json.loads(content)
    except Exception:
        return None


def _find_first_json_object(content: str, start_index: int = 0) -> typing.Optional[str]:
    if not content:
        return None
    start = content.find("{", start_index)
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(content)):
        ch = content[idx]
        if in_string:
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == "\"":
                in_string = False
            continue
        if ch == "\"":
            in_string = True
            continue
        if ch == "{":
            depth += 1
            continue
        if ch == "}":
            depth -= 1
            if depth == 0:
                return content[start:idx + 1]
    return None


def _extract_fenced_content(content: str) -> typing.Optional[str]:
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    if "```" in content:
        start = content.find("```")
        end = content.rfind("```")
        if start != -1 and end != -1 and end > start + 3:
            inner = content[start + 3:end]
            if inner.startswith("json"):
                inner = inner[4:]
            return inner.strip()
    return None


def _strip_wrapping_quotes(content: str) -> str:
    if (content.startswith("'") and content.endswith("'")) or (
        content.startswith('"') and content.endswith('"')
    ):
        return content[1:-1].strip()
    return content
