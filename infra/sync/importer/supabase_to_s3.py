#!/usr/bin/env python3
"""
Supabase → S3 Importer for OctoBot Sync
========================================
Reads data from Supabase tables and uploads JSON documents into S3
following the storagePath conventions defined in collections.json.

Only unencrypted collections (encryption: "none") are handled.

Usage:
    # Full import (all collections)
    python supabase_to_s3.py

    # Full import of specific collections
    python supabase_to_s3.py --collections news exchanges cryptocurrencies

    # Incremental import (rows updated since last run)
    python supabase_to_s3.py --incremental

    # Dry-run (log what would be uploaded without writing to S3)
    python supabase_to_s3.py --dry-run

Environment variables (see .env.example):
    SUPABASE_URL            Supabase project URL
    SUPABASE_SERVICE_KEY    Supabase service-role key (bypasses RLS)
    S3_ENDPOINT             S3-compatible endpoint (e.g. Garage)
    S3_BUCKET               Target bucket name
    S3_ACCESS_KEY           S3 access key
    S3_SECRET_KEY           S3 secret key
    S3_REGION               S3 region (default: garage)
    STATE_FILE              Path to incremental-state JSON (default: .import_state.json)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from supabase import create_client, Client as SupabaseClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("supabase_to_s3")

COLLECTIONS_JSON = (
    Path(__file__).resolve().parent.parent
    / "ansible"
    / "roles"
    / "stack"
    / "files"
    / "collections.json"
)
DEFAULT_STATE_FILE = Path(__file__).resolve().parent / ".import_state.json"
DEFAULT_S3_REGION = "garage"
SUPABASE_PAGE_SIZE = 1000  # rows per request (Supabase max)


class CollectionImporter:
    """Base class for a single collection importer."""

    def __init__(
        self,
        name: str,
        storage_path: str,
        supabase: SupabaseClient,
        s3_client: Any,
        bucket: str,
        dry_run: bool = False,
    ):
        self.name = name
        self.storage_path = storage_path
        self.supabase = supabase
        self.s3 = s3_client
        self.bucket = bucket
        self.dry_run = dry_run

    def _paginate(
        self,
        table: str,
        select: str = "*",
        order_col: str = "id",
        filters: dict[str, Any] | None = None,
        since: datetime | None = None,
        since_column: str = "created_at",
    ) -> list[dict]:
        """Fetch all rows from *table* with automatic pagination."""
        rows: list[dict] = []
        offset = 0
        while True:
            q = (
                self.supabase.table(table)
                .select(select)
                .order(order_col)
                .range(offset, offset + SUPABASE_PAGE_SIZE - 1)
            )
            if filters:
                for col, val in filters.items():
                    q = q.eq(col, val)
            if since is not None:
                q = q.gte(since_column, since.isoformat())
            resp = q.execute()
            batch = resp.data or []
            rows.extend(batch)
            if len(batch) < SUPABASE_PAGE_SIZE:
                break
            offset += SUPABASE_PAGE_SIZE
        return rows

    def _upload_json(self, key: str, data: Any) -> None:
        """Upload a JSON document to S3 at *key*."""
        body = json.dumps(data, default=str, ensure_ascii=False)
        if self.dry_run:
            logger.info("[DRY-RUN] Would upload %s (%d bytes)", key, len(body))
            return
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Uploaded %s (%d bytes)", key, len(body))

    def run(self, since: datetime | None = None) -> int:
        """Execute the import. Returns the number of S3 objects written."""
        raise NotImplementedError


class ExchangesImporter(CollectionImporter):
    """exchanges → public/exchanges"""

    def run(self, since: datetime | None = None) -> int:
        rows = self._paginate(
            "exchanges",
            select="id, name, internal_name, logo_url, premium, availability, "
                   "metadata, url, url_required, password_required, oauth, "
                   "trusted_ips, created_at, updated_at",
            since=since,
            since_column="updated_at",
        )
        rows = [r for r in rows if not r.get("deleted")]
        self._upload_json(self.storage_path, rows)
        return 1


class CryptocurrenciesImporter(CollectionImporter):
    """cryptocurrencies → public/cryptocurrencies"""

    def run(self, since: datetime | None = None) -> int:
        rows = self._paginate(
            "cryptocurrencies",
            select="id, name, symbol, last_price, price_change_percentage, "
                   "market_cap, total_supply, ath, atl, image_url, website_url, metadata",
        )
        self._upload_json(self.storage_path, rows)
        return 1


class CryptocurrencyDetailImporter(CollectionImporter):
    """cryptocurrency-detail → public/cryptocurrencies/{cryptocurrency}"""

    def run(self, since: datetime | None = None) -> int:
        rows = self._paginate(
            "cryptocurrencies",
            select="id, name, symbol, description_translations, last_price, "
                   "price_change_percentage, market_cap, total_supply, ath, atl, "
                   "image_url, website_url, metadata",
        )
        count = 0
        for row in rows:
            symbol = row.get("symbol")
            if not symbol:
                continue
            key = self.storage_path.replace("{cryptocurrency}", symbol.lower())
            self._upload_json(key, row)
            count += 1
        return count


class CategoriesImporter(CollectionImporter):
    """categories → public/products/categories"""

    def run(self, since: datetime | None = None) -> int:
        rows = self._paginate(
            "product_categories",
            select="id, slug, name_translations, type, metadata, "
                   "why_translations, description_translations, "
                   "subcategories_translations, educational_translations, "
                   "created_at, updated_at",
            since=since,
            since_column="updated_at",
        )
        rows = [r for r in rows if not r.get("deleted")]
        self._upload_json(self.storage_path, rows)
        return 1


class PlansImporter(CollectionImporter):
    """plans → public/products/plans"""

    def run(self, since: datetime | None = None) -> int:
        rows = self._paginate(
            "product_plans",
            select="id, slug, product_id, prices, interval, active, metadata, created_at",
        )
        rows = [r for r in rows if r.get("active")]
        self._upload_json(self.storage_path, rows)
        return 1


class NewsImporter(CollectionImporter):
    """news → public/news/{lang}/{month}

    Groups news rows by (lang, YYYY-MM) and uploads one object per group.
    """

    def run(self, since: datetime | None = None) -> int:
        rows = self._paginate(
            "news",
            select="id, title, difficulty, summary, source_key, source_url, "
                   "image_url, lang, metadata, published_on, relevancy, "
                   "source_name, types",
            order_col="published_on",
            since=since,
            since_column="published_on",
        )
        # Group by (lang, month)
        groups: dict[tuple[str, str], list[dict]] = {}
        for row in rows:
            lang = row.get("lang") or "en"
            pub = row.get("published_on") or ""
            month = pub[:7] if len(pub) >= 7 else "unknown"  # YYYY-MM
            groups.setdefault((lang, month), []).append(row)

        count = 0
        for (lang, month), group_rows in groups.items():
            key = (
                self.storage_path
                .replace("{lang}", lang)
                .replace("{month}", month)
            )
            self._upload_json(key, group_rows)
            count += 1
        return count


class CoursesImporter(CollectionImporter):
    """courses → public/courses

    Merges courses with their course_chapters.
    """

    def run(self, since: datetime | None = None) -> int:
        chapters = self._paginate(
            "course_chapters",
            select="id, name_translations, description_translations, type, "
                   "position, metadata, slug",
        )
        chapters_by_id = {c["id"]: c for c in chapters}

        courses = self._paginate(
            "courses",
            select="id, name_translations, description_translations, lessons, "
                   "course_chapter_id, metadata, slug",
        )
        # Attach chapter info
        for course in courses:
            ch_id = course.get("course_chapter_id")
            if ch_id and ch_id in chapters_by_id:
                course["chapter"] = chapters_by_id[ch_id]

        self._upload_json(self.storage_path, {"chapters": chapters, "courses": courses})
        return 1


class HighlightsImporter(CollectionImporter):
    """highlights → public/products/highlights

    Selects visible products that have current results (i.e. performance data).
    """

    def run(self, since: datetime | None = None) -> int:
        rows = self._paginate(
            "products",
            select="id, slug, content, logo_url, category_id, attributes, "
                   "metadata, visibility, current_result_id, created_at",
        )
        highlights = [
            r for r in rows
            if r.get("visibility") == "public"
            and r.get("current_result_id") is not None
            and r.get("deleted_at") is None
        ]
        self._upload_json(self.storage_path, highlights)
        return 1


class ProductsIndexImporter(CollectionImporter):
    """products-index → public/products/index

    Public index of all visible products.
    """

    def run(self, since: datetime | None = None) -> int:
        rows = self._paginate(
            "products",
            select="id, slug, content, logo_url, category_id, attributes, "
                   "metadata, visibility, current_version_id, current_config_id, "
                   "current_result_id, author_id, trial_period, access_policy, "
                   "created_at, updated_at",
        )
        public = [
            r for r in rows
            if r.get("visibility") == "public"
            and r.get("deleted_at") is None
        ]
        self._upload_json(self.storage_path, public)
        return 1


class SignalsImporter(CollectionImporter):
    """signals → products/{productId}/signals/{version}"""

    def run(self, since: datetime | None = None) -> int:
        rows = self._paginate(
            "signals",
            select="id, created_at, product_id, signal",
            since=since,
            since_column="created_at",
        )
        # Group by product_id
        by_product: dict[str, list[dict]] = {}
        for r in rows:
            by_product.setdefault(r["product_id"], []).append(r)

        count = 0
        for product_id, signals in by_product.items():
            # Use "latest" as the version bucket
            key = (
                self.storage_path
                .replace("{productId}", product_id)
                .replace("{version}", "latest")
            )
            self._upload_json(key, signals)
            count += 1
        return count


class ProductProfilesImporter(CollectionImporter):
    """product-profiles → products/{productId}/profile"""

    def run(self, since: datetime | None = None) -> int:
        rows = self._paginate(
            "products",
            select="id, slug, content, logo_url, attributes, metadata, "
                   "visibility, author_id, created_at, updated_at",
            since=since,
            since_column="updated_at",
        )
        count = 0
        for r in rows:
            if r.get("deleted_at") is not None:
                continue
            content = r.get("content") or {}
            profile = {
                "name": content.get("name_translations", {}).get("en", ""),
                "description": content.get("description_translations", {}).get("en", ""),
            }
            if r.get("attributes"):
                attrs = r["attributes"]
                if isinstance(attrs, dict):
                    profile["website"] = attrs.get("website", "")
                    profile["twitter"] = attrs.get("twitter", "")
                    profile["tags"] = attrs.get("tags", [])
            key = self.storage_path.replace("{productId}", r["id"])
            self._upload_json(key, profile)
            count += 1
        return count


class ProductVersionsImporter(CollectionImporter):
    """product-versions → products/{productId}/versions/{version}/document"""

    def run(self, since: datetime | None = None) -> int:
        rows = self._paginate(
            "product_versions",
            select="id, version, state, content, product_id, logo_url, "
                   "download_url, created_at, updated_at",
            since=since,
            since_column="created_at",
        )
        count = 0
        for r in rows:
            product_id = r.get("product_id")
            version = r.get("version")
            if not product_id or not version:
                continue
            doc = {"description": ""}
            if r.get("content"):
                doc["description"] = str(r["content"])
            key = (
                self.storage_path
                .replace("{productId}", product_id)
                .replace("{version}", version)
            )
            self._upload_json(key, doc)
            count += 1
        return count


class PerformanceImporter(CollectionImporter):
    """performance → products/{productId}/performance/{version}"""

    def run(self, since: datetime | None = None) -> int:
        rows = self._paginate(
            "product_results",
            select="id, created_at, starts_at, ends_at, profitability, "
                   "product_id, asset_path, reference_market_profitability",
            since=since,
            since_column="created_at",
        )
        count = 0
        for r in rows:
            product_id = r.get("product_id")
            if not product_id:
                continue
            key = (
                self.storage_path
                .replace("{productId}", product_id)
                .replace("{version}", "latest")
            )
            self._upload_json(key, r)
            count += 1
        return count





IMPORTER_REGISTRY: dict[str, type[CollectionImporter]] = {
    # Public / static
    "exchanges": ExchangesImporter,
    "cryptocurrencies": CryptocurrenciesImporter,
    "cryptocurrency-detail": CryptocurrencyDetailImporter,
    "categories": CategoriesImporter,
    "plans": PlansImporter,
    "news": NewsImporter,
    "courses": CoursesImporter,
    "highlights": HighlightsImporter,
    "products-index": ProductsIndexImporter,
    # Per-product
    "signals": SignalsImporter,
    "product-profiles": ProductProfilesImporter,
    "product-versions": ProductVersionsImporter,
    "performance": PerformanceImporter,
}



def _load_state(path: Path) -> dict[str, str]:
    """Load {collection_name: last_import_iso} from state file."""
    if path.is_file():
        return json.loads(path.read_text())
    return {}


def _save_state(path: Path, state: dict[str, str]) -> None:
    path.write_text(json.dumps(state, indent=2))



def load_collections_config(path: Path) -> list[dict]:
    """Read collections.json and return only unencrypted collections."""
    data = json.loads(path.read_text())
    return [
        c for c in data.get("collections", [])
        if c.get("encryption", "none") == "none"
    ]


def build_s3_client(
    endpoint: str,
    access_key: str,
    secret_key: str,
    region: str,
) -> Any:
    """Create a boto3 S3 client for the given endpoint."""
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=BotoConfig(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def run_import(
    collections_filter: list[str] | None = None,
    incremental: bool = False,
    dry_run: bool = False,
) -> None:
    """Main entry point: read config, connect clients, run importers."""

    # env
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    s3_endpoint = os.environ["S3_ENDPOINT"]
    s3_bucket = os.environ["S3_BUCKET"]
    s3_access = os.environ["S3_ACCESS_KEY"]
    s3_secret = os.environ["S3_SECRET_KEY"]
    s3_region = os.environ.get("S3_REGION", DEFAULT_S3_REGION)
    state_file = Path(os.environ.get("STATE_FILE", str(DEFAULT_STATE_FILE)))

    # clients
    supabase: SupabaseClient = create_client(supabase_url, supabase_key)
    s3 = build_s3_client(s3_endpoint, s3_access, s3_secret, s3_region)

    # collections
    collections_path = Path(
        os.environ.get("COLLECTIONS_JSON", str(COLLECTIONS_JSON))
    )
    collections = load_collections_config(collections_path)
    logger.info(
        "Loaded %d unencrypted collections from %s",
        len(collections),
        collections_path,
    )

    # state for incremental
    state = _load_state(state_file) if incremental else {}
    run_start = datetime.now(timezone.utc)

    # execute
    total_objects = 0
    for col in collections:
        name = col["name"]
        if collections_filter and name not in collections_filter:
            continue
        if name not in IMPORTER_REGISTRY:
            logger.warning("No importer registered for collection '%s', skipping", name)
            continue

        since = None
        if incremental and name in state:
            since = datetime.fromisoformat(state[name])
            logger.info("Incremental import for '%s' since %s", name, since)

        importer_cls = IMPORTER_REGISTRY[name]
        importer = importer_cls(
            name=name,
            storage_path=col["storagePath"],
            supabase=supabase,
            s3_client=s3,
            bucket=s3_bucket,
            dry_run=dry_run,
        )

        try:
            count = importer.run(since=since)
            total_objects += count
            logger.info("Collection '%s': %d object(s) uploaded", name, count)
            state[name] = run_start.isoformat()
        except Exception:
            logger.exception("Failed to import collection '%s'", name)

    # persist state
    if incremental and not dry_run:
        _save_state(state_file, state)
        logger.info("Incremental state saved to %s", state_file)

    logger.info("Import complete: %d total object(s) written", total_objects)



def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import Supabase data into S3 for OctoBot Sync",
    )
    parser.add_argument(
        "--collections",
        nargs="*",
        default=None,
        help="Only import these collections (space-separated names). "
             f"Available: {', '.join(sorted(IMPORTER_REGISTRY))}",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only fetch rows updated since the last successful import",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be uploaded without writing to S3",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    run_import(
        collections_filter=args.collections,
        incremental=args.incremental,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
