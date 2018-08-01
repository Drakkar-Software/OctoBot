from backtesting.collector.data_file_manager import get_all_available_data_files, get_file_description


def get_data_files_with_description():
    files = get_all_available_data_files()
    files_with_description = {
        file: get_file_description(file) for file in files
    }
    return files_with_description


def start_backtesting_using_files(files):
    return True, "Backtesting started"
