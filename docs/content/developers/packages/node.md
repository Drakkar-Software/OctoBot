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

**Key split between server and browser.** Keys are divided strictly by who needs them at runtime. The server holds the four INPUTS keys — used to decrypt incoming task content and verify its signature before execution, and to re-sign and re-encrypt results before storage. These are the only keys the node process ever loads, set via four environment variables (`TASKS_INPUTS_RSA_PRIVATE_KEY`, `TASKS_INPUTS_ECDSA_PUBLIC_KEY`, `TASKS_INPUTS_RSA_PUBLIC_KEY`, `TASKS_INPUTS_ECDSA_PRIVATE_KEY`). The four OUTPUTS keys — used to decrypt results produced by the node — are never loaded by the server. They exist only in the browser, entered once in the Settings page and stored locally. A node process running with only the four INPUTS keys in its environment is fully functional; the OUTPUTS keys have no server-side role.

**Metadata format asymmetry.** The accompanying metadata envelope — which carries `ENCRYPTED_AES_KEY_B64`, `IV_B64`, and `SIGNATURE_B64` — is serialised differently depending on direction. For task inputs, `encrypt_task_content` returns the metadata as `base64(JSON)`: the JSON object is first serialised to a string, then base64-encoded again. The corresponding `decrypt_task_content` therefore base64-decodes then JSON-parses. For task outputs, `encrypt_task_result` returns the metadata as a plain JSON string with no outer base64 layer, and `decrypt_task_result` JSON-parses directly. The asymmetry exists because input metadata is transmitted as a CSV or API field where a single opaque string is easier to embed without escaping, while output metadata is stored in the database and consumed programmatically by code that already handles JSON. Being aware of this distinction matters when building a producer or any tooling that reads raw database records.

**`encrypted_task` context manager.** This wraps each task execution transparently. On entry it decrypts `task.content` if the input keys are present and `task.content_metadata` is non-null. On exit it encrypts `task.result` if the output keys are present. The two directions are independent — a node can be configured to decrypt inputs only, encrypt outputs only, or both. If decryption fails, the context manager does not propagate the exception into the workflow; instead it writes a structured error dict to `task.result`, so the failure is observable via the API without crashing the scheduler.

**Security boundary with `octobot_flow`.** The `encrypted_task` context manager wraps the call to `octobot_flow`'s `AutomationJob.run()` inside the node's workflow step. This means the scheduler — the master node that stores and routes tasks — only ever sees encrypted payloads. Task content is decrypted just before execution on the consumer node that holds the private keys, and the result is re-encrypted immediately after. The scheduler database, its API, and any intermediary never handle plaintext. A compromised scheduler leaks only ciphertext. From flow's perspective, nothing changes — it receives a plaintext `AutomationState` dict and returns an updated one. The flow package has no awareness of encryption, which means the same engine works identically in encrypted node deployments, unencrypted nodes, and standalone bots.

**Key loading and validation.** The four INPUTS keys are accepted as PEM-encoded strings via environment variables, decoded to `bytes` at process startup by a `BeforeValidator` in the pydantic `Settings` model. There is no lazy loading — `settings` is a module-level singleton instantiated at import time, so a misconfigured key value fails fast before any requests are served. The `is_node_side_encryption_enabled` computed property checks whether all four INPUTS keys are present simultaneously, and `tasks_encryption_enabled` is an alias for it — enabling clean conditional logic throughout the codebase without repeating null checks.

**Browser key storage.** The OUTPUTS keys entered in the browser Settings page, and the login passphrase, are both stored in `IndexedDB` encrypted with a device-bound, non-extractable AES-256-GCM key. That device key is generated on first login using `crypto.subtle.generateKey` with `extractable: false`, stored in the same `IndexedDB` database, and can be used by the browser but never exported or read as raw bytes — not even from a filesystem dump of the database file. The device key is origin-bound, so it cannot be used from another domain or browser profile. Neither the passphrase nor the OUTPUTS keys are ever stored in `localStorage` or sent to the server.

**Key generation.** For a fresh deployment, `generate_and_save_keys` creates all four key pairs at once — two 4096-bit RSA pairs (one for inputs, one for outputs) and two ECDSA pairs on the SECP256R1 curve — and writes them to a single `task_encryption_keys.json` file. From that file, the server operator copies the four INPUTS keys into the node's environment variables, and enters the four OUTPUTS keys into the browser Settings page. Keys can also be generated manually with openssl:

```bash
# RSA 4096-bit key pair (repeat for inputs and outputs)
openssl genrsa -out rsa_private.pem 4096
openssl rsa -in rsa_private.pem -pubout -out rsa_public.pem

# ECDSA SECP256R1 key pair (repeat for inputs and outputs)
openssl ecparam -genkey -name prime256v1 -noout -out ecdsa_private.pem
openssl ec -in ecdsa_private.pem -pubout -out ecdsa_public.pem
```

The four INPUTS PEM strings go into the node's `.env` file. The four OUTPUTS PEM strings are entered in the browser Settings page and stored locally — they are never sent to the server.

Encryption is opt-in. If the INPUTS keys are absent from the environment, the corresponding path is skipped and the field stays plaintext, which is the backward-compatible default.
