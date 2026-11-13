#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import octobot_commons.constants as commons_constants

MANIFEST_FILE_NAME = "mobile-update.json"
MANIFEST_SCHEMA = 2
MIN_SEQUENCE = 1
MAX_SEQUENCE = 2**53 - 1
PUBLIC_KEY_SEPARATOR = ","
MAX_FILES = 2000
MAX_TOTAL_BYTES = 200 * 1024 * 1024

MANIFEST_FETCH_TIMEOUT_SECONDS = 15
FILE_DOWNLOAD_TIMEOUT_SECONDS = 120
CONNECT_TIMEOUT_SECONDS = 10

ENV_UPDATE_BASE_URL = "OCTOBOT_MOBILE_UI_BASE_URL"
ENV_MANIFEST_PUBLIC_KEY = "OCTOBOT_MOBILE_UI_PUBLIC_KEY"

# Filled in by the publish step when the mobile UI bucket is live.
# DEFAULT_MANIFEST_PUBLIC_KEY may hold a comma-separated list of base64 Ed25519 public keys.
DEFAULT_UPDATE_BASE_URL = ""
DEFAULT_MANIFEST_PUBLIC_KEY = ""

VERSION_DIR_NAME = "versions"
CURRENT_FILE_NAME = "current.json"
INSTALLED_MANIFEST_FILE_NAME = "manifest.json"
TMP_DIR_PREFIX = "tmp-"

DEFAULT_ROOT_DIR_RELATIVE = f"{commons_constants.USER_FOLDER}/mobile_ui"

VERSION_PATTERN = r"^[0-9a-f]{8,64}$"

CONTENT_TYPE_BY_EXTENSION = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".wasm": "application/wasm",
}

CACHE_IMMUTABLE_PREFIXES = ("_expo/static/", "assets/")
CACHE_CONTROL_IMMUTABLE = "public, max-age=31536000, immutable"
CACHE_CONTROL_NO_CACHE = "no-cache"

NOT_INSTALLED_HTML = (
    "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
    "<title>Mobile UI</title></head><body>"
    "<p>The mobile UI is not installed yet. Install it from the node interface.</p>"
    "</body></html>"
)
