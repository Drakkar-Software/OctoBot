#! /usr/bin/env bash

set -e
set -x

python -c "import octobot_node.app.main; import json; print(json.dumps(octobot_node.app.main.app.openapi()))" > openapi.json
npm run generate-client