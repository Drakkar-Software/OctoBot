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
import typing
import json
import re


def extract_json_from_content(content: str) -> typing.Optional[typing.Dict[str, typing.Any]]:
    if not content:
        return None
    
    # Try multiple approaches to extract JSON
    approaches = [
        # Approach 1: Direct JSON object (curly braces)
        extract_json_between_braces,
        # Approach 2: JSON wrapped in markdown code block
        extract_json_from_markdown,
        # Approach 3: JSON wrapped in XML tags (e.g., <final_answer>)
        extract_json_from_xml_tags,
    ]
    
    for approach in approaches:
        try:
            data = approach(content)
            if data:
                return data
        except Exception:
            continue
    
    return None


def extract_json_between_braces(content: str) -> typing.Optional[typing.Dict[str, typing.Any]]:
    json_start = content.find("{")
    json_end = content.rfind("}") + 1
    if json_start >= 0 and json_end > json_start:
        try:
            json_str = content[json_start:json_end]
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    return None


def extract_json_from_markdown(content: str) -> typing.Optional[typing.Dict[str, typing.Any]]:
    # Look for ```json ... ``` blocks
    pattern = r'```(?:json)?\s*\n(.*?)\n```'
    matches = re.findall(pattern, content, re.DOTALL)
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue
    return None


def extract_json_from_xml_tags(content: str) -> typing.Optional[typing.Dict[str, typing.Any]]:
    # Look for any tag with JSON content
    pattern = r'<[^>]+>(.*?)</[^>]+>'
    matches = re.findall(pattern, content, re.DOTALL)
    for match in matches:
        match_str = match.strip()
        # Recursively try to extract JSON from the tag content
        try:
            return json.loads(match_str)
        except json.JSONDecodeError:
            # Try extracting braces from within the tag
            try:
                data = extract_json_between_braces(match_str)
                if data:
                    return data
            except Exception:
                pass
    return None
