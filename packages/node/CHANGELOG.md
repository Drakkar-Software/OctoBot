# Changelog
All notable changes to this project will be documented in this file.

## [0.0.5] - 2026-01-09
### Added
- `TaskResultKeys` enum to standardize task result dictionary keys (`status`, `task`, `result`, `error`, `metadata`)
- `get_task_name()` method in scheduler to extract task names from task data structures
- Metadata column support in CSV task imports for encrypted task metadata
- `parse_key_to_bytes()` utility function for automatic encryption key format conversion
- `EncryptedTask` context manager in `task_context.py` for automatic task content decryption and result encryption
- `content_metadata` field to Task model for storing encrypted content metadata separately
- `result` and `result_metadata` fields to Task model for storing encrypted task results and their metadata
- `METADATA` key to `TaskResultKeys` enum for standardized metadata handling in task results

### Changed
- Task names now display actual task names instead of task IDs in the UI and API responses
- Scheduled task descriptions now show ETA timestamp (e.g., "Scheduled at 2026-01-09 10:30:00") instead of generic "Scheduled task" messages
- Encryption key configuration now accepts both string and bytes formats (automatic conversion via `BeforeValidator`)
- Encryption metadata now uses base64 encoding/decoding for improved compatibility
- Task result dictionaries now use standardized `TaskResultKeys` enum values instead of hardcoded strings
- Logging messages now use task names instead of task IDs for better readability
- Task result dictionaries now include task name in the `task` field for better traceability
- Task execution now uses `EncryptedTask` context manager for automatic encryption/decryption handling
- Task functions now set `task.result` directly instead of returning encrypted result dictionaries
- Task result dictionaries now use `TaskStatus.COMPLETED` enum value instead of hardcoded "done" string
- Task result dictionaries now include `metadata` field for encrypted result metadata
- Task model `metadata` field renamed to `content_metadata` for clarity (input metadata vs result metadata)

## [0.0.4] - 2026-01-09
### Added
- Task encryption and decryption functionality for task inputs and outputs
- Hybrid encryption module using RSA (4096-bit), AES-GCM (256-bit), and ECDSA signatures (SECP256R1)
- `encrypt_task_content()` and `decrypt_task_content()` functions for encrypting/decrypting task inputs
- `encrypt_task_result()` and `decrypt_task_result()` functions for encrypting/decrypting task outputs
- Automatic task content decryption during task execution when encryption keys are configured
- CSV encryption utilities for task imports (`encrypt_csv_content`, `decrypt_csv_content`, `merge_and_encrypt_csv`)
- Key generation and management utilities for encryption keys
- Encryption key configuration via environment variables:
  - `TASKS_INPUTS_RSA_PUBLIC_KEY` and `TASKS_INPUTS_RSA_PRIVATE_KEY`
  - `TASKS_INPUTS_ECDSA_PUBLIC_KEY` and `TASKS_INPUTS_ECDSA_PRIVATE_KEY`
  - `TASKS_OUTPUTS_RSA_PUBLIC_KEY` and `TASKS_OUTPUTS_RSA_PRIVATE_KEY`
  - `TASKS_OUTPUTS_ECDSA_PUBLIC_KEY` and `TASKS_OUTPUTS_ECDSA_PRIVATE_KEY`
- Custom exception classes for encryption errors: `EncryptionTaskError`, `MissingMetadataError`, `MetadataParsingError`, `SignatureVerificationError`
- Comprehensive encryption module documentation (README.md)

### Changed
- Task execution now automatically decrypts task content if encryption keys are configured
- Tasks operate in plaintext mode when encryption keys are not set (backward compatible)

## [0.0.3] - 2026-01-08
### Added
- `--master` CLI flag to enable master node mode (schedules tasks)
- `--consumers N` CLI flag to configure number of consumer worker threads (0 disables consumers)
- `--environment {local,production}` CLI flag to set environment mode
- `--admin-username` and `--admin-password` CLI flags to set admin credentials
- `--verbose` CLI flag to enable verbose logging with HTTP access logs
- Support for nodes to operate as both master and consumer simultaneously
- Automatic auto-reload when environment is set to "local"

### Changed
- Replaced `--workers` and `--reload` CLI flags with new `--master` and `--consumers` flags
- Replaced `SCHEDULER_NODE_TYPE` configuration with `IS_MASTER_MODE` boolean flag
- Default `SCHEDULER_WORKERS` changed from 4 to 0 (consumers disabled by default)
- Default `ENVIRONMENT` changed from "local" to "production"
- Removed "staging" from environment options (now only "local" and "production")
- Default host binding: 127.0.0.1 for non-master nodes, 0.0.0.0 for master nodes in production
- FastAPI server now always runs with a single worker (consumer workers are separate)
- Admin credentials validation now only required when master mode is enabled
- Task list API endpoint now returns raw task data instead of Task model instances
- Node status API now returns node_type as "master", "consumer", "both", or "none"
- Redis connection now uses `decode_responses=False` for better compatibility
- Improved logging messages and error handling throughout scheduler components

### Fixed
- Fixed Redis decode_responses configuration for better compatibility
- Fixed task parsing error messages formatting

## [0.0.2] - 2026-01-07
### Added
- Default values for admin credentials (`ADMIN_USERNAME` and `ADMIN_PASSWORD`) to simplify local setup
- Default admin username: `admin@example.com`
- Default admin password: `changethis`

### Changed
- Renamed `FIRST_SUPERUSER` environment variable to `ADMIN_USERNAME`
- Renamed `FIRST_SUPERUSER_PASSWORD` environment variable to `ADMIN_PASSWORD`
- Admin credentials now have default values (previously required to be set)
- Validation warnings now use logging instead of Python warnings module
- Updated `.env.sample` and `.env.test` files to use new variable names

## [0.0.1] - 2026-01-07
### Added
- OctoBot Node alpha version
