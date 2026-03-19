#!/usr/bin/env python3
"""Pre-commit hook: ensure vault.yml and hosts.yml are encrypted before committing.

Install:
    cp infra/sync/ansible/scripts/pre-commit-vault-check.py .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit   # Unix only, not needed on Windows

Works on Linux, macOS, and Windows.
"""

import fnmatch
import subprocess
import sys

SENSITIVE_PATTERNS = [
    "infra/sync/ansible/inventories/*/group_vars/all/vault.yml",
    "infra/sync/ansible/inventories/*/hosts.yml",
]

VAULT_HEADER = "$ANSIBLE_VAULT"


def get_staged_files():
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip().splitlines()


def matches_any_pattern(filepath):
    # Normalize to forward slashes for cross-platform matching
    normalized = filepath.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, p) for p in SENSITIVE_PATTERNS)


def is_encrypted(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        return first_line.startswith(VAULT_HEADER)
    except (OSError, UnicodeDecodeError):
        # Binary or unreadable — likely already encrypted
        return True


def main():
    staged = get_staged_files()
    failed = []

    for filepath in staged:
        if matches_any_pattern(filepath) and not is_encrypted(filepath):
            failed.append(filepath)

    if failed:
        print("ERROR: The following files are NOT encrypted:")
        for f in failed:
            print(f"  {f}")
        print()
        print("Encrypt them before committing:")
        for f in failed:
            print(f"  ansible-vault encrypt {f}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
