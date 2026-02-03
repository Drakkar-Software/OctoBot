import datetime as datetime
import json as json

import octobot_commons.enums as commons_enums
import octobot_commons.pretty_printer as pretty_printer
import octobot_services.constants as services_constants
import tentacles.Meta.Keywords.scripting_library.backtesting.run_data_analysis as run_data_analysis
import octobot_trading.modes.script_keywords as script_keywords


async def default_backtesting_analysis_script(ctx: script_keywords.Context):
    async with ctx.backtesting_results() as (run_data, run_display):
        historical_values = await run_data_analysis.load_historical_values(run_data, None)
        if ctx.backtesting_analysis_settings["plot_pnl_on_main_chart"]:
            with run_display.part("main-chart") as part:
                try:
                    await run_data_analysis.plot_historical_portfolio_value(
                        run_data, part,
                        historical_values=historical_values,
                    )
                    await run_data_analysis.plot_historical_pnl_value(
                        run_data, part, x_as_trade_count=False,
                        own_yaxis=True,
                        include_unitary=ctx.backtesting_analysis_settings["plot_trade_gains_on_main_chart"],
                        historical_values=historical_values,
                    )
                except Exception as err:
                    ctx.logger.exception(err, True, f"Error when computing main chant graphs {err}")
        with run_display.part("backtesting-run-overview") as part:
            try:
                if ctx.backtesting_analysis_settings.get("plot_hist_portfolio_on_backtesting_chart", True):
                    await run_data_analysis.plot_historical_portfolio_value(
                        run_data, part,
                        historical_values=historical_values,
                    )
                if ctx.backtesting_analysis_settings["plot_pnl_on_backtesting_chart"]:
                    await run_data_analysis.plot_historical_pnl_value(
                        run_data, part, x_as_trade_count=False,
                        own_yaxis=True,
                        include_unitary=ctx.backtesting_analysis_settings["plot_trade_gains_on_backtesting_chart"],
                        historical_values=historical_values,
                    )
                if ctx.backtesting_analysis_settings["plot_best_case_growth_on_backtesting_chart"]:
                    await run_data_analysis.plot_best_case_growth(
                        run_data, part, x_as_trade_count=True, own_yaxis=False,
                        historical_values=historical_values,
                    )
                if ctx.backtesting_analysis_settings["plot_funding_fees_on_backtesting_chart"]:
                    await run_data_analysis.plot_historical_funding_fees(
                        run_data, part, own_yaxis=True,
                    )
                if ctx.backtesting_analysis_settings["plot_wins_and_losses_count_on_backtesting_chart"]:
                    await run_data_analysis.plot_historical_wins_and_losses(
                        run_data, part, own_yaxis=True, x_as_trade_count=False,
                        historical_values=historical_values,
                    )
                if ctx.backtesting_analysis_settings["plot_win_rate_on_backtesting_chart"]:
                    await run_data_analysis.plot_historical_win_rates(
                        run_data, part, own_yaxis=True, x_as_trade_count=False,
                        historical_values=historical_values,
                    )
                # await plot_withdrawals(run_data, part)
            except Exception as err:
                ctx.logger.exception(err, True, f"Error when computing run overview graphs {err}")
        if ctx.backtesting_analysis_settings["display_backtest_details"]:
            with run_display.part("backtesting-details", "value") as part:
                try:
                    backtesting_report = await get_backtesting_report_template(
                        run_data, ctx.backtesting_analysis_settings, historical_values
                    )
                    await run_data_analysis.display_html(part, backtesting_report)
                except Exception as err:
                    ctx.logger.exception(err, True, f"Error when computing details part {err}")
        if ctx.backtesting_analysis_settings["display_trades_and_positions"]:
            with run_display.part("list-of-trades-part", "table") as part:
                try:
                    await run_data_analysis.plot_trades(run_data, part, historical_values=historical_values)
                    await run_data_analysis.plot_orders(run_data, part, historical_values=historical_values)
                    await run_data_analysis.plot_positions(run_data, part)
                    # await plot_table(run_data, part, "SMA 1")  # plot any cache key as a table
                except Exception as err:
                    ctx.logger.exception(err, True, f"Error when computing trades part {err}")
    return run_display


