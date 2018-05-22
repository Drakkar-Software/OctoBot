import matplotlib.pyplot as plt
from matplotlib import ticker
from mpl_finance import candlestick_ohlc

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
    def show_candlesticks_dataframe_with_indicator(prices_data_frame, indicator_data_frame, in_graph=True):
        if in_graph:
            n_rows = 1
        else:
            n_rows = 2

        fig, axes = plt.subplots(nrows=n_rows, sharex=True)

        if in_graph:
            DataVisualiser.get_plot_candlesticks_dataframe(prices_data_frame, axes)
            axe = fig.add_subplot(111, frameon=False)
            axe.get_yaxis().set_ticks([])
            DataVisualiser.add_indicator_to_plot(indicator_data_frame, axe)
        else:
            DataVisualiser.get_plot_candlesticks_dataframe(prices_data_frame, axes[0])
            DataVisualiser.add_indicator_to_plot(indicator_data_frame, axes[1])

        fig.autofmt_xdate()
        fig.tight_layout()

        plt.show()

    @staticmethod
    def show_candlesticks_dataframe_with_indicators(prices_data_frame, indicator_data_frames):
        count_in_graph = 1
        for indicator_data_frame in indicator_data_frames:
            if not indicator_data_frame["in_graph"]:
                count_in_graph += 1

        fig, axes = plt.subplots(nrows=count_in_graph, sharex=True)

        if count_in_graph > 1:
            ref_axe = axes[0]
            DataVisualiser.get_plot_candlesticks_dataframe(prices_data_frame, axes[0])
            axes[0].set_title('Symbol prices')
        else:
            ref_axe = axes
            DataVisualiser.get_plot_candlesticks_dataframe(prices_data_frame, axes)
            axes.set_title('Symbol prices')

        row = 1
        for indicator_data_frame in indicator_data_frames:
            if indicator_data_frame["in_graph"]:
                if indicator_data_frame["points"]:

                    if indicator_data_frame["share_x"]:
                        share_x = ref_axe
                    else:
                        share_x = None

                    if indicator_data_frame["share_y"]:
                        share_y = ref_axe
                    else:
                        share_y = None

                    axe = fig.add_subplot(count_in_graph * 100 + 10 + row, frameon=False,
                                          sharey=share_y, sharex=share_x)
                    axe.get_yaxis().set_ticks([])
                    DataVisualiser.add_indicator_to_plot(indicator_data_frame["data"],
                                                         axe,
                                                         points=True)
                else:
                    axe = fig.add_subplot(count_in_graph * 100 + 10 + row, frameon=False)
                    axe.get_yaxis().set_ticks([])
                    DataVisualiser.add_indicator_to_plot(indicator_data_frame["data"],
                                                         axe)
            else:
                DataVisualiser.add_indicator_to_plot(indicator_data_frame["data"],
                                                     axes[row],
                                                     indicator_data_frame["title"])
                row += 1

        fig.autofmt_xdate()
        fig.tight_layout()
        plt.show()

    @staticmethod
    def add_indicator_to_plot(indicator_data_frame, ax, points=False, title=None):
        DataVisualiser.get_plot_indicator_dataframe(indicator_data_frame, ax, points)
        if title is not None:
            ax.set_title('Axe {0}'.format(title))

    @staticmethod
    def get_plot_candlesticks_dataframe(data_frame, ax):
        candlestick_ohlc(ax,
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

        def get_date(x, _):
            try:
                return xdate[int(x)]
            except IndexError:
                return ''

        ax.xaxis.set_major_formatter(ticker.FuncFormatter(get_date))

    @staticmethod
    def get_plot_indicator_dataframe(indicator_data_frame, ax, points):
        if points:
            ax.plot(*zip(*indicator_data_frame), marker='o', color='r', ls='')
        else:
            ax.plot(indicator_data_frame.values)
