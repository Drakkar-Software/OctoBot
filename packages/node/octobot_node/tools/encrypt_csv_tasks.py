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
CLI script to encrypt CSV task files using RSA public key and ECDSA private key.

This script takes a CSV file as input, encrypts the content column using the provided
RSA public key and ECDSA private key, and outputs an encrypted CSV file.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from octobot_node.tools.csv_utils import (
    load_keys,
    KEY_NAMES,
    set_key_from_file_or_env,
    set_key_from_string,
    encrypt_csv_file as csv_utils_encrypt_csv_file,
)


def generate_output_filename(input_file_path: str) -> str:
    """Generate output filename based on input filename with _encrypted suffix.
    
    Args:
        input_file_path: Path to the input CSV file
        
    Returns:
        Output file path with _encrypted suffix
    """
    input_path = Path(input_file_path)
    output_path = input_path.parent / f"{input_path.stem}_encrypted{input_path.suffix}"
    return str(output_path)


def set_keys_in_settings(
    rsa_public_key_path: Optional[str] = None,
    ecdsa_private_key_path: Optional[str] = None
) -> None:
    """Load keys from files or environment variables and set them in settings.
    
    Priority order:
    1. File path (if provided)
    2. Environment variable (loaded automatically by settings system if file path not provided)
    
    Args:
        rsa_public_key_path: Optional path to the RSA public key file
        ecdsa_private_key_path: Optional path to the ECDSA private key file
        
    Raises:
        FileNotFoundError: If a key file path is provided but doesn't exist
        IOError: If a key file cannot be read
        ValueError: If neither file path nor environment variable is available for required keys
    """
    set_key_from_file_or_env(
        rsa_public_key_path,
        "TASKS_INPUTS_RSA_PUBLIC_KEY",
        "TASKS_INPUTS_RSA_PUBLIC_KEY",
        "RSA public key"
    )
    set_key_from_file_or_env(
        ecdsa_private_key_path,
        "TASKS_INPUTS_ECDSA_PRIVATE_KEY",
        "TASKS_INPUTS_ECDSA_PRIVATE_KEY",
        "ECDSA private key"
    )


def encrypt_csv_file(
    input_file_path: str,
    output_file_path: str,
    rsa_public_key_path: Optional[str] = None,
    ecdsa_private_key_path: Optional[str] = None,
    content_column: str = "content"
) -> None:
    """Encrypt a CSV file and write the encrypted version to output file.
    
    Args:
        input_file_path: Path to the input CSV file
        output_file_path: Path to the output encrypted CSV file
        rsa_public_key_path: Optional path to the RSA public key file
        ecdsa_private_key_path: Optional path to the ECDSA private key file
        content_column: Name of the column containing content to encrypt
        
    Raises:
        FileNotFoundError: If input file or key files don't exist
        ValueError: If CSV parsing fails or encryption keys are not set
        Exception: If encryption or file writing fails
    """
    if not Path(input_file_path).exists():
        raise FileNotFoundError(f"Input CSV file not found: {input_file_path}")
    
    set_keys_in_settings(rsa_public_key_path, ecdsa_private_key_path)
    
    print(f"Encrypting CSV file: {input_file_path}")
    csv_utils_encrypt_csv_file(input_file_path, output_file_path, content_column)
    print(f"Successfully encrypted CSV and saved to: {output_file_path}")


def set_keys_in_settings_from_strings(rsa_public_key: str, ecdsa_private_key: str) -> None:
    """Set encryption keys in settings from string values (e.g., from JSON keys file).
    
    Args:
        rsa_public_key: RSA public key as string (PEM format)
        ecdsa_private_key: ECDSA private key as string (PEM format)
    """
    set_key_from_string(rsa_public_key, "TASKS_INPUTS_RSA_PUBLIC_KEY")
    set_key_from_string(ecdsa_private_key, "TASKS_INPUTS_ECDSA_PRIVATE_KEY")


def encrypt_csv_file_from_keys_file(
    input_file_path: str,
    output_file_path: str,
    keys_file_path: str,
    content_column: str = "content"
) -> None:
    """Encrypt a CSV file using keys from a JSON keys file.
    
    This is a convenience function that extracts RSA public key and ECDSA private key
    from a JSON keys file and encrypts the CSV.
    
    Args:
        input_file_path: Path to the input CSV file
        output_file_path: Path to the output encrypted CSV file
        keys_file_path: Path to the JSON keys file
        content_column: Name of the column containing content to encrypt
        
    Raises:
        FileNotFoundError: If input file or keys file doesn't exist
        ValueError: If CSV parsing fails or encryption keys are not set
        Exception: If encryption or file writing fails
    """
    keys = load_keys(keys_file_path)
    
    rsa_public_key_str = keys.get(KEY_NAMES["TASKS_INPUTS_RSA_PUBLIC_KEY"])
    ecdsa_private_key_str = keys.get(KEY_NAMES["TASKS_INPUTS_ECDSA_PRIVATE_KEY"])
    
    if not rsa_public_key_str or not ecdsa_private_key_str:
        raise ValueError(
            f"Required keys not found in keys file. "
            f"RSA public key: {rsa_public_key_str is not None}, "
            f"ECDSA private key: {ecdsa_private_key_str is not None}"
        )
    
    set_keys_in_settings_from_strings(rsa_public_key_str, ecdsa_private_key_str)
    print(f"Encrypting CSV file: {input_file_path}")
    csv_utils_encrypt_csv_file(input_file_path, output_file_path, content_column)
    print(f"Successfully encrypted CSV and saved to: {output_file_path}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Encrypt CSV task files using RSA public key and ECDSA private key",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s tasks.csv --rsa-public-key rsa_public.pem --ecdsa-private-key ecdsa_private.pem
  %(prog)s tasks.csv --rsa-public-key rsa_public.pem --ecdsa-private-key ecdsa_private.pem --output encrypted_tasks.csv
  %(prog)s tasks.csv  # Uses TASKS_INPUTS_RSA_PUBLIC_KEY and TASKS_INPUTS_ECDSA_PRIVATE_KEY environment variables
        """
    )
    
    parser.add_argument(
        "csv_file",
        type=str,
        help="Path to the input CSV file to encrypt"
    )
    
    parser.add_argument(
        "--rsa-public-key",
        type=str,
        required=False,
        default=None,
        help="Path to the RSA public key file (PEM format). If not provided, will use TASKS_INPUTS_RSA_PUBLIC_KEY environment variable."
    )
    
    parser.add_argument(
        "--ecdsa-private-key",
        type=str,
        required=False,
        default=None,
        help="Path to the ECDSA private key file (PEM format). If not provided, will use TASKS_INPUTS_ECDSA_PRIVATE_KEY environment variable."
    )
    
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Path to the output encrypted CSV file (default: input_filename_encrypted.csv)"
    )
    
    parser.add_argument(
        "--content-column",
        type=str,
        default="content",
        help="Name of the column containing content to encrypt (default: 'content')"
    )
    
    args = parser.parse_args()
    
    # Determine output file path
    if args.output:
        output_file_path = args.output
    else:
        output_file_path = generate_output_filename(args.csv_file)
    
    try:
        encrypt_csv_file(
            input_file_path=args.csv_file,
            output_file_path=output_file_path,
            rsa_public_key_path=args.rsa_public_key,
            ecdsa_private_key_path=args.ecdsa_private_key,
            content_column=args.content_column
        )
        print("\nEncryption completed successfully!")
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
