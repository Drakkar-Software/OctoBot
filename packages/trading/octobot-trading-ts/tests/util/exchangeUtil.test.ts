import { describe, it, expect } from "vitest";
import {
  getOrderSide,
  isMissingTradingFees,
  getCommonTradedQuote,
  getAssociatedSymbol,
  exchangeErrorTranslator,
} from "../../src/util/exchangeUtil.js";
import { ExchangeConstantsOrderColumns as EOC, TradeOrderSide } from "../../src/enums.js";
import { OctoBotTradingError, AuthenticationError } from "../../src/errors.js";

describe("exchangeUtil", () => {
  it("extracts order side from a parsed order", () => {
    expect(getOrderSide({ [EOC.SIDE]: "buy" })).toBe(TradeOrderSide.BUY);
    expect(getOrderSide({ [EOC.SIDE]: "sell" })).toBe(TradeOrderSide.SELL);
    expect(getOrderSide({})).toBeNull();
  });

  it("flags missing fees when no fee object is attached", () => {
    expect(isMissingTradingFees({})).toBe(true);
    expect(isMissingTradingFees({ [EOC.FEE]: { cost: 0.5 } })).toBe(false);
  });

  it("computes the most common quote across symbols", () => {
    expect(getCommonTradedQuote(["BTC/USDT", "ETH/USDT", "ADA/EUR"])).toBe("USDT");
    expect(getCommonTradedQuote([])).toBeNull();
  });

  it("finds the symbol matching base/quote", () => {
    expect(getAssociatedSymbol(["BTC/USDT", "ETH/EUR"], "BTC", "USDT")).toBe("BTC/USDT");
    expect(getAssociatedSymbol(["BTC/USDT"], "DOGE", "USDT")).toBeNull();
  });

  it("preserves typed OctoBot errors and translates by class name", () => {
    const original = new OctoBotTradingError("known");
    expect(exchangeErrorTranslator(original)).toBe(original);

    class FakeAuthError extends Error { constructor() { super("bad creds"); this.name = "AuthError"; } }
    const translated = exchangeErrorTranslator(new FakeAuthError());
    expect(translated).toBeInstanceOf(AuthenticationError);
  });
});
