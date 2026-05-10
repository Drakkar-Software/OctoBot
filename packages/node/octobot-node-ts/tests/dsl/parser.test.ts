import { describe, it, expect } from "vitest";
import { parseDsl } from "../../src/dsl/parser.js";
import { DslParseError } from "../../src/errors.js";

describe("parseDsl", () => {
  it("parses a market call with mixed arg types", () => {
    const r = parseDsl("market(buy, BTC/USDT, 0.1)");
    expect(r).toEqual({ keyword: "market", args: ["buy", "BTC/USDT", 0.1] });
  });

  it("parses OHLCV close with string timeframe", () => {
    const r = parseDsl("close(BTC/USDT, 1h)");
    expect(r).toEqual({ keyword: "close", args: ["BTC/USDT", "1h"] });
  });

  it("parses single-arg keyword", () => {
    const r = parseDsl("total(BTC)");
    expect(r).toEqual({ keyword: "total", args: ["BTC"] });
  });

  it("parses quoted string arg", () => {
    const r = parseDsl('cancel_order("BTC/USDT")');
    expect(r).toEqual({ keyword: "cancel_order", args: ["BTC/USDT"] });
  });

  it("parses single-quoted arg", () => {
    const r = parseDsl("cancel_order('BTC/USDT')");
    expect(r).toEqual({ keyword: "cancel_order", args: ["BTC/USDT"] });
  });

  it("parses limit with four mixed args", () => {
    const r = parseDsl("limit(sell, BTC/USDT, 0.5, 60000)");
    expect(r).toEqual({ keyword: "limit", args: ["sell", "BTC/USDT", 0.5, 60000] });
  });

  it("tolerates extra whitespace around args", () => {
    const r = parseDsl("market(  buy ,  BTC/USDT , 20 )");
    expect(r).toEqual({ keyword: "market", args: ["buy", "BTC/USDT", 20] });
  });

  it("parses zero-arg keyword", () => {
    const r = parseDsl("noop()");
    expect(r).toEqual({ keyword: "noop", args: [] });
  });

  it("parses integer arg as number", () => {
    const r = parseDsl("fetch_trades(BTC/USDT, 10)");
    expect(r).toEqual({ keyword: "fetch_trades", args: ["BTC/USDT", 10] });
    expect(typeof r.args[1]).toBe("number");
  });

  it("throws DslParseError when ( is missing", () => {
    expect(() => parseDsl("market buy, BTC/USDT")).toThrow(DslParseError);
  });

  it("throws DslParseError when ) is missing", () => {
    expect(() => parseDsl("market(buy, BTC/USDT")).toThrow(DslParseError);
  });

  it("throws DslParseError on empty argument (double comma)", () => {
    expect(() => parseDsl("market(buy,, BTC/USDT)")).toThrow(DslParseError);
  });

  it("throws DslParseError for unterminated string", () => {
    expect(() => parseDsl('market("buy, BTC/USDT)')).toThrow(DslParseError);
  });

  it("throws DslParseError for nested call in args", () => {
    expect(() => parseDsl("market(buy, inner(x), 1)")).toThrow(DslParseError);
  });
});
