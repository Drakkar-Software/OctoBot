function get_symbol_price_graph(exchange_name, symbol, time_frame){
    $.ajax({
        url: "/dashboard/currency_graph_update/"+ exchange_name +"/" + symbol + "/" + time_frame,
        type: "POST",
        dataType: "json",
        contentType: 'application/json',
        data: null,
        success: function(msg, status){
            console.log(msg);
        },
        error: function(result, status, error){
            window.console&&console.error(result);
            window.console&&console.error(status);
            window.console&&console.error(error);
        },
    });
}

function create_candlestick_graph(element_id, data_time, data_close, data_high, data_low, data_open){
    var price_trace = {
      x: data_time,
      close: data_close,
      decreasing: {line: {color: '#7F7F7F'}},
      high: data_high,
      increasing: {line: {color: '#17BECF'}},
      line: {color: 'rgba(31,119,180,1)'},
      low: data_low,
      open: data_open,
      type: 'candlestick',
      xaxis: 'x',
      yaxis: 'y'
    };

    var data = [price_trace];

    var layout = {
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
      }
    };

    Plotly.plot(element_id, data, layout);
}