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

The central design constraint is directional key separation. There are two independent key pairs — one for task inputs, one for task outputs — and each pair is split across the two sides. The node holds the private key to decrypt incoming inputs and the public key to encrypt outgoing results. The producer holds the complementary keys. Neither side has all eight keys. A compromised node can read the task inputs it needs to execute, but cannot decrypt the results it just produced — those are only readable by the producer.

**Metadata format asymmetry.** The accompanying metadata envelope — which carries `ENCRYPTED_AES_KEY_B64`, `IV_B64`, and `SIGNATURE_B64` — is serialised differently depending on direction. For task inputs, `encrypt_task_content` returns the metadata as `base64(JSON)`: the JSON object is first serialised to a string, then base64-encoded again. The corresponding `decrypt_task_content` therefore base64-decodes then JSON-parses. For task outputs, `encrypt_task_result` returns the metadata as a plain JSON string with no outer base64 layer, and `decrypt_task_result` JSON-parses directly. The asymmetry exists because input metadata is transmitted as a CSV or API field where a single opaque string is easier to embed without escaping, while output metadata is stored in the database and consumed programmatically by code that already handles JSON. Being aware of this distinction matters when building a producer or any tooling that reads raw database records.

**`encrypted_task` context manager.** This wraps each task execution transparently. On entry it decrypts `task.content` if the input keys are present and `task.content_metadata` is non-null. On exit it encrypts `task.result` if the output keys are present. The two directions are independent — a node can be configured to decrypt inputs only, encrypt outputs only, or both. If decryption fails, the context manager does not propagate the exception into the workflow; instead it writes a structured error dict to `task.result`, so the failure is observable via the API without crashing the scheduler.

**Security boundary with `octobot_flow`.** The `encrypted_task` context manager wraps the call to `octobot_flow`'s `AutomationJob.run()` inside the node's workflow step. This means the scheduler — the master node that stores and routes tasks — only ever sees encrypted payloads. Task content is decrypted just before execution on the consumer node that holds the private keys, and the result is re-encrypted immediately after. The scheduler database, its API, and any intermediary never handle plaintext. A compromised scheduler leaks only ciphertext. From flow's perspective, nothing changes — it receives a plaintext `AutomationState` dict and returns an updated one. The flow package has no awareness of encryption, which means the same engine works identically in encrypted node deployments, unencrypted nodes, and standalone bots.

**Key loading and validation.** All eight keys are accepted as PEM-encoded strings via environment variables, decoded to `bytes` at process startup by a `BeforeValidator` in the pydantic `Settings` model. There is no lazy loading — `settings` is a module-level singleton instantiated at import time, so a misconfigured key value fails fast before any requests are served. Two computed properties — `is_node_side_encryption_enabled` and `is_producer_side_encryption_enabled` — check whether all four keys for each role are present simultaneously, enabling clean conditional logic elsewhere in the codebase without repeating null checks. The broader `tasks_encryption_enabled` flag requires all eight keys, which is only meaningful when a single process is acting as both producer and node (uncommon outside of testing).

**CSV bulk tools.** The `tools/` directory contains three standalone CLI scripts — `encrypt_csv_tasks.py`, `decrypt_csv_tasks.py`, and `decrypt_csv_results.py` — intended for batch operations outside the running service. All three load keys either from PEM files passed on the command line or from the environment variables, falling back gracefully between the two with an explicit priority order. A companion `csv_utils.py` implements the column-merging logic shared with the TypeScript `node_web_interface` frontend: it reads a flat CSV where arbitrary columns are collapsed into a JSON `content` object on encryption, and expands an encrypted result dict back into separate columns on decryption. This symmetry means a producer can author tasks in a spreadsheet-friendly multi-column format, encrypt in bulk, and upload the resulting file directly to the API without any intermediate reformatting. The `generate_and_save_keys` helper in `csv_utils.py` also handles first-time key provisioning — generating all four key pairs (4096-bit RSA and ECDSA) and writing them to a `task_encryption_keys.json` file — which is the recommended path for setting up a fresh deployment.

**Key generation.** For a fresh deployment, `generate_and_save_keys` creates all four key pairs at once — two 4096-bit RSA pairs (one for inputs, one for outputs) and two ECDSA pairs on the SECP256R1 curve — and writes them to a single `task_encryption_keys.json` file. The node operator and producer each extract their half of the keys from that file. This single-generation approach guarantees that the key pairs are mathematically matched and avoids the error-prone step of generating keys on each side independently. Keys can also be generated manually with openssl:

```bash
# RSA 4096-bit key pair (repeat for inputs and outputs)
openssl genrsa -out rsa_private.pem 4096
openssl rsa -in rsa_private.pem -pubout -out rsa_public.pem

# ECDSA SECP256R1 key pair (repeat for inputs and outputs)
openssl ecparam -genkey -name prime256v1 -noout -out ecdsa_private.pem
openssl ec -in ecdsa_private.pem -pubout -out ecdsa_public.pem
```

The resulting PEM strings are set as environment variables on the appropriate side — four keys per role (node and producer).

Encryption is opt-in. If the relevant keys are absent, the corresponding path is skipped and the field stays plaintext, which is the backward-compatible default.
