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

function get_symbol_price_graph(element_id, exchange_name, symbol, time_frame, backtesting=false, replace=false){
    const backtesting_enabled = backtesting ? "backtesting" : "live";
    const ajax_url = "/dashboard/currency_price_graph_update/"+ exchange_name +"/" + symbol + "/"
        + time_frame + "/" + backtesting_enabled;
    $.ajax({
        url: ajax_url,
        type: "POST",
        dataType: "json",
        contentType: 'application/json',
        success: function(msg, status){
            create_candlestick_graph(element_id, msg, symbol, exchange_name, time_frame, replace=replace);
        },
        error: function(result, status, error){
            window.console&&console.error(error);
        }
    });
}

function get_first_symbol_price_graph(element_id, in_backtesting_mode=false) {
    const url = $("#first_symbol_graph").attr(update_url_attr);
    $.get(url,function(data) {
        if("time_frame" in data){
            let formatted_symbol = data["symbol"].replace(new RegExp("/","g"), "|");
            get_symbol_price_graph(element_id, data["exchange"], formatted_symbol, data["time_frame"], in_backtesting_mode);
        }
    });
}

function get_watched_symbol_price_graph(element) {
    const symbol = element.attr("symbol");
    let formatted_symbol = symbol.replace(new RegExp("/","g"), "|");
    const ajax_url = "/dashboard/watched_symbol/"+ formatted_symbol;
    $.get(ajax_url,function(data) {
        if("time_frame" in data){
            let formatted_symbol = data["symbol"].replace(new RegExp("/","g"), "|");
            get_symbol_price_graph(element.attr("id"), data["exchange"], formatted_symbol, data["time_frame"], false);
        }
    });
}

function create_candlesticks(candles){
    const data_time = candles["time"];
    const data_close = candles["close"];
    const data_high = candles["high"];
    const data_low = candles["low"];
    const data_open = candles["open"];

    return {
      x: data_time,
      close: data_close,
      decreasing: {line: {color: '#F65A33'}},
      high: data_high,
      increasing: {line: {color: '#7DF98D'}},
      line: {color: 'rgba(31,119,180,1)'},
      low: data_low,
      open: data_open,
      type: 'candlestick',
      name: 'Prices',
      xaxis: 'x',
      yaxis: 'y2'
    };
}

function create_volume(candles){

    const data_time = candles["time"];
    const data_close = candles["close"];
    const data_volume = candles["vol"];
    const sell_color = "#ff0000";
    const buy_color = "#009900";
    
    const colors = [];
    $.each(data_close, function (i, value) {
        if(i !== 0) {
            if (value > data_close[i - 1]) {
                colors.push(buy_color);
            }else{
                colors.push(sell_color);
            }
        }
        else{
            colors.push(sell_color);
        }

    });

    return {
          x: data_time,
          y: data_volume,
          marker: {
              color: colors
          },
          type: 'bar',
          name: 'Volume',
          xaxis: 'x',
          yaxis: 'y1'
    };
}

function create_trades(trades, trader){

    if (isDefined(trades) && isDefined(trades["time"]) && trades["time"].length > 0) {
        const data_time = trades["time"];
        const data_price = trades["price"];
        const data_trade_description = trades["trade_description"];
        const data_order_side = trades["order_side"];

        const marker_size = trader === "Simulator" ? 16 : 18;
        const marker_opacity = trader === "Simulator" ? 0.6 : 0.75;

        const sell_color = "#ff0000";
        const buy_color = "#009900";
        const colors = [];
        $.each(data_order_side, function (index, value) {
            if (value === "sell") {
                colors.push(sell_color);
            } else {
                colors.push(buy_color);
            }
        });

        const line_with = trader === "Simulator" ? 0 : 2;

        return {
            x: data_time,
            y: data_price,
            mode: 'markers',
            name: trader,
            text: data_trade_description,
            marker: {
                color: colors,
                // color: buy_color,
                size: marker_size,
                opacity: marker_opacity,
                line: {
                    width: line_with
                }
            },
            xaxis: 'x',
            yaxis: 'y2'
        }
    }else{
        return {}
    }
}

function create_candlestick_graph(element_id, symbol_price_data, symbol, exchange_name, time_frame, replace=false){
    const candles = symbol_price_data["candles"];
    const real_trades = symbol_price_data["real_trades"];
    const simulated_trades = symbol_price_data["simulated_trades"];

    const price_trace = create_candlesticks(candles);

    const volume_trace = create_volume(candles);

    const real_trader_trades = create_trades(real_trades, "Real trader");
    const simulator_trades = create_trades(simulated_trades, "Simulator");

    const data = [volume_trace, price_trace, real_trader_trades, simulator_trades];

    let graph_title = symbol;
    if (exchange_name !== "ExchangeSimulator"){
        graph_title = graph_title + " (" + exchange_name + ", time frame: " + time_frame +")";
    }

    const layout = {
      title: graph_title,
      dragmode: 'zoom',
      margin: {
        r: 10,
        t: 25,
        b: 40,
        l: 60
      },
      showlegend: true,
      xaxis: {
        autorange: true,
        domain: [0, 1],
        title: 'Date',
        type: 'date'
      },
      yaxis1: {
        domain: [0, 0.2],
        title: 'Volume',
        autorange: true,
        showgrid:false,
        showticklabels: false
      },
      yaxis2: {
        domain: [0.2, 1],
        autorange: true,
        title: 'Price'
      },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: {
        color: "white"
      }
    };
    if(replace){
        Plotly.newPlot(element_id, data, layout);
    }else{
        Plotly.plot(element_id, data, layout);
    }
}
