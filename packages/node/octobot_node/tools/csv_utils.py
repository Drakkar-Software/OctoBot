#  Drakkar-Software OctoBot-Node
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

import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import octobot_commons.cryptography as cryptography
from octobot_node.scheduler.encryption.task_inputs import (
    encrypt_task_content,
    decrypt_task_content,
)
from octobot_node.scheduler.encryption.task_outputs import (
    encrypt_task_result,
    decrypt_task_result,
)
from octobot_node.scheduler.encryption.task_outputs import (
    encrypt_task_result,
    decrypt_task_result,
)

################################################################################
# This file is used to test the functions inside node_web_interface/src/lib/csv.ts
# It provides Python implementations of the CSV column merging logic to verify
# that the TypeScript implementation behaves correctly.
################################################################################

COLUMN_NAME = "name"
COLUMN_CONTENT = "content"
COLUMN_TYPE = "type"
COLUMN_METADATA = "metadata"

REQUIRED_KEYS = [COLUMN_NAME, COLUMN_TYPE]
KEYS_OUTSIDE_CONTENT = [COLUMN_NAME, COLUMN_TYPE, COLUMN_METADATA]

DEFAULT_KEYS_FILE = "task_encryption_keys.json"

KEY_NAMES = {
    "TASKS_INPUTS_RSA_PUBLIC_KEY": "tasks_inputs_rsa_public_key",
    "TASKS_INPUTS_RSA_PRIVATE_KEY": "tasks_inputs_rsa_private_key",
    "TASKS_INPUTS_ECDSA_PUBLIC_KEY": "tasks_inputs_ecdsa_public_key",
    "TASKS_INPUTS_ECDSA_PRIVATE_KEY": "tasks_inputs_ecdsa_private_key",
    "TASKS_OUTPUTS_RSA_PUBLIC_KEY": "tasks_outputs_rsa_public_key",
    "TASKS_OUTPUTS_RSA_PRIVATE_KEY": "tasks_outputs_rsa_private_key",
    "TASKS_OUTPUTS_ECDSA_PUBLIC_KEY": "tasks_outputs_ecdsa_public_key",
    "TASKS_OUTPUTS_ECDSA_PRIVATE_KEY": "tasks_outputs_ecdsa_private_key",
}


def load_key_file(key_file_path: str) -> bytes:
    """Load a key from a PEM file.
    
    Args:
        key_file_path: Path to the key file
        
    Returns:
        The key content as bytes
        
    Raises:
        FileNotFoundError: If the key file doesn't exist
        IOError: If the key file cannot be read
    """
    key_path = Path(key_file_path)
    if not key_path.exists():
        raise FileNotFoundError(f"Key file not found: {key_file_path}")
    
    try:
        with open(key_path, 'rb') as f:
            key_content = f.read()
        return key_content
    except IOError as e:
        raise IOError(f"Failed to read key file {key_file_path}: {e}") from e


def set_key_from_file_or_env(
    key_file_path: Optional[str],
    settings_key_name: str,
    env_var_name: str,
    key_display_name: str
) -> None:
    """Load a key from a file or environment variable and set it in settings.
    
    Priority order:
    1. File path (if provided)
    2. Environment variable (loaded automatically by settings system if file path not provided)
    
    Args:
        key_file_path: Optional path to the key file
        settings_key_name: Name of the settings attribute to set (e.g., 'TASKS_INPUTS_RSA_PUBLIC_KEY')
        env_var_name: Name of the environment variable (for error messages)
        key_display_name: Display name for the key (for user messages)
        
    Raises:
        FileNotFoundError: If a key file path is provided but doesn't exist
        IOError: If a key file cannot be read
        ValueError: If neither file path nor environment variable is available
    """
    from octobot_node.config import settings
    
    if key_file_path:
        key = load_key_file(key_file_path)
        setattr(settings, settings_key_name, key)
        print(f"Successfully loaded {key_display_name} from file: {key_file_path}")
    else:
        # Settings system automatically loads from environment variable
        key_value = getattr(settings, settings_key_name, None)
        if key_value:
            print(f"Using {key_display_name} from environment variable: {env_var_name}")
        else:
            raise ValueError(
                f"{key_display_name} not found. Provide file path or set {env_var_name} environment variable."
            )


def find_column_index(column_names: List[str], key: str) -> int:
    for i, col in enumerate(column_names):
        if col.lower() == key.lower():
            return i
    return -1


