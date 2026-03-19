"""Generate an nginx config from an OctoBot sync collections.json.

Produces an nginx server block where:
- Public + pull_only collections  → cached with long TTL (1h)
- Public + writable collections   → cached with short TTL (30s)
- Everything else                 → proxy_pass straight to OctoBot sync, no cache
- Rate limiting from global rateLimit config + per-collection rateLimit flag

CLI usage:
    python -m octobot_sync.nginx_conf collections.json > nginx.conf
    python -m octobot_sync.nginx_conf collections.json --upstream octobot-sync:3000 --listen 80
"""

import argparse
import json
import math
import re
import sys
import textwrap


def storage_path_to_regex(storage_path: str) -> str:
    """Convert a storagePath to an nginx location regex.

    "items/{itemId}/feed/{version}" → "items/[^/]+/feed/[^/]+"
    "public/catalog"               → "public/catalog"
    """
    return re.sub(r"\{[^}]+\}", "[^/]+", storage_path)


def rate_to_nginx(max_requests: int, window_ms: int) -> tuple[str, int]:
    """Convert maxRequests/windowMs to nginx rate string and burst.

    Returns (rate_str, burst) e.g. ("2r/s", 20).
    """
    window_s = window_ms / 1000
    rps = max_requests / window_s
    if rps >= 1:
        rate_str = f"{math.ceil(rps)}r/s"
    else:
        rpm = max_requests / (window_s / 60)
        rate_str = f"{math.ceil(rpm)}r/m"
    burst = max(1, max_requests // 2)
    return rate_str, burst


def generate(collections_path: str, upstream: str, listen: int) -> str:
    with open(collections_path) as f:
        config = json.load(f)

    collections = config.get("collections", [])
    global_rate_limit = config.get("rateLimit")

    # Rate limit zones
    rate_limit_block = ""
    global_rate_str = ""
    global_burst = 0
    strict_rate_str = ""
    strict_burst = 0
    if global_rate_limit:
        window_ms = global_rate_limit["windowMs"]
        max_requests = global_rate_limit["maxRequests"]
        global_rate_str, global_burst = rate_to_nginx(max_requests, window_ms)
        strict_rate_str, strict_burst = rate_to_nginx(
            max(1, max_requests // 2), window_ms
        )
        rate_limit_block = textwrap.dedent(f"""\
            limit_req_zone $binary_remote_addr zone=sync_global:10m rate={global_rate_str};
            limit_req_zone $binary_remote_addr zone=sync_strict:10m rate={strict_rate_str};
            limit_req_status 429;
        """)

    # Cached pull locations for public collections
    cached_locations = []
    for col in collections:
        read_roles = col.get("readRoles", [])
        if "public" not in read_roles:
            continue

        path_re = storage_path_to_regex(col["storagePath"])
        pull_only = col.get("pullOnly", False)
        name = col["name"]

        ttl = "1h" if pull_only else "30s"

        rate_line = ""
        if global_rate_limit:
            rate_line = f"\n        limit_req zone=sync_global burst={global_burst} nodelay;"

        cached_locations.append(
            textwrap.dedent(f"""\
    # {name} (public, {"pull_only" if pull_only else "writable"})
    location ~* ^/v1/pull/{path_re}$ {{
        proxy_pass http://octobot_sync;
        proxy_cache sync_cache;
        proxy_cache_valid 200 {ttl};
        proxy_cache_use_stale error timeout updating;
        proxy_cache_lock on;
        add_header X-Cache-Status $upstream_cache_status;{rate_line}
    }}""")
        )

    # Strict rate-limited push locations for collections with rateLimit: true
    rate_limited_push_locations = []
    if global_rate_limit:
        for col in collections:
            if not col.get("rateLimit"):
                continue
            if col.get("pullOnly"):
                continue

            path_re = storage_path_to_regex(col["storagePath"])
            name = col["name"]

            rate_limited_push_locations.append(
                textwrap.dedent(f"""\
    # {name} (rate limited push)
    location ~* ^/v1/push/{path_re}$ {{
        proxy_pass http://octobot_sync;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        limit_req zone=sync_strict burst={strict_burst} nodelay;
    }}""")
            )

    cached_block = "\n\n".join(cached_locations) if cached_locations else ""
    push_block = "\n\n".join(rate_limited_push_locations) if rate_limited_push_locations else ""

    # Global rate limit on catch-all
    catchall_rate_line = ""
    if global_rate_limit:
        catchall_rate_line = f"\n        limit_req zone=sync_global burst={global_burst} nodelay;"

    return textwrap.dedent(f"""\
proxy_cache_path /var/cache/nginx/sync
    levels=1:2
    keys_zone=sync_cache:10m
    max_size=1g
    inactive=60m
    use_temp_path=off;

{rate_limit_block}upstream octobot_sync {{
    server {upstream};
}}

server {{
    listen {listen};
    server_name _;

    client_max_body_size 10m;

    # ── Health (no cache, no rate limit) ──
    location = /health {{
        proxy_pass http://octobot_sync;
    }}

{textwrap.indent(cached_block, "    ") if cached_block else "    # (no public collections found)"}

{textwrap.indent(push_block, "    ") if push_block else ""}

    # ── Catch-all: proxy to OctoBot sync, no cache ──
    location /v1/ {{
        proxy_pass http://octobot_sync;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;{catchall_rate_line}
    }}

    # Reject anything outside /v1 and /health
    location / {{
        return 404;
    }}
}}
""")


def main():
    parser = argparse.ArgumentParser(
        description="Generate nginx config from OctoBot sync collections.json"
    )
    parser.add_argument("collections", help="Path to collections.json")
    parser.add_argument(
        "--upstream", default="octobot-sync:3000",
        help="OctoBot sync upstream host:port (default: octobot-sync:3000)",
    )
    parser.add_argument(
        "--listen", type=int, default=80,
        help="nginx listen port (default: 80)",
    )
    args = parser.parse_args()

    sys.stdout.write(generate(args.collections, args.upstream, args.listen))


if __name__ == "__main__":
    main()
