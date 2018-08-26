let bot_simulated_profitability = undefined;
let bot_real_profitability = undefined;
let market_profitability = undefined;
let profitability_chart = undefined;

function get_profitability(){
    const url = $("#profitability_graph").attr(update_url_attr);
    $.get(url,function(data, status){
        bot_simulated_profitability = data["bot_simulated_profitability"];
        bot_real_profitability = data["bot_real_profitability"];
        market_profitability = data["market_average_profitability"];
        if(is_worth_displaying_profitability()){
            $("#graph-profitability-description").html("");
            display_profitability("graph-profitability");
        }
        else{
            $("#graph-profitability-description").html("<h4>Nothing to display yet: profitability is 0 for the moment.</h4>")
        }
    });

}

function should_display_profitability(profitability){
    return isDefined(profitability) && (isDefined(profitability_chart) || Math.abs(profitability) >= 0.05);
}

function is_worth_displaying_profitability(){
    return (
        should_display_profitability(bot_simulated_profitability)
        || should_display_profitability(bot_real_profitability)
        || should_display_profitability(market_profitability)
    );
}

function fill_profitabiliy_bar(profitability, reference_profitability, label, labels, backgroundColors, borderColor, profitabilities){
    if(isDefined(profitability)){
        let color = ['rgba(255, 99, 132, 0.2)', 'rgba(255, 99, 132, 1)'];
        if(profitability >= reference_profitability){
            color = ['rgba(75, 192, 192, 0.2)', 'rgba(75, 192, 192, 1)'];
        }
        labels.push(label);
        backgroundColors.push(color[0]);
        borderColor.push(color[1]);
        profitabilities.push(profitability);
    }
}

function display_profitability(element_id){
    if(isDefined(market_profitability)){
        const labels = [];
        const backgroundColors = [];
        const borderColor = [];
        const profitabilities = [];
        fill_profitabiliy_bar(bot_real_profitability, market_profitability, "OctoBot Real Trader Profitability", labels, backgroundColors, borderColor, profitabilities);
        fill_profitabiliy_bar(bot_simulated_profitability, market_profitability, "OctoBot Trader Simulator Profitability", labels, backgroundColors, borderColor, profitabilities);
        fill_profitabiliy_bar(market_profitability, 0, "Watched symbols average profitability", labels, backgroundColors, borderColor, profitabilities);
        let datasets = [{
            label: '% Profitability',
            data: profitabilities,
            backgroundColor: backgroundColors,
            borderColor: borderColor,
            color: 'white',
            borderWidth: 1
        }];
        if(!isDefined(profitability_chart)){
            profitability_chart = create_bars_chart($("#graph-profitability")[0], labels, datasets, 0, false);
        }else{
            update_bars_chart(profitability_chart, datasets);
        }
    }
}

function update_dashboard(){
    get_profitability();
}

$(document).ready(function() {
    get_profitability();
    get_first_symbol_price_graph("graph-symbol-price");
    setInterval(function(){ update_dashboard(); }, 15000);
});
