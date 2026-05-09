// Subset port of octobot_commons.symbols. Only the parsing/formatting helpers
// the downstream packages actually use are reproduced.

const MARKET_SEPARATOR = "/";
const SETTLEMENT_ASSET_SEPARATOR = ":";
const SETTLEMENT_DATE_SEPARATOR = "-";
const SETTLEMENT_DATE_OPTION_SEPARATOR = "-";
const FUTURE_OPTION_PUT = "P";
const FUTURE_OPTION_CALL = "C";

export interface ParsedSymbol {
  base: string;
  quote: string;
  settlementAsset: string;
  identifier: string;
  strikePrice: string;
  optionType: string;
}

export function parseSymbol(symbol: string): ParsedSymbol {
  // Format: BASE/QUOTE[:SETTLEMENT[-IDENTIFIER[-STRIKE-OPTIONTYPE]]]
  const [marketPart, suffix = ""] = symbol.split(SETTLEMENT_ASSET_SEPARATOR);
  const [base = "", quote = ""] = marketPart.split(MARKET_SEPARATOR);

  let settlementAsset = "";
  let identifier = "";
  let strikePrice = "";
  let optionType = "";

  if (suffix) {
    const parts = suffix.split(SETTLEMENT_DATE_SEPARATOR);
    settlementAsset = parts[0] || "";
    if (parts.length >= 2) identifier = parts[1] || "";
    if (parts.length >= 4) {
      strikePrice = parts[2] || "";
      optionType = parts[3] || "";
    }
  }

  return { base, quote, settlementAsset, identifier, strikePrice, optionType };
}

export function isFutureSymbol(symbol: string): boolean {
  const parsed = parseSymbol(symbol);
  return !!parsed.settlementAsset && !parsed.optionType;
}

export function isOptionSymbol(symbol: string): boolean {
  const parsed = parseSymbol(symbol);
  return parsed.optionType === FUTURE_OPTION_PUT || parsed.optionType === FUTURE_OPTION_CALL;
}

export function isInverseFutureSymbol(symbol: string): boolean {
  const parsed = parseSymbol(symbol);
  return !!parsed.settlementAsset && parsed.settlementAsset === parsed.base;
}

export function isLinearFutureSymbol(symbol: string): boolean {
  const parsed = parseSymbol(symbol);
  return !!parsed.settlementAsset && parsed.settlementAsset === parsed.quote;
}

export function mergeCurrencies(base: string, quote: string): string {
  return `${base}${MARKET_SEPARATOR}${quote}`;
}

export function buildSymbol(
  base: string,
  quote: string,
  settlementAsset = "",
  identifier = "",
  strikePrice = "",
  optionType = "",
): string {
  let s = mergeCurrencies(base, quote);
  if (settlementAsset) {
    s += `${SETTLEMENT_ASSET_SEPARATOR}${settlementAsset}`;
    if (identifier) s += `${SETTLEMENT_DATE_SEPARATOR}${identifier}`;
    if (strikePrice && optionType) {
      s += `${SETTLEMENT_DATE_OPTION_SEPARATOR}${strikePrice}${SETTLEMENT_DATE_OPTION_SEPARATOR}${optionType}`;
    }
  }
  return s;
}

export const SYMBOL_CONSTANTS = {
  MARKET_SEPARATOR,
  SETTLEMENT_ASSET_SEPARATOR,
  SETTLEMENT_DATE_SEPARATOR,
  FUTURE_OPTION_PUT,
  FUTURE_OPTION_CALL,
} as const;
