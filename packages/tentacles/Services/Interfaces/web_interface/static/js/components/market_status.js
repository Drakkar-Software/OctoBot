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


function init_update_handler(){
    socket.on("candle_graph_update_data", function (data) {
        if(!cancel_next_update){
            updating_graph = true;
            update_graph(graph.attr("exchange"), true, data.data);
        }else{
            cancel_next_update = false;
        }
    });
    socket.on('new_data', function (data) {
        if(!cancel_next_update) {
            updating_graph = true;
            update_graph(graph.attr("exchange"), true, data.data, false);
        }
    });
}

function schedule_update(){
    setTimeout(function () {
        socket.emit("candle_graph_update", update_details);
    }, price_graph_update_interval)
}


function update_graph(exchange, update=false, data=undefined, re_update=true, initialization=false){
    const in_backtesting = get_in_backtesting_mode();
    if(isDefined(update_details.time_frame) && isDefined(update_details.symbol) && isDefined(exchange)){
        const formated_symbol = update_details.symbol.replace(new RegExp("/","g"), "|");
        if(isDefined(data) && (formated_symbol !== data.symbol.replace(new RegExp("/","g"), "|") ||
            update_details.exchange_id !== data.exchange_id)){
            return;
        }
        if (initialization && !in_backtesting){
            init_update_handler();
            updating_graph = false;
        }
        const valid_exchange_name = exchange.split("[")[0];
        get_symbol_price_graph("graph-symbol-price", update_details.exchange_id, valid_exchange_name,
            formated_symbol, update_details.time_frame, true, in_backtesting, !update,
            true, 0, data, schedule_update);
        if (update && re_update && !in_backtesting){
            schedule_update();
        }
    }else{
        const loadingSelector = $("div[name='loadingSpinner']");
        if (loadingSelector.length) {
            loadingSelector.addClass(hidden_class);
        }
        $("#graph-symbol-price").html("<h7>Impossible to display price graph, if this error keeps appearing, " +
            "go to back to <strong>Trading</strong> and re-display this page.</h7>")
    }
}

function change_time_frame(new_time_frame) {
    update_details.time_frame = new_time_frame;
    update_graph(graph.attr("exchange"));
}

const graph = $("#symbol_graph");
const timeFrameSelect = $("#time-frame-select");
const update_details = {
    exchange_id: graph.attr("exchange_id"),
    symbol: graph.attr("symbol"),
    time_frame: timeFrameSelect.val()
};
let updating_graph = false;
let cancel_next_update = false;

const socket = get_websocket("/dashboard");

$(document).ready(function() {
    update_graph(graph.attr("exchange"), false, undefined, true, true);
    timeFrameSelect.on('change', function () {
        const new_val = this.value;
        cancel_next_update = true;
        if(updating_graph){
            setTimeout(function () {
                change_time_frame(new_val)
            }, 50);
        }else{
            change_time_frame(new_val);
        }
    });

});
