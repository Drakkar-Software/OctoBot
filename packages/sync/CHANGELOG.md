# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- [Mirror] Event-triggered node-side cloud mirror (DRAFT). `MirrorService` keeps one
  `ChannelScheduler` per wallet and one `SpaceMirrorChannel` per collection, so a local write
  re-mirrors only the collection that changed. One channel per collection is what makes that
  safe: `plan_space_mirror` filters existing nodes by the channel's own registry, so a
  single-collection channel structurally cannot clear its siblings.
- [Mirror] Trigger hook on `AbstractLocalCollectionProvider._notify_mirror_changed`, called from
  `BaseLocalCollectionProvider._save_state` and `SingleItemLocalCollectionProvider.save_state` —
  fire-and-forget and never raising, so a mirror failure cannot fail the local write.

### Changed
- [Mirror] One `octobot-mirror` space per wallet instead of three; `visibility` now selects a
  storage tier (`shared` -> isolated/`objinv`, `private` -> space keyring/`objdoc`, `public` ->
  `objpub`) rather than a space. `mirrordoc_path` takes the collection id first and finally
  routes the public tier, which it previously did not.
- [Mirror] Requires `starfish-replica[space]` (full install only — it transitively pulls
  `starfish-server`). starfish pins bumped to 3.0.0a72.

### Removed
- [Mirror] The hand-rolled writer (`sync_cloud_mirror` and its space/node/CAS mechanics) and
  `plan.py`, both superseded by `starfish_replica.space`'s channel. Neither had any caller.

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
