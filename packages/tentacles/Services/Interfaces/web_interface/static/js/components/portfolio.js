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

    const createPortfolioChart = (element_id, title, update) => {
        const data = {};
        const element = $(`#${element_id}`);
        const max_medium_screen_legend_items = 50;
        const max_mobile_legend_items = 6;
        let at_least_one_value = false;
        let displayLegend = true;
        let graphHeight = element.attr("data-md-height");
        if(isMobileDisplay()){
            graphHeight = element.attr("data-sm-height");
        }
        element.attr("height", graphHeight);

        $(".symbol-holding").each(function (){
            const total_value = $(this).find(".total-value").text();
            if($.isNumeric(total_value)){
                data[$(this).find(".symbol").text()] = Number(total_value);
                if(Number(total_value) > 0 ){
                    at_least_one_value = true;
                }
            }
        });
        const dataLength = Object.keys(data).length;
        // display graph only if at least one value is available
        if(at_least_one_value && dataLength > 0 && element.length > 0){
            if(isMobileDisplay() && dataLength > max_mobile_legend_items){
                // legend is hiding the chart on smaller displays if too many elements are present
                displayLegend = false;
            }else if(dataLength > max_medium_screen_legend_items){
                // legend is hiding the chart on if too many elements are present
                displayLegend = false;
            }
            create_doughnut_chart(element[0], data, title, displayLegend, graphHeight, update);
        }else{
            element.addClass(hidden_class);
        }
    }

    const handle_portfolio_button = () => {
        const refreshButton = $("#refresh-portfolio");
        if(refreshButton){
            refreshButton.click(function () {
                const update_url = refreshButton.attr(update_url_attr);
                send_and_interpret_bot_update({}, update_url, null, generic_request_success_callback, generic_request_failure_callback);
            });
        }
    }

    const start_periodic_refresh = () => {
        setInterval(function() {
            $("#portfolio-display").load(location.href + " #portfolio-display", function (){
                update_display(true, true);
            });
        }, portfolio_update_interval);
    }

    const displayPortfolioTable = () => {
        handle_rounded_numbers_display();
        ordersDataTable = $('#holdings-table').DataTable({
            "paging": false,
            "bDestroy": true,
            "order": [[ 2, "desc" ]],
            "searching": $("tr.symbol-holding").length > 10,
        });
    }

    const displayPortfolioContent = (referenceMarket, update) => {
        displayPortfolioTable();
        const chartTitle = `Assets value (${referenceMarket})`;
        createPortfolioChart("portfolio_doughnutChart", chartTitle, update);
        handleButtons();
    }

    const update_display = (withImages, update) => {
        const referenceMarket = $("#portfoliosCard").attr("reference_market");
        displayPortfolioContent(referenceMarket, update);
        if(withImages){
            handleDefaultImages();
        }
    }

    let firstLoad = true;
    const handleClearButton = () => {
        $("#clear-portfolio-history-button").on("click", (event) => {
            if (confirm("Clear portfolio history ?") === false) {
                return false;
            }
            const url = $(event.currentTarget).data("url")
            const success = (updated_data, update_url, dom_root_element, msg, status) => {
                // reload page on success
                location.reload();
            }
            send_and_interpret_bot_update(null, url, null, success, generic_request_failure_callback)
        })
    }

    const handleButtons = () => {
        handle_portfolio_button();
        handleClearButton()
    }
    update_display(false, false);
    if(firstLoad){
        start_periodic_refresh();
    }
});
