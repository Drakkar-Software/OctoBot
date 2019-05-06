
/*
 * Drakkar-Software OctoBot
 * Copyright (c) Drakkar-Software, All rights reserved.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3.0 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.
 */

function start_backtesting(request, update_url){
    send_and_interpret_bot_update(request, update_url, null, start_success_callback, start_error_callback)
}

function start_success_callback(updated_data, update_url, dom_root_element, msg, status){
    $("#progess_bar_anim").css('width', 0+'%').attr("aria-valuenow", 0);
    create_alert("success", msg, "");
}

function start_error_callback(updated_data, update_url, dom_root_element, result, status, error){
    create_alert("error", result.responseText, "");
    $("#backtesting_progress_bar").hide();
    lock_interface(false);
}

function lock_interface(lock=true){
    let should_lock = lock;
    if(!should_lock){
        lock_interface_callbacks.forEach(function (value) {
            if(value()){
                should_lock = true;
            }
        });
    }
    $('#startBacktesting').prop('disabled', should_lock);
}

function load_report(report, should_alert=False){
    const url = $("#backtestingReport").attr(update_url_attr);
    $.get(url,function(data){
        if ("bot_report" in data){
            report.show();
            let profitability = data["bot_report"]["profitability"];
            const errors_count = data["errors_count"];
            if ("error" in data || errors_count > 0) {
                let error_message = "Warning: error(s) during backtesting [";
                if ("error" in data){
                     error_message += " " + data["error"] ;
                }
                if (errors_count > 0){
                     error_message += " " + errors_count + " error(s)" ;
                }
                error_message += " ], more details in logs.";
                profitability = profitability + " " + error_message;
                if (should_alert) {
                    create_alert("error", error_message, "");
                }
                $("#backtestingErrorsAlert").show()
            }else{
                $("#backtestingErrorsAlert").hide()
            }

            const symbol_reports = [];
            $.each( data["symbol_report"], function( index, value ) {
                $.each( value, function( symbol, profitability ) {
                    symbol_reports.push(symbol+": "+profitability);
                });
            });
            const all_profitability = symbol_reports.join(", ");
            $("#bProf").html(profitability);
            $("#maProf").html(data["bot_report"]["market_average_profitability"]);
            $("#refM").html(data["bot_report"]["reference_market"]);
            $("#sProf").html(all_profitability);
            $("#reportTradingModeName").html(data["bot_report"]["trading_mode"]);
            $("#reportTradingModeNameLink").attr("href", $("#reportTradingModeNameLink").attr("base_href") + data["bot_report"]["trading_mode"]);
            const end_portfolio_reports = [];
                $.each( data["bot_report"]["end_portfolio"], function( symbol, holdings ) {
                    end_portfolio_reports.push(symbol+": "+holdings["total"]);
                });
            $("#ePort").html(end_portfolio_reports.join(", "));
            const starting_portfolio_reports = [];
                $.each( data["bot_report"]["starting_portfolio"], function( symbol, holdings ) {
                    starting_portfolio_reports.push(symbol+": "+holdings["total"]);
                });
            $("#sPort").html(starting_portfolio_reports.join(", "));

            add_graphs(data["symbols_with_time_frames_frames"]);
        }
    }).fail(function () {
        report.hide();
    }).always(function () {
        report.attr("loading", "false");
    });
}

function add_graphs(symbols_with_time_frames){
    const result_graph_id = "result-graph-";
    const graph_symbol_price_id = "graph-symbol-price-";
    const result_graphs = $("#result-graphs");
    result_graphs.empty();
    $.each(symbols_with_time_frames, function (symbol, time_frame) {
        const target_template = $("#"+result_graph_id+config_default_value);
        const graph_card = target_template.html().replace(new RegExp(config_default_value,"g"), symbol);
        result_graphs.append(graph_card);
        const formated_symbol = symbol.replace(new RegExp("/","g"), "|");
        get_symbol_price_graph(graph_symbol_price_id+symbol, "ExchangeSimulator", formated_symbol, time_frame, true);
    })
}

function update_progress(progress){
    $("#progess_bar_anim").css('width', progress+'%').attr("aria-valuenow", progress)
}

function check_backtesting_state(){
    const url = $("#backtestingPage").attr(update_url_attr);
    $.get(url,function(data, status){
        const backtesting_status = data["status"];
        const progress = data["progress"];

        const report = $("#backtestingReport");
        const progress_bar = $("#backtesting_progress_bar");

        if(backtesting_status === "computing"){
            lock_interface(true);
            progress_bar.show();
            update_progress(progress);
            first_refresh_state = backtesting_status;
            if(report.is(":visible")){
                report.hide();
            }
        }
        else{
            lock_interface(false);
            progress_bar.hide();
            if(backtesting_status === "finished"){
                const should_alert = first_refresh_state !== "" && first_refresh_state !== "finished";
                if(should_alert){
                    create_alert("success", "Backtesting finished.", "");
                    first_refresh_state="finished";
                }
                if(!report.is(":visible") && report.attr("loading") === "false"){
                    report.attr("loading", "true");
                    load_report(report, should_alert);
                }
            }
        }
        if(first_refresh_state === ""){
            first_refresh_state = backtesting_status;
        }
    });
}

let first_refresh_state = "";

const lock_interface_callbacks = [];
