import decimal
import datetime
import pytest
import typing

import tentacles.Trading.Mode.profile_copy_trading_mode.profile_distribution as profile_distribution
import tentacles.Trading.Mode.index_trading_mode.index_distribution as index_distribution
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants

if typing.TYPE_CHECKING:
    import tentacles.Services.Services_feeds.exchange_service_feed as exchange_service_feed


class MockProfileData:
    def __init__(self, profile_id: str, positions: list = None, portfolio=None):
        self.profile_id: str = profile_id
        self.positions: list[dict] = positions if positions is not None else []
        self.portfolio = portfolio


class MockAsset:
    def __init__(self, total: decimal.Decimal):
        self.total = total


class MockPortfolio:
    def __init__(self, assets: dict[str, decimal.Decimal]):
        self.portfolio = {
            currency: MockAsset(total) for currency, total in assets.items()
        }


class PortfolioTestCase(typing.NamedTuple):
    name: str
    positions: typing.List[typing.Dict]
    portfolio: typing.Optional[typing.Dict[str, decimal.Decimal]]
    expected_source: str
    expected_tradable_ratio: decimal.Decimal
    expected_symbols: typing.List[str]
    excluded_symbols: typing.List[str]
    weight_assertion: typing.Optional[str]


class TimestampTestCase(typing.NamedTuple):
    timestamp_offsets_and_symbols: typing.List[typing.Tuple[int, str]]
    expected_symbols: typing.List[str]


class UnrealizedPnlTestCase(typing.NamedTuple):
    min_unrealized_pnl_percent: typing.Optional[float]
    max_unrealized_pnl_percent: typing.Optional[float]
    positions: typing.List[typing.Dict]
    expected_symbols: typing.List[str]


class MarkPriceTestCase(typing.NamedTuple):
    min_mark_price: typing.Optional[decimal.Decimal]
    max_mark_price: typing.Optional[decimal.Decimal]
    positions: typing.List[typing.Dict]
    expected_symbols: typing.List[str]


class TradableRatioTestCase(typing.NamedTuple):
    margins: typing.List[float]
    filtered_count: int
    expected_tradable_ratio: decimal.Decimal


class NewPositionOnlyTestCase(typing.NamedTuple):
    new_position_only: bool
    expected_btc_present: bool
    expected_eth_present: bool
    btc_higher_than_eth: typing.Optional[bool]


def _make_distribution(assets: list[tuple]) -> list[dict]:
    """Helper to create distribution list from (name, value, price) tuples."""
    return [
        {
            index_distribution.DISTRIBUTION_NAME: name,
            index_distribution.DISTRIBUTION_VALUE: value,
            index_distribution.DISTRIBUTION_PRICE: price,
        }
        for name, value, price in assets
    ]


def _make_profile_dist(distribution: list[dict], tradable_ratio: decimal.Decimal = trading_constants.ONE, source: str = profile_distribution.DistributionSource.POSITIONS.value) -> dict:
    """Helper to create profile distribution dict."""
    return {
        profile_distribution.DISTRIBUTION_KEY: distribution,
        profile_distribution.TRADABLE_RATIO: tradable_ratio,
        profile_distribution.DISTRIBUTION_SOURCE: source,
    }


def test_update_global_distribution_merges_overlapping_assets():
    distribution_per_exchange_profile = {
        "profile1": _make_profile_dist(_make_distribution([
            ("BTC", 50.0, decimal.Decimal("50000")),
            ("ETH", 30.0, decimal.Decimal("3000")),
        ])),
        "profile2": _make_profile_dist(_make_distribution([
            ("BTC", 40.0, decimal.Decimal("51000")),
            ("SOL", 60.0, decimal.Decimal("100")),
        ])),
    }
    
    result = profile_distribution.update_global_distribution(
        distribution_per_exchange_profile,
        decimal.Decimal("0.5"),
        ["profile1", "profile2"]
    )
    
    # BTC: (50.0 * 0.5) + (40.0 * 0.5) = 45.0, ETH: 30.0 * 0.5 = 15.0, SOL: 60.0 * 0.5 = 30.0
    assert result[profile_distribution.RATIO_PER_ASSET]["BTC"][index_distribution.DISTRIBUTION_VALUE] == decimal.Decimal("45.0")
    # ETH should be weighted: 30.0 * 0.5 = 15.0
    assert result[profile_distribution.RATIO_PER_ASSET]["ETH"][index_distribution.DISTRIBUTION_VALUE] == decimal.Decimal("15.0")
    # SOL should be weighted: 60.0 * 0.5 = 30.0
    assert result[profile_distribution.RATIO_PER_ASSET]["SOL"][index_distribution.DISTRIBUTION_VALUE] == decimal.Decimal("30.0")
    # Total should be 45.0 + 15.0 + 30.0 = 90.0
    assert result[profile_distribution.TOTAL_RATIO_PER_ASSET] == decimal.Decimal("90.0")


