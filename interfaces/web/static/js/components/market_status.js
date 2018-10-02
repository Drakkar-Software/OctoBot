function update_graph(time_frame, symbol, exchange){
    if(isDefined(time_frame) && isDefined(symbol) && isDefined(exchange)){
        const formated_symbol = symbol.replace(new RegExp("/","g"), "|");
        get_symbol_price_graph("graph-symbol-price", exchange, formated_symbol, time_frame, backtesting=false, replace=true);
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
