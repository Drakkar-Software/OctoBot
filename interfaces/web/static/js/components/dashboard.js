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

let bot_simulated_profitability = undefined;
let simulated_no_trade_profitability = undefined;
let bot_real_profitability = undefined;
let real_no_trade_profitability = undefined;
let market_profitability = undefined;
let profitability_chart = undefined;

function get_profitability(){
    const url = $("#profitability_graph").attr(update_url_attr);
    $.get(url,function(data, status){
        bot_simulated_profitability = data["bot_simulated_profitability"];
        simulated_no_trade_profitability = data["simulated_no_trade_profitability"];
        bot_real_profitability = data["bot_real_profitability"];
        real_no_trade_profitability = data["real_no_trade_profitability"];
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
    return isDefined(profitability) && (isDefined(profitability_chart) || Math.abs(profitability) >= 0.2);
}

function is_worth_displaying_profitability(){
    return (
        should_display_profitability(bot_simulated_profitability)
        || should_display_profitability(bot_real_profitability)
        || should_display_profitability(market_profitability)
    );
}

function fill_profitabiliy_bar(profitability, reference_profitability, label, labels, backgroundColors, borderColor, profitabilities, color_theme){
    if(isDefined(profitability)){
        let color = ['rgba(255, 99, 132, 0.2)', 'rgba(255, 99, 132, 1)']; //red
        if(color_theme === "wallet"){
            color = ['rgba(255, 99, 132, 0.2)', 'rgba(255, 99, 132, 1)']; //red
            if(profitability >= reference_profitability){
                color = ['rgba(75, 192, 192, 0.2)', 'rgba(75, 192, 192, 1)']; //blue
            }
        }else{
            color = ['rgba(197, 202, 233, 0.2)', 'rgba(255, 99, 132, 1)'];  //gray_red_border
            if(profitability >= reference_profitability){
                color = ['rgba(197, 202, 233, 0.2)', 'rgba(75, 192, 192, 1)']; //gray_blue_border
            }
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
        fill_profitabiliy_bar(bot_real_profitability, real_no_trade_profitability, "Current Real Portfolio", labels, backgroundColors, borderColor, profitabilities, "wallet");
        fill_profitabiliy_bar(real_no_trade_profitability, market_profitability, "Initial Real Portfolio", labels, backgroundColors, borderColor, profitabilities, "wallet");
        fill_profitabiliy_bar(bot_simulated_profitability, simulated_no_trade_profitability, "Current Simulated Portfolio", labels, backgroundColors, borderColor, profitabilities, "wallet");
        fill_profitabiliy_bar(simulated_no_trade_profitability, market_profitability, "Initial Simulated Portfolio", labels, backgroundColors, borderColor, profitabilities, "wallet");
        fill_profitabiliy_bar(market_profitability, 0, "Traded symbols average profitability", labels, backgroundColors, borderColor, profitabilities, "market");
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

function get_in_backtesting_mode() {
    return $("#first_symbol_graph").attr("backtesting_mode") === "True";
}

function update_dashboard(){
    get_profitability();
}

function get_announcements(){
    const annoncementsAlertDiv = $("#annoncementsAlert");
    $.get({
        url: annoncementsAlertDiv.attr(update_url_attr),
        dataType: "json",
        success: function(msg, status){
            if(msg){
                annoncementsAlertDiv.text(msg);
                annoncementsAlertDiv.removeClass(disabled_item_class);
            }
        }
    })
}

$(document).ready(function() {
    get_profitability();
    get_announcements();
    let useDefaultGraph = true;
    $(".watched-symbol-graph").each(function () {
        useDefaultGraph = false;
        get_watched_symbol_price_graph($(this));
    });
    if(useDefaultGraph){
        get_first_symbol_price_graph("graph-symbol-price", get_in_backtesting_mode());
    }
    setInterval(function(){ update_dashboard(); }, 15000);
});
