---
title: "Accounts"
description: "The protocol account graph (Account, AccountAuthentication, ExchangeConfig), create/update emit ordering, account kinds, and holdings."
sidebar_position: 5
---

# Accounts

Every write below returns an `ActionHandle`, not an immediate result — see [User actions](user-actions.md)
if you haven't read it yet.

## The protocol-0.4.0 account graph

An account is not one object on the wire — it's three, linked by derived ids:

```
Account { authentication_id → AccountAuthentication.id
          specifics.exchange_config_ids[0] → ExchangeConfig.id }
```

- `AccountAuthentication` carries credentials (`api_key`/`api_secret` for an exchange, `public_key`
  for a wallet address). Id: `auth_{accountId}`.
- `ExchangeConfig` carries the venue (`exchange`, `sandboxed`). Id: `cfg_{accountId}`. Exchange
  accounts only.
- `Account` itself carries display fields and asset quantities, and references the other two.

The ids are **derived** (`auth_` / `cfg_` + the account id), not stored separately, so a client can
always reconstruct them from the account id alone — see `protocol/actions.ts::accountAuthIdFor` /
`exchangeConfigIdFor` and their inverses.

**The node does not cascade deletes.** `client.accounts.delete(id)` emits `account_delete` plus
the two companion deletes itself — a raw `account_delete` alone leaves orphaned auth/config items.

## `client.accounts.create()`

```ts
const action = await octobot.accounts.create({
  name: 'Binance', type: 'exchange', exchange: 'binance',
  credentials: { apiKey, apiSecret },
})
const account = await action.settled()
```

Emits, in order: `account_auth_create`, `exchange_config_create`, `account_create`. Three actions,
one `ActionHandle` — `settled()` resolves once the node confirms all three (in practice, the last one
appended, `account_create`, since it references the other two and the node applies them in order).

## `client.accounts.update()`

Emits credential/exchange-config edits **before** the account edit: `account_auth_edit`,
`exchange_config_edit` (exchange accounts only), then `account_edit`. This ordering matters — the
node's account re-validation on `account_edit` reads whatever credentials/exchange config are
current at that point, so rotating them first means the account edit is validated against the *new*
keys, not the ones about to be replaced. `update()` also preserves the account's original
`created_at` by pulling the existing record before building the edit — it does not re-stamp it to
the current time.

## Kinds

| `AccountInput.type` | Node `specifics.account_type` | Notes |
|---|---|---|
| `'exchange'` | `'exchange'` | Real credentials, a real venue. |
| `'wallet'` | `'generic'` | The node's `'blockchain'` account type isn't supported yet — wallets ride as generic with the address in `AccountAuthentication.public_key`. |
| `'generic'` | `'generic'` | No credentials — a manually-tracked balance. |

## Holdings

`AccountView.holdings` carries quantities only (`symbol`/`total`/`free`/`used`) — no fiat valuation.
The node's `DetailedAsset` schema has no per-asset value field; pricing holdings against a quote
currency is presentation logic that belongs one layer up, not in this package.
