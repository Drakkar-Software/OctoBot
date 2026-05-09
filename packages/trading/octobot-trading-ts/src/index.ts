// Public API surface — mirrors octobot_trading/exchanges/__init__.py with the
// scope reduced to REST + WebSocket + adapters.

export * from "./enums.js";
export * from "./errors.js";
export * from "./exchanges.js";
export * from "./exchangeManager.js";
export * from "./exchangeBuilder.js";
export * from "./exchangeDetails.js";
export * from "./abstractExchange.js";
export * from "./abstractWebsocketExchange.js";

export * from "./types/restExchange.js";
export * from "./types/websocketExchange.js";

export * from "./implementations/defaultRestExchange.js";
export * from "./implementations/defaultWebsocketExchange.js";

export * from "./adapters/abstractAdapter.js";
export * from "./adapters/ccxtAdapter.js";

export * from "./connectors/ccxt/ccxtConnector.js";
export * from "./connectors/ccxt/ccxtWebsocketConnector.js";
export * from "./connectors/ccxt/ccxtClientUtil.js";
export * from "./connectors/ccxt/ccxtConstants.js";
export * from "./connectors/ccxt/ccxtEnums.js";
export * from "./connectors/util.js";

export * from "./config/exchangeConfigData.js";
export * from "./config/exchangeProxyConfig.js";
export * from "./config/exchangeCredentialsData.js";
export * from "./config/channelSpecs.js";

export * from "./util/exchangeData.js";
export * from "./util/exchangeDataUtil.js";
export * from "./util/exchangeMarketStatusFixer.js";
export {
  exchangeErrorTranslator,
  getOrderSide,
  isMissingTradingFees,
  applyTradesFees,
  logTimeSyncError,
  getEnabledExchanges,
  isAuthRequiredExchanges,
  isErrorOnThisType,
  getDefaultExchangeType,
  getSupportedExchangeTypes,
  getCommonTradedQuote,
  getAssociatedSymbol,
} from "./util/exchangeUtil.js";
export * from "./util/symbolDetails.js";
export * from "./util/websocketsUtil.js";

export * from "./marketFilters/marketFilterFactory.js";

// Re-export commons-ts logger and event bus for callers who want to wire a
// custom backend without depending directly on @drakkarsoftware/octobot-commons.
export {
  type Logger,
  type LoggerBackend,
  getLogger,
  setLoggerBackend,
  EventBus,
  Decimal,
  type DecimalLike,
} from "@drakkarsoftware/octobot-commons";

// Default export is the builder factory — most browser callers start with it.
import { createExchangeBuilderInstance } from "./exchangeBuilder.js";
export default { createExchangeBuilderInstance };
