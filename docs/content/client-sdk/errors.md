---
title: "Errors"
description: "The full OctoBotError taxonomy — every class, its .code, its extra fields, and when it throws — plus handling patterns: switching on .code across package boundaries and AbortError passthrough."
sidebar_position: 4
mdx:
  format: mdx
---

import DemoEmbed from '@site/src/components/demo/Embed';

# Errors

Nine ways a call into this SDK can end badly — eight typed `OctoBotError` subclasses, plus one you
have to catch yourself. Every method throws one of the eight (or lets an `AbortError` `DOMException`
through unwrapped, per the platform convention).

<DemoEmbed section="errors" />

## The taxonomy

| Class | `code` | Extra fields | When |
|---|---|---|---|
| `OctoBotConfigError` | `'config'` | — | Bad `ConnectOptions` — an unparseable `url`, or a `client.node.*` call made without `basicAuth`. |
| `OctoBotConnectionError` | `'unreachable'` \| `'timeout'` \| `'aborted'` | — | The node could not be reached at all — offline, wrong port, the connect-time budget expired, or the caller's own `AbortSignal` fired during connect. |
| `OctoBotAuthError` | `'unauthorized'` | `.address` `.userId` `.derivation` | The node answered but didn't authorize this wallet — the fields name exactly what was tried. |
| `OctoBotHttpError` | `'http'` | `.status` | A `client.node.*` REST call answered non-2xx. |
| `OctoBotConflictError` | `'conflict'` | `.serverHash` | A document push raced another writer — the `baseHash` you pushed against is no longer current. `.serverHash` carries the node's current hash so you can pull-and-retry without a round trip. |
| `OctoBotActionError` | `'action_failed'` | `.detail` `.phase` | The node executed a queued action and rejected it. Not retriable by resubmitting unchanged. |
| `OctoBotTimeoutError` | `'action_timeout'` | `.phase` | `ActionHandle.settled()` gave up waiting — the action may still complete. |
| `OctoBotScopeError` | `'forbidden_collection'` | `.collection` | A read-only session reached a collection its pairing grant doesn't cover — thrown client-side, before any network request. See [Read-only devices](read-only-pairing.md). |
| `AbortError` (`DOMException`) | — not an `OctoBotError` | — | A caller's own `AbortSignal` fired. Passed through unwrapped, matching how `fetch` itself behaves — `isOctoBotError()` on it is `false`. |

## Switch on `.code`, not `instanceof`, across package boundaries

```ts
import { isOctoBotError } from '@drakkar.software/octobot-client'

try {
  await octobot.accounts.create(input)
} catch (err) {
  if (isOctoBotError(err)) {
    switch (err.code) {
      case 'unauthorized':
        // re-derive with a different seedDerivation
        break
      case 'conflict':
        // pull again, retry the write
        break
      default:
        console.error(err.code, err.message)
    }
  } else {
    throw err // an AbortError, or something outside this package entirely
  }
}
```

`instanceof OctoBotError` works fine within a single install of this package. It can silently fail
across a duplicated package instance (a monorepo hoisting quirk, a bundler that doesn't dedupe) —
`.code` is a plain string and survives that.

## `AbortError` is not wrapped

Every method that accepts `{ signal }` lets an aborted call's `DOMException` (`name === 'AbortError'`)
through unwrapped, matching how `fetch` itself behaves. Check for it separately if you care:

```ts
catch (err) {
  if (err instanceof DOMException && err.name === 'AbortError') return // cancelled, not a failure
  throw err
}
```

## `OctoBotActionError` vs `OctoBotTimeoutError`

These only come from `ActionHandle.settled()` (or the underlying two-phase automation orchestration
— see [User actions](user-actions.md)). `OctoBotActionError` means the node executed the action and
rejected it — resubmitting the same configuration will fail the same way. `OctoBotTimeoutError`
means the node never confirmed within the timeout budget; the action may still be pending or
running, so a fresh `settled()`-driving call (not a resubmit) is the right retry.
