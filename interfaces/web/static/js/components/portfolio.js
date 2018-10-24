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
    const chartTitle = "Holdings in "+referenceMarket;
    $.get(url,function(data) {
        createPortfolioChart("real_portfolio_doughnutChart", data["real_portfolio_holdings"], chartTitle);
        createPortfolioChart("simulated_portfolio_doughnutChart", data["simulated_portfolio_holdings"], chartTitle);
    });
});
