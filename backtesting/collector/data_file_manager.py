import time
import os
import json
import gzip

from tools.symbol_util import merge_currencies


Exchange_Data_Collector_File_Ext = ".data"


def interpret_file_name(file_name):
    data = os.path.basename(file_name).split("_")
    try:
        exchange_name = data[0]
        symbol = merge_currencies(data[1], data[2])
        timestamp = data[3] + data[4].replace(Exchange_Data_Collector_File_Ext, "")
    except KeyError:
        exchange_name = None
        symbol = None
        timestamp = None

    return exchange_name, symbol, timestamp


def build_file_name(exchange, symbol):
    return f"{exchange.get_name()}_{symbol.replace('/', '_')}_" \
           f"{time.strftime('%Y%m%d_%H%M%S')}{Exchange_Data_Collector_File_Ext}"


def write_data_file(file_name, content, ):
    with gzip.open(file_name, 'wt') as json_file:
        json.dump(content, json_file)


def read_data_file(file_name):
    try:
        # try zipfile
        with gzip.open(file_name, 'r') as file_to_parse:
            file_content = json.loads(file_to_parse.read())
    except OSError:
        # try without unzip
        with open(file_name) as file_to_parse:
            file_content = json.loads(file_to_parse.read())
    return file_content
