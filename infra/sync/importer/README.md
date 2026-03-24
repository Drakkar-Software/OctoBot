# Supabase → S3 Importer

Imports data from Supabase tables into the S3-compatible storage (Garage) used by [OctoBot Sync](../ansible/), following the `storagePath` conventions defined in [`collections.json`](../ansible/roles/stack/files/collections.json).

Only **unencrypted** collections (`encryption: "none"`) are imported. Encrypted collections (`identity`, `server`, `delegated`) are skipped.

## Prerequisites

- Python 3.10+
- A Supabase project with a **service-role key** (bypasses RLS)
- An S3-compatible endpoint (Garage, MinIO, or AWS S3) with a bucket already created

Install dependencies:

```bash
pip install boto3 supabase
```

## Configuration

Copy the environment template and fill in your credentials:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | yes | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | yes | Service-role key (not the anon key) |
| `S3_ENDPOINT` | yes | S3-compatible endpoint (e.g. `http://localhost:3900`) |
| `S3_BUCKET` | yes | Target bucket name |
| `S3_ACCESS_KEY` | yes | S3 access key |
| `S3_SECRET_KEY` | yes | S3 secret key |
| `S3_REGION` | no | S3 region (default: `garage`) |
| `COLLECTIONS_JSON` | no | Override path to `collections.json` |
| `STATE_FILE` | no | Override path to incremental state file (default: `.import_state.json`) |

## Usage

```bash
# Full import of all supported collections
python supabase_to_s3.py

# Import specific collections only
python supabase_to_s3.py --collections news exchanges cryptocurrencies

# Incremental import (only rows updated since last run)
python supabase_to_s3.py --incremental

# Dry-run: log what would be uploaded without writing to S3
python supabase_to_s3.py --dry-run

# Combine flags
python supabase_to_s3.py --incremental --collections signals performance --verbose
```

## Supported collections

### Public (static path)

| Collection | Supabase table(s) | S3 path |
|---|---|---|
| `exchanges` | `exchanges` | `public/exchanges` |
| `cryptocurrencies` | `cryptocurrencies` | `public/cryptocurrencies` |
| `cryptocurrency-detail` | `cryptocurrencies` (one object per symbol) | `public/cryptocurrencies/{cryptocurrency}` |
| `categories` | `product_categories` | `public/products/categories` |
| `plans` | `product_plans` | `public/products/plans` |
| `news` | `news` (grouped by lang + month) | `public/news/{lang}/{month}` |
| `courses` | `courses`, `course_chapters` | `public/courses` |
| `highlights` | `products` (public with results) | `public/products/highlights` |
| `products-index` | `products` (public, not deleted) | `public/products/index` |

### Per-product

| Collection | Supabase table(s) | S3 path |
|---|---|---|
| `signals` | `signals` | `products/{productId}/signals/{version}` |
| `product-profiles` | `products` | `products/{productId}/profile` |
| `product-versions` | `product_versions` | `products/{productId}/versions/{version}/document` |
| `performance` | `product_results` | `products/{productId}/performance/{version}` |

## Incremental mode

When `--incremental` is passed, the script:

1. Reads `.import_state.json` which stores the last successful import timestamp per collection.
2. Filters Supabase queries to only fetch rows with `created_at` (or `updated_at` where applicable) newer than the stored timestamp.
3. After a successful import, updates the state file with the current run timestamp.

The state file is **not updated** during `--dry-run`.

## Skipped collections

The following collections are not handled by this importer (encrypted or per-user scoped):

`bots`, `accounts`, `settings`, `notifications`, `recovery`, `courses-user`, `platform-affiliates`, `platform-referrals`, `errors`, `profiles`, `referrals`, `invoices`, `affiliate`, `donations`