@pytest.mark.parametrize("allocation,profiles_count,tradable_ratios,expected_ref_market", [
    # Single profile, 50% allocation = 50% reserve
    (decimal.Decimal("0.5"), 1, [decimal.Decimal("1")], decimal.Decimal("0.5")),
    # Single profile, 100% allocation = 0% reserve
    (decimal.Decimal("1.0"), 1, [decimal.Decimal("1")], decimal.Decimal("0")),
    # Two profiles, 30% each = 40% reserve
    (decimal.Decimal("0.3"), 2, [decimal.Decimal("1"), decimal.Decimal("1")], decimal.Decimal("0.4")),
    # Over-allocation capped at 0% reserve
    (decimal.Decimal("0.6"), 2, [decimal.Decimal("1"), decimal.Decimal("1")], decimal.Decimal("0")),
    # Partial tradable ratio: 50% allocation * 50% tradable = 25% effective, 75% reserve
    (decimal.Decimal("0.5"), 1, [decimal.Decimal("0.5")], decimal.Decimal("0.75")),
])
def test_update_global_distribution_reference_market_ratio(allocation, profiles_count, tradable_ratios, expected_ref_market):
    """Test reference market ratio calculation with various allocation scenarios."""
    distribution_per_exchange_profile = {}
    profile_ids = []
    for i in range(profiles_count):
        profile_id = f"profile{i+1}"
        profile_ids.append(profile_id)
        distribution_per_exchange_profile[profile_id] = _make_profile_dist(
            _make_distribution([(f"ASSET{i}", 100.0, decimal.Decimal("1000"))]),
            tradable_ratio=tradable_ratios[i]
        )
    
    result = profile_distribution.update_global_distribution(
        distribution_per_exchange_profile, allocation, profile_ids
    )
    assert result[profile_distribution.REFERENCE_MARKET_RATIO] == expected_ref_market


def test_get_smoothed_distribution_from_profile_data_aggregates_same_symbols():
    profile_data: "exchange_service_feed.ExchangeProfile" = MockProfileData("profile1", [
        {
            trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value: "BTC/USDT",
            trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value: 100.0,
            trading_enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value: 50000.0,
        },
        {
            trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value: "BTC/USDT",
            trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value: 50.0,
            trading_enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value: 51000.0,
        },
        {
            trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value: "ETH/USDT",
            trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value: 50.0,
            trading_enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value: 3000.0,
        },
    ])
    
    started_at = datetime.datetime.now()
    result, tradable_ratio, source = profile_distribution.get_smoothed_distribution_from_profile_data(
        profile_data, new_position_only=False, started_at=started_at
    )
    
    # All positions are tradable (no filters), so tradable_ratio should be 1.0
    assert tradable_ratio == decimal.Decimal("1")
    assert source == profile_distribution.DistributionSource.POSITIONS.value
    
    # BTC should have aggregated margin: 100 + 50 = 150 out of 200 total (75%)
    # ETH should have 50 out of 200 total (25%)
    btc_dist = next((d for d in result if d[index_distribution.DISTRIBUTION_NAME] == "BTC/USDT"), None)
    eth_dist = next((d for d in result if d[index_distribution.DISTRIBUTION_NAME] == "ETH/USDT"), None)
    
    assert btc_dist is not None
    assert eth_dist is not None
    # BTC should have higher value than ETH due to aggregated margin
    assert btc_dist[index_distribution.DISTRIBUTION_VALUE] > eth_dist[index_distribution.DISTRIBUTION_VALUE]
    # Verify price information is included in the distribution
    # When multiple positions have the same symbol, the last price is used (51000.0)
    assert btc_dist[index_distribution.DISTRIBUTION_PRICE] == decimal.Decimal("51000.0")
    assert eth_dist[index_distribution.DISTRIBUTION_PRICE] == decimal.Decimal("3000.0")

    # without prices
    profile_data.positions[-1].pop(trading_enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value)
    result, tradable_ratio, source = profile_distribution.get_smoothed_distribution_from_profile_data(
        profile_data, new_position_only=False, started_at=started_at
    )
    
    btc_dist = next((d for d in result if d[index_distribution.DISTRIBUTION_NAME] == "BTC/USDT"), None)
    eth_dist = next((d for d in result if d[index_distribution.DISTRIBUTION_NAME] == "ETH/USDT"), None)
    
    assert btc_dist is not None
    assert eth_dist is not None
    # BTC should still have price from the second BTC position (51000.0)
    assert btc_dist[index_distribution.DISTRIBUTION_PRICE] == decimal.Decimal("51000.0")
    # ETH should have price as 0 (default value when missing)
    assert eth_dist[index_distribution.DISTRIBUTION_PRICE] == decimal.Decimal("0")


