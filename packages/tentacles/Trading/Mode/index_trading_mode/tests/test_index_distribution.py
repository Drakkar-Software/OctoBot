import decimal
import pytest

import tentacles.Trading.Mode.index_trading_mode.index_distribution as index_distribution
import octobot_copy.enums as copy_enums


def test_get_uniform_distribution():
    assert index_distribution.get_uniform_distribution([], {}) == []
    assert index_distribution.get_uniform_distribution(
        ["BTC", "1", "2", "3"],
        {"BTC": decimal.Decimal("50000"), "1": decimal.Decimal("100"), "2": decimal.Decimal("200"), "3": decimal.Decimal("300")}
    ) == [
        {
            copy_enums.DistributionKeys.NAME: "BTC",
            copy_enums.DistributionKeys.VALUE: 25,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("50000"),
        },
        {
            copy_enums.DistributionKeys.NAME: "1",
            copy_enums.DistributionKeys.VALUE: 25,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("100"),
        },
        {
            copy_enums.DistributionKeys.NAME: "2",
            copy_enums.DistributionKeys.VALUE: 25,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("200"),
        },
        {
            copy_enums.DistributionKeys.NAME: "3",
            copy_enums.DistributionKeys.VALUE: 25,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("300"),
        }
    ]
    assert index_distribution.get_uniform_distribution(
        ["BTC", "1", "2"],
        {"BTC": decimal.Decimal("50000"), "1": decimal.Decimal("100"), "2": decimal.Decimal("200")}
    ) == [
        {
            copy_enums.DistributionKeys.NAME: "BTC",
            copy_enums.DistributionKeys.VALUE: 33.3,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("50000"),
        },
        {
            copy_enums.DistributionKeys.NAME: "1",
            copy_enums.DistributionKeys.VALUE: 33.3,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("100"),
        },
        {
            copy_enums.DistributionKeys.NAME: "2",
            copy_enums.DistributionKeys.VALUE: 33.3,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("200"),
        },
    ]
    # Test when price_by_coin is None
    assert index_distribution.get_uniform_distribution(
        ["BTC", "1", "2"],
        None
    ) == [
        {
            copy_enums.DistributionKeys.NAME: "BTC",
            copy_enums.DistributionKeys.VALUE: 33.3,
            copy_enums.DistributionKeys.PRICE: None,
        },
        {
            copy_enums.DistributionKeys.NAME: "1",
            copy_enums.DistributionKeys.VALUE: 33.3,
            copy_enums.DistributionKeys.PRICE: None,
        },
        {
            copy_enums.DistributionKeys.NAME: "2",
            copy_enums.DistributionKeys.VALUE: 33.3,
            copy_enums.DistributionKeys.PRICE: None,
        },
    ]
    # Test when some coins are not in price_by_coin
    assert index_distribution.get_uniform_distribution(
        ["BTC", "1", "2", "3"],
        {"BTC": decimal.Decimal("50000"), "1": decimal.Decimal("100")}
    ) == [
        {
            copy_enums.DistributionKeys.NAME: "BTC",
            copy_enums.DistributionKeys.VALUE: 25,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("50000"),
        },
        {
            copy_enums.DistributionKeys.NAME: "1",
            copy_enums.DistributionKeys.VALUE: 25,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("100"),
        },
        {
            copy_enums.DistributionKeys.NAME: "2",
            copy_enums.DistributionKeys.VALUE: 25,
            copy_enums.DistributionKeys.PRICE: None,
        },
        {
            copy_enums.DistributionKeys.NAME: "3",
            copy_enums.DistributionKeys.VALUE: 25,
            copy_enums.DistributionKeys.PRICE: None,
        }
    ]


