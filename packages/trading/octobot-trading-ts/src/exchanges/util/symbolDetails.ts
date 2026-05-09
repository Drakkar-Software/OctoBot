// Mirror of util/symbol_details.py — kept lean since the deprecated `info`/`parsed`
// dicts are noted for removal in the Python source.

export interface CCXTDetails {
  info: Record<string, unknown>;
  parsed: Record<string, unknown>;
}

export interface SymbolDetails {
  ccxt: CCXTDetails;
}

export function makeSymbolDetails(): SymbolDetails {
  return { ccxt: { info: {}, parsed: {} } };
}
