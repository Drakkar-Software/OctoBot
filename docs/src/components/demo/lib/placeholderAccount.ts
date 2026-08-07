export const PLACEHOLDER_ACCOUNT_ID = "demo-account"

/** Whether `automations.create()` genuinely used the placeholder accountId
 *  because this node really has zero accounts — not because
 *  `accounts.list()` never ran, or ran and failed. A failed list (e.g. this
 *  wallet isn't authorized on this node at all) also leaves `accounts` null,
 *  which used to look identical to "a real node with zero accounts" here —
 *  the regression this guards against. `accountId` alone already implies
 *  "no accounts to pick from"; this only adds "and that's because the list
 *  call actually succeeded", not because it never ran or failed. */
export function usedGenuinePlaceholder(opts: {
  accountId: string
  listSucceeded: boolean
}): boolean {
  return opts.accountId === PLACEHOLDER_ACCOUNT_ID && opts.listSucceeded
}

/** Whether the "expected: the node validated the queued action and
 *  correctly rejected the placeholder" copy is honest to show. Even when the
 *  placeholder really was used, `automations.create()` can still fail for a
 *  reason that has nothing to do with the placeholder — most notably an
 *  `unauthorized` 403 from a key that was never authorized on this node at
 *  all, which is exactly the bug that shipped this copy under the wrong
 *  error. Only `action_failed` (`OctoBotActionError` — the node genuinely
 *  validated the queued action and rejected it) makes the "expected" framing
 *  true. */
export function isExpectedPlaceholderRejection(opts: {
  usedPlaceholder: boolean
  errorCode: string | undefined
}): boolean {
  return opts.usedPlaceholder && opts.errorCode === "action_failed"
}
