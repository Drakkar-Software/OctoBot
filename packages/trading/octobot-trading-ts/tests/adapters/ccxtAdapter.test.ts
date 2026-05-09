import { describe, it, expect } from "vitest";
import { CCXTAdapter } from "../../src/exchanges/adapters/ccxtAdapter.js";
import {
  ExchangeConstantsOrderColumns as EOC,
  ExchangeConstantsTickersColumns as ETC,
  ExchangeConstantsMarketStatusColumns as EMSC,
} from "../../src/exchanges/enums.js";

class StubConnector {
  exchangeManager = { isFuture: false };
  getContractSize() { return null; }
  getExchangeCurrentTime() { return 1700000000; }
}

describe("CCXTAdapter.fixOrder", () => {
  it("renames 'id' to 'exchange_id' and uniformizes the timestamp", () => {
    const adapter = new CCXTAdapter(new StubConnector());
    const fixed = adapter.fixOrder({ [EOC.ID]: "abc-123", [EOC.TIMESTAMP]: 1700000000000 });
    expect(fixed[EOC.EXCHANGE_ID]).toBe("abc-123");
    expect(fixed[EOC.ID]).toBeUndefined();
    expect(fixed[EOC.TIMESTAMP]).toBe(1700000000);
  });
});

describe("CCXTAdapter.fixMarketStatus", () => {
  it("converts string precision to digit counts", () => {
    const adapter = new CCXTAdapter(new StubConnector());
    const fixed = adapter.fixMarketStatus({
      [EMSC.PRECISION]: { [EMSC.PRECISION_AMOUNT]: 0.001, [EMSC.PRECISION_PRICE]: 0.0001 },
      [EMSC.LIMITS]: {},
    });
    expect(fixed[EMSC.PRECISION][EMSC.PRECISION_AMOUNT]).toBe(3);
    expect(fixed[EMSC.PRECISION][EMSC.PRECISION_PRICE]).toBe(4);
  });

  it("nulls out price limits when removePriceLimits is set", () => {
    const adapter = new CCXTAdapter(new StubConnector());
    const fixed = adapter.fixMarketStatus({
      [EMSC.PRECISION]: { [EMSC.PRECISION_AMOUNT]: 0.01, [EMSC.PRECISION_PRICE]: 0.01 },
      [EMSC.LIMITS]: {
        [EMSC.LIMITS_PRICE]: { [EMSC.LIMITS_PRICE_MIN]: 0.5, [EMSC.LIMITS_PRICE_MAX]: 100 },
      },
    }, true);
    expect(fixed[EMSC.LIMITS][EMSC.LIMITS_PRICE][EMSC.LIMITS_PRICE_MIN]).toBeNull();
    expect(fixed[EMSC.LIMITS][EMSC.LIMITS_PRICE][EMSC.LIMITS_PRICE_MAX]).toBeNull();
  });
});

describe("CCXTAdapter.createTickerFromKline", () => {
  it("turns an OHLCV row into a ticker dict", () => {
    const adapter = new CCXTAdapter(new StubConnector());
    const ticker = adapter.createTickerFromKline([1700000000, 100, 110, 95, 105, 12.5] as unknown as Record<string, unknown>, "BTC/USDT");
    expect(ticker[ETC.SYMBOL]).toBe("BTC/USDT");
    expect(ticker[ETC.OPEN]).toBe(100);
    expect(ticker[ETC.HIGH]).toBe(110);
    expect(ticker[ETC.LOW]).toBe(95);
    expect(ticker[ETC.CLOSE]).toBe(105);
    expect(ticker[ETC.LAST]).toBe(105);
  });
});
