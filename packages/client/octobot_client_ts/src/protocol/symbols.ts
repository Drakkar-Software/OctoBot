/** Base currency of a trading pair symbol, e.g. `'BTC/USDT'` or the
 *  perpetual-futures form `'BTC/USDT:USDT'` → `'BTC'`. Order/Trade/Position
 *  `symbol` fields are always pairs, never a bare coin — this is the one
 *  place that assumption is encoded, for per-asset filtering and logo
 *  lookups (which key by bare coin symbol). Returns the input unchanged when
 *  it does not look like a pair (defensive default, never throws). */
export function baseCurrencyOf(pairSymbol: string): string {
  const [base] = pairSymbol.split('/')
  return base || pairSymbol
}
