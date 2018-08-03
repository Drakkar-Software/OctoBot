import numpy as np


class DataUtil:

    @staticmethod
    def normalize_data(data):
        if data:
            return (data - np.mean(data)) / (data.max() - data.min())
        else:
            return data

    @staticmethod
    def drop_nan(data):
        return data[~np.isnan(data)]

    @staticmethod
    def mean(number_list):
        return sum(number_list) / len(number_list) if number_list else 0
