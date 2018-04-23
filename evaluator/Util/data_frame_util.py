

class DataFrameUtil:

    @staticmethod
    def normalize_data_frame(data_frame):
        return (data_frame - data_frame.mean()) / (data_frame.max() - data_frame.min())
