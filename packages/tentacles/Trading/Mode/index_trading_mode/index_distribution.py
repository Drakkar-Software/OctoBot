import decimal
import typing
import numpy

import octobot_trading.constants
import octobot_copy.enums as copy_enums
import octobot_copy.rebalancing.planner.distributions as planner_distributions

MAX_DISTRIBUTION_AFTER_COMMA_DIGITS = 1

get_uniform_distribution = planner_distributions.get_uniform_distribution


def get_linear_distribution(weight_by_coin: dict[str, decimal.Decimal], price_by_coin: typing.Optional[dict[str, decimal.Decimal]] = None) -> typing.List:
    total_weight = sum(weight for weight in weight_by_coin.values())
    if total_weight <= octobot_trading.constants.ZERO:
        raise ValueError(f"total weight is {total_weight}")
    return [
        {
            copy_enums.DistributionKeys.NAME.value: coin,
            copy_enums.DistributionKeys.VALUE.value: float(round(
                weight / total_weight * octobot_trading.constants.ONE_HUNDRED,
                MAX_DISTRIBUTION_AFTER_COMMA_DIGITS
            )),
            copy_enums.DistributionKeys.PRICE.value: price_by_coin.get(coin) if price_by_coin else None
        }
        for coin, weight in weight_by_coin.items()
    ]


def get_smoothed_distribution(weight_by_coin: dict[str, decimal.Decimal], price_by_coin: typing.Optional[dict[str, decimal.Decimal]] = None) -> typing.List:
    return get_linear_distribution({
        coin: decimal.Decimal(str(numpy.cbrt(float(weight))))
        for coin, weight in weight_by_coin.items()
    }, price_by_coin)
