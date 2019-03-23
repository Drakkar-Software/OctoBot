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


function get_in_backtesting_mode() {
    return $("#symbol_graph").attr("backtesting_mode") === "True";
}


function update_graph(time_frame, symbol, exchange){
    if(isDefined(time_frame) && isDefined(symbol) && isDefined(exchange)){
        const formated_symbol = symbol.replace(new RegExp("/","g"), "|");
        const valid_exchange = exchange.split("[")[0];
        get_symbol_price_graph("graph-symbol-price", valid_exchange, formated_symbol, time_frame, backtesting=get_in_backtesting_mode(), replace=true);
    }else{
        $("#graph-symbol-price").text("Impossible to display price graph.")
    }
}

const graph = $("#symbol_graph");

$(document).ready(function() {
    const timeFrameSelect = $("#time-frame-select");
    update_graph(timeFrameSelect.val(), graph.attr("symbol"), graph.attr("exchange"));
    timeFrameSelect.on('change', function () {
        update_graph(this.value, graph.attr("symbol"), graph.attr("exchange"));
    });

});