def test_update_global_distribution_merges_identical_assets_from_multiple_profiles():
    distribution_per_exchange_profile = {
        "profile1": _make_profile_dist(_make_distribution([
            ("BTC", 100.0, decimal.Decimal("50000")),
        ])),
        "profile2": _make_profile_dist(_make_distribution([
            ("BTC", 100.0, decimal.Decimal("51000")),
        ])),
    }
    
    # Both profiles have same asset with same value, each gets 40% portfolio allocation
    result = profile_distribution.update_global_distribution(
        distribution_per_exchange_profile,
        decimal.Decimal("0.4"),  # 40% per profile
        ["profile1", "profile2"]
    )
    
    # Both profiles contribute 100.0 * 0.4 = 40.0, merged = 80.0
    assert result[profile_distribution.RATIO_PER_ASSET]["BTC"][index_distribution.DISTRIBUTION_VALUE] == decimal.Decimal("80.0")
    assert result[profile_distribution.TOTAL_RATIO_PER_ASSET] == decimal.Decimal("80.0")


def test_update_global_distribution_handles_missing_prices():
    distribution_per_exchange_profile = {
        "profile1": _make_profile_dist([
            {index_distribution.DISTRIBUTION_NAME: "BTC", index_distribution.DISTRIBUTION_VALUE: 50.0, index_distribution.DISTRIBUTION_PRICE: decimal.Decimal("50000")},
            {index_distribution.DISTRIBUTION_NAME: "ETH", index_distribution.DISTRIBUTION_VALUE: 30.0},  # No price
        ]),
        "profile2": _make_profile_dist([
            {index_distribution.DISTRIBUTION_NAME: "BTC", index_distribution.DISTRIBUTION_VALUE: 40.0},  # No price
            {index_distribution.DISTRIBUTION_NAME: "SOL", index_distribution.DISTRIBUTION_VALUE: 60.0, index_distribution.DISTRIBUTION_PRICE: decimal.Decimal("100")},
        ]),
    }
    
    result = profile_distribution.update_global_distribution(
        distribution_per_exchange_profile,
        decimal.Decimal("0.5"),
        ["profile1", "profile2"]
    )
    
    assert result[profile_distribution.INDEXED_COINS_PRICES]["BTC"] == decimal.Decimal("50000")
    # ETH: no price in any profile, so should not be in INDEXED_COINS_PRICES
    assert "ETH" not in result[profile_distribution.INDEXED_COINS_PRICES]
    assert result[profile_distribution.INDEXED_COINS_PRICES]["SOL"] == decimal.Decimal("100")

