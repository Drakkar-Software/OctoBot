import type { UserActionConfiguration } from '@drakkar.software/octobot-protocol'

/** Best-effort human label for one proposed action, when the proposal itself
 *  carries no overall `label` — derived generically from `action_type` (and,
 *  when present, the nested config's `name`) rather than special-cased per
 *  kind, so a future action type is still legible instead of blank.
 *
 *  `action_type` is a non-optional discriminant string literal on every one
 *  of `UserActionConfiguration`'s 18 members (see
 *  `@drakkar.software/octobot-protocol`'s own `discriminator` on the type),
 *  so it needs no cast to READ — the `?? 'action'` below is deliberate
 *  runtime defensiveness against a malformed/incomplete wire payload the
 *  type system can't actually guarantee against, not a type-driven need.
 *  `configuration` (the nested config) is NOT present on every member (e.g.
 *  `RefreshAccountsConfiguration` has none) and its shape varies across the
 *  members that do have one — narrowed with `in` checks rather than a blind
 *  cast, so a genuinely absent/differently-shaped field falls back to no
 *  name instead of silently reading `undefined` through an assumed shape.
 *
 *  Shared across every proposal consumer — mobile2's scan/confirm screen and
 *  the node web interface's paste dialog both render the same wording for
 *  the same entry, since this is the only place that decides it. */
export function describeProposedAction(configuration: UserActionConfiguration): string {
  const actionType = configuration.action_type ?? 'action'
  const label = actionType.replace(/_/g, ' ')
  const inner = 'configuration' in configuration ? configuration.configuration : undefined
  const name = inner != null && typeof inner === 'object' && 'name' in inner ? inner.name : undefined
  return typeof name === 'string' ? `${label} — "${name}"` : label
}
