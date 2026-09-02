#  Drakkar-Software OctoBot-Protocol
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.
#
# CLI: regenerate test/compat/static/openapi_schema_manifest.json from openapi.json.
#
# Run after editing openapi.json (non-breaking: same PR; breaking: after migration work):
#   python -m scripts.build_openapi_schema_manifest
#
# test/compat/test_openapi_compat.py compares the live manifest to this committed baseline.

import argparse
import pathlib
import sys

import scripts.lib.openapi_compat_lib as openapi_compat_lib


def main() -> int:
    parser = argparse.ArgumentParser(description="Build OpenAPI schema compatibility manifest.")
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=None,
        help="Output path (default: test/compat/static/openapi_schema_manifest.json)",
    )
    args = parser.parse_args()
    openapi_document = openapi_compat_lib.load_openapi_document()
    manifest = openapi_compat_lib.build_schema_manifest(openapi_document)
    output_path = args.output or openapi_compat_lib.manifest_baseline_path()
    openapi_compat_lib.write_json(output_path, manifest)
    print(f"Wrote schema manifest with {len(manifest)} schemas to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
