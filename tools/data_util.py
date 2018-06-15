import numpy as np


class DataUtil:

    @staticmethod
    def normalize_data(data):
        return (data - np.mean(data)) / (data.max() - data.min())

    @staticmethod
    def drop_nan(data):
        return data[~np.isnan(data)]