def validate_required_keys(column_names: List[str]) -> Dict[int, str]:
    required_keys_indices: Dict[int, str] = {}
    for key in REQUIRED_KEYS:
        index = find_column_index(column_names, key)
        if index == -1:
            raise ValueError(f"Required key '{key}' not found in CSV header")
        required_keys_indices[index] = key
    return required_keys_indices


def find_keys_outside_content_indices(column_names: List[str]) -> Dict[int, str]:
    indices: Dict[int, str] = {}
    for key in KEYS_OUTSIDE_CONTENT:
        index = find_column_index(column_names, key)
        if index != -1:
            indices[index] = key
    return indices


def build_content(
    values: List[str],
    column_names: List[str],
    keys_outside_content_indices: Dict[int, str],
    content_column_index: int
) -> str:
    content_object: Dict[str, Any] = {}
    
    # Add all columns (except keys outside content and the content column itself) to the JSON object
    for i in range(min(len(column_names), len(values))):
        if i not in keys_outside_content_indices and i != content_column_index:
            value = values[i].strip() if i < len(values) else ""
            if value:
                column_name = column_names[i]
                upper_key = column_name.upper()
                
                # Try to parse as JSON, otherwise use as string
                try:
                    parsed_value = json.loads(value)
                    content_object[upper_key] = parsed_value
                except (json.JSONDecodeError, ValueError):
                    # If not valid JSON, use as string
                    content_object[upper_key] = value
    
    # If there's a content column, try to parse it as JSON and merge it
    if content_column_index != -1 and content_column_index < len(values):
        content_column_value = values[content_column_index].strip()
        if content_column_value:
            try:
                parsed_content = json.loads(content_column_value)
                # Merge the parsed content into the content object
                if isinstance(parsed_content, dict) and parsed_content is not None:
                    content_object.update(parsed_content)
                else:
                    # If content is not an object, add it as a special key
                    content_object["CONTENT"] = parsed_content
            except (json.JSONDecodeError, ValueError):
                # If not valid JSON, add as string
                content_object["CONTENT"] = content_column_value
    
    return json.dumps(content_object)


def validate_row_has_required_keys(
    values: List[str],
    required_keys_indices: Dict[int, str]
) -> bool:
    for index in required_keys_indices:
        if index >= len(values) or not values[index].strip():
            return False
    return True


def process_row(
    values: List[str],
    column_names: List[str],
    required_keys_indices: Dict[int, str],
    keys_outside_content_indices: Dict[int, str],
    content_column_index: int
) -> Optional[Dict[str, str]]:
    if not values or all(not v.strip() for v in values):
        return None
    
    while len(values) < len(column_names):
        values.append("")
    
    if not validate_row_has_required_keys(values, required_keys_indices):
        return None
    
    keys_outside_content_values: Dict[str, str] = {}
    for index, key in keys_outside_content_indices.items():
        if index < len(values):
            value = values[index].strip()
            if value:
                keys_outside_content_values[key] = value
    
    has_metadata = COLUMN_METADATA in keys_outside_content_values
    
    # For encrypted CSVs (with metadata), pass through content as-is (base64 string)
    # For non-encrypted CSVs, build JSON content from columns
    if has_metadata and content_column_index != -1:
        final_content = values[content_column_index].strip() if content_column_index < len(values) else ""
    else:
        final_content = build_content(
            values,
            column_names,
            keys_outside_content_indices,
            content_column_index
        )
    
    result = {
        COLUMN_NAME: keys_outside_content_values.get(COLUMN_NAME, ""),
        COLUMN_CONTENT: final_content,
        COLUMN_TYPE: keys_outside_content_values.get(COLUMN_TYPE, ""),
    }
    
    # Include metadata if present
    if COLUMN_METADATA in keys_outside_content_values:
        result[COLUMN_METADATA] = keys_outside_content_values[COLUMN_METADATA]
    
    return result


