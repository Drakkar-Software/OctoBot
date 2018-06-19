import json
import os

from config.cst import CONFIG_DATA_COLLECTOR_PATH, PriceIndexes


class DataCollectorParser:
    @staticmethod
    def parse(file, use_legacy_parsing=False):
        if os.path.isfile(CONFIG_DATA_COLLECTOR_PATH + file):
            with open(CONFIG_DATA_COLLECTOR_PATH + file) as file_to_parse:
                file_content = json.loads(file_to_parse.read())
                if not use_legacy_parsing:
                    file_content = DataCollectorParser.merge_arrays(file_content)
        else:
            with open(file) as file_to_parse:
                file_content = json.loads(file_to_parse.read())
                if not use_legacy_parsing:
                    file_content = DataCollectorParser.merge_arrays(file_content)
        return file_content

    @staticmethod
    def merge_arrays(arrays):
        time_frames_data = {}
        for time_frame in arrays:
            data = arrays[time_frame]
            time_frames_data[time_frame] = [None]*len(PriceIndexes)
            for i in range(len(data[PriceIndexes.IND_PRICE_TIME.value])):
                time_frames_data[time_frame].insert(i, [])
                time_frames_data[time_frame][i].insert(PriceIndexes.IND_PRICE_CLOSE.value,
                                                       data[PriceIndexes.IND_PRICE_CLOSE.value][i])
                time_frames_data[time_frame][i].insert(PriceIndexes.IND_PRICE_OPEN.value,
                                                       data[PriceIndexes.IND_PRICE_OPEN.value][i])
                time_frames_data[time_frame][i].insert(PriceIndexes.IND_PRICE_HIGH.value,
                                                       data[PriceIndexes.IND_PRICE_HIGH.value][i])
                time_frames_data[time_frame][i].insert(PriceIndexes.IND_PRICE_LOW.value,
                                                       data[PriceIndexes.IND_PRICE_LOW.value][i])
                time_frames_data[time_frame][i].insert(PriceIndexes.IND_PRICE_TIME.value,
                                                       data[PriceIndexes.IND_PRICE_TIME.value][i])
                time_frames_data[time_frame][i].insert(PriceIndexes.IND_PRICE_VOL.value,
                                                       data[PriceIndexes.IND_PRICE_VOL.value][i])

        return time_frames_data
