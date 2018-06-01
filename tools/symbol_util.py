from config.cst import MARKET_SEPARATOR


# Return currency, market
def split_symbol(symbol):
    splitted = symbol.split(MARKET_SEPARATOR)
    return splitted[0], splitted[1]


# Return merged currency and market without /
def merge_symbol(symbol):
    return symbol.replace(MARKET_SEPARATOR, "")


# Merge currency and market
def merge_currencies(currency, market):
    return "{0}/{1}".format(currency, market)
