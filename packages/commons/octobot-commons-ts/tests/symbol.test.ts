import { describe, it, expect } from "vitest";
import {
  parseSymbol,
  buildSymbol,
  isFutureSymbol,
  isLinearFutureSymbol,
  isInverseFutureSymbol,
  isOptionSymbol,
} from "../src/symbol.js";

describe("symbol parsing", () => {
  it("splits BASE/QUOTE", () => {
    const p = parseSymbol("BTC/USDT");
    expect(p.base).toBe("BTC");
    expect(p.quote).toBe("USDT");
    expect(p.settlementAsset).toBe("");
  });

  it("parses settlement asset", () => {
    const p = parseSymbol("BTC/USDT:USDT");
    expect(p.settlementAsset).toBe("USDT");
    expect(p.optionType).toBe("");
  });

  it("recognizes linear future", () => {
    expect(isFutureSymbol("BTC/USDT:USDT")).toBe(true);
    expect(isLinearFutureSymbol("BTC/USDT:USDT")).toBe(true);
    expect(isInverseFutureSymbol("BTC/USDT:USDT")).toBe(false);
  });

  it("recognizes inverse future", () => {
    expect(isInverseFutureSymbol("BTC/USD:BTC")).toBe(true);
    expect(isLinearFutureSymbol("BTC/USD:BTC")).toBe(false);
  });

  it("recognizes option", () => {
    expect(isOptionSymbol("BTC/USDT:USDT-241227-30000-C")).toBe(true);
    expect(isOptionSymbol("BTC/USDT:USDT")).toBe(false);
  });

  it("builds back the original symbol", () => {
    const s = "BTC/USDT:USDT";
    const p = parseSymbol(s);
    expect(buildSymbol(p.base, p.quote, p.settlementAsset, p.identifier, p.strikePrice, p.optionType)).toBe(s);
  });
});
