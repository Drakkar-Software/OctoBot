// Subset port of octobot_commons.enums — only enums shared with downstream
// packages.

export enum TimeFrames {
  ONE_MINUTE = "1m",
  THREE_MINUTES = "3m",
  FIVE_MINUTES = "5m",
  FIFTEEN_MINUTES = "15m",
  THIRTY_MINUTES = "30m",
  ONE_HOUR = "1h",
  TWO_HOURS = "2h",
  THREE_HOURS = "3h",
  FOUR_HOURS = "4h",
  SIX_HOURS = "6h",
  HEIGHT_HOURS = "8h",
  TWELVE_HOURS = "12h",
  ONE_DAY = "1d",
  THREE_DAYS = "3d",
  ONE_WEEK = "1w",
  ONE_MONTH = "1M",
  ONE_YEAR = "1y",
}

export const TimeFramesMinutes: Record<TimeFrames, number> = {
  [TimeFrames.ONE_MINUTE]: 1,
  [TimeFrames.THREE_MINUTES]: 3,
  [TimeFrames.FIVE_MINUTES]: 5,
  [TimeFrames.FIFTEEN_MINUTES]: 15,
  [TimeFrames.THIRTY_MINUTES]: 30,
  [TimeFrames.ONE_HOUR]: 60,
  [TimeFrames.TWO_HOURS]: 120,
  [TimeFrames.THREE_HOURS]: 180,
  [TimeFrames.FOUR_HOURS]: 240,
  [TimeFrames.SIX_HOURS]: 360,
  [TimeFrames.HEIGHT_HOURS]: 480,
  [TimeFrames.TWELVE_HOURS]: 720,
  [TimeFrames.ONE_DAY]: 1440,
  [TimeFrames.THREE_DAYS]: 4320,
  [TimeFrames.ONE_WEEK]: 10080,
  [TimeFrames.ONE_MONTH]: 43200,
  [TimeFrames.ONE_YEAR]: 524160,
};

export enum PriceIndexes {
  IND_PRICE_TIME = 0,
  IND_PRICE_OPEN = 1,
  IND_PRICE_HIGH = 2,
  IND_PRICE_LOW = 3,
  IND_PRICE_CLOSE = 4,
  IND_PRICE_VOL = 5,
}

export enum PriceStrings {
  STR_PRICE_TIME = "time",
  STR_PRICE_CLOSE = "close",
  STR_PRICE_OPEN = "open",
  STR_PRICE_HIGH = "high",
  STR_PRICE_LOW = "low",
  STR_PRICE_VOL = "vol",
}

export enum OptionTypes {
  PUT = "P",
  CALL = "C",
}
