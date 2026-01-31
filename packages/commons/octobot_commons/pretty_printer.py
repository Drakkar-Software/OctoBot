# pylint: disable=C0415
#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import octobot_commons
import octobot_commons.enums as enums
import octobot_commons.constants as constants
import octobot_commons.logging as logging_util
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_commons.timestamp_util as timestamp_util
import octobot_commons.number_util as number_util

ORDER_TIME_FORMAT = "%m-%d %H:%M"
LOGGER = logging_util.get_logger("PrettyPrinter")


def open_order_pretty_printer(exchange_name, dict_order, markdown=False) -> str:
    """
    Open Order pretty printer
    :param exchange_name: the exchange name
    :param dict_order: the order dict
    :param markdown: if printer use markdown
    :return: the order pretty printed
    """
    try:
        from octobot_trading.enums import (
            ExchangeConstantsOrderColumns,
            TraderOrderType,
            TradeOrderSide,
        )
        from octobot_trading.api.orders import parse_order_type

        _, _, code = get_markers(markdown)
        market = symbol_util.parse_symbol(
            str(dict_order.get(ExchangeConstantsOrderColumns.SYMBOL.value, ""))
        ).quote
        quantity_currency = dict_order.get(
            ExchangeConstantsOrderColumns.QUANTITY_CURRENCY.value, ""
        )
        order_type = parse_order_type(dict_order)
        if order_type == TraderOrderType.UNKNOWN:
            order_type = TradeOrderSide(
                dict_order.get(ExchangeConstantsOrderColumns.SIDE.value)
            )
        quantity = dict_order.get(ExchangeConstantsOrderColumns.AMOUNT.value, 0.0)
        price = dict_order.get(ExchangeConstantsOrderColumns.PRICE.value, 0.0)

        return (
            f"{code}{order_type.name.replace('_', ' ')}{code}: {code}"
            f"{get_min_string_from_number(quantity)} "
            f"{quantity_currency}{code} at {code}"
            f"{get_min_string_from_number(price)} {market}{code} "
            f"on {exchange_name.capitalize()}"
        )
    except ImportError:
        LOGGER.error(
            "open_order_pretty_printer requires OctoBot-Trading package installed"
        )
    return ""


def trade_pretty_printer(exchange_name, trade, markdown=False) -> str:
    """
    Trade pretty printer
    :param exchange_name: the exchange name
    :param trade: the trade object
    :param markdown: if printer use markdown
    :return: the trade pretty printed
    """
    try:
        from octobot_trading.enums import TraderOrderType

        _, _, code = get_markers(markdown)
        trade_type = trade.trade_type
        if trade_type == TraderOrderType.UNKNOWN:
            trade_type = trade.side

        trade_executed_time_str = (
            timestamp_util.convert_timestamp_to_datetime(
                trade.executed_time, time_format=ORDER_TIME_FORMAT, local_timezone=True
            )
            if trade.executed_time
            else ""
        )
        return (
            f"{code}{trade_type.name.replace('_', ' ')}{code}: {code}"
            f"{get_min_string_from_number(trade.executed_quantity)} "
            f"{trade.quantity_currency}{code} at {code}"
            f"{get_min_string_from_number(trade.executed_price)} {trade.market}{code} "
            f"{exchange_name.capitalize()} "
            f"{trade_executed_time_str} "
        )
    except ImportError:
        LOGGER.error(
            "open_order_pretty_printer requires OctoBot-Trading package installed"
        )
    return ""


def cryptocurrency_alert(result, final_eval) -> (str, str):
    """
    Cryptocurrency alert
    :param result: the result
    :param final_eval: the final eval
    :return: alert and the markdown alert
    """
    try:
        import telegram.helpers

        _, _, code = get_markers(True)
        display_result = str(result).split(".")[1].replace("_", " ")
        alert = f"Result : {display_result}\n" f"Evaluation : {final_eval}"
        alert_markdown = (
            f"Result : {code}{display_result}{code}\n"
            f"Evaluation : {code}{telegram.helpers.escape_markdown(str(final_eval))}{code}"
        )
        return alert, alert_markdown
    except ImportError:
        LOGGER.error("cryptocurrency_alert requires Telegram package installed")
    return "", ""


def _get_row_pretty_portfolio_row(holdings, currency, ref_market, ref_market_value):
    """
    :return: the portfolio row adapted for a raw format
    """
    str_holdings = get_min_string_from_number(holdings)
    if ref_market:
        return f"{str_holdings} {currency}{get_min_string_from_number(ref_market_value)} {ref_market}"
    return f"{str_holdings} {currency}"


def _get_max_digits(number):
    abs_number = abs(number)
    if abs_number < 0.0001:
        return 8
    if abs_number < 0.01:
        return 6
    if abs_number < 1:
        return 4
    if abs_number < 10000:
        return 2
    return 0


