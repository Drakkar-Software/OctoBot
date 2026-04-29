---
title: Trading Backend
description: Exchange backend layer handling broker identification, API key permission checks, and account validation across 20+ supported exchanges.
sidebar_position: 1
---

# Trading Backend

`trading_backend` is the exchange-facing validation layer that runs before any trading begins. Its job is to inspect API key permissions and account state so the rest of the system can trust that the credentials it has are actually capable of the operations it intends to perform.

## Structure

`Exchange` is the base class. Each supported exchange has a subclass that overrides only what differs from the default behaviour — most overrides are small: a different permissions endpoint URL, a different error code to interpret, or broker-tagging logic specific to that venue. A factory selects the right subclass at runtime using the ccxt exchange `id`. Unrecognised exchanges fall back to the base class, which covers the common case well enough.

## Permission detection

Two strategies exist for detecting what an API key is allowed to do. Exchanges that expose a dedicated permissions endpoint are queried directly. For exchanges that don't, the package uses a cancellation probe: it attempts to cancel a non-existent order and interprets the error response. A permission error means the key is read-only; an order-not-found error means trading rights are present; a nonce error signals clock drift between the client and exchange server.

If withdrawal rights are detected and `ALLOW_WITHDRAWAL_KEYS` is not explicitly enabled, the key is rejected before trading starts. This is a safety default — keys that can withdraw funds carry more risk than keys that can only trade, and most automated strategies have no reason to withdraw.
