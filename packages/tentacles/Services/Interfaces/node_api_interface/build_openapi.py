#!/usr/bin/env python
"""
Build script to generate OpenAPI specification for NodeApiInterface.
This script can be run independently without requiring tentacles to be installed.
"""
import json
import sys
from pathlib import Path

# Add current directory to path to enable imports
sys.path.insert(0, str(Path(__file__).parent))

# Import node_api_interface module
import node_api_interface

# Generate OpenAPI spec
app = node_api_interface.NodeApiInterface.create_app()
openapi_spec = app.openapi()

# Output to stdout
print(json.dumps(openapi_spec, indent=2))
