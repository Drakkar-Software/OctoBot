// Common timeframe strings used with CCXT fetchOHLCV

export const TimeFrames = {
  ONE_MINUTE: "1m",
  THREE_MINUTES: "3m",
  FIVE_MINUTES: "5m",
  FIFTEEN_MINUTES: "15m",
  THIRTY_MINUTES: "30m",
  ONE_HOUR: "1h",
  TWO_HOURS: "2h",
  FOUR_HOURS: "4h",
  SIX_HOURS: "6h",
  EIGHT_HOURS: "8h",
  TWELVE_HOURS: "12h",
  ONE_DAY: "1d",
  THREE_DAYS: "3d",
  ONE_WEEK: "1w",
  ONE_MONTH: "1M",
} as const
export type TimeFrameValue = (typeof TimeFrames)[keyof typeof TimeFrames]

// Map timeframe string → seconds — mirrors TimeFramesMinutes * MINUTE_TO_SECONDS
export const TimeFrameSeconds: Record<string, number> = {
  "1m": 60,
  "3m": 180,
  "5m": 300,
  "15m": 900,
  "30m": 1800,
  "1h": 3600,
  "2h": 7200,
  "4h": 14400,
  "6h": 21600,
  "8h": 28800,
  "12h": 43200,
  "1d": 86400,
  "3d": 259200,
  "1w": 604800,
  "1M": 2592000,
}
