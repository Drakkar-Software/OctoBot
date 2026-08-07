/** Substitutes `{key}` placeholders in a storage-path template, e.g.
 *  `resolveStoragePath('users/{identity}/accounts', { identity: userId })`.
 *  Generic — carries no product knowledge of which collections exist. */
export function resolveStoragePath(storagePath: string, params: Record<string, string>): string {
  return Object.entries(params).reduce(
    (path, [key, value]) => path.replaceAll(`{${key}}`, encodeURIComponent(value)),
    storagePath,
  )
}

export function pullPath(storagePath: string, params: Record<string, string>): string {
  return `/pull/${resolveStoragePath(storagePath, params)}`
}

export function pushPath(storagePath: string, params: Record<string, string>): string {
  return `/push/${resolveStoragePath(storagePath, params)}`
}
