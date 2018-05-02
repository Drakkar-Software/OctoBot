

class DataFrameUtil:

    @staticmethod
    def normalize_data_frame(data_frame):
        return (data_frame - data_frame.mean()) / (data_frame.max() - data_frame.min())

    @staticmethod
    def drop_nan_and_reset_index(data_frame):
        result = data_frame.dropna()
        result.reset_index(drop=True, inplace=True)
        return result
