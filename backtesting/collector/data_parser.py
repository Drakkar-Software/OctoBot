import json
import os

from config.cst import CONFIG_DATA_COLLECTOR_PATH, PriceIndexes


class DataCollectorParser:
    @staticmethod
    def parse(file):
        if os.path.isfile(CONFIG_DATA_COLLECTOR_PATH + file):
            with open(CONFIG_DATA_COLLECTOR_PATH + file) as file_to_parse:
                file_content = DataCollectorParser.merge_arrays(json.loads(file_to_parse.read()))
        else:
            with open(file) as file_to_parse:
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

    @staticmethod
    def convert_legacy_format(file_path_to_convert):
        with open(file_path_to_convert) as file_to_parse:
            file_content = json.loads(file_to_parse.read())

        converted_time_frames_data = {}
        for time_frame in file_content:
            data = file_content[time_frame]
            converted_time_frames_data[time_frame] = []

            converted_time_frames_data[time_frame].insert(PriceIndexes.IND_PRICE_OPEN.value, [])
            converted_time_frames_data[time_frame].insert(PriceIndexes.IND_PRICE_HIGH.value, [])
            converted_time_frames_data[time_frame].insert(PriceIndexes.IND_PRICE_LOW.value, [])
            converted_time_frames_data[time_frame].insert(PriceIndexes.IND_PRICE_TIME.value, [])
            converted_time_frames_data[time_frame].insert(PriceIndexes.IND_PRICE_VOL.value, [])
            converted_time_frames_data[time_frame].insert(PriceIndexes.IND_PRICE_CLOSE.value, [])

            for i in range(len(data)):
                converted_time_frames_data[time_frame][PriceIndexes.IND_PRICE_CLOSE.value]\
                    .append(data[i][PriceIndexes.IND_PRICE_CLOSE.value])

                converted_time_frames_data[time_frame][PriceIndexes.IND_PRICE_OPEN.value] \
                    .append(data[i][PriceIndexes.IND_PRICE_OPEN.value])

                converted_time_frames_data[time_frame][PriceIndexes.IND_PRICE_HIGH.value] \
                    .append(data[i][PriceIndexes.IND_PRICE_HIGH.value])

                converted_time_frames_data[time_frame][PriceIndexes.IND_PRICE_TIME.value] \
                    .append(data[i][PriceIndexes.IND_PRICE_TIME.value])

                converted_time_frames_data[time_frame][PriceIndexes.IND_PRICE_VOL.value] \
                    .append(data[i][PriceIndexes.IND_PRICE_VOL.value])

                converted_time_frames_data[time_frame][PriceIndexes.IND_PRICE_LOW.value] \
                    .append(data[i][PriceIndexes.IND_PRICE_LOW.value])

        with open("{}_new".format(file_path_to_convert), 'w') as json_file:
            json.dump(converted_time_frames_data, json_file)

