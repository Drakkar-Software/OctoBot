import json
import os
import gzip

from config.cst import CONFIG_DATA_COLLECTOR_PATH, PriceIndexes


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
        try:
            # try zipfile
            with gzip.open(file_name, 'r') as file_to_parse:
                file_content = DataCollectorParser.merge_arrays(json.loads(file_to_parse.read()))
        except OSError as e:
            # try without unzip
            with open(file_name) as file_to_parse:
                file_content = DataCollectorParser.merge_arrays(json.loads(file_to_parse.read()))
        return file_content

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
