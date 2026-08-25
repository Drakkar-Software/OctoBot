import type { Account, ExchangeConfig } from "@/client"
import { getAccountExchangeConfigIds } from "@/lib/debug/display-utils"
import type {
  HistoricalAssetValue,
  PortfolioHistoricalValue,
  PortfolioHistoricalValuesState,
} from "@/lib/debug/portfolio-historical-values-types"

export const NEGATIVE_HOLDINGS_SIGNIFICANCE_RATIO = 0.01

const USD_LIKE_SYMBOLS = new Set(["USDC", "USD", "BUSD", "DAI"])

export type NegativeHoldingsWarning = {
  symbol: string
  suggestedTradeSymbol: string
  exchangeConfigLabel?: string
}

type AssetSnapshot = Map<string, HistoricalAssetValue>

export function getNegativeHoldingsWarnings(
  state: PortfolioHistoricalValuesState | undefined,
  referenceMarket = "USDT",
  account?: Account | null,
  exchangeConfigs: ExchangeConfig[] = [],
): NegativeHoldingsWarning[] {
  const historyValues = [...(state?.history?.values ?? [])].sort(
    (leftHistoryValue, rightHistoryValue) =>
      Date.parse(leftHistoryValue.timestamp) - Date.parse(rightHistoryValue.timestamp),
  )
  const exchangeConfigLabel = resolveExchangeConfigLabel(account, exchangeConfigs)

  const warnings: NegativeHoldingsWarning[] = []
  const warnedSymbols = new Set<string>()

  for (const historyValue of historyValues) {
    for (const asset of flattenAssets(historyValue)) {
      if (warnedSymbols.has(asset.symbol) || !isSignificantNegative(asset, historyValue.total)) {
        continue
      }
      warnedSymbols.add(asset.symbol)
      const previousDay = findPreviousHistoryValue(historyValues, historyValue)
      warnings.push({
        symbol: asset.symbol,
        suggestedTradeSymbol: inferSuggestedTradeSymbol(
          asset.symbol,
          historyValue,
          previousDay,
          historyValues,
          referenceMarket,
        ),
        exchangeConfigLabel,
      })
    }
  }

  return warnings.sort((leftWarning, rightWarning) =>
    leftWarning.symbol.localeCompare(rightWarning.symbol),
  )
}

export function formatSuggestedTradePair(
  negativeSymbol: string,
  counterpartySymbol: string,
  referenceMarket: string,
): string {
  if (isUsdLikeSymbol(negativeSymbol, referenceMarket)) {
    return `${counterpartySymbol}/${negativeSymbol}`
  }
  if (isUsdLikeSymbol(counterpartySymbol, referenceMarket)) {
    return `${negativeSymbol}/${counterpartySymbol}`
  }
  return `${negativeSymbol}/${counterpartySymbol}`
}

function flattenAssets(historyValue: PortfolioHistoricalValue): HistoricalAssetValue[] {
  return historyValue.assets?.flatMap((assetsForType) => assetsForType.assets ?? []) ?? []
}

function buildAssetSnapshot(historyValue: PortfolioHistoricalValue): AssetSnapshot {
  const snapshot: AssetSnapshot = new Map()
  for (const asset of flattenAssets(historyValue)) {
    snapshot.set(asset.symbol, asset)
  }
  return snapshot
}

function isSignificantNegative(asset: HistoricalAssetValue, total: number): boolean {
  if (asset.holdings >= 0 || total <= 0) {
    return false
  }
  return Math.abs(asset.value) / total > NEGATIVE_HOLDINGS_SIGNIFICANCE_RATIO
}

function findPreviousHistoryValue(
  historyValues: PortfolioHistoricalValue[],
  currentHistoryValue: PortfolioHistoricalValue,
): PortfolioHistoricalValue | undefined {
  const currentIndex = historyValues.indexOf(currentHistoryValue)
  if (currentIndex <= 0) {
    return undefined
  }
  return historyValues[currentIndex - 1]
}

function isUsdLikeSymbol(symbol: string, referenceMarket: string): boolean {
  return symbol === referenceMarket || USD_LIKE_SYMBOLS.has(symbol)
}

function inferSuggestedTradeSymbol(
  negativeSymbol: string,
  triggerDay: PortfolioHistoricalValue,
  previousDay: PortfolioHistoricalValue | undefined,
  historyValues: PortfolioHistoricalValue[],
  referenceMarket: string,
): string {
  if (previousDay) {
    const previousSnapshot = buildAssetSnapshot(previousDay)
    const currentSnapshot = buildAssetSnapshot(triggerDay)
    const negativeAsset = currentSnapshot.get(negativeSymbol)
    if (negativeAsset) {
      const previousNegativeAsset = previousSnapshot.get(negativeSymbol)
      const negativeValueDelta = negativeAsset.value - (previousNegativeAsset?.value ?? 0)
      const counterpartySymbol = findCounterpartySymbol(
        negativeSymbol,
        negativeValueDelta,
        referenceMarket,
        previousSnapshot,
        currentSnapshot,
      )
      if (counterpartySymbol) {
        return formatSuggestedTradePair(negativeSymbol, counterpartySymbol, referenceMarket)
      }
    }
  }

  return resolveFallbackTradeSymbol(negativeSymbol, triggerDay, historyValues, referenceMarket)
}

