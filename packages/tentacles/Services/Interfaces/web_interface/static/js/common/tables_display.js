const MAX_PRICE_DIGITS = 8;
const _displaySort = (data, type) => {
    if (type === 'display') {
        return data.display
    }
    return data.sort;
}
const displayTradesTable = (elementId, trades, refMarket, update) => {
    const table = $(document.getElementById(elementId));
    const rows = trades.map((element) => {
        return [
            element.symbol,
            element.type,
            round_digits(element.price, MAX_PRICE_DIGITS),
            round_digits(element.amount, MAX_PRICE_DIGITS),
            element.exchange,
            {display: `${round_digits(element.cost, 5)} ${element.market}`, sort: element.cost},
            {
                display: `${element.ref_market_cost === null ? `no ${element.market} price in ${refMarket}` : round_digits(element.ref_market_cost, 5)}`,
                sort: element.ref_market_cost === null ? 0 : element.ref_market_cost
            },
            {display: `${round_digits(element.fee_cost, 5)} ${element.fee_currency}`, sort: element.fee_cost},
            {display: element.date, sort: element.time},
            element.id,
            element.SoR,
        ]
    });
    let previousSearch = undefined;
    let previousOrder = [[8, "desc"]];
    let addedRows = true;
    if (update && $.fn.DataTable.isDataTable(`#${elementId}`)) {
        const previousDataTable = table.DataTable();
        previousSearch = previousDataTable.search();
        previousOrder = previousDataTable.order();
        addedRows = rows.length !== previousDataTable.rows().data().length;
        previousDataTable.destroy();
    }
    table.DataTable({
        data: rows,
        columns: [
            {title: "Pair"},
            {title: "Type"},
            {title: "Price"},
            {title: "Quantity"},
            {title: "Exchange"},
            {title: "Total", render: _displaySort},
            {title: `${refMarket} Total`, render: _displaySort},
            {title: "Fee", render: _displaySort},
            {title: "Execution", render: _displaySort},
            {title: "ID"},
            {title: "#"},
        ],
        paging: true,
        search: {
            search: previousSearch,
        },
        order: previousOrder,
    });
    return addedRows;
}
const displayPositionsTable = (elementId, positions, closePositionUrl, update) => {
    const table = $(document.getElementById(elementId));
    const rows = positions.map((element) => {
        return [
            `${element.side.toUpperCase()} ${element.contract}`,
            round_digits(element.amount, 5),
            {display: `${round_digits(element.value, 5)} ${element.market}`, sort: element.value},
            round_digits(element.entry_price, MAX_PRICE_DIGITS),
            round_digits(element.liquidation_price, MAX_PRICE_DIGITS),
            {display: `${round_digits(element.margin, 5)} ${element.market}`, sort: element.margin},
            {display: `${round_digits(element.unrealized_pnl, 5)} ${element.market}`, sort: element.unrealized_pnl},
            element.exchange,
            element.SoR,
            {symbol: element.symbol, side: element.side},
        ]
    });
    let previousSearch = undefined;
    let previousOrder = undefined;
    if (update) {
        const previousDataTable = table.DataTable();
        previousSearch = previousDataTable.search();
        previousOrder = previousDataTable.order();
        previousDataTable.destroy();
    }
    table.DataTable({
        data: rows,
        columns: [
            {title: "Contract"},
            {title: "Size"},
            {title: "Value", render: _displaySort},
            {title: "Entry price"},
            {title: "Liquidation price"},
            {title: "Position margin", render: _displaySort},
            {title: "Unrealized PNL", render: _displaySort},
            {title: "Exchange"},
            {title: "#"},
            {
                title: "Close",
                render: (data, type) => {
                    if (type === 'display') {
                        return `<button type="button" class="btn btn-sm btn-outline-danger waves-effect" 
                                       data-action="close_position" data-position_symbol=${data.symbol} 
                                       data-position_side="${data.side}"
                                       data-update-url="${closePositionUrl}">
                                       <i class="fas fa-ban"></i></button>`
                    }
                    return data;
                },
            },
        ],
        paging: false,
        search: {
            search: previousSearch,
        },
        order: previousOrder,
    });
}
const displayOrdersTable = (elementId, orders, cancelOrderUrl, update) => {
    const table = $(document.getElementById(elementId));
    const canCancelOrders = cancelOrderUrl !== undefined;
    const rows = orders.map((element) => {
        const row = [
            element.symbol,
            element.type,
            round_digits(element.price, MAX_PRICE_DIGITS),
            round_digits(element.amount, MAX_PRICE_DIGITS),
            element.exchange,
            {display: element.date, sort: element.time},
            {display: `${round_digits(element.cost, MAX_PRICE_DIGITS)} ${element.market}`, sort: element.cost},
            element.SoR,
            element.id,
        ]
        if (canCancelOrders){
            row.push(element.id)
        }
        return row
    });
    let previousOrder = [[5, "desc"]];
    if(update){
        const previousDataTable = table.DataTable();
        previousOrder = previousDataTable.order();
        previousDataTable.destroy();
    }
    const columns = [
        { title: "Pair" },
        { title: "Type" },
        { title: "Price" },
        { title: "Quantity" },
        { title: "Exchange" },
        { title: "Date", render: _displaySort },
        { title: "Total", render: _displaySort },
        { title: "#" },
    ]
    if (canCancelOrders) {
        columns.push({
            title: "Cancel",
            render: (data, type) => {
                if (type === 'display') {
                   return `<button type="button" class="btn btn-sm btn-outline-danger waves-effect" 
                                   action="cancel_order" order_desc="${ data }" 
                                   update-url="${cancelOrderUrl}">
                                   <i class="fas fa-ban"></i></button>`
                }
                return data;
            },
        });
    }
    table.DataTable({
        data: rows,
        columns: columns,
        paging: false,
        order: previousOrder,
    });
}
