#  Drakkar-Software OctoBot-Tentacles
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

import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Any

CCXT_PATH = '../../../../../../../ccxt'
FILE_MAPPINGS: Dict[str, Dict[str, Any]] = {
    f'{CCXT_PATH}/python/ccxt/polymarket.py': {
        'destination': '../ccxt/polymarket_sync.py',
        'patches': [
            ('from ccxt.abstract.polymarket import ImplicitAPI', 'from .polymarket_abstract import ImplicitAPI'),
        ],
    },
    f'{CCXT_PATH}/python/ccxt/async_support/polymarket.py': {
        'destination': '../ccxt/polymarket_async.py',
        'patches': [
            ('from ccxt.abstract.polymarket import ImplicitAPI', 'from .polymarket_abstract import ImplicitAPI'),
        ],
    },
    f'{CCXT_PATH}/python/ccxt/pro/polymarket.py': {
        'destination': '../ccxt/polymarket_pro.py',
        'patches': [
            ('import ccxt.async_support', 'from .polymarket_async import polymarket'),
            ('class polymarket(ccxt.async_support.polymarket):', 'class polymarket(polymarket):'),
        ],
    },
    f'{CCXT_PATH}/python/ccxt/abstract/polymarket.py': {
        'destination': '../ccxt/polymarket_abstract.py',
        'patches': [],
    },
}


def apply_patches(file_path: str, patches: List[Tuple[str, str]]) -> None:
    """
    Apply patches to the copied file.
    
    Args:
        file_path: Path to the destination file
        patches: List of (old_string, new_string) tuples to replace
    """
    if not patches:
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Apply each patch
    for old_string, new_string in patches:
        if old_string in content:
            content = content.replace(old_string, new_string)
            print(f"  Applied patch: {old_string[:50]}... -> {new_string[:50]}...")
        else:
            print(f"  Warning: Patch pattern not found: {old_string[:50]}...")
    
    # Only write if content changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Patches applied successfully")
    else:
        print(f"  No changes made (patches may have already been applied)")


def copy_files() -> None:
    """
    Copy files from ccxt directory to local ccxt directory with optional patches.
    """
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    
    for source_rel, config in FILE_MAPPINGS.items():
        dest_rel = config['destination']
        patches = config.get('patches', [])
        
        # Resolve paths relative to script directory
        source_path = (script_dir / source_rel).resolve()
        dest_path = (script_dir / dest_rel).resolve()
        
        # Check if source file exists
        if not source_path.exists():
            print(f"Warning: Source file not found: {source_path}")
            continue
        
        # Ensure destination directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy the file
        print(f"Copying {source_path.name} -> {dest_path}")
        shutil.copy2(source_path, dest_path)
        
        # Apply patches if any are specified
        if patches:
            print(f"Applying {len(patches)} patch(es) to {dest_path.name}")
            apply_patches(str(dest_path), patches)
        else:
            print(f"No patches needed for {dest_path.name}")


if __name__ == '__main__':
    copy_files()

