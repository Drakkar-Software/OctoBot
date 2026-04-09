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
import os
import sys
from pathlib import Path
from typing import Optional

from octobot_node.tools.csv_utils import (
    decrypt_result_csv_file,
    load_keys,
    KEY_NAMES,
    load_key_file,
)


def _load_key_bytes(file_path: Optional[str], env_var: str, display_name: str) -> bytes:
    if file_path:
        return load_key_file(file_path)
    value = os.environ.get(env_var)
    if value:
        return value.encode("utf-8")
    raise ValueError(
        f"{display_name} not found. Provide --{display_name.lower().replace(' ', '-')} or set {env_var}."
    )


def generate_output_filename(input_file_path: str) -> str:
    input_path = Path(input_file_path)
    output_path = input_path.parent / f"{input_path.stem}_decrypted{input_path.suffix}"
    return str(output_path)


def decrypt_csv_file_tool(
    input_file_path: str,
    output_file_path: str,
    rsa_private_key_path: Optional[str] = None,
    ecdsa_public_key_path: Optional[str] = None,
    result_column: str = "result",
    metadata_column: str = "result_metadata",
) -> None:
    if not Path(input_file_path).exists():
        raise FileNotFoundError(f"Input CSV file not found: {input_file_path}")

    rsa_private_key = _load_key_bytes(rsa_private_key_path, "TASKS_OUTPUTS_RSA_PRIVATE_KEY", "RSA private key")
    ecdsa_public_key = _load_key_bytes(ecdsa_public_key_path, "TASKS_OUTPUTS_ECDSA_PUBLIC_KEY", "ECDSA public key")

    print(f"Decrypting CSV results file: {input_file_path}")
    decrypt_result_csv_file(
        input_file_path=input_file_path,
        output_file_path=output_file_path,
        rsa_private_key=rsa_private_key,
        ecdsa_public_key=ecdsa_public_key,
        result_column=result_column,
        metadata_column=metadata_column,
    )
    print(f"Successfully decrypted CSV and saved to: {output_file_path}")


def decrypt_csv_file_from_keys_file(
    input_file_path: str,
    output_file_path: str,
    keys_file_path: str,
    result_column: str = "result",
    metadata_column: str = "result_metadata",
) -> None:
    keys = load_keys(keys_file_path)

    rsa_private_key_str = keys.get(KEY_NAMES["TASKS_OUTPUTS_RSA_PRIVATE_KEY"])
    ecdsa_public_key_str = keys.get(KEY_NAMES["TASKS_OUTPUTS_ECDSA_PUBLIC_KEY"])

    if not rsa_private_key_str or not ecdsa_public_key_str:
        raise ValueError(
            f"Required keys not found in keys file. "
            f"RSA private key: {rsa_private_key_str is not None}, "
            f"ECDSA public key: {ecdsa_public_key_str is not None}"
        )

    rsa_private_key = rsa_private_key_str.encode("utf-8")
    ecdsa_public_key = ecdsa_public_key_str.encode("utf-8")

    print(f"Decrypting CSV results file: {input_file_path}")
    decrypt_result_csv_file(
        input_file_path=input_file_path,
        output_file_path=output_file_path,
        rsa_private_key=rsa_private_key,
        ecdsa_public_key=ecdsa_public_key,
        result_column=result_column,
        metadata_column=metadata_column,
    )
    print(f"Successfully decrypted CSV and saved to: {output_file_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Decrypt CSV results files using RSA private key and ECDSA public key",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s encrypted_results.csv --rsa-private-key rsa_private.pem --ecdsa-public-key ecdsa_public.pem
  %(prog)s encrypted_results.csv --output decrypted_results.csv
  %(prog)s encrypted_results.csv  # Uses TASKS_OUTPUTS_RSA_PRIVATE_KEY and TASKS_OUTPUTS_ECDSA_PUBLIC_KEY env vars
        """
    )

    parser.add_argument("csv_file", type=str, help="Path to the input encrypted CSV results file to decrypt")
    parser.add_argument(
        "--rsa-private-key", type=str, default=None,
        help="Path to the RSA private key file (PEM format). If not provided, uses TASKS_OUTPUTS_RSA_PRIVATE_KEY env var."
    )
    parser.add_argument(
        "--ecdsa-public-key", type=str, default=None,
        help="Path to the ECDSA public key file (PEM format). If not provided, uses TASKS_OUTPUTS_ECDSA_PUBLIC_KEY env var."
    )
    parser.add_argument("--output", "-o", type=str, default=None, help="Path to the output decrypted CSV file")
    parser.add_argument("--result-column", type=str, default="result", help="Column containing encrypted result (default: result)")
    parser.add_argument("--metadata-column", type=str, default="result_metadata", help="Column containing metadata (default: result_metadata)")

    args = parser.parse_args()
    output_file_path = args.output or generate_output_filename(args.csv_file)

    try:
        decrypt_csv_file_tool(
            input_file_path=args.csv_file,
            output_file_path=output_file_path,
            rsa_private_key_path=args.rsa_private_key,
            ecdsa_public_key_path=args.ecdsa_public_key,
            result_column=args.result_column,
            metadata_column=args.metadata_column,
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
