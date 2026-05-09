import { describe, it, expect } from "vitest";
import { createMarketFilter } from "../../src/exchanges/marketFilters/marketFilterFactory.js";
import { ExchangeConstantsMarketStatusColumns as Ecmsc, ExchangeTypes } from "../../src/exchanges/enums.js";

function market(symbol: string, base: string, quote: string, type = ExchangeTypes.SPOT) {
  return {
    [Ecmsc.SYMBOL]: symbol,
    [Ecmsc.CURRENCY]: base,
    [Ecmsc.MARKET]: quote,
    [Ecmsc.TYPE]: type,
  };
}

describe("createMarketFilter", () => {
  it("keeps symbols matching the requested quote", () => {
    const f = createMarketFilter({ toKeepQuote: "USDT", forceUsdLikeMarkets: false });
    expect(f(market("BTC/USDT", "BTC", "USDT"))).toBe(true);
    expect(f(market("ETH/BTC", "ETH", "BTC"))).toBe(false);
  });

  it("includes USD-like markets when forceUsdLikeMarkets is set (default)", () => {
    const f = createMarketFilter({ toKeepQuote: "USDT" });
    expect(f(market("USDC/USDT", "USDC", "USDT"))).toBe(true);
    // USDC is USD-like base — that's allowed for portfolio conversion
    expect(f(market("USDC/EUR", "USDC", "EUR"))).toBe(true);
  });

  it("excludes non-spot markets even when quote matches", () => {
    const f = createMarketFilter({ toKeepQuote: "USDT" });
    expect(f(market("BTC/USDT:USDT", "BTC", "USDT", ExchangeTypes.FUTURE))).toBe(false);
  });

  it("retains forced symbols regardless of quote rules", () => {
    const f = createMarketFilter({ toKeepQuote: "USDT", toKeepSymbols: ["DOGE/EUR"] });
    expect(f(market("DOGE/EUR", "DOGE", "EUR"))).toBe(true);
  });
});