@pytest.mark.parametrize(
    "test_case",
    [
        TimestampTestCase(
            timestamp_offsets_and_symbols=[
                (-3600, "BTC/USDT"),  # 1 hour before - excluded
                (3600, "ETH/USDT"),   # 1 hour after - included
                (7200, "SOL/USDT"),   # 2 hours after - included
            ],
            expected_symbols=["ETH/USDT", "SOL/USDT"],
        ),
        TimestampTestCase(
            timestamp_offsets_and_symbols=[
                (-3600, "BTC/USDT"),  # 1 hour before - excluded
                (-1800, "ETH/USDT"),  # 30 minutes before - excluded
            ],
            expected_symbols=[],
        ),
        TimestampTestCase(
            timestamp_offsets_and_symbols=[
                (0, "BTC/USDT"),      # Exactly at - excluded
                (1, "ETH/USDT"),      # 1 second after - included
            ],
            expected_symbols=["ETH/USDT"],
        ),
    ],
)
def test_get_positions_to_consider_filters_by_timestamp_when_new_position_only_true(test_case: TimestampTestCase):
    """Test that positions are filtered by timestamp when new_position_only is True"""
    started_at = datetime.datetime(2024, 1, 1, 12, 0, 0)
    profile_positions = [
        {
            trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value: symbol,
            trading_enums.ExchangeConstantsPositionColumns.TIMESTAMP.value: started_at.timestamp() + offset_seconds,
        }
        for offset_seconds, symbol in test_case.timestamp_offsets_and_symbols
    ]
    
    result = profile_distribution.get_positions_to_consider(
        profile_positions, new_position_only=True, started_at=started_at
    )
    
    result_symbols = [
        pos[trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value] for pos in result
    ]
    assert result_symbols == test_case.expected_symbols


@pytest.mark.parametrize(
    "test_case",
    [
        NewPositionOnlyTestCase(
            new_position_only=True,
            expected_btc_present=False,
            expected_eth_present=True,
            btc_higher_than_eth=None,
        ),  # Only new positions (ETH) included
        NewPositionOnlyTestCase(
            new_position_only=False,
            expected_btc_present=True,
            expected_eth_present=True,
            btc_higher_than_eth=True,
        ),  # All positions included, BTC has higher margin
    ],
)
def test_get_smoothed_distribution_from_profile_data_respects_new_position_only(
    test_case: NewPositionOnlyTestCase
):
    """Test that get_smoothed_distribution_from_profile_data respects new_position_only parameter"""
    started_at = datetime.datetime(2024, 1, 1, 12, 0, 0)
    profile_data: "exchange_service_feed.ExchangeProfile" = MockProfileData("profile1", [
        {
            trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value: "BTC/USDT",
            trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value: 100.0,
            trading_enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value: 50000.0,
            trading_enums.ExchangeConstantsPositionColumns.TIMESTAMP.value: started_at.timestamp() - 3600,
        },
        {
            trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value: "ETH/USDT",
            trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value: 50.0,
            trading_enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value: 3000.0,
            trading_enums.ExchangeConstantsPositionColumns.TIMESTAMP.value: started_at.timestamp() + 3600,
        },
    ])
    
    result, tradable_ratio, source = profile_distribution.get_smoothed_distribution_from_profile_data(
        profile_data, new_position_only=test_case.new_position_only, started_at=started_at
    )
    
    btc_dist = next((d for d in result if d[index_distribution.DISTRIBUTION_NAME] == "BTC/USDT"), None)
    eth_dist = next((d for d in result if d[index_distribution.DISTRIBUTION_NAME] == "ETH/USDT"), None)
    
    assert (btc_dist is not None) == test_case.expected_btc_present
    assert (eth_dist is not None) == test_case.expected_eth_present
    
    if test_case.expected_eth_present:
        assert eth_dist[index_distribution.DISTRIBUTION_VALUE] > decimal.Decimal("0")
        assert eth_dist[index_distribution.DISTRIBUTION_PRICE] == decimal.Decimal("3000.0")
    
    if test_case.btc_higher_than_eth and btc_dist is not None and eth_dist is not None:
        assert btc_dist[index_distribution.DISTRIBUTION_VALUE] > eth_dist[index_distribution.DISTRIBUTION_VALUE]


