import { describe, it, expect } from 'vitest'
import { classifyScannedCode } from '../src/node-api/wallet.js'
import { createReadOnlyPairing } from '../src/identity/pairing.js'
import { encodeActionProposal } from '../src/protocol/proposal.js'
import { buildStopAutomationConfig } from '../src/protocol/actions.js'

// BIP39 test vectors — real checksums, so validateSeedPhrase accepts them.
const SEED_12 = 'legal winner thank year wave sausage worth useful legal winner thank yellow'
const SEED_24 =
  'legal winner thank year wave sausage worth useful legal winner thank year ' +
  'wave sausage worth useful legal winner thank year wave sausage worth title'
const KEY = '0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318'

describe('classifyScannedCode', () => {
  it('reads a node pairing payload', async () => {
    const data = JSON.stringify({ url: 'http://10.0.0.4:5001', address: '0xabc', password: SEED_12 })
    expect(await classifyScannedCode(data)).toEqual({
      kind: 'node',
      payload: {
        url: 'http://10.0.0.4:5001',
        address: '0xabc',
        secret: SEED_12,
        secretKind: 'wallet',
      },
    })
  })

  it('keeps a pairing payload a pairing payload, envelope reader notwithstanding', async () => {
    // Both shapes now use `password`; only the pairing one has url + address,
    // and it has to win, or scanning a node would stop adding the node.
    const data = JSON.stringify({ url: 'http://10.0.0.4:5001', address: '0xabc', password: KEY })
    expect((await classifyScannedCode(data)).kind).toBe('node')
  })

  it('reads a read-only pairing payload', async () => {
    const { payload } = await createReadOnlyPairing(SEED_12, 'bip44', { host: '10.0.0.4', port: 5001 })
    const result = await classifyScannedCode(payload)
    expect(result.kind).toBe('octobotReadOnlyPairing')
    if (result.kind === 'octobotReadOnlyPairing') {
      expect(result.payload.scope.ops).not.toContain('write')
    }
  })

  it('reads an action proposal payload', async () => {
    const payload = encodeActionProposal([{ configuration: buildStopAutomationConfig('auto_1') }])
    const result = await classifyScannedCode(payload)
    expect(result.kind).toBe('octobotActionProposal')
    if (result.kind === 'octobotActionProposal') {
      expect(result.payload.actions).toHaveLength(1)
    }
  })

  it('reads a 0x-prefixed private key', async () => {
    expect(await classifyScannedCode(KEY)).toEqual({ kind: 'privateKey', value: KEY })
  })

  it('normalizes a bare-hex private key to 0x form', async () => {
    expect(await classifyScannedCode(` ${KEY.slice(2).toUpperCase()} `))
      .toEqual({ kind: 'privateKey', value: KEY })
  })

  it('reads a 12-word phrase', async () => {
    expect(await classifyScannedCode(SEED_12)).toEqual({ kind: 'seed', value: SEED_12 })
  })

  it('reads a 24-word phrase', async () => {
    expect(await classifyScannedCode(SEED_24)).toEqual({ kind: 'seed', value: SEED_24 })
  })

  it('lowercases and collapses whitespace in a phrase', async () => {
    expect(await classifyScannedCode(`  LEGAL   winner\nthank ${SEED_12.split(' ').slice(3).join(' ')}  `))
      .toEqual({ kind: 'seed', value: SEED_12 })
  })

  it('rejects a phrase whose checksum does not hold', async () => {
    const broken = SEED_12.replace('yellow', 'zoo')
    expect(await classifyScannedCode(broken)).toEqual({ kind: 'unknown' })
  })

  it('rejects a wrong-length word list', async () => {
    expect(await classifyScannedCode('legal winner thank')).toEqual({ kind: 'unknown' })
  })

  it('rejects hex of the wrong width', async () => {
    expect(await classifyScannedCode('0xdeadbeef')).toEqual({ kind: 'unknown' })
  })

  it('rejects JSON that is not a pairing payload', async () => {
    expect(await classifyScannedCode('{"url":"http://x"}')).toEqual({ kind: 'unknown' })
  })

  describe('standalone secret envelope', () => {
    const envelope = (password: unknown) => JSON.stringify({ password })

    it('reads a 0x private key', async () => {
      expect(await classifyScannedCode(envelope(KEY))).toEqual({ kind: 'privateKey', value: KEY })
    })

    it('reads a seed phrase', async () => {
      expect(await classifyScannedCode(envelope(SEED_12))).toEqual({ kind: 'seed', value: SEED_12 })
    })

    it('lowercases and collapses whitespace in a phrase, as the bare path does', async () => {
      const messy = `  LEGAL   winner\nthank ${SEED_12.split(' ').slice(3).join(' ')}  `
      expect(await classifyScannedCode(envelope(messy))).toEqual({ kind: 'seed', value: SEED_12 })
    })

    it('rejects a 0x value that is not a usable key', async () => {
      expect(await classifyScannedCode(envelope('0xdeadbeef'))).toEqual({ kind: 'unknown' })
    })

    it('rejects a phrase whose checksum does not hold', async () => {
      expect(await classifyScannedCode(envelope(SEED_12.replace('yellow', 'zoo'))))
        .toEqual({ kind: 'unknown' })
    })

    it('rejects a node login password, which is not key material', async () => {
      expect(await classifyScannedCode(envelope('hunter2'))).toEqual({ kind: 'unknown' })
    })

    it('rejects a non-string value', async () => {
      expect(await classifyScannedCode(envelope(42))).toEqual({ kind: 'unknown' })
    })

    it('ignores a private_key field — only password is read', async () => {
      expect(await classifyScannedCode(JSON.stringify({ private_key: KEY }))).toEqual({ kind: 'unknown' })
    })

    it('does not apply the 0x rule to a bare code', async () => {
      // A bare scan has no field name to go on, so both formats are still tried
      // and unprefixed hex keeps working.
      expect(await classifyScannedCode(KEY.slice(2))).toEqual({ kind: 'privateKey', value: KEY })
      expect(await classifyScannedCode(envelope(KEY.slice(2)))).toEqual({ kind: 'unknown' })
    })
  })

  it('rejects an empty code', async () => {
    expect(await classifyScannedCode('   ')).toEqual({ kind: 'unknown' })
  })
})