def parse_csv(input_file_path: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    
    with open(input_file_path, 'r', encoding='utf-8', newline='') as csvfile:
        reader = csv.reader(csvfile)
        
        try:
            column_names = next(reader)
        except StopIteration:
            raise ValueError("No header found in CSV file")
        
        column_names = [col.strip() for col in column_names if col.strip()]
        
        if not column_names:
            raise ValueError("No column names found in CSV header")
        
        required_keys_indices = validate_required_keys(column_names)
        keys_outside_content_indices = find_keys_outside_content_indices(column_names)
        content_column_index = find_column_index(column_names, COLUMN_CONTENT)
        
        for row_values in reader:
            try:
                processed_row = process_row(
                    row_values,
                    column_names,
                    required_keys_indices,
                    keys_outside_content_indices,
                    content_column_index
                )
                if processed_row is not None:
                    rows.append(processed_row)
            except Exception as e:
                print(f"Failed to process CSV row: {e}")
                continue
    
    return rows


def escape_csv_value(value: str) -> str:
    if not value:
        return ""
    
    if ',' in value or '"' in value or '\n' in value:
        escaped_value = value.replace('"', '""')
        return f'"{escaped_value}"'
    
    return value


def generate_csv(rows: List[Dict[str, str]], output_file_path: str) -> None:
    headers = [COLUMN_NAME, COLUMN_CONTENT, COLUMN_TYPE]
    
    with open(output_file_path, 'w', encoding='utf-8', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([
                row.get(COLUMN_NAME, ""),
                row.get(COLUMN_CONTENT, ""),
                row.get(COLUMN_TYPE, "")
            ])


def merge_csv_columns(input_file_path: str, output_file_path: str) -> None:
    rows = parse_csv(input_file_path)
    generate_csv(rows, output_file_path)


def generate_and_save_keys(keys_file_path: str = DEFAULT_KEYS_FILE) -> Dict[str, str]:
    if os.path.exists(keys_file_path):
        print(f"Keys file already exists at {keys_file_path}. Loading existing keys...")
        with open(keys_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    print(f"Generating new encryption keys and saving to {keys_file_path}...")
    
    keys: Dict[str, str] = {}
    
    print("Generating RSA key pair for task inputs...")
    rsa_private_key, rsa_public_key = cryptography.generate_rsa_key_pair(key_size=4096)
    keys[KEY_NAMES["TASKS_INPUTS_RSA_PRIVATE_KEY"]] = rsa_private_key.decode('utf-8')
    keys[KEY_NAMES["TASKS_INPUTS_RSA_PUBLIC_KEY"]] = rsa_public_key.decode('utf-8')
    
    print("Generating ECDSA key pair for task inputs...")
    ecdsa_private_key, ecdsa_public_key = cryptography.generate_ecdsa_key_pair()
    keys[KEY_NAMES["TASKS_INPUTS_ECDSA_PRIVATE_KEY"]] = ecdsa_private_key.decode('utf-8')
    keys[KEY_NAMES["TASKS_INPUTS_ECDSA_PUBLIC_KEY"]] = ecdsa_public_key.decode('utf-8')
    
    print("Generating RSA key pair for task outputs...")
    rsa_private_key, rsa_public_key = cryptography.generate_rsa_key_pair(key_size=4096)
    keys[KEY_NAMES["TASKS_OUTPUTS_RSA_PRIVATE_KEY"]] = rsa_private_key.decode('utf-8')
    keys[KEY_NAMES["TASKS_OUTPUTS_RSA_PUBLIC_KEY"]] = rsa_public_key.decode('utf-8')
    
    print("Generating ECDSA key pair for task outputs...")
    ecdsa_private_key, ecdsa_public_key = cryptography.generate_ecdsa_key_pair()
    keys[KEY_NAMES["TASKS_OUTPUTS_ECDSA_PRIVATE_KEY"]] = ecdsa_private_key.decode('utf-8')
    keys[KEY_NAMES["TASKS_OUTPUTS_ECDSA_PUBLIC_KEY"]] = ecdsa_public_key.decode('utf-8')
    
    with open(keys_file_path, 'w', encoding='utf-8') as f:
        json.dump(keys, f, indent=2)
    
    print(f"Keys successfully saved to {keys_file_path}")
    return keys


def load_keys(keys_file_path: str = DEFAULT_KEYS_FILE) -> Dict[str, str]:
    if not os.path.exists(keys_file_path):
        raise FileNotFoundError(f"Keys file not found at {keys_file_path}. Run generate_and_save_keys() first.")
    
    with open(keys_file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def set_key_from_string(key_string: str, settings_key_name: str) -> None:
    """Set a key in settings from a string value (e.g., from JSON keys file).
    
    Args:
        key_string: Key as string (PEM format)
        settings_key_name: Name of the settings attribute to set
    """
    from octobot_node.config import settings
    setattr(settings, settings_key_name, key_string.encode('utf-8') if key_string else None)


def set_keys_in_settings(keys_file_path: str = DEFAULT_KEYS_FILE) -> None:
    from octobot_node.config import settings
    
    keys = load_keys(keys_file_path)
    
    def to_bytes(key_value: str) -> bytes:
        if isinstance(key_value, bytes):
            return key_value
        return key_value.encode('utf-8') if key_value else None
    
    settings.TASKS_INPUTS_RSA_PUBLIC_KEY = to_bytes(keys.get(KEY_NAMES["TASKS_INPUTS_RSA_PUBLIC_KEY"]))
    settings.TASKS_INPUTS_RSA_PRIVATE_KEY = to_bytes(keys.get(KEY_NAMES["TASKS_INPUTS_RSA_PRIVATE_KEY"]))
    settings.TASKS_INPUTS_ECDSA_PUBLIC_KEY = to_bytes(keys.get(KEY_NAMES["TASKS_INPUTS_ECDSA_PUBLIC_KEY"]))
    settings.TASKS_INPUTS_ECDSA_PRIVATE_KEY = to_bytes(keys.get(KEY_NAMES["TASKS_INPUTS_ECDSA_PRIVATE_KEY"]))
    
    settings.TASKS_OUTPUTS_RSA_PUBLIC_KEY = to_bytes(keys.get(KEY_NAMES["TASKS_OUTPUTS_RSA_PUBLIC_KEY"]))
    settings.TASKS_OUTPUTS_RSA_PRIVATE_KEY = to_bytes(keys.get(KEY_NAMES["TASKS_OUTPUTS_RSA_PRIVATE_KEY"]))
    settings.TASKS_OUTPUTS_ECDSA_PUBLIC_KEY = to_bytes(keys.get(KEY_NAMES["TASKS_OUTPUTS_ECDSA_PUBLIC_KEY"]))
    settings.TASKS_OUTPUTS_ECDSA_PRIVATE_KEY = to_bytes(keys.get(KEY_NAMES["TASKS_OUTPUTS_ECDSA_PRIVATE_KEY"]))
    
    print("Keys successfully loaded into settings")


def encrypt_csv_content(
    csv_rows: List[Dict[str, str]],
    content_column: str = "content"
) -> List[Dict[str, str]]:
    from octobot_node.config import settings
    
    if settings.TASKS_INPUTS_RSA_PUBLIC_KEY is None or settings.TASKS_INPUTS_ECDSA_PRIVATE_KEY is None:
        raise ValueError(
            f"Encryption keys are not set in settings. "
            f"TASKS_INPUTS_RSA_PUBLIC_KEY={settings.TASKS_INPUTS_RSA_PUBLIC_KEY is not None}, "
            f"TASKS_INPUTS_ECDSA_PRIVATE_KEY={settings.TASKS_INPUTS_ECDSA_PRIVATE_KEY is not None}. "
            f"Call set_keys_in_settings() or provide keys to merge_and_encrypt_csv() first."
        )
    
    encrypted_rows: List[Dict[str, str]] = []
    
    for row in csv_rows:
        encrypted_row = row.copy()
        content = row.get(content_column, "")
        
        if content:
            try:
                encrypted_content, metadata = encrypt_task_content(content)
                encrypted_row[content_column] = encrypted_content
                encrypted_row["metadata"] = metadata
            except Exception as e:
                error_msg = f"Failed to encrypt content for row '{row.get('name', 'unknown')}': {e}"
                raise Exception(error_msg) from e
        else:
            encrypted_row["metadata"] = ""
        
        encrypted_rows.append(encrypted_row)
    
    return encrypted_rows


def decrypt_csv_content(
    csv_rows: List[Dict[str, str]],
    content_column: str = "content",
    metadata_column: str = "metadata"
) -> List[Dict[str, str]]:
    decrypted_rows: List[Dict[str, str]] = []
    
    for row in csv_rows:
        decrypted_row = row.copy()
        encrypted_content = row.get(content_column, "")
        metadata = row.get(metadata_column, "")
        
        if encrypted_content and metadata:
            try:
                decrypted_content = decrypt_task_content(encrypted_content, metadata)
                decrypted_row[content_column] = decrypted_content
            except Exception as e:
                print(f"Failed to decrypt content for row '{row.get('name', 'unknown')}': {e}")
        elif not encrypted_content:
            pass
        else:
            print(f"Warning: Row '{row.get('name', 'unknown')}' has content but no metadata. Skipping decryption.")
        
        decrypted_row.pop(metadata_column, None)
        decrypted_rows.append(decrypted_row)
    
    return decrypted_rows


def encrypt_csv_file(
    input_file_path: str,
    output_file_path: str,
    content_column: str = "content"
) -> None:
    rows = parse_csv(input_file_path)
    encrypted_rows = encrypt_csv_content(rows, content_column)
    headers = ["name", content_column, "type", "metadata"]
    
    with open(output_file_path, 'w', encoding='utf-8', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        for row in encrypted_rows:
            writer.writerow([
                row.get("name", ""),
                row.get(content_column, ""),
                row.get("type", ""),
                row.get("metadata", "")
            ])


def decrypt_csv_file(
    input_file_path: str,
    output_file_path: str,
    content_column: str = "content",
    metadata_column: str = "metadata"
) -> None:
    rows = []
    with open(input_file_path, 'r', encoding='utf-8', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rows.append(dict(row))
    decrypted_rows = decrypt_csv_content(rows, content_column, metadata_column)
    headers = ["name", content_column, "type"]
    
    with open(output_file_path, 'w', encoding='utf-8', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        
        for row in decrypted_rows:
            writer.writerow([
                row.get("name", ""),
                row.get(content_column, ""),
                row.get("type", "")
            ])


def merge_and_encrypt_csv(
    input_file_path: str,
    output_file_path: str,
    content_column: str = "content",
    keys: Optional[Dict[str, str]] = None,
    keys_file_path: Optional[str] = None
) -> None:
    if keys_file_path:
        set_keys_in_settings(keys_file_path)
    elif keys:
        from octobot_node.config import settings
        
        def to_bytes(key_value: str) -> bytes:
            if isinstance(key_value, bytes):
                return key_value
            return key_value.encode('utf-8') if key_value else None
        
        settings.TASKS_INPUTS_RSA_PUBLIC_KEY = to_bytes(keys.get(KEY_NAMES["TASKS_INPUTS_RSA_PUBLIC_KEY"]))
        settings.TASKS_INPUTS_RSA_PRIVATE_KEY = to_bytes(keys.get(KEY_NAMES["TASKS_INPUTS_RSA_PRIVATE_KEY"]))
        settings.TASKS_INPUTS_ECDSA_PUBLIC_KEY = to_bytes(keys.get(KEY_NAMES["TASKS_INPUTS_ECDSA_PUBLIC_KEY"]))
        settings.TASKS_INPUTS_ECDSA_PRIVATE_KEY = to_bytes(keys.get(KEY_NAMES["TASKS_INPUTS_ECDSA_PRIVATE_KEY"]))
        settings.TASKS_OUTPUTS_RSA_PUBLIC_KEY = to_bytes(keys.get(KEY_NAMES["TASKS_OUTPUTS_RSA_PUBLIC_KEY"]))
        settings.TASKS_OUTPUTS_RSA_PRIVATE_KEY = to_bytes(keys.get(KEY_NAMES["TASKS_OUTPUTS_RSA_PRIVATE_KEY"]))
        settings.TASKS_OUTPUTS_ECDSA_PUBLIC_KEY = to_bytes(keys.get(KEY_NAMES["TASKS_OUTPUTS_ECDSA_PUBLIC_KEY"]))
        settings.TASKS_OUTPUTS_ECDSA_PRIVATE_KEY = to_bytes(keys.get(KEY_NAMES["TASKS_OUTPUTS_ECDSA_PRIVATE_KEY"]))
    
    rows = parse_csv(input_file_path)
    encrypted_rows = encrypt_csv_content(rows, content_column)
    headers = ["name", content_column, "type", "metadata"]
    
    with open(output_file_path, 'w', encoding='utf-8', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        for row in encrypted_rows:
            writer.writerow([
                row.get("name", ""),
                row.get(content_column, ""),
                row.get("type", ""),
                row.get("metadata", "")
            ])


def encrypt_result_csv_content(
    csv_rows: List[Dict[str, str]],
    result_column: str = "result"
) -> List[Dict[str, str]]:
    from octobot_node.config import settings
    
    if settings.TASKS_OUTPUTS_RSA_PUBLIC_KEY is None or settings.TASKS_OUTPUTS_ECDSA_PRIVATE_KEY is None:
        raise ValueError(
            f"Encryption keys are not set in settings. "
            f"TASKS_OUTPUTS_RSA_PUBLIC_KEY={settings.TASKS_OUTPUTS_RSA_PUBLIC_KEY is not None}, "
            f"TASKS_OUTPUTS_ECDSA_PRIVATE_KEY={settings.TASKS_OUTPUTS_ECDSA_PRIVATE_KEY is not None}. "
            f"Call set_keys_in_settings() first."
        )
    
    encrypted_rows: List[Dict[str, str]] = []
    
    for row in csv_rows:
        encrypted_row = row.copy()
        result = row.get(result_column, "")
        
        if result:
            try:
                encrypted_result, metadata = encrypt_task_result(result)
                encrypted_row[result_column] = encrypted_result
                encrypted_row["result_metadata"] = metadata
            except Exception as e:
                error_msg = f"Failed to encrypt result for row '{row.get('name', 'unknown')}': {e}"
                raise Exception(error_msg) from e
        else:
            encrypted_row["result_metadata"] = ""
        
        encrypted_rows.append(encrypted_row)
    
    return encrypted_rows


def decrypt_result_csv_content(
    csv_rows: List[Dict[str, str]],
    result_column: str = "result",
    metadata_column: str = "result_metadata"
) -> List[Dict[str, str]]:
    decrypted_rows: List[Dict[str, str]] = []
    
    for row in csv_rows:
        decrypted_row = row.copy()
        encrypted_result = row.get(result_column, "")
        metadata = row.get(metadata_column, "")
        
        if encrypted_result and metadata:
            try:
                decrypted_result = decrypt_task_result(encrypted_result, metadata)
                result_dict = decrypted_result if isinstance(decrypted_result, dict) else None
                if result_dict is None:
                    try:
                        parsed = json.loads(decrypted_result)
                        result_dict = parsed if isinstance(parsed, dict) else None
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        pass
                
                if result_dict:
                    # Split dict into separate columns
                    for key, value in result_dict.items():
                        decrypted_row[key] = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
                    decrypted_row.pop(result_column, None)
                else:
                    decrypted_row[result_column] = decrypted_result
            except Exception as e:
                print(f"Failed to decrypt result for row '{row.get('name', 'unknown')}': {e}")
        elif not encrypted_result:
            # Remove result column if it exists but is empty
            decrypted_row.pop(result_column, None)
        else:
            print(f"Warning: Row '{row.get('name', 'unknown')}' has result but no metadata. Skipping decryption.")
        
        decrypted_row.pop(metadata_column, None)
        decrypted_rows.append(decrypted_row)
    
    return decrypted_rows


def encrypt_result_csv_file(
    input_file_path: str,
    output_file_path: str,
    result_column: str = "result"
) -> None:
    rows = []
    with open(input_file_path, 'r', encoding='utf-8', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rows.append(dict(row))
    
    encrypted_rows = encrypt_result_csv_content(rows, result_column)
    headers = list(rows[0].keys()) if rows else ["name", result_column]
    if "result_metadata" not in headers:
        headers.append("result_metadata")
    
    with open(output_file_path, 'w', encoding='utf-8', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for row in encrypted_rows:
            writer.writerow(row)


def decrypt_result_csv_file(
    input_file_path: str,
    output_file_path: str,
    result_column: str = "result",
    metadata_column: str = "result_metadata"
) -> None:
    rows = []
    with open(input_file_path, 'r', encoding='utf-8', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rows.append(dict(row))
    
    decrypted_rows = decrypt_result_csv_content(rows, result_column, metadata_column)
    
    all_headers = set()
    for row in decrypted_rows:
        all_headers.update(row.keys())
    
    original_headers = [col for col in (list(rows[0].keys()) if rows else ["name", result_column]) if col != metadata_column]
    headers = []
    seen = set()
    
    for col in original_headers:
        if col != result_column and col in all_headers:
            headers.append(col)
            seen.add(col)
    
    if result_column in all_headers and result_column not in seen:
        headers.append(result_column)
        seen.add(result_column)
    
    for col in sorted(all_headers - seen):
        headers.append(col)
    
    with open(output_file_path, 'w', encoding='utf-8', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for row in decrypted_rows:
            writer.writerow({k: v for k, v in row.items() if k in headers})
