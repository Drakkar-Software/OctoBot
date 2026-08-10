import { describe, it, expect } from 'vitest'
import { StarfishHttpError, ConflictError } from '@drakkar.software/starfish-client'
import { NodeHttpError } from '../src/transport/rest.js'
import {
  OctoBotError,
  OctoBotConfigError,
  OctoBotConnectionError,
  OctoBotAuthError,
  OctoBotHttpError,
  OctoBotConflictError,
  OctoBotActionError,
  OctoBotTimeoutError,
  OctoBotScopeError,
  isOctoBotError,
  toOctoBotError,
} from '../src/client/core/errors.js'

describe('every OctoBotError subclass sets the .code the docs tell callers to switch on', () => {
  const cases: [Error, string][] = [
    [new OctoBotConfigError('bad config'), 'config'],
    [new OctoBotConnectionError('unreachable', 'x'), 'unreachable'],
    [new OctoBotConnectionError('timeout', 'x'), 'timeout'],
    [new OctoBotConnectionError('aborted', 'x'), 'aborted'],
    [new OctoBotAuthError('0x' + '11'.repeat(20), 'user1', 'bip44'), 'unauthorized'],
    [new OctoBotHttpError(503), 'http'],
    [new OctoBotConflictError(null), 'conflict'],
    [new OctoBotActionError('detail'), 'action_failed'],
    [new OctoBotTimeoutError(), 'action_timeout'],
    [new OctoBotScopeError('settings'), 'forbidden_collection'],
  ]

  it.each(cases)('%s carries the documented .code', (err, code) => {
    expect((err as OctoBotError).code).toBe(code)
    expect(isOctoBotError(err)).toBe(true)
  })

  it('isOctoBotError is false for a plain Error and for an AbortError DOMException', () => {
    expect(isOctoBotError(new Error('nope'))).toBe(false)
    expect(isOctoBotError(new DOMException('aborted', 'AbortError'))).toBe(false)
  })
})

describe('toOctoBotError maps every real underlying error into the public hierarchy', () => {
  it('a 401/403 StarfishHttpError maps to code "unauthorized"', () => {
    expect(toOctoBotError(new StarfishHttpError(401, 'no')).code).toBe('unauthorized')
    expect(toOctoBotError(new StarfishHttpError(403, 'no')).code).toBe('unauthorized')
  })

  it('a 500 StarfishHttpError maps to code "http"', () => {
    expect(toOctoBotError(new StarfishHttpError(500, 'no')).code).toBe('http')
  })

  it('a NodeHttpError maps to OctoBotHttpError with the real status', () => {
    const mapped = toOctoBotError(new NodeHttpError(503))
    expect(mapped).toBeInstanceOf(OctoBotHttpError)
    expect((mapped as OctoBotHttpError).status).toBe(503)
  })

  it('REGRESSION: a ConflictError maps to OctoBotConflictError carrying the REAL currentHash, not always null', () => {
    const mapped = toOctoBotError(new ConflictError('hash-42'))
    expect(mapped).toBeInstanceOf(OctoBotConflictError)
    expect((mapped as OctoBotConflictError).serverHash).toBe('hash-42')
  })

  it('a ConflictError with no hash (server could not read it) maps to serverHash: null, not empty string', () => {
    const mapped = toOctoBotError(new ConflictError())
    expect((mapped as OctoBotConflictError).serverHash).toBeNull()
  })

  it('REGRESSION: an unrecognized error maps to a real OctoBotConnectionError instance, not a base OctoBotError', () => {
    const mapped = toOctoBotError(new Error('fetch failed'))
    expect(mapped.code).toBe('unreachable')
    expect(mapped).toBeInstanceOf(OctoBotConnectionError)
  })

  it('an already-typed OctoBotError passes through unchanged', () => {
    const original = new OctoBotScopeError('accounts')
    expect(toOctoBotError(original)).toBe(original)
  })
})