def test_get_linear_distribution():
    with pytest.raises(ValueError):
        index_distribution.get_linear_distribution({}, {})
    assert index_distribution.get_linear_distribution({
        "BTC": decimal.Decimal(122),
        "1": decimal.Decimal(12),
        "2": decimal.Decimal("0.4"),
        "3": decimal.Decimal(44)
    }, {
        "BTC": decimal.Decimal("50000"),
        "1": decimal.Decimal("100"),
        "2": decimal.Decimal("200"),
        "3": decimal.Decimal("300")
    }) == [
        {
            copy_enums.DistributionKeys.NAME: "BTC",
            copy_enums.DistributionKeys.VALUE: 68.4,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("50000"),
        },
        {
            copy_enums.DistributionKeys.NAME: "1",
            copy_enums.DistributionKeys.VALUE: 6.7,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("100"),
        },
        {
            copy_enums.DistributionKeys.NAME: "2",
            copy_enums.DistributionKeys.VALUE: 0.2,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("200"),
        },
        {
            copy_enums.DistributionKeys.NAME: "3",
            copy_enums.DistributionKeys.VALUE: 24.7,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("300"),
        }
    ]
    assert index_distribution.get_linear_distribution({
        "BTC": decimal.Decimal(12332),
        "1": decimal.Decimal(12),
        "3": decimal.Decimal(433334)
    }, {
        "BTC": decimal.Decimal("50000"),
        "1": decimal.Decimal("100"),
        "3": decimal.Decimal("300")
    }) == [
        {
            copy_enums.DistributionKeys.NAME: "BTC",
            copy_enums.DistributionKeys.VALUE: 2.8,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("50000"),
        },
        {
            copy_enums.DistributionKeys.NAME: "1",
            copy_enums.DistributionKeys.VALUE: 0,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("100"),
        },
        {
            copy_enums.DistributionKeys.NAME: "3",
            copy_enums.DistributionKeys.VALUE: 97.2,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("300"),
        },
    ]
    # Test when price_by_coin is None
    assert index_distribution.get_linear_distribution({
        "BTC": decimal.Decimal(122),
        "1": decimal.Decimal(12),
        "2": decimal.Decimal("0.4"),
        "3": decimal.Decimal(44)
    }, None) == [
        {
            copy_enums.DistributionKeys.NAME: "BTC",
            copy_enums.DistributionKeys.VALUE: 68.4,
            copy_enums.DistributionKeys.PRICE: None,
        },
        {
            copy_enums.DistributionKeys.NAME: "1",
            copy_enums.DistributionKeys.VALUE: 6.7,
            copy_enums.DistributionKeys.PRICE: None,
        },
        {
            copy_enums.DistributionKeys.NAME: "2",
            copy_enums.DistributionKeys.VALUE: 0.2,
            copy_enums.DistributionKeys.PRICE: None,
        },
        {
            copy_enums.DistributionKeys.NAME: "3",
            copy_enums.DistributionKeys.VALUE: 24.7,
            copy_enums.DistributionKeys.PRICE: None,
        }
    ]
    # Test when some coins are not in price_by_coin
    assert index_distribution.get_linear_distribution({
        "BTC": decimal.Decimal(122),
        "1": decimal.Decimal(12),
        "2": decimal.Decimal("0.4"),
        "3": decimal.Decimal(44)
    }, {
        "BTC": decimal.Decimal("50000"),
        "3": decimal.Decimal("300")
    }) == [
        {
            copy_enums.DistributionKeys.NAME: "BTC",
            copy_enums.DistributionKeys.VALUE: 68.4,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("50000"),
        },
        {
            copy_enums.DistributionKeys.NAME: "1",
            copy_enums.DistributionKeys.VALUE: 6.7,
            copy_enums.DistributionKeys.PRICE: None,
        },
        {
            copy_enums.DistributionKeys.NAME: "2",
            copy_enums.DistributionKeys.VALUE: 0.2,
            copy_enums.DistributionKeys.PRICE: None,
        },
        {
            copy_enums.DistributionKeys.NAME: "3",
            copy_enums.DistributionKeys.VALUE: 24.7,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("300"),
        }
    ]


def test_get_smoothed_distribution():
    with pytest.raises(ValueError):
        index_distribution.get_smoothed_distribution({})
    assert index_distribution.get_smoothed_distribution({
        "BTC": decimal.Decimal(122),
        "1": decimal.Decimal(12),
        "2": decimal.Decimal("0.4"),
        "3": decimal.Decimal(44)
    }) == [
        {
            copy_enums.DistributionKeys.NAME: "BTC",
            copy_enums.DistributionKeys.VALUE: 43.1,
            copy_enums.DistributionKeys.PRICE: None,
        },
        {
            copy_enums.DistributionKeys.NAME: "1",
            copy_enums.DistributionKeys.VALUE: 19.9,
            copy_enums.DistributionKeys.PRICE: None,
        },
        {
            copy_enums.DistributionKeys.NAME: "2",
            copy_enums.DistributionKeys.VALUE: 6.4,
            copy_enums.DistributionKeys.PRICE: None,
        },
        {
            copy_enums.DistributionKeys.NAME: "3",
            copy_enums.DistributionKeys.VALUE: 30.7,
            copy_enums.DistributionKeys.PRICE: None,
        }
    ]
    assert index_distribution.get_smoothed_distribution({
        "BTC": decimal.Decimal(12332),
        "1": decimal.Decimal(12),
        "3": decimal.Decimal(433334)
    }) == [
        {
            copy_enums.DistributionKeys.NAME: "BTC",
            copy_enums.DistributionKeys.VALUE: 22.9,
            copy_enums.DistributionKeys.PRICE: None,
        },
        {
            copy_enums.DistributionKeys.NAME: "1",
            copy_enums.DistributionKeys.VALUE: 2.3,
            copy_enums.DistributionKeys.PRICE: None,
        },
        {
            copy_enums.DistributionKeys.NAME: "3",
            copy_enums.DistributionKeys.VALUE: 74.9,
            copy_enums.DistributionKeys.PRICE: None,
        },
    ]
    # Test when price_by_coin is provided
    assert index_distribution.get_smoothed_distribution({
        "BTC": decimal.Decimal(122),
        "1": decimal.Decimal(12),
        "2": decimal.Decimal("0.4"),
        "3": decimal.Decimal(44)
    }, {
        "BTC": decimal.Decimal("50000"),
        "1": decimal.Decimal("100"),
        "2": decimal.Decimal("200"),
        "3": decimal.Decimal("300")
    }) == [
        {
            copy_enums.DistributionKeys.NAME: "BTC",
            copy_enums.DistributionKeys.VALUE: 43.1,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("50000"),
        },
        {
            copy_enums.DistributionKeys.NAME: "1",
            copy_enums.DistributionKeys.VALUE: 19.9,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("100"),
        },
        {
            copy_enums.DistributionKeys.NAME: "2",
            copy_enums.DistributionKeys.VALUE: 6.4,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("200"),
        },
        {
            copy_enums.DistributionKeys.NAME: "3",
            copy_enums.DistributionKeys.VALUE: 30.7,
            copy_enums.DistributionKeys.PRICE: decimal.Decimal("300"),
        }
    ]
