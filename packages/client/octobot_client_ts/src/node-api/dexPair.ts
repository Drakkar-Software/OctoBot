/** Reference-price-only exchange (no traded-pairs list) supported today.
 *  A future second source becomes a small ordered list, mirroring `PAIR_SOURCES`
 *  in `pairs.ts` — not needed yet for exactly one. */
export const DEX_REFERENCE_EXCHANGE_ID = 'dexscreener'

export const DEX_PAIR_EXAMPLE = 'WETH/USDT@BASE!PANCAKESWAP'
export const DEX_PAIR_FORMAT = 'BASE/QUOTE@NETWORK!DEX'

// Dexscreener pair identifier: base/quote@network required, !dex optional.
// Segments accept tickers and contract addresses (no whitespace, '/', '@' or '!').
export const DEX_PAIR_REGEX =
  /^([^\s/@!]+)\/([^\s/@!]+)@([^\s/@!]+)(?:!([^\s/@!]+))?$/

export type ParsedDexPair = {
  base: string
  quote: string
  network: string
  dex?: string
}

export function parseDexPair(raw: string): ParsedDexPair | undefined {
  const match = DEX_PAIR_REGEX.exec(raw.trim())
  if (!match) {
    return undefined
  }
  const [, base, quote, network, dex] = match
  return { base, quote, network, dex }
}

export function isValidDexPair(raw: string): boolean {
  return parseDexPair(raw) != undefined
}

// Lenient split used for live previews while the user is typing: segments may
// be empty or invalid, validity is reported per segment.
export type DexPairSegments = {
  pair: string
  network: string
  dex: string
}

const PAIR_SEGMENT_REGEX = /^[^\s/@!]+\/[^\s/@!]+$/
const NAME_SEGMENT_REGEX = /^[^\s/@!]+$/

export function splitDexPairSegments(raw: string): DexPairSegments {
  const trimmed = raw.trim()
  const atIndex = trimmed.indexOf('@')
  const pair = atIndex >= 0 ? trimmed.slice(0, atIndex) : trimmed
  const rest = atIndex >= 0 ? trimmed.slice(atIndex + 1) : ''
  const bangIndex = rest.indexOf('!')
  const network = bangIndex >= 0 ? rest.slice(0, bangIndex) : rest
  const dex = bangIndex >= 0 ? rest.slice(bangIndex + 1) : ''
  return { pair, network, dex }
}

export function isValidDexPairSegment(segment: string): boolean {
  return PAIR_SEGMENT_REGEX.test(segment)
}

export function isValidDexNameSegment(segment: string): boolean {
  return NAME_SEGMENT_REGEX.test(segment)
}
