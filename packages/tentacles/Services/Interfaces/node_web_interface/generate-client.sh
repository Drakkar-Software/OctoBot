#! /usr/bin/env bash

set -e
set -x

python -c "import json; from tentacles.Services.Interfaces.node_api.node_api_interface import NodeApiInterface; print(json.dumps(NodeApiInterface.create_app().openapi()))" > openapi.json
npm run generate-client
