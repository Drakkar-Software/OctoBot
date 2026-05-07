// [timestamp_seconds, open, high, low, close, volume]
// Mirrors PriceIndexes: IND_PRICE_TIME=0, IND_PRICE_OPEN=1, IND_PRICE_HIGH=2,
//                       IND_PRICE_LOW=3, IND_PRICE_CLOSE=4, IND_PRICE_VOL=5
export type OctoBotOHLCV = [number, number, number, number, number, number]

export const PriceIndexes = {
  IND_PRICE_TIME: 0,
  IND_PRICE_OPEN: 1,
  IND_PRICE_HIGH: 2,
  IND_PRICE_LOW: 3,
  IND_PRICE_CLOSE: 4,
  IND_PRICE_VOL: 5,
} as const
