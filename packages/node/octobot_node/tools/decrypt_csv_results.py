#!/usr/bin/env python3
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

"""
CLI script to decrypt CSV results files using RSA private key and ECDSA public key.

This script takes an encrypted CSV results file as input, decrypts the result column using the provided
RSA private key and ECDSA public key, and outputs a decrypted CSV file.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from octobot_node.config import settings
from octobot_node.tools.csv_utils import (
    decrypt_result_csv_file,
    load_keys,
    KEY_NAMES,
    set_key_from_file_or_env,
    set_key_from_string,
)


def set_keys_in_settings(
    rsa_private_key_path: Optional[str] = None,
    ecdsa_public_key_path: Optional[str] = None
) -> None:
    """Load keys from files or environment variables and set them in settings.
    
    Priority order:
    1. File path (if provided)
    2. Environment variable (loaded automatically by settings system if file path not provided)
    
    Args:
        rsa_private_key_path: Optional path to the RSA private key file
        ecdsa_public_key_path: Optional path to the ECDSA public key file
        
    Raises:
        FileNotFoundError: If a key file path is provided but doesn't exist
        IOError: If a key file cannot be read
        ValueError: If neither file path nor environment variable is available for required keys
    """
    set_key_from_file_or_env(
        rsa_private_key_path,
        "TASKS_OUTPUTS_RSA_PRIVATE_KEY",
        "TASKS_OUTPUTS_RSA_PRIVATE_KEY",
        "RSA private key"
    )
    set_key_from_file_or_env(
        ecdsa_public_key_path,
        "TASKS_OUTPUTS_ECDSA_PUBLIC_KEY",
        "TASKS_OUTPUTS_ECDSA_PUBLIC_KEY",
        "ECDSA public key"
    )


def generate_output_filename(input_file_path: str) -> str:
    """Generate output filename based on input filename with _decrypted suffix.
    
    Args:
        input_file_path: Path to the input CSV file
        
    Returns:
        Output file path with _decrypted suffix
    """
    input_path = Path(input_file_path)
    output_path = input_path.parent / f"{input_path.stem}_decrypted{input_path.suffix}"
    return str(output_path)


def decrypt_csv_file_tool(
    input_file_path: str,
    output_file_path: str,
    rsa_private_key_path: Optional[str] = None,
    ecdsa_public_key_path: Optional[str] = None,
    result_column: str = "result",
    metadata_column: str = "result_metadata"
) -> None:
    """Decrypt a CSV results file and write the decrypted version to output file.
    
    Args:
        input_file_path: Path to the input encrypted CSV results file
        output_file_path: Path to the output decrypted CSV file
        rsa_private_key_path: Optional path to the RSA private key file
        ecdsa_public_key_path: Optional path to the ECDSA public key file
        result_column: Name of the column containing encrypted result (default: 'result')
        metadata_column: Name of the column containing metadata (default: 'result_metadata')
        
    Raises:
        FileNotFoundError: If input file or key files don't exist
        ValueError: If CSV parsing fails or decryption keys are not set
        Exception: If decryption or file writing fails
    """
    if not Path(input_file_path).exists():
        raise FileNotFoundError(f"Input CSV file not found: {input_file_path}")
    
    set_keys_in_settings(rsa_private_key_path, ecdsa_public_key_path)
    
    if settings.TASKS_OUTPUTS_RSA_PRIVATE_KEY is None or settings.TASKS_OUTPUTS_ECDSA_PUBLIC_KEY is None:
        raise ValueError(
            f"Decryption keys are not set in settings. "
            f"TASKS_OUTPUTS_RSA_PRIVATE_KEY={settings.TASKS_OUTPUTS_RSA_PRIVATE_KEY is not None}, "
            f"TASKS_OUTPUTS_ECDSA_PUBLIC_KEY={settings.TASKS_OUTPUTS_ECDSA_PUBLIC_KEY is not None}."
        )
    
    print(f"Decrypting CSV results file: {input_file_path}")
    decrypt_result_csv_file(
        input_file_path=input_file_path,
        output_file_path=output_file_path,
        result_column=result_column,
        metadata_column=metadata_column
    )
    print(f"Successfully decrypted CSV and saved to: {output_file_path}")


def set_keys_in_settings_from_strings(rsa_private_key: str, ecdsa_public_key: str) -> None:
    """Set decryption keys in settings from string values (e.g., from JSON keys file).
    
    Args:
        rsa_private_key: RSA private key as string (PEM format)
        ecdsa_public_key: ECDSA public key as string (PEM format)
    """
    set_key_from_string(rsa_private_key, "TASKS_OUTPUTS_RSA_PRIVATE_KEY")
    set_key_from_string(ecdsa_public_key, "TASKS_OUTPUTS_ECDSA_PUBLIC_KEY")


def decrypt_csv_file_from_keys_file(
    input_file_path: str,
    output_file_path: str,
    keys_file_path: str,
    result_column: str = "result",
    metadata_column: str = "result_metadata"
) -> None:
    """Decrypt a CSV results file using keys from a JSON keys file.
    
    This is a convenience function that extracts RSA private key and ECDSA public key
    from a JSON keys file and decrypts the CSV results file.
    
    Args:
        input_file_path: Path to the input encrypted CSV results file
        output_file_path: Path to the output decrypted CSV file
        keys_file_path: Path to the JSON keys file
        result_column: Name of the column containing encrypted result (default: 'result')
        metadata_column: Name of the column containing metadata (default: 'result_metadata')
        
    Raises:
        FileNotFoundError: If input file or keys file doesn't exist
        ValueError: If CSV parsing fails or decryption keys are not set
        Exception: If decryption or file writing fails
    """
    keys = load_keys(keys_file_path)
    
    rsa_private_key_str = keys.get(KEY_NAMES["TASKS_OUTPUTS_RSA_PRIVATE_KEY"])
    ecdsa_public_key_str = keys.get(KEY_NAMES["TASKS_OUTPUTS_ECDSA_PUBLIC_KEY"])
    
    if not rsa_private_key_str or not ecdsa_public_key_str:
        raise ValueError(
            f"Required keys not found in keys file. "
            f"RSA private key: {rsa_private_key_str is not None}, "
            f"ECDSA public key: {ecdsa_public_key_str is not None}"
        )
    
    set_keys_in_settings_from_strings(rsa_private_key_str, ecdsa_public_key_str)
    
    if settings.TASKS_OUTPUTS_RSA_PRIVATE_KEY is None or settings.TASKS_OUTPUTS_ECDSA_PUBLIC_KEY is None:
        raise ValueError(
            f"Decryption keys are not set in settings. "
            f"TASKS_OUTPUTS_RSA_PRIVATE_KEY={settings.TASKS_OUTPUTS_RSA_PRIVATE_KEY is not None}, "
            f"TASKS_OUTPUTS_ECDSA_PUBLIC_KEY={settings.TASKS_OUTPUTS_ECDSA_PUBLIC_KEY is not None}."
        )
    
    print(f"Decrypting CSV results file: {input_file_path}")
    decrypt_result_csv_file(
        input_file_path=input_file_path,
        output_file_path=output_file_path,
        result_column=result_column,
        metadata_column=metadata_column
    )
    print(f"Successfully decrypted CSV and saved to: {output_file_path}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Decrypt CSV results files using RSA private key and ECDSA public key",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s encrypted_results.csv --rsa-private-key rsa_private.pem --ecdsa-public-key ecdsa_public.pem
  %(prog)s encrypted_results.csv --rsa-private-key rsa_private.pem --ecdsa-public-key ecdsa_public.pem --output decrypted_results.csv
  %(prog)s encrypted_results.csv  # Uses TASKS_OUTPUTS_RSA_PRIVATE_KEY and TASKS_OUTPUTS_ECDSA_PUBLIC_KEY environment variables
        """
    )
    
    parser.add_argument(
        "csv_file",
        type=str,
        help="Path to the input encrypted CSV results file to decrypt"
    )
    
    parser.add_argument(
        "--rsa-private-key",
        type=str,
        required=False,
        default=None,
        help="Path to the RSA private key file (PEM format). If not provided, will use TASKS_OUTPUTS_RSA_PRIVATE_KEY environment variable."
    )
    
    parser.add_argument(
        "--ecdsa-public-key",
        type=str,
        required=False,
        default=None,
        help="Path to the ECDSA public key file (PEM format). If not provided, will use TASKS_OUTPUTS_ECDSA_PUBLIC_KEY environment variable."
    )
    
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Path to the output decrypted CSV file (default: input_filename_decrypted.csv)"
    )
    
    parser.add_argument(
        "--result-column",
        type=str,
        default="result",
        help="Name of the column containing encrypted result (default: 'result')"
    )
    
    parser.add_argument(
        "--metadata-column",
        type=str,
        default="result_metadata",
        help="Name of the column containing metadata (default: 'result_metadata')"
    )
    
    args = parser.parse_args()
    
    if args.output:
        output_file_path = args.output
    else:
        output_file_path = generate_output_filename(args.csv_file)
    
    try:
        decrypt_csv_file_tool(
            input_file_path=args.csv_file,
            output_file_path=output_file_path,
            rsa_private_key_path=args.rsa_private_key,
            ecdsa_public_key_path=args.ecdsa_public_key,
            result_column=args.result_column,
            metadata_column=args.metadata_column
        )
        print("\nDecryption completed successfully!")
        sys.exit(0)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
