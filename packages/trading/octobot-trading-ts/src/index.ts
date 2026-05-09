// Public API surface — mirrors octobot_trading/exchanges/__init__.py with the
// scope reduced to REST + WebSocket + adapters.

export * from "./exchanges/enums.js";
export * from "./exchanges/errors.js";
export * from "./exchanges/exchanges.js";
export * from "./exchanges/exchangeManager.js";
export * from "./exchanges/exchangeBuilder.js";
export * from "./exchanges/exchangeDetails.js";
export * from "./exchanges/abstractExchange.js";
export * from "./exchanges/abstractWebsocketExchange.js";

export * from "./exchanges/types/restExchange.js";
export * from "./exchanges/types/websocketExchange.js";

export * from "./exchanges/implementations/defaultRestExchange.js";
export * from "./exchanges/implementations/defaultWebsocketExchange.js";

export * from "./exchanges/adapters/abstractAdapter.js";
export * from "./exchanges/adapters/ccxtAdapter.js";

export * from "./exchanges/connectors/ccxt/ccxtConnector.js";
export * from "./exchanges/connectors/ccxt/ccxtWebsocketConnector.js";
export * from "./exchanges/connectors/ccxt/ccxtClientUtil.js";
export * from "./exchanges/connectors/ccxt/ccxtConstants.js";
export * from "./exchanges/connectors/ccxt/ccxtEnums.js";
export * from "./exchanges/connectors/util.js";

export * from "./exchanges/config/exchangeConfigData.js";
export * from "./exchanges/config/exchangeProxyConfig.js";
export * from "./exchanges/config/exchangeCredentialsData.js";
export * from "./exchanges/config/channelSpecs.js";

export * from "./exchanges/util/exchangeData.js";
export * from "./exchanges/util/exchangeDataUtil.js";
export * from "./exchanges/util/exchangeMarketStatusFixer.js";
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
} from "./exchanges/util/exchangeUtil.js";
export * from "./exchanges/util/symbolDetails.js";
export * from "./exchanges/util/websocketsUtil.js";

export * from "./exchanges/marketFilters/marketFilterFactory.js";

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
import { createExchangeBuilderInstance } from "./exchanges/exchangeBuilder.js";
export default { createExchangeBuilderInstance };
