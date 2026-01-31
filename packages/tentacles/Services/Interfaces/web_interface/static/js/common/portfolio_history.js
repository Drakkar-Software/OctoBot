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

$(document).ready(function() {
    const createHistoricalPortfolioChart = (element_id, reference_market, update) => {
        const element = $(`#${element_id}`);
        const selectedTimeFrame = "1d"; // todo add timeframe selector
        const url = `${element.data("url")}${selectedTimeFrame}`;
        const success = (updated_data, update_url, dom_root_element, msg, status) => {
            const graphDiv = $(`#profitability_graph`);
            const defaultDiv = $(`#no_profitability_graph`);
            const height = isMobileDisplay()? 250 : isMediumDisplay() ? 450 : undefined;
            if(msg.length > 1){
                graphDiv.removeClass(hidden_class);
                defaultDiv.addClass(hidden_class);
                const current_value = msg[msg.length - 1].value;
                const title = `${current_value > 0 ? current_value : '-'} ${reference_market}`
                create_line_chart(document.getElementById(element_id), msg, title, 'white', update, height);
            }else{
                graphDiv.addClass(hidden_class);
                defaultDiv.removeClass(hidden_class);
            }
        }
        send_and_interpret_bot_update(null, url, null, success, generic_request_failure_callback, "GET");
    }

    const displayPortfolioHistory = (elementId, referenceMarket, update) => {
        createHistoricalPortfolioChart(elementId, referenceMarket, update);
    }

    const update_display = (update) => {
        const elementId = "portfolio_historyChart";
        const referenceMarket = $(`#${elementId}`).data("reference-market");
        displayPortfolioHistory(elementId, referenceMarket, update);
    }

    const start_periodic_refresh = () => {
        setInterval(function() {
            update_display(true, true);
        }, profitability_update_interval);
    }

    let firstLoad = true;
    update_display(false);
    if(firstLoad){
        start_periodic_refresh();
    }
});
