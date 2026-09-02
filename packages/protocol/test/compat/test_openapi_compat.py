#  Drakkar-Software OctoBot-Protocol
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.

import scripts.lib.openapi_compat_lib as openapi_compat_lib


class TestOpenApiManifestMatchesBaseline:
    def test_current_manifest_matches_committed_baseline(self):
        openapi_document = openapi_compat_lib.load_openapi_document()
        current_manifest = openapi_compat_lib.build_schema_manifest(openapi_document)
        baseline_manifest = openapi_compat_lib.read_json(openapi_compat_lib.manifest_baseline_path())
        openapi_compat_lib.compare_manifest_to_baseline(current_manifest, baseline_manifest)
