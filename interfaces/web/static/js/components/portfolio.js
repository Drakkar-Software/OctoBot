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

function createPortfolioChart(element_id, data, title){
    const element = $("#"+element_id);
    if(element.length > 0 ){
        create_pie_chart(element[0], data, title);
    }
}

$(document).ready(function() {
    const portfolioElem=$("#portfoliosCard");
    const url = portfolioElem.attr(update_url_attr);
    const referenceMarket = portfolioElem.attr("reference_market");
    const chartTitle = "Traded assets value in "+referenceMarket;
    $.get(url,function(data) {
        createPortfolioChart("real_portfolio_doughnutChart", data["real_portfolio_holdings"], chartTitle);
        createPortfolioChart("simulated_portfolio_doughnutChart", data["simulated_portfolio_holdings"], chartTitle);
    });
});