@pytest.mark.parametrize(
    "new_position_only,expected_btc_present,expected_eth_present",
    [
        (True, False, True),   # Only new positions (ETH) included
        (False, True, True),  # All positions included
    ],
)
def test_update_distribution_based_on_profile_data_respects_new_position_only(
    new_position_only, expected_btc_present, expected_eth_present
):
    """Test that update_distribution_based_on_profile_data respects new_position_only parameter"""
    started_at = datetime.datetime(2024, 1, 1, 12, 0, 0)
    profile_data: "exchange_service_feed.ExchangeProfile" = MockProfileData("profile1", [
        {
            trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value: "BTC/USDT",
            trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value: 100.0,
            trading_enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value: 50000.0,
            trading_enums.ExchangeConstantsPositionColumns.TIMESTAMP.value: started_at.timestamp() - 3600,
        },
        {
            trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value: "ETH/USDT",
            trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value: 50.0,
            trading_enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value: 3000.0,
            trading_enums.ExchangeConstantsPositionColumns.TIMESTAMP.value: started_at.timestamp() + 3600,
        },
    ])
    
    result = profile_distribution.update_distribution_based_on_profile_data(
        profile_data, {}, new_position_only=new_position_only, started_at=started_at
    )
    
    assert "profile1" in result
    profile_result = result["profile1"]
    distribution = profile_result["distribution"]
    btc_dist = next((d for d in distribution if d[index_distribution.DISTRIBUTION_NAME] == "BTC/USDT"), None)
    eth_dist = next((d for d in distribution if d[index_distribution.DISTRIBUTION_NAME] == "ETH/USDT"), None)
    
    assert (btc_dist is not None) == expected_btc_present
    assert (eth_dist is not None) == expected_eth_present

def _position(symbol: str, collateral: float, unrealized_pnl: float, initial_margin: float = None, entry_price: float = 50000.0, mark_price: float = None) -> dict:
    m = {
        trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value: symbol,
        trading_enums.ExchangeConstantsPositionColumns.COLLATERAL.value: collateral,
        trading_enums.ExchangeConstantsPositionColumns.UNREALIZED_PNL.value: unrealized_pnl,
        trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value: initial_margin if initial_margin is not None else collateral,
        trading_enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value: entry_price,
    }
    if mark_price is not None:
        m[trading_enums.ExchangeConstantsPositionColumns.MARK_PRICE.value] = mark_price
    return m


@pytest.mark.parametrize(
    "test_case",
    [
        UnrealizedPnlTestCase(
            min_unrealized_pnl_percent=None,
            max_unrealized_pnl_percent=None,
            positions=[_position("A", 100.0, 5.0), _position("B", 100.0, 15.0)],
            expected_symbols=["A", "B"],
        ),
        UnrealizedPnlTestCase(
            min_unrealized_pnl_percent=0.1,
            max_unrealized_pnl_percent=None,
            positions=[_position("A", 100.0, 10.0), _position("B", 100.0, 5.0)],
            expected_symbols=["A"],
        ),
        UnrealizedPnlTestCase(
            min_unrealized_pnl_percent=0.1,
            max_unrealized_pnl_percent=None,
            positions=[_position("A", 0.0, 5.0)],
            expected_symbols=["A"],
        ),
        UnrealizedPnlTestCase(
            min_unrealized_pnl_percent=None,
            max_unrealized_pnl_percent=0.1,
            positions=[_position("A", 100.0, 5.0), _position("B", 100.0, 10.0), _position("C", 100.0, 15.0)],
            expected_symbols=["A", "B"],
        ),
        UnrealizedPnlTestCase(
            min_unrealized_pnl_percent=0.05,
            max_unrealized_pnl_percent=0.15,
            positions=[_position("A", 100.0, 5.0), _position("B", 100.0, 10.0), _position("C", 100.0, 15.0), _position("D", 100.0, 20.0)],
            expected_symbols=["A", "B", "C"],
        ),
    ],
)
def test_get_positions_to_consider_min_max_unrealized_pnl_ratio(test_case: UnrealizedPnlTestCase):
    started_at = datetime.datetime(2024, 1, 1, 12, 0, 0)
    result = profile_distribution.get_positions_to_consider(
        test_case.positions, new_position_only=False, started_at=started_at,
        min_unrealized_pnl_percent=test_case.min_unrealized_pnl_percent,
        max_unrealized_pnl_percent=test_case.max_unrealized_pnl_percent,
    )
    assert [p[trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value] for p in result] == test_case.expected_symbols


