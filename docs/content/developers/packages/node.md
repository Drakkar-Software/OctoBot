---
title: Node
description: OctoBot Node — a durable task execution server that runs OctoBot automations via a FastAPI backend and DBOS-powered scheduler.
sidebar_position: 1
---

# OctoBot Node

The `node` package is a standalone service that executes OctoBot automations as durable, distributed tasks. It runs a FastAPI application backed by [DBOS](https://docs.dbos.dev/) — a workflow engine that persists every step of every execution to a database, making the node resilient to crashes and safe to restart mid-task.

## What a node does

A node receives automation tasks over its REST and WebSocket API, stores them in either SQLite or PostgreSQL, and hands them off to the `octobot_flow` runtime for execution. Each task describes a DAG of actions. The node handles scheduling, retries, crash recovery, and per-workflow log isolation. Task payloads can optionally be encrypted end-to-end.

An instance can play one or more roles: it can accept and schedule tasks (master), pull and execute them (consumer), or both. Running them separately is what allows the consumer tier to scale independently. Multi-node deployments require a shared PostgreSQL database; SQLite is single-node only.

## Workflow lifecycle

DBOS persists every workflow invocation and step result to the database. If the process crashes mid-execution, the workflow resumes from the last completed step rather than starting over. Each automation iteration runs as a separate child workflow — a deliberate design choice that prevents a long-running automation from accumulating an unbounded step history in a single workflow record. Child workflow IDs embed the parent UUID4 as a prefix so the API can group them back into a coherent execution history.

The `execute_iteration` function is itself a DBOS step rather than a plain async call. This is what prevents double-execution: DBOS records step entry and exit atomically, so a crash between those two points replays the step rather than running it a second time. Steps are retried up to three times before the workflow exits with an error.

User-triggered actions — things like a manual override sent through the API — are delivered as DBOS messages on the `"user_actions"` topic while the workflow is running. This lets them bypass the DAG's scheduled next step and be drained as extra iterations immediately after the current one completes.

Log messages emitted inside any workflow or step are routed to a per-workflow file under `logs/automations/`. Child workflows share their parent's log file, keyed by the first 36 characters of the workflow ID.

## Encryption

Task payloads are optionally encrypted using a hybrid RSA/AES-GCM/ECDSA scheme. Each encryption call generates a fresh AES-256-GCM key and IV; the AES key is wrapped with RSA-OAEP so the bulk payload never travels under the asymmetric key directly. An ECDSA signature over the ciphertext — computed as `ciphertext + encrypted_aes_key + iv` concatenated — is verified before any decryption attempt, preventing chosen-ciphertext attacks.

**Split-ownership key model.** The server holds two private keys set via environment variables:

| Environment variable | Purpose |
|---|---|
| `TASKS_SERVER_RSA_PRIVATE_KEY` | Decrypts incoming task content (wrapped AES key) |
| `TASKS_SERVER_ECDSA_PRIVATE_KEY` | Signs outgoing task results |

The browser holds two private keys, entered once in the Settings page and stored locally:

| Browser key | Purpose |
|---|---|
| `USER_RSA_PRIVATE_KEY` | Decrypts result content from the server |
| `USER_ECDSA_PRIVATE_KEY` | Signs task content before submission |

User public keys are not configured on the server. When the browser submits an encrypted task, it derives both public keys from the stored private keys using the Web Crypto API. The ECDSA public key is embedded in the task payload (`user_ecdsa_public_key`) so the server can verify the input signature whenever that task is consumed. The RSA public key is not stored with the task; instead, the browser derives it fresh and includes it in each export-results request, so the server can wrap the AES key specifically for the requesting user. This separation means the ECDSA key is tied to when a task was created, while the RSA encryption key is always the user's current key — key rotation is transparently supported without resubmitting tasks.

The server public keys (`SERVER_RSA_PUBLIC_KEY` and `SERVER_ECDSA_PUBLIC_KEY`) are never entered manually — the browser fetches them on demand from `GET /tasks/server-public-keys`, which derives and returns them from the server's private keys at runtime. The server never loads the user's private keys; the browser never loads the server's private keys.

**Encryption in the browser.** When submitting encrypted tasks the browser performs all cryptographic operations locally using the Web Crypto API (`crypto.subtle`), without sending any key material to the server. The `encryptAndSign` function first fetches the server's RSA public key from `GET /tasks/server-public-keys`, generates a fresh AES-256-GCM key, encrypts the task payload, wraps the AES key with that server RSA public key (RSA-OAEP), then signs the concatenation of ciphertext, wrapped key, and IV with `USER_ECDSA_PRIVATE_KEY`. The ECDSA signature is converted from the IEEE P1363 format that Web Crypto produces to DER format before transmission, because Python's `cryptography` library expects DER.

**Metadata format.** The accompanying metadata envelope carries `ENCRYPTED_AES_KEY_B64`, `IV_B64`, and `SIGNATURE_B64`. For task inputs, `content_metadata` is `base64(JSON)` — the JSON object is serialised then base64-encoded — because it travels as a CSV or API field where a single opaque string is easiest to embed. For task results, `result_metadata` is a plain JSON string; it is stored in the database and consumed by code that already handles JSON, so the extra base64 layer would be noise. Being aware of this distinction matters when building tooling that reads raw database records.

**`encrypted_task` context manager.** This wraps each task execution on the consumer node transparently. On entry it decrypts `task.content` using `TASKS_SERVER_RSA_PRIVATE_KEY` and verifies the signature when `task.content_metadata` is non-null. Signature verification uses the task's own `user_ecdsa_public_key` field first (browser-submitted tasks carry it inline); if absent, falls back to the `TASKS_USER_ECDSA_PUBLIC_KEY` env var; then falls back to the server's own ECDSA public key (server-generated internal state, signed with `TASKS_SERVER_ECDSA_PRIVATE_KEY`). If decryption fails the context manager logs the error and continues with the original encrypted content — it does not crash the workflow. On exit it restores the original `task.content` and does not touch results.

**Internal state and result encryption.** Between iterations the automation state is stored in DBOS encrypted with `encrypt_task_content` (AES-GCM wrapped with SERVER_RSA_PUBLIC, signed with SERVER_ECDSA_PRIVATE), making it readable only by the server. When the user explicitly exports completed results, the browser includes its current RSA public PEM in the export-results request body. The scheduler decrypts the stored state using the `encrypted_task` context manager (SERVER_RSA_PRIVATE + SERVER/USER ECDSA public), then re-encrypts it with `encrypt_task_result` (AES-GCM wrapped with the request-supplied RSA public key, signed with SERVER_ECDSA_PRIVATE) before returning it. If no RSA public key is supplied in the request, the scheduler returns the decrypted state as plaintext. Decryption happens in the browser using `USER_RSA_PRIVATE_KEY`, with the signature verified against `SERVER_ECDSA_PUBLIC_KEY`. Because the RSA key comes from the request rather than the task, a user who rotates their keys or exports a task that was originally submitted without encryption both receive correctly encrypted results without resubmitting anything.

**Security boundary with `octobot_flow`.** The `encrypted_task` context manager wraps the call to `octobot_flow`'s `AutomationJob.run()` inside the node's workflow step. Task content is decrypted just before execution on the consumer node that holds the server private keys. From flow's perspective nothing changes — it receives a plaintext `AutomationState` dict and returns an updated one. The flow package has no awareness of encryption, which means the same engine works identically in encrypted node deployments, unencrypted nodes, and standalone bots.

**Key loading and validation.** The two server keys are accepted as PEM-encoded strings via environment variables, decoded to `bytes` at process startup by a `BeforeValidator` in the pydantic `Settings` model. There is no lazy loading — `settings` is a module-level singleton instantiated at import time, so a misconfigured key value fails fast before any requests are served. The `is_node_side_encryption_enabled` property checks whether both server keys are present, and `tasks_encryption_enabled` is an alias used in API responses.

**Browser key storage.** The browser keys entered in the Settings page, and the login passphrase, are stored in `IndexedDB` encrypted with a device-bound, non-extractable AES-256-GCM key. That device key is generated on first login using `crypto.subtle.generateKey` with `extractable: false` and can never be exported or read as raw bytes — not even from a filesystem dump of the database file. It is origin-bound, so it cannot be used from another domain or browser profile. Neither the passphrase nor the user keys are ever stored in `localStorage` or sent to the server.

**Key generation.** Generate the server key pairs with openssl:

```bash
# Server RSA-4096 keypair (private key → TASKS_SERVER_RSA_PRIVATE_KEY env var)
openssl genrsa -out server_rsa_private.pem 4096

# Server ECDSA-P256 keypair (private key → TASKS_SERVER_ECDSA_PRIVATE_KEY env var)
openssl ecparam -genkey -name prime256v1 -noout -out server_ecdsa_ec.pem
openssl pkcs8 -topk8 -nocrypt -in server_ecdsa_ec.pem -out server_ecdsa_private.pem
```

The server public keys are never distributed manually — the browser fetches them via `GET /tasks/server-public-keys` at runtime.

User key pairs are generated by the browser on first use and stored locally in the Settings page. The browser derives the corresponding public keys from the stored private keys using the Web Crypto API and embeds them in each task at submission time. No user public key configuration is required on the server.

Encryption is opt-in. If the server keys are absent from the environment, the corresponding path is skipped and fields stay plaintext.

## Wallet security

The node supports multiple wallets — each identified by an EVM address — so that different users can share a single node instance without accessing each other's tasks or credentials. Wallet security rests on two distinct layers that are often confused: the passphrase, which is for authentication, and the at-rest envelope, which is for storage protection.

**Passphrase role.** The passphrase is a per-wallet authentication credential, not an encryption key. When a wallet is registered, the passphrase is hashed with PBKDF2-HMAC-SHA256 at 600,000 iterations and the hash is stored alongside the wallet — the plaintext passphrase is never written anywhere. At login, the incoming passphrase is hashed and compared to the stored digest using a constant-time comparison to prevent timing attacks. This design keeps multi-tenant access control independent of encryption: the node can validate that a user is who they say they are without needing the passphrase for any other purpose.

**Private key storage.** Wallet private keys are stored in plaintext in the wallet list JSON rather than encrypted with the passphrase. This is an intentional tradeoff that enables bot auto-unlock: when the node process starts, the admin bot needs its wallet available immediately without waiting for a human to type a passphrase. Storing the key encrypted with the user passphrase would break unattended startup. The protection for private keys at rest therefore comes from the storage envelope, not the passphrase. When `OCTOBOT_WALLET_AES_KEY` is set, the entire wallet list is wrapped in AES-256-GCM before writing to disk — any attacker who reads the file without the environment-level key sees only ciphertext. Without that env var the wallet list is plaintext JSON, protected only by filesystem permissions. For production deployments, setting `OCTOBOT_WALLET_AES_KEY` and restricting read access to the config file are the primary defenses.

**Per-wallet browser key storage.** The browser-side encryption keys (RSA and ECDSA private keys) that users configure in the Settings page are stored in IndexedDB, encrypted with a key derived from the user's wallet passphrase and address using PBKDF2. The derivation uses the address as a deterministic salt, so each wallet address produces a different encryption key. This has two practical consequences: first, two users sharing a browser cannot read each other's keys even if they can inspect the raw IndexedDB records; second, when a user logs out and the passphrase is cleared from memory, the client keys become inaccessible — they are still physically present in the database but cannot be decrypted without the passphrase. Sessions on new devices or browsers start with no client keys and must re-enter them in Settings.

**Security boundary.** An attacker with read access to the node's disk (but not its running environment) can reach the wallet list file. If `OCTOBOT_WALLET_AES_KEY` is absent, they can extract private keys directly. If the env var is set, they need both the file and the key. Either way, an attacker with both the wallet list and the passphrase hash gains nothing extra — the passphrase hash cannot be used to derive the private key because the private key was never encrypted with the passphrase. For the browser keys, an attacker who can dump the IndexedDB store (e.g. from a local machine compromise) still needs the passphrase for the wallet in question to decrypt them.

## Template importing

Both the CSV import flow and the export results page support user-defined templates loaded from JSON files. This lets teams share reusable configurations without touching application code.

**Import templates** (used during CSV task import) compose multiple base action templates into a single combined template by listing them as ordered steps. Each step can pre-fill parameter values as defaults and mark parameters as hidden so they don't appear in the form. The import UI validates the JSON with a Zod schema, checks that every referenced base template exists, and rejects any hidden required parameter that lacks a default — preventing the form from silently blocking submission. Templates that pass validation are saved to `localStorage` and appear alongside the built-in templates in the action dropdown immediately.

**Export templates** (used on the export results page) define flat column mappings: each column specifies a label, a JSON path into the task result object, and an optional formatter (`text`, `number`, `date`, or `json`). JSON paths starting and ending with double underscores (e.g. `__task_name__`) resolve against task-level metadata rather than the result payload. Like import templates, export templates are Zod-validated on ingest, stored in `localStorage`, and appear in the template dropdown without a page reload.

Both systems use the same localStorage-backed CRUD pattern — load, upsert by ID, delete — and silently skip malformed entries on load so a corrupted template doesn't break the entire list. Built-in template IDs are reserved; attempting to import a user template with the same ID as a built-in raises an error.

Example files for both systems ship with the application:
- Import meta-template examples: `public/meta-template-examples/`
- Export template examples: `public/export-template-examples/`

The export template JSON format:

```json
{
  "id": "my_export",
  "label": "My Export",
  "description": "Custom export columns",
  "columns": [
    { "key": "name", "label": "Name", "jsonPath": "__task_name__", "formatter": "text" },
    { "key": "amount", "label": "Amount", "jsonPath": "amount", "formatter": "number" },
    { "key": "fee", "label": "Fee", "jsonPath": "fee.cost", "formatter": "number" }
  ]
}
```
