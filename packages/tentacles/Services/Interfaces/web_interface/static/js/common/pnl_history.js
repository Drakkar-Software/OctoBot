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

const loadPnlFullChartHistory = (data, update) => {
    const unit = $("#pnl_historyChart").data("unit");
    const parentDiv = $(`#pnl_historyChart`);
    if(data.length > 1){
        parentDiv.removeClass(hidden_class);
        let total_pnl = 0;
        const chartedData = data.map((element) => {
            total_pnl += element.pnl;
            return {
                time: element.ex_t,
                y1: total_pnl,
                y2: element.pnl,
            }
        })
        create_histogram_chart(
            document.getElementById("pnl_historyChart"), chartedData, `cumulated profit/loss`, "profit/loss", unit, getTextColor(), false
        );
    }else{
        parentDiv.addClass(hidden_class);
    }
}

const loadPnlTableHistory = (data, update) => {
    let total_pnl = 0;
    const hasDetails = data.length && data[0].d !== null;
    const rows = data.map((element) => {
        total_pnl += element.pnl;
        if(hasDetails){
            return [
                {
                    timestamp: element.d.en_t,
                    date: element.d.en_d,
                    side: element.d.en_s,
                    base: element.d.b,
                    quote: element.q,
                    symbol: element.d.s,
                    exchange: element.d.ex,
                    trades: element.tc,
                    amount: round_digits(element.d.en_a, 8),
                    price: round_digits(element.d.en_p, 8),
                    total : round_digits(element.d.en_a * element.d.en_p, 8),
                },
                {
                    timestamp: element.ex_t,
                    date: element.ex_d,
                    side: element.d.ex_s,
                    base: element.d.b,
                    quote: element.q,
                    symbol: element.d.s,
                    exchange: element.d.ex,
                    trades: element.tc,
                    amount: round_digits(element.d.ex_a, 8),
                    price: round_digits(element.d.ex_p, 8),
                    total : round_digits(element.d.ex_a * element.d.ex_p, 8)
                },
                round_digits(element.pnl, 8),
                {
                    special: element.d.s_f.map(e => {return {f: round_digits(e.f, 8), c: e.c}}),
                    amount: round_digits(element.d.f, 8),
                    quote: element.q,
                },
            ]
        }else{
            return [
                {timestamp: element.ex_t, date: element.ex_d, quote: element.q},
                round_digits(element.pnl, 8),
                round_digits(total_pnl, 8),
                round_digits(element.pnl_a, 8),
            ]
        }
    });
    const pnlTable = $("#pnl_historyTable");
    const unit = rows.length ? rows[0][0].quote : pnlTable.data("unit");
    let previousOrder = [[0, "desc"]];
    if(update){
        const previousDataTable = pnlTable.DataTable();
        previousOrder = previousDataTable.order();
        previousDataTable.destroy();
    }

    const getSideBadge = (side) => {
        return `<span class="badge font-size-90 badge-${side === 'sell' ? 'danger': 'success'}">${side}</span>`
    }

    const getBoldRender = (amount) => {
        return `<span class="font-weight-bold">${amount}</span>`
    }

    const getPnlOrdersDetails = (data) => {
        return `<span data-toggle="tooltip" title="symbol: ${data.symbol} exchange: ${data.exchange} trades: ${data.trades}">${getSideBadge(data.side)} ${data.date}: ${getBoldRender(data.amount)} ${data.base} at ${getBoldRender(data.price)}, total ${getBoldRender(data.total)}</span>`;
    }

    const columns = (
        hasDetails ? [
            {
                title: `Entry (${unit})`,
                render: (data, type) => {
                    if (type === 'display' || type === 'filter') {
                        return getPnlOrdersDetails(data);
                    }
                    return data.timestamp;
                },
                width: "39%",
            },
            {
                title: `Close (${unit})`,
                render: (data, type) => {
                    if (type === 'display' || type === 'filter') {
                        return getPnlOrdersDetails(data);
                    }
                    return data.timestamp;
                },
                width: "39%",
            },
            {
                title: `${unit} PNL`,
                width: "11%",
            },
            {
                title: 'Total fees',
                render: (data, type) => {
                    if (type === 'display' || type === 'filter') {
                        const base = data.amount ? `${data.amount} ${data.quote}${data.special.length ?' + ' : ''}` : "";
                        const special = data.special.length ? data.special.map(e => `${e.f} ${e.c}`).join(", ") : "";
                        return `${base}${special}`
                    }
                    return data.amount;
                },
                width: "11%",
            },
        ] : [
            {
                title: 'Closing time',
                render: (data, type) => {
                    if (type === 'display' || type === 'filter') {
                        return data.date
                    }
                    return data.timestamp;
                },
                width: "25%",
            },
            {
                title: `${unit} Profit and Loss`,
                width: "25%",
            },
            {
                title: `Cumulated ${unit} Profit and Loss`,
                width: "25%",
            },
            {
                title: `${unit} traded volume`,
                width: "25%",
            },
        ]
    );
    pnlTable.DataTable({
        data: rows.reverse(),
        columns: columns,
        order: previousOrder,
    });
}

const fetchPnlHistory = async (scale, pair) => {
    const url = $("#pnl_historyChart").data("url");
    if(typeof url === "undefined"){
        return [];
    }
    return await async_send_and_interpret_bot_update(null, `${url}${scale}&symbol=${pair}`, null, "GET", true)
}
