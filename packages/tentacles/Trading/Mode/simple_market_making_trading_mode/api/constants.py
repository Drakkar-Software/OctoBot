import decimal

VOLUME_KEY = "volume"
ERROR_KEY = "error"
PRICE_KEY = "price"
AMOUNT_KEY = "amount"
TOTAL_KEY = "total"
BIDS_KEY = "bids"
ASKS_KEY = "asks"

BASE_ORDER_BOOK_FETCH_SIZE = None
DEFAULT_LARGER_ORDER_BOOK_FETCH_SIZE = 500
LARGER_ORDER_BOOK_FETCH_SIZE_BY_EXCHANGE = {
    "binance": 999, # 50 weight, more has 250 weight https://binance-docs.github.io/apidocs/spot/en/#order-book
}
DEPTH_SCORE_MID_PRICE_THRESHOLD = 0.01
DEPTH_SCORE_THRESHOLDS = [
    [
        # High depth
        [decimal.Decimal(str(0.02)), decimal.Decimal(str(1))],
        [decimal.Decimal(str(1)), decimal.Decimal(str(1))]
    ],
    [
        # Moderate depth
        [decimal.Decimal(str(0.005)), decimal.Decimal(str(0.02))],
        [decimal.Decimal(str(0.3)), decimal.Decimal(str(1))]
    ],
    [
        # Low depth
        [decimal.Decimal(str(0)), decimal.Decimal(str(0.005))],
        [decimal.Decimal(str(0)), decimal.Decimal(str(0))]
    ],
]
SPREAD_SCORE_THRESHOLDS = [
    [
        # Tight spread
        [decimal.Decimal(str(0)), decimal.Decimal(str(0.001))],
        [decimal.Decimal(str(1)), decimal.Decimal(str(1))]
    ],
    [
        # Moderate spread
        [decimal.Decimal(str(0.001)), decimal.Decimal(str(0.005))],
        [decimal.Decimal(str(0.3)), decimal.Decimal(str(1))]
    ],
    [
        # Wide spread
        [decimal.Decimal(str(0.005)), decimal.Decimal(str(1))],
        [decimal.Decimal(str(0)), decimal.Decimal(str(0))]
    ],
]
LIQUIDITY_SCORE_DEPTH_SCORE_PART = decimal.Decimal("0.5")
LIQUIDITY_SCORE_SPREAD_SCORE_PART = decimal.Decimal("0.5")