async def get_backtesting_report_template(run_data, backtesting_analysis_settings, historical_values):
    price_data, _, _, _, _, metadata = historical_values
    optimizer_id_display = get_column_display(commons_enums.BacktestingMetadata.OPTIMIZER_ID.value,
                                              commons_enums.BacktestingMetadata.OPTIMIZER_ID.value) \
        if commons_enums.BacktestingMetadata.OPTIMIZER_ID.value in metadata.keys() else ""
    paid_fees_display = get_column_display(services_constants.PAID_FEES_STR,
                                           metadata["paid_fees"]) if "paid_fees" in metadata.keys() else ""
    performance_summary = ""
    reference_market = metadata[commons_enums.DBRows.REFERENCE_MARKET.value]
    if backtesting_analysis_settings.get("display_backtest_details_performances", True):
        start_portfolio_value, end_portfolio_value = await run_data_analysis.get_portfolio_values(run_data)
        gains = f"{pretty_printer.get_min_string_from_number(metadata[commons_enums.BacktestingMetadata.GAINS.value])} " \
                f"({pretty_printer.get_min_string_from_number(metadata[commons_enums.BacktestingMetadata.PERCENT_GAINS.value])}%)"
        performance_summary \
            += get_section_display("Performance",
                                   get_column_display(commons_enums.BacktestingMetadata.START_PORTFOLIO.value,
                                                      get_portfolio_display(
                                                          metadata[commons_enums.BacktestingMetadata.START_PORTFOLIO.value]
                                                      )) +
                                   get_column_display(commons_enums.BacktestingMetadata.END_PORTFOLIO.value,
                                                      get_portfolio_display(
                                                          metadata[
                                                              commons_enums.BacktestingMetadata.END_PORTFOLIO.value])) +
                                   get_column_display(f"{commons_enums.BacktestingMetadata.START_PORTFOLIO.value} "
                                                      f"{reference_market} value",
                                                      start_portfolio_value) +
                                   get_column_display(f"{commons_enums.BacktestingMetadata.END_PORTFOLIO.value} "
                                                      f"{reference_market} value",
                                                      end_portfolio_value) +
                                   get_column_display(f"{reference_market} gains", gains) +
                                   get_column_display(
                                       commons_enums.BacktestingMetadata.MARKETS_PROFITABILITY.value,
                                       metadata.get(commons_enums.BacktestingMetadata.MARKETS_PROFITABILITY.value, {})
                                   ) +
                                   get_column_display(
                                       commons_enums.BacktestingMetadata.TRADES.value + " (entries and exits)",
                                       metadata[commons_enums.BacktestingMetadata.TRADES.value])
                                   # todo fix those values
                                   # + get_column_display(commons_enums.BacktestingMetadata.ENTRIES.value,
                                   #                    metadata[commons_enums.BacktestingMetadata.ENTRIES.value]) +
                                   # get_column_display(commons_enums.BacktestingMetadata.WINS.value,
                                   #                    metadata[commons_enums.BacktestingMetadata.WINS.value]) +
                                   # get_column_display(commons_enums.BacktestingMetadata.LOSES.value,
                                   #                    metadata[commons_enums.BacktestingMetadata.LOSES.value]) +
                                   # get_column_display(commons_enums.BacktestingMetadata.WIN_RATE.value,
                                   #                    metadata[commons_enums.BacktestingMetadata.WIN_RATE.value]) +
                                   # get_column_display(commons_enums.BacktestingMetadata.DRAW_DOWN.value,
                                   #                    metadata[commons_enums.BacktestingMetadata.DRAW_DOWN.value]) +
                                   # get_column_display(
                                   #     commons_enums.BacktestingMetadata.COEFFICIENT_OF_DETERMINATION_MAX_BALANCE.value,
                                   #     metadata[commons_enums.BacktestingMetadata
                                   #         .COEFFICIENT_OF_DETERMINATION_MAX_BALANCE.value]) +
                                   # paid_fees_display
                                   )
    if backtesting_analysis_settings.get("display_backtest_details_general", True):
        performance_summary \
            += get_section_display("General",
                                  get_column_display(commons_enums.BacktestingMetadata.NAME.value,
                                                     metadata[commons_enums.BacktestingMetadata.NAME.value])
                                  + get_column_display(commons_enums.BacktestingMetadata.OPTIMIZATION_CAMPAIGN.value,
                                                       metadata[commons_enums.BacktestingMetadata.
                                                       OPTIMIZATION_CAMPAIGN.value])
                                  + optimizer_id_display
                                  + get_column_display(commons_enums.BacktestingMetadata.ID.value,
                                                       metadata[commons_enums.BacktestingMetadata.ID.value])
                                  + get_column_display(commons_enums.DBRows.EXCHANGES.value,
                                                       metadata[commons_enums.DBRows.EXCHANGES.value])
                                  + get_column_display(commons_enums.BacktestingMetadata.BACKTESTING_FILES.value,
                                                       metadata[commons_enums.BacktestingMetadata.BACKTESTING_FILES.value]))
    if backtesting_analysis_settings.get("display_backtest_details_details", True):
        performance_summary \
            += get_section_display("Details",
                                   get_column_display(commons_enums.BacktestingMetadata.TIME_FRAMES.value,
                                                      get_badges_from_list(
                                                          metadata[commons_enums.BacktestingMetadata.TIME_FRAMES.value])) +
                                   get_column_display(commons_enums.BacktestingMetadata.START_TIME.value,
                                                      datetime.datetime.fromtimestamp(
                                                          metadata[commons_enums.DBRows.START_TIME.value])) +
                                   get_column_display(commons_enums.BacktestingMetadata.END_TIME.value,
                                                      datetime.datetime.fromtimestamp(
                                                          metadata[commons_enums.DBRows.END_TIME.value])) +
                                   get_column_display(commons_enums.BacktestingMetadata.SYMBOLS.value,
                                                      get_badges_from_list(
                                                          metadata[commons_enums.BacktestingMetadata.SYMBOLS.value])) +
                                   get_column_display(f"{commons_enums.BacktestingMetadata.DURATION.value} (s)",
                                                      metadata[commons_enums.BacktestingMetadata.DURATION.value]) +
                                   get_column_display(commons_enums.BacktestingMetadata.LEVERAGE.value,
                                                      metadata[commons_enums.BacktestingMetadata.LEVERAGE.value]) +
                                   get_column_display("Backtesting time",
                                                      datetime.datetime.fromtimestamp(
                                                          metadata[commons_enums.BacktestingMetadata.TIMESTAMP.value]))
                                   )

    if backtesting_analysis_settings.get("display_backtest_details_strategy_settings", True):
        performance_summary \
            += get_section_display("Strategy Settings",
                                   get_user_inputs_display(metadata)
                                   )

    return performance_summary


