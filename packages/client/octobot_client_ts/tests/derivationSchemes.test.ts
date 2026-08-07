import { describe, it, expect } from 'vitest'
import {
  getDerivationScheme,
  registerDerivationScheme,
  listDerivationSchemeIds,
  DEFAULT_DERIVATION_SCHEME_ID,
} from '../src/identity/derivationSchemes.js'

describe('derivationSchemes registry', () => {
  it('ships bip44 as the only built-in scheme, and the default', () => {
    expect(listDerivationSchemeIds()).toEqual(['bip44'])
    expect(DEFAULT_DERIVATION_SCHEME_ID).toBe('bip44')
  })

  it('throws a clear error for an unknown id, rather than silently deriving under the wrong scheme', () => {
    expect(() => getDerivationScheme('not-a-real-scheme')).toThrow(/unknown derivation scheme/)
  })

  it('lets a caller register a new scheme for a future wallet type', async () => {
    const derive = async (x: string) => `derived:${x}`
    registerDerivationScheme({ id: 'test-scheme', derive })
    expect(listDerivationSchemeIds()).toContain('test-scheme')
    expect(await getDerivationScheme('test-scheme').derive('phrase')).toBe('derived:phrase')
  })

  it('refuses to silently replace an already-registered scheme id', () => {
    const derive = async (x: string) => x
    registerDerivationScheme({ id: 'no-clobber', derive })
    expect(() => registerDerivationScheme({ id: 'no-clobber', derive })).toThrow(/already registered/)
  })
})
