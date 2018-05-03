import warnings
import matplotlib.cbook

warnings.filterwarnings("ignore", category=matplotlib.cbook.mplDeprecation)

import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib.finance import candlestick2_ohlc

from config.cst import PriceStrings


class DataVisualiser:
    @staticmethod
    def show_dataframe_graph(dataframe, column):
        plt.scatter(dataframe.index, dataframe[column])

    @staticmethod
    def show_candlesticks_dataframe(data_frame):
        fig, ax = plt.subplots()

        DataVisualiser.get_plot_candlesticks_dataframe(data_frame, ax)

        fig.autofmt_xdate()
        fig.tight_layout()

        plt.show()

    @staticmethod
    def show_candlesticks_dataframe_with_indicator(prices_data_frame, indicator_data_frame):
        fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)

        DataVisualiser.get_plot_candlesticks_dataframe(prices_data_frame, ax1)
        DataVisualiser.get_plot_indicator_dataframe(indicator_data_frame, ax2)

        fig.autofmt_xdate()
        fig.tight_layout()

        plt.show()

    @staticmethod
    def get_plot_candlesticks_dataframe(data_frame, ax):
        candlestick2_ohlc(ax,
                          data_frame[PriceStrings.STR_PRICE_OPEN.value],
                          data_frame[PriceStrings.STR_PRICE_HIGH.value],
                          data_frame[PriceStrings.STR_PRICE_LOW.value],
                          data_frame[PriceStrings.STR_PRICE_CLOSE.value],
                          width=0.8,
                          colorup='#008000',
                          colordown='#FF0000',
                          alpha=1)

        # xdate = [datetime.datetime.fromtimestamp(i) for i in dataframe[PriceStrings.STR_PRICE_TIME.value]]
        xdate = data_frame[PriceStrings.STR_PRICE_TIME.value].values

        ax.xaxis.set_major_locator(ticker.MaxNLocator(6))

        def get_date(x, pos):
            try:
                return xdate[int(x)]
            except IndexError:
                return ''

        ax.xaxis.set_major_formatter(ticker.FuncFormatter(get_date))

    @staticmethod
    def get_plot_indicator_dataframe(indicator_data_frame, ax):
        ax.plot(indicator_data_frame.values)