def _get_markdown_pretty_portfolio_row(
    holdings, currency, ref_market, ref_market_value
):
    """
    :return: the portfolio row adapted for a markdown format
    """
    str_currency = "{:<4}".format(currency)
    str_holdings = "{:<12}".format(get_min_string_from_number(holdings))
    str_ref_market_value = "{:<12}".format("")
    if ref_market:
        str_ref_market_value = "{:<12}".format(
            get_min_string_from_number(ref_market_value)
        )
    return f"{str_currency} {str_holdings} {str_ref_market_value}"


def global_portfolio_pretty_print(
    global_portfolio,
    currency_values=None,
    ref_market_name=None,
    separator="\n",
    markdown=False,
) -> str:
    """
    Global portfolio pretty printer
    :param global_portfolio: the global portfolio
    :param currency_values: dict of current currency values {"BTC": 20000, "ETH": 1000 }
    :param ref_market_name: current ref market "USD"
    :param separator: the printer separator
    :param markdown: if printer use markdown
    :return: the global portfolio pretty printed
    """
    results = []
    currency = "currency"
    holdings = "holdings"
    value = "value"
    for asset, asset_dict in global_portfolio.items():
        if asset_dict[constants.PORTFOLIO_TOTAL] > 0:
            holdings_value = 0
            if currency_values and ref_market_name:
                if ref_market_name == asset:
                    holdings_value = asset_dict[constants.PORTFOLIO_TOTAL]
                else:
                    try:
                        holdings_value = (
                            currency_values[asset]
                            * asset_dict[constants.PORTFOLIO_TOTAL]
                        )
                    except KeyError:
                        # no currency value
                        pass
            results.append(
                {
                    currency: asset,
                    holdings: asset_dict[constants.PORTFOLIO_TOTAL],
                    value: holdings_value,
                }
            )
    results.sort(key=lambda r: r[value], reverse=True)
    if markdown:
        # fill lines with empty spaces if necessary
        header = (
            f"{'{:<4}'.format('')} "
            f"{'  {:<9}'.format('Holdings')}  "
            f"{'    {:<7}'.format(ref_market_name or '')}"
        )
        header_separator = f"{'-' * 4}|{'-' * 12}|{'-' * 12}"
        content = separator.join(
            [
                _get_markdown_pretty_portfolio_row(
                    result[holdings], result[currency], ref_market_name, result[value]
                )
                for result in results
            ]
        )
        return f"{header}\n{header_separator}\n{content}"
    return separator.join(
        [
            _get_row_pretty_portfolio_row(
                result[holdings], result[currency], ref_market_name, result[value]
            )
            for result in results
        ]
    )


def portfolio_profitability_pretty_print(
    profitability, profitability_percent, reference
) -> str:
    """
    Profitability pretty printer
    :param profitability: the profitability
    :param profitability_percent: the profitability percent
    :param reference: the reference
    :return: the profitability pretty printed
    """
    difference = (
        f"({get_min_string_from_number(profitability_percent, 5)}%)"
        if profitability_percent is not None
        else ""
    )
    return f"{get_min_string_from_number(profitability, 5)} {reference} {difference}"


def pretty_print_dict(dict_content, default="0", markdown=False) -> str:
    """
    Dict pretty printer
    :param dict_content: the dict to be printed
    :param default: the default printed
    :param markdown: if printer use markdown
    :return: the dict pretty printed
    """
    _, _, code = get_markers(markdown)
    if dict_content:
        result_str = octobot_commons.DICT_BULLET_TOKEN_STR
        return (
            f"{result_str}{code}"
            f"{octobot_commons.DICT_BULLET_TOKEN_STR.join(f'{value} {key}' for key, value in dict_content.items())}"
            f"{code}"
        )
    return default


def round_with_decimal_count(number, max_digits=8) -> float:
    """
    Round a decimal count
    :param number: the number to round
    :param max_digits: the digits
    :return: the rounded number
    """
    if number is None:
        return 0
    return float(get_min_string_from_number(number, max_digits))


def get_min_string_from_number(number, max_digits=None) -> str:
    """
    Get a min string from number
    :param number: the number
    :param max_digits: the mex digits
    :return: the string from number
    """
    max_digits = _get_max_digits(number) if max_digits is None else max_digits
    if number is None or round(number, max_digits) == 0.0:
        return "0"
    if number % 1 != 0:
        number_str = number_util.round_into_str_with_max_digits(number, max_digits)
        # remove post comma trailing 0
        if "." in number_str:
            # remove "0" first and only the "." to avoid removing 2x"0" in 10.0 and returning 1 for example.
            number_str = number_str.rstrip("0").rstrip(".")
        return number_str
    return "{:f}".format(number).split(".")[0]


# return markers for italic, bold and code
def get_markers(markdown=False) -> (str, str, str):
    """
    Get the markdown markers
    :param markdown: if printer use markdown
    :return: the italic marker, the bold marker, the code marker
    """
    if markdown:
        return (
            enums.MarkdownFormat.ITALIC.value,
            enums.MarkdownFormat.BOLD.value,
            enums.MarkdownFormat.CODE.value,
        )
    return "", "", ""
