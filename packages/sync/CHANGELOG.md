# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-20
### Added
- [Collections] `product-profiles` collection with JSON Schema validation (name, description, website, twitter, tags)
- [Collections] `product-logos` binary collection with MIME type validation (PNG, JPEG, GIF, WebP)
- [Collections] `product-versions` collection with JSON Schema validation for version documents
- [Signals] `member` role for signal reads — public products allow all authenticated users, private products require on-chain `has_access`
- [RoleEnricher] Assign `member` role via on-chain `has_access` check (owner gets both `owner` and `member`)
- [NginxConf] Escape regex metacharacters in storage paths to prevent nginx config injection
- [NginxConf] Validate collection names (alphanumeric, hyphens, underscores only)
- [NginxConf] Reject zero/negative rate limit values
- [Security] Auth failure logging via `octobot_sync.security` logger
### Changed
- [Constants] Reduce auth timestamp window from 30s to 10s
### Removed
- [Routes] Remove manual product routes (GET/PUT) — replaced by declarative Starfish collections
- [Routes] Remove unused `/verify` endpoint (auth handled by starfish role_resolver)
- [App] Remove `app.state` dependencies (object_store, registry, platform_pubkey) — all handled by Starfish router
