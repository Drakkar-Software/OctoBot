function get_symbol_price_graph(element_id, exchange_name, symbol, time_frame, backtesting=false){
    let backtesting_enabled = backtesting ? "backtesting" : "live";
    const ajax_url = "/dashboard/currency_price_graph_update/"+ exchange_name +"/" + symbol + "/"
        + time_frame + "/" + backtesting_enabled;
    $.ajax({
        url: ajax_url,
        type: "POST",
        dataType: "json",
        contentType: 'application/json',
        success: function(msg, status){
            create_candlestick_graph(element_id, msg, symbol, exchange_name);
        },
        error: function(result, status, error){
            window.console&&console.error(error);
        },
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
      xaxis: 'x',
      yaxis: 'y'
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
            }
        }
    }else{
        return {}
    }
}

function create_candlestick_graph(element_id, symbol_price_data, symbol, exchange_name){
    const candles = symbol_price_data["candles"];
    const real_trades = symbol_price_data["real_trades"];
    const simulated_trades = symbol_price_data["simulated_trades"];

    const price_trace = create_candlesticks(candles);

    const real_trader_trades = create_trades(real_trades, "Real trader");
    const simulator_trades = create_trades(simulated_trades, "Simulator");

    const data = [price_trace, real_trader_trades, simulator_trades];

    var graph_title = symbol
    if (exchange_name !== "ExchangeSimulator"){
        graph_title = graph_title + " (" + exchange_name + ")";
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
      yaxis: {
        autorange: true,
        domain: [0, 1],
        type: 'linear',
        title: 'Price'
      },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: {
        color: "white"
      }
    };

    console.log(data);
    Plotly.plot(element_id, data, layout);
}