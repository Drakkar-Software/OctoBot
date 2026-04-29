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

import asyncio
import fnmatch
import logging as std_logging
import os
import sys

import octobot_commons.logging as logging

# Glob patterns always use forward slash as separator (POSIX convention)
PATTERN_SEP = '/'


async def execute_tentacle_build(tentacle, logger: std_logging.Logger = None) -> None:
    if not tentacle.build_command:
        return
    
    logger = logger or logging.get_logger(__name__)
    logger.info(f"Executing build commands for {tentacle.name}: {tentacle.build_command}")
    
    for command in tentacle.build_command:
        # Replace 'python' with sys.executable to use the current Python interpreter
        command = command.replace('python ', f'"{sys.executable}" ', 1)
        
        logger.debug(f"Running: {command}")
        
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=tentacle.tentacle_module_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(
                f"Build command '{command}' failed for {tentacle.name} "
                f"with return code {process.returncode}: {error_msg}"
            )
        
        if stdout:
            logger.debug(f"Command output: {stdout.decode()}")
    
    logger.info(f"All build commands completed successfully for {tentacle.name}")


def matches_pattern(filepath: str, pattern: str) -> bool:
    """
    Check if filepath matches a glob pattern.
    Supports *, ?, [seq], and ** for recursive matching.
    Patterns without separators only match files at the top level.
    """
    # Normalize filepath to use forward slashes (glob patterns always use /)
    filepath = filepath.replace(os.sep, PATTERN_SEP)
    
    # Pattern without separator only matches top-level files
    if PATTERN_SEP not in pattern:
        return PATTERN_SEP not in filepath and fnmatch.fnmatch(filepath, pattern)
    
    # Simple pattern without ** - use fnmatch
    if '**' not in pattern:
        return fnmatch.fnmatch(filepath, pattern)
    
    # Pattern has ** - use recursive matching
    return _match_parts(filepath.split(PATTERN_SEP), pattern.split(PATTERN_SEP))


def _match_parts(filepath_parts, pattern_parts):
    """Recursively match filepath parts against pattern parts."""
    def match_recursive(fp_idx, pat_idx):
        # Consume all non-** pattern parts
        while pat_idx < len(pattern_parts) and pattern_parts[pat_idx] != '**':
            if fp_idx >= len(filepath_parts) or not fnmatch.fnmatch(filepath_parts[fp_idx], pattern_parts[pat_idx]):
                return False
            fp_idx += 1
            pat_idx += 1
        
        # All patterns consumed - check if all filepath parts consumed
        if pat_idx == len(pattern_parts):
            return fp_idx == len(filepath_parts)
        
        # Current pattern is ** - try matching from any position
        for i in range(fp_idx, len(filepath_parts) + 1):
            if match_recursive(i, pat_idx + 1):
                return True
        return False
    
    return match_recursive(0, 0)


def could_match_under_dir(dir_rel_path: str, pattern: str) -> bool:
    """
    Check if pattern could match files under a directory.
    Used to optimize directory traversal.
    
    :param dir_rel_path: Relative directory path (normalized to forward slashes)
    :param pattern: Glob pattern (uses forward slashes)
    :return: True if files under this directory could match the pattern
    """
    # Normalize path to forward slashes
    dir_rel_path = dir_rel_path.replace(os.sep, PATTERN_SEP)
    
    # Check if directory path aligns with pattern prefix
    dir_parts = dir_rel_path.split(PATTERN_SEP)
    pattern_parts = pattern.split(PATTERN_SEP)
    
    for dir_part, pat_part in zip(dir_parts, pattern_parts):
        if pat_part == '**':
            # ** matches zero or more segments; anything nested here could match
            return True
        if not fnmatch.fnmatch(dir_part, pat_part):
            return False
    
    # Directory could contain files that match if pattern has more parts
    return len(dir_parts) <= len(pattern_parts)
