function get_symbol_price_graph(element_id, exchange_name, symbol, time_frame){
    const ajax_url = "/dashboard/currency_price_graph_update/"+ exchange_name +"/" + symbol + "/" + time_frame;
    $.ajax({
        url: ajax_url,
        type: "POST",
        dataType: "json",
        contentType: 'application/json',
        success: function(msg, status){
            create_candlestick_graph(element_id, msg);
        },
        error: function(result, status, error){
            window.console&&console.error(error);
        },
    });
}

function create_candlestick_graph(element_id, symbol_price_data){
    const data_time = symbol_price_data["time"];
    const data_close = symbol_price_data["close"];
    const data_high = symbol_price_data["high"];
    const data_low = symbol_price_data["low"];
    const data_open = symbol_price_data["open"];

    const price_trace = {
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

    const data = [price_trace];

    const layout = {
      dragmode: 'zoom',
      margin: {
        r: 10,
        t: 25,
        b: 40,
        l: 60
      },
      showlegend: false,
      xaxis: {
        autorange: true,
        domain: [0, 1],
        title: 'Date',
        type: 'date'
      },
      yaxis: {
        autorange: true,
        domain: [0, 1],
        type: 'linear'
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