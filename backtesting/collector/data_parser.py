import os

from config import CONFIG_DATA_COLLECTOR_PATH, PriceIndexes
from backtesting.collector.data_file_manager import read_data_file


class DataCollectorParser:
    @staticmethod
    def parse(file):
        if os.path.isfile(CONFIG_DATA_COLLECTOR_PATH + file):
            file_content = DataCollectorParser.get_file_content(CONFIG_DATA_COLLECTOR_PATH + file)
        else:
            file_content = DataCollectorParser.get_file_content(file)
        return file_content

    @staticmethod
    def get_file_content(file_name):
        file_content = read_data_file(file_name)
        return DataCollectorParser.merge_arrays(file_content)

    @staticmethod
    def merge_arrays(arrays):
        time_frames_data = {}
        for time_frame in arrays:
            data = arrays[time_frame]
            time_frames_data[time_frame] = []
            for i in range(len(data[PriceIndexes.IND_PRICE_TIME.value])):
                time_frames_data[time_frame].insert(i, [None]*len(PriceIndexes))
                time_frames_data[time_frame][i][PriceIndexes.IND_PRICE_CLOSE.value] = \
                    data[PriceIndexes.IND_PRICE_CLOSE.value][i]
                time_frames_data[time_frame][i][PriceIndexes.IND_PRICE_OPEN.value] = \
                    data[PriceIndexes.IND_PRICE_OPEN.value][i]
                time_frames_data[time_frame][i][PriceIndexes.IND_PRICE_HIGH.value] = \
                    data[PriceIndexes.IND_PRICE_HIGH.value][i]
                time_frames_data[time_frame][i][PriceIndexes.IND_PRICE_LOW.value] = \
                    data[PriceIndexes.IND_PRICE_LOW.value][i]
                time_frames_data[time_frame][i][PriceIndexes.IND_PRICE_TIME.value] = \
                    data[PriceIndexes.IND_PRICE_TIME.value][i]
                time_frames_data[time_frame][i][PriceIndexes.IND_PRICE_VOL.value] = \
                    data[PriceIndexes.IND_PRICE_VOL.value][i]

        return time_frames_data