def test_get_smoothed_distribution_from_profile_data_respects_min_unrealized_pnl_ratio():
    profile_data = MockProfileData("p1", [
        _position("BTC/USDT", 100.0, 10.0),
        _position("ETH/USDT", 100.0, 5.0),
    ])
    started_at = datetime.datetime(2024, 1, 1, 12, 0, 0)
    result, tradable_ratio, source = profile_distribution.get_smoothed_distribution_from_profile_data(
        profile_data, new_position_only=False, started_at=started_at,
        min_unrealized_pnl_percent=0.1,
    )
    symbols = [d[index_distribution.DISTRIBUTION_NAME] for d in result]
    assert "BTC/USDT" in symbols
    assert "ETH/USDT" not in symbols
    assert tradable_ratio == decimal.Decimal("0.5")


@pytest.mark.parametrize(
    "test_case",
    [
        MarkPriceTestCase(
            min_mark_price=None,
            max_mark_price=None,
            positions=[_position("A", 100.0, 5.0, mark_price=100.0), _position("B", 100.0, 5.0, mark_price=200.0)],
            expected_symbols=["A", "B"],
        ),
        MarkPriceTestCase(
            min_mark_price=decimal.Decimal("150"),
            max_mark_price=None,
            positions=[_position("A", 100.0, 5.0, mark_price=100.0), _position("B", 100.0, 5.0, mark_price=200.0)],
            expected_symbols=["B"],
        ),
        MarkPriceTestCase(
            min_mark_price=None,
            max_mark_price=decimal.Decimal("150"),
            positions=[_position("A", 100.0, 5.0, mark_price=100.0), _position("B", 100.0, 5.0, mark_price=200.0)],
            expected_symbols=["A"],
        ),
        MarkPriceTestCase(
            min_mark_price=decimal.Decimal("150"),
            max_mark_price=decimal.Decimal("250"),
            positions=[_position("A", 100.0, 5.0, mark_price=100.0), _position("B", 100.0, 5.0, mark_price=200.0), _position("C", 100.0, 5.0, mark_price=300.0)],
            expected_symbols=["B"],
        ),
    ],
)
def test_get_positions_to_consider_min_max_mark_price(test_case: MarkPriceTestCase):
    started_at = datetime.datetime(2024, 1, 1, 12, 0, 0)
    result = profile_distribution.get_positions_to_consider(
        test_case.positions, new_position_only=False, started_at=started_at,
        min_mark_price=test_case.min_mark_price, max_mark_price=test_case.max_mark_price,
    )
    assert [p[trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value] for p in result] == test_case.expected_symbols


@pytest.mark.parametrize(
    "test_case",
    [
        TradableRatioTestCase(
            margins=[100.0, 100.0, 100.0],
            filtered_count=1,
            expected_tradable_ratio=decimal.Decimal("2") / decimal.Decimal("3"),
        ),
        TradableRatioTestCase(
            margins=[200.0, 100.0, 100.0],
            filtered_count=1,
            expected_tradable_ratio=decimal.Decimal("0.5"),
        ),
        TradableRatioTestCase(
            margins=[100.0, 100.0, 100.0],
            filtered_count=2,
            expected_tradable_ratio=decimal.Decimal("1") / decimal.Decimal("3"),
        ),
    ],
)
def test_tradable_ratio_calculation(test_case: TradableRatioTestCase):
    """Test tradable_ratio calculation with various margin and filter scenarios."""
    # Create positions where first `filtered_count` have low mark_price (will be filtered)
    positions = []
    for i, margin in enumerate(test_case.margins):
        mark_price = 100.0 if i < test_case.filtered_count else 200.0
        positions.append(_position(f"ASSET{i}/USDT", margin, 5.0, mark_price=mark_price))
    
    profile_data = MockProfileData("p1", positions)
    started_at = datetime.datetime(2024, 1, 1, 12, 0, 0)
    
    result, tradable_ratio, source = profile_distribution.get_smoothed_distribution_from_profile_data(
        profile_data, new_position_only=False, started_at=started_at,
        min_mark_price=decimal.Decimal("150"),  # Filters positions with mark_price < 150
    )
    
    assert abs(tradable_ratio - test_case.expected_tradable_ratio) < decimal.Decimal("0.0001")


