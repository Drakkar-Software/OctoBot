import pandas
from config.cst import PriceStrings, PriceIndexes


class DataFrameUtil:

    @staticmethod
    def normalize_data_frame(data_frame):
        return (data_frame - data_frame.mean()) / (data_frame.max() - data_frame.min())

    @staticmethod
    def drop_nan_and_reset_index(data_frame):
        result = data_frame.dropna()
        result.reset_index(drop=True, inplace=True)
        return result

    # Candles to dataframe
    @staticmethod
    def candles_array_to_data_frame(candles_array):
        prices = {PriceStrings.STR_PRICE_HIGH.value: [],
                  PriceStrings.STR_PRICE_LOW.value: [],
                  PriceStrings.STR_PRICE_OPEN.value: [],
                  PriceStrings.STR_PRICE_CLOSE.value: [],
                  PriceStrings.STR_PRICE_VOL.value: [],
                  PriceStrings.STR_PRICE_TIME.value: []}

        for c in candles_array:
            prices[PriceStrings.STR_PRICE_TIME.value].append(float(c[PriceIndexes.IND_PRICE_TIME.value]))
            prices[PriceStrings.STR_PRICE_OPEN.value].append(float(c[PriceIndexes.IND_PRICE_OPEN.value]))
            prices[PriceStrings.STR_PRICE_HIGH.value].append(float(c[PriceIndexes.IND_PRICE_HIGH.value]))
            prices[PriceStrings.STR_PRICE_LOW.value].append(float(c[PriceIndexes.IND_PRICE_LOW.value]))
            prices[PriceStrings.STR_PRICE_CLOSE.value].append(float(c[PriceIndexes.IND_PRICE_CLOSE.value]))
            prices[PriceStrings.STR_PRICE_VOL.value].append(float(c[PriceIndexes.IND_PRICE_VOL.value]))

        return pandas.DataFrame(data=prices)