function findCounterpartySymbol(
  negativeSymbol: string,
  negativeValueDelta: number,
  referenceMarket: string,
  previousSnapshot: AssetSnapshot,
  currentSnapshot: AssetSnapshot,
): string | undefined {
  const counterpartyByValueDelta = findBestCounterpartyByValueDelta(
    negativeSymbol,
    negativeValueDelta,
    previousSnapshot,
    currentSnapshot,
  )
  if (counterpartyByValueDelta) {
    return counterpartyByValueDelta
  }

  const includeSymbol = isUsdLikeSymbol(negativeSymbol, referenceMarket)
    ? (symbol: string) => !isUsdLikeSymbol(symbol, referenceMarket)
    : (symbol: string) => isUsdLikeSymbol(symbol, referenceMarket)

  return findLargestPositiveHoldingsDelta(
    negativeSymbol,
    previousSnapshot,
    currentSnapshot,
    includeSymbol,
  )
}

function findBestCounterpartyByValueDelta(
  negativeSymbol: string,
  negativeValueDelta: number,
  previousSnapshot: AssetSnapshot,
  currentSnapshot: AssetSnapshot,
): string | undefined {
  let bestCounterpartySymbol: string | undefined
  let bestMatchDistance = Number.POSITIVE_INFINITY

  for (const [symbol, currentAsset] of currentSnapshot) {
    if (symbol === negativeSymbol) {
      continue
    }

    const previousAsset = previousSnapshot.get(symbol)
    const valueDelta = currentAsset.value - (previousAsset?.value ?? 0)
    if (valueDelta <= 0) {
      continue
    }

    const matchDistance = Math.abs(valueDelta + negativeValueDelta)
    if (matchDistance < bestMatchDistance) {
      bestMatchDistance = matchDistance
      bestCounterpartySymbol = symbol
    }
  }

  return bestCounterpartySymbol
}

function findLargestPositiveHoldingsDelta(
  negativeSymbol: string,
  previousSnapshot: AssetSnapshot,
  currentSnapshot: AssetSnapshot,
  includeSymbol: (symbol: string) => boolean,
): string | undefined {
  let bestCounterpartySymbol: string | undefined
  let largestHoldingsDelta = 0

  for (const [symbol, currentAsset] of currentSnapshot) {
    if (symbol === negativeSymbol || !includeSymbol(symbol)) {
      continue
    }

    const previousAsset = previousSnapshot.get(symbol)
    const holdingsDelta = currentAsset.holdings - (previousAsset?.holdings ?? 0)
    if (holdingsDelta > largestHoldingsDelta) {
      largestHoldingsDelta = holdingsDelta
      bestCounterpartySymbol = symbol
    }
  }

  return bestCounterpartySymbol
}

function detectPortfolioQuoteSymbol(
  triggerDay: PortfolioHistoricalValue,
  historyValues: PortfolioHistoricalValue[],
  referenceMarket: string,
): string {
  const quoteHoldingsBySymbol = new Map<string, number>()

  for (const historyValue of historyValues) {
    for (const asset of flattenAssets(historyValue)) {
      if (!isUsdLikeSymbol(asset.symbol, referenceMarket)) {
        continue
      }
      const currentHoldings = quoteHoldingsBySymbol.get(asset.symbol) ?? 0
      quoteHoldingsBySymbol.set(asset.symbol, currentHoldings + Math.abs(asset.holdings))
    }
  }

  if (quoteHoldingsBySymbol.has(referenceMarket)) {
    return referenceMarket
  }

  let detectedQuote = referenceMarket
  let largestQuoteHoldings = 0
  for (const [symbol, holdings] of quoteHoldingsBySymbol) {
    if (holdings > largestQuoteHoldings) {
      largestQuoteHoldings = holdings
      detectedQuote = symbol
    }
  }

  if (largestQuoteHoldings === 0) {
    const triggerSnapshot = buildAssetSnapshot(triggerDay)
    for (const [symbol, asset] of triggerSnapshot) {
      if (isUsdLikeSymbol(symbol, referenceMarket)) {
        return symbol
      }
    }
  }

  return detectedQuote
}

function resolveFallbackTradeSymbol(
  negativeSymbol: string,
  triggerDay: PortfolioHistoricalValue,
  historyValues: PortfolioHistoricalValue[],
  referenceMarket: string,
): string {
  const detectedQuote = detectPortfolioQuoteSymbol(triggerDay, historyValues, referenceMarket)

  if (isUsdLikeSymbol(negativeSymbol, referenceMarket)) {
    return `/${detectedQuote}`
  }

  return `${negativeSymbol}/${detectedQuote}`
}

function resolveExchangeConfigLabel(
  account: Account | null | undefined,
  exchangeConfigs: ExchangeConfig[],
): string | undefined {
  if (!account) {
    return undefined
  }
  const configIds = getAccountExchangeConfigIds(account)
  if (configIds.length === 0) {
    return undefined
  }
  const exchangeConfig = exchangeConfigs.find((config) => config.id === configIds[0])
  if (!exchangeConfig) {
    return configIds[0]
  }
  return exchangeConfig.name ?? exchangeConfig.exchange ?? exchangeConfig.id
}