def get_section_display(title, content):
    return f''' 
        <div data-role="values" class="backtesting-run-container-values container-fluid row mb-5">
            <div class="col-12">
                <h4 class="text-center">{title}</h4>
            </div>
            {content}
        </div>
    '''


def get_column_display(title, value):
    return f'''
        <div class="col-6 col-md-3  text-center">
            <div class="backtesting-run-container-values-label text-capitalize">
                {title}
            </div>
            <div class="backtesting-run-container-values-value">
                {', '.join(value) if (isinstance(value, list) and value and isinstance(value[0], (int, float, str)))
                    else pretty_printer.get_min_string_from_number(value) if isinstance(value, float) 
                    else ', '.join(f"{key}: {val}" for key, val in value.items()) if isinstance(value, dict) 
                    else value}
            </div>
        </div>
    '''


def get_badges_from_list(_list):
    _html = ""
    for _item in _list:
        _html += f'<span class="badge badge-light mx-1">{_item}</span>'
    return _html


def get_portfolio_display(_dict):
    _html = ""
    _dict_str = _dict.replace("\'", '"')
    _dict_str = json.loads(_dict_str)
    for _key in _dict_str:
        _html += f'<span class="mx-1">{_key}: {pretty_printer.get_min_string_from_number(_dict_str[_key]["total"])}</span>'
    return _html


def get_user_inputs_display(metadata):
    content = ""
    for _evaluator in metadata['user inputs']:
        _section_content = ""
        for input_name in metadata['user inputs'][_evaluator]:
            _section_content += get_column_display(input_name, metadata['user inputs'][_evaluator][input_name])

        content += get_section_display(_evaluator, _section_content)
    return content