def test_tradable_ratio_with_new_position_only():
    """Test tradable_ratio when filtering by new_position_only."""
    started_at = datetime.datetime(2024, 1, 1, 12, 0, 0)
    profile_data = MockProfileData("p1", [
        {
            trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value: "BTC/USDT",
            trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value: 100.0,
            trading_enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value: 50000.0,
            trading_enums.ExchangeConstantsPositionColumns.TIMESTAMP.value: started_at.timestamp() - 3600,  # old
        },
        {
            trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value: "ETH/USDT",
            trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value: 100.0,
            trading_enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value: 3000.0,
            trading_enums.ExchangeConstantsPositionColumns.TIMESTAMP.value: started_at.timestamp() + 3600,  # new
        },
    ])
    
    result, tradable_ratio, source = profile_distribution.get_smoothed_distribution_from_profile_data(
        profile_data, new_position_only=True, started_at=started_at,
    )
    
    # Only ETH should be in distribution (BTC is old), tradable_ratio = 100/200 = 0.5
    symbols = [d[index_distribution.DISTRIBUTION_NAME] for d in result]
    assert "BTC/USDT" not in symbols
    assert "ETH/USDT" in symbols
    assert tradable_ratio == decimal.Decimal("0.5")

@pytest.mark.parametrize(
    "test_case",
    [
        PortfolioTestCase(
            name="portfolio_when_no_positions",
            positions=[],  # No positions
            portfolio={"BTC": decimal.Decimal("1.0"), "ETH": decimal.Decimal("10.0"), "USDT": decimal.Decimal("1000.0")},  # Portfolio
            expected_source=profile_distribution.DistributionSource.PORTFOLIO.value,
            expected_tradable_ratio=trading_constants.ONE,
            expected_symbols=["BTC", "ETH", "USDT"],
            excluded_symbols=[],  # No excluded symbols
            weight_assertion=None,  # No weight assertion
        ),
        PortfolioTestCase(
            name="prefers_positions_over_portfolio",
            positions=[  # Has positions
                {
                    trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value: "SOL/USDT",
                    trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value: 100.0,
                    trading_enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value: 100.0,
                },
            ],
            portfolio={"BTC": decimal.Decimal("1.0"), "ETH": decimal.Decimal("10.0")},  # Has portfolio too
            expected_source=profile_distribution.DistributionSource.POSITIONS.value,
            expected_tradable_ratio=trading_constants.ONE,
            expected_symbols=["SOL/USDT"],
            excluded_symbols=["BTC", "ETH"],  # These should NOT be present
            weight_assertion=None,  # No weight assertion
        ),
        PortfolioTestCase(
            name="empty_profile",
            positions=[],  # No positions
            portfolio=None,  # No portfolio
            expected_source=profile_distribution.DistributionSource.POSITIONS.value,
            expected_tradable_ratio=trading_constants.ZERO,
            expected_symbols=[],  # Empty result
            excluded_symbols=[],  # No excluded symbols
            weight_assertion=None,  # No weight assertion
        ),
        PortfolioTestCase(
            name="portfolio_weights",
            positions=[],  # No positions
            portfolio={"BTC": decimal.Decimal("2.0"), "ETH": decimal.Decimal("10.0")},  # Portfolio with different weights
            expected_source=profile_distribution.DistributionSource.PORTFOLIO.value,
            expected_tradable_ratio=trading_constants.ONE,
            expected_symbols=["BTC", "ETH"],
            excluded_symbols=[],  # No excluded symbols
            weight_assertion="ETH > BTC",  # ETH should have higher weight than BTC
        ),
    ],
)
def test_get_smoothed_distribution_portfolio_scenarios(test_case: PortfolioTestCase):
    portfolio_obj = MockPortfolio(test_case.portfolio) if test_case.portfolio is not None else None
    profile_data = MockProfileData("profile1", positions=test_case.positions, portfolio=portfolio_obj)
    
    started_at = datetime.datetime.now()
    result, tradable_ratio, source = profile_distribution.get_smoothed_distribution_from_profile_data(
        profile_data, new_position_only=False, started_at=started_at
    )
    
    assert source == test_case.expected_source
    assert tradable_ratio == test_case.expected_tradable_ratio
    
    symbols = [d[index_distribution.DISTRIBUTION_NAME] for d in result]
    assert symbols == test_case.expected_symbols
    
    # Check excluded symbols are not present
    for symbol in test_case.excluded_symbols:
        assert symbol not in symbols
    
    # Check weight assertions
    if test_case.weight_assertion == "ETH > BTC":
        btc_dist = next((d for d in result if d[index_distribution.DISTRIBUTION_NAME] == "BTC"), None)
        eth_dist = next((d for d in result if d[index_distribution.DISTRIBUTION_NAME] == "ETH"), None)
        assert eth_dist[index_distribution.DISTRIBUTION_VALUE] > btc_dist[index_distribution.DISTRIBUTION_VALUE]

