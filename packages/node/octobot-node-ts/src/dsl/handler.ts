import { createTradingKeywords, createMarketDataKeywords } from "@drakkarsoftware/octobot-flow";
import type { AbstractExchange } from "@drakkarsoftware/octobot-flow";
import type { ActionHandler } from "../actions.js";
import { DslParseError, DslKeywordMismatchError } from "../errors.js";
import { parseDsl } from "./parser.js";

type KeywordFn = (...args: unknown[]) => Promise<unknown>;

export function createDslActionHandler(keyword: KeywordFn): ActionHandler {
  return async (action) => {
    if (!action.dsl) throw new DslParseError("", "action.dsl is empty");
    const parsed = parseDsl(action.dsl);
    if (parsed.keyword !== action.actionType) {
      throw new DslKeywordMismatchError(action.actionType, parsed.keyword);
    }
    return keyword(...parsed.args);
  };
}

export function createFlowActionHandlers(exchange: AbstractExchange): Record<string, ActionHandler> {
  const kw = {
    ...createTradingKeywords(exchange),
    ...createMarketDataKeywords(exchange),
  } as Record<string, KeywordFn>;
  return Object.fromEntries(
    Object.entries(kw).map(([name, fn]) => [name, createDslActionHandler(fn)]),
  );
}
