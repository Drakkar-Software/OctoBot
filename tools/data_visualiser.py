import datetime

import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib.finance import candlestick2_ohlc

from config.cst import PriceStrings


class DataVisualiser:
    @staticmethod
    def show_dataframe_graph(dataframe, column):
        plt.scatter(dataframe.index, dataframe[column])

    @staticmethod
    def show_candlesticks_dataframe(dataframe):

        fig, ax = plt.subplots()

        candlestick2_ohlc(ax,
                          dataframe[PriceStrings.STR_PRICE_OPEN],
                          dataframe[PriceStrings.STR_PRICE_HIGH],
                          dataframe[PriceStrings.STR_PRICE_LOW],
                          dataframe[PriceStrings.STR_PRICE_CLOSE],
                          width=0.6)

        xdate = [datetime.datetime.fromtimestamp(i) for i in dataframe[PriceStrings.STR_PRICE_TIME]]

        ax.xaxis.set_major_locator(ticker.MaxNLocator(6))

        def get_date(x, pos):
            try:
                return xdate[int(x)]
            except IndexError:
                return ''

        ax.xaxis.set_major_formatter(ticker.FuncFormatter(get_date))

        fig.autofmt_xdate()
        fig.tight_layout()

        plt.show()