@pytest.mark.parametrize("allocation_ratio,padding_ratio,expected_ref_market", [
    # No padding: 50% allocation = 50% reference market
    (decimal.Decimal("0.5"), decimal.Decimal("0"), decimal.Decimal("0.5")),
    # 20% padding on 50% allocation, but still only 100% tradable means effective = 50%
    (decimal.Decimal("0.5"), decimal.Decimal("0.2"), decimal.Decimal("0.5")),
    # Full allocation: 0% reference market
    (decimal.Decimal("1.0"), decimal.Decimal("0"), decimal.Decimal("0")),
])
def test_update_global_distribution_allocation_padding_ratio(allocation_ratio, padding_ratio, expected_ref_market):
    """Test that allocation_padding_ratio is correctly applied."""
    distribution_per_exchange_profile = {
        "profile1": _make_profile_dist(_make_distribution([
            ("BTC", 100.0, decimal.Decimal("50000")),
        ]), tradable_ratio=trading_constants.ONE),
    }
    
    result = profile_distribution.update_global_distribution(
        distribution_per_exchange_profile,
        allocation_ratio,
        ["profile1"],
        allocation_padding_ratio=padding_ratio
    )
    
    assert result[profile_distribution.REFERENCE_MARKET_RATIO] == expected_ref_market


def test_update_global_distribution_allocation_padding_allows_more_usage():
    # Profile with 50% tradable ratio
    distribution_per_exchange_profile = {
        "profile1": _make_profile_dist(_make_distribution([
            ("BTC", 100.0, decimal.Decimal("50000")),
        ]), tradable_ratio=decimal.Decimal("0.5")),
    }
    
    # 50% allocation with 50% tradable = 25% effective allocation
    result_no_padding = profile_distribution.update_global_distribution(
        distribution_per_exchange_profile,
        decimal.Decimal("0.5"),
        ["profile1"],
        allocation_padding_ratio=decimal.Decimal("0")
    )
    
    # 75% reference market (1 - 0.25)
    assert result_no_padding[profile_distribution.REFERENCE_MARKET_RATIO] == decimal.Decimal("0.75")
    
    # With padding, the effective allocation is still capped by tradable_ratio
    # 50% * 0.5 tradable = 25%, capped at 50% * 1.2 = 60% max
    result_with_padding = profile_distribution.update_global_distribution(
        distribution_per_exchange_profile,
        decimal.Decimal("0.5"),
        ["profile1"],
        allocation_padding_ratio=decimal.Decimal("0.2")
    )
    
    # Same result since tradable_ratio < 1 anyway
    assert result_with_padding[profile_distribution.REFERENCE_MARKET_RATIO] == decimal.Decimal("0.75")
