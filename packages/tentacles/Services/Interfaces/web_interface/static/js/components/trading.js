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


$(document).ready(async () => {
const addOrRemoveWatchedSymbol = (event) => {
    const sourceElement = $(event.target);
    const symbol = sourceElement.attr("symbol");
    let action = "add";
    if(sourceElement.hasClass("fas")){
        action = "remove";
    }
    const request = {};
    request["action"]=action;
    request["symbol"]=symbol;
    const update_url = sourceElement.attr("update_url");
    send_and_interpret_bot_update(request, update_url, sourceElement, watched_symbols_success_callback, watched_symbols_error_callback)
}

const watched_symbols_success_callback = (updated_data, update_url, dom_root_element, msg, status) => {
    create_alert("success", msg, "");
    if(updated_data["action"] === "add"){
        dom_root_element.removeClass("far");
        dom_root_element.addClass("fas");
    }else{
        dom_root_element.removeClass("fas");
        dom_root_element.addClass("far");
    }
}

const watched_symbols_error_callback = (updated_data, update_url, dom_root_element, result, status, error) => {
    create_alert("error", result.responseText, "");
}

const update_pairs_colors = () => {
    $(".pair_status_card").each((_, jselement) => {
        const element = $(jselement);
        const first_eval = element.find(".status");
        const status = first_eval.attr("status");
        if(status.toLowerCase().includes("very long")){
            element.addClass("card-very-long");
        }else if(status.toLowerCase().includes("long")){
            element.addClass("card-long");
        }else if(status.toLowerCase().includes("very short")){
            element.addClass("card-very-short");
        }else if(status.toLowerCase().includes("short")){
            element.addClass("card-short");
        }
    })
}

const get_displayed_orders_desc = () => {
    const orderDescs = [];
    const cancelButtonIndex = 8;
    $("#orders-table").DataTable().rows({filter: 'applied'}).data().map((value) => {
        orderDescs.push(value[cancelButtonIndex]);
    });
    return orderDescs;
}

const handleClearButton = () => {
    $("#clear-trades-history-button").on("click", (event) => {
        if (confirm("Clear trades history ?") === false) {
            return false;
        }
        const url = $(event.currentTarget).data("url")
        const success = (updated_data, update_url, dom_root_element, msg, status) => {
            // reload page on success
            reload_trades(true);
            reload_pnl(true);
        }
        send_and_interpret_bot_update(null, url, null, success, generic_request_failure_callback)
    })
}

const handle_cancel_buttons = () => {
    $("#cancel_all_orders").click((e) => {
        const to_cancel_orders = get_displayed_orders_desc();
        $("#ordersCount").text(to_cancel_orders.length);
        cancel_after_confirm($('#CancelAllOrdersModal'), to_cancel_orders, $(e.currentTarget).attr(update_url_attr), true);
    });
}

const handle_close_buttons = () => {
    $("button[data-action=close_position]").each((_, jsElement) => {
        $(jsElement).click((e) => {
            const element = $(e.currentTarget);
            close_after_confirm($('#ClosePositionModal'), element.data("position_symbol"),
                element.data("position_side"), element.data("update-url"));
        });
    });
}

const cancel_after_confirm = (modalElement, data, update_url, disable_cancel_buttons=false) => {
    modalElement.modal("toggle");
    const confirmButton = modalElement.find(".btn-danger");
    confirmButton.off("click");
    modalElement.keypress((e) => {
        if(e.which === 13) {
            handle_confirm(modalElement, confirmButton, data, update_url, disable_cancel_buttons);
        }
    });
    confirmButton.click(() => {
        handle_confirm(modalElement, confirmButton, data, update_url, disable_cancel_buttons);
    });
}

const close_after_confirm = (modalElement, symbol, side, update_url) => {
    modalElement.modal("toggle");
    const confirmButton = modalElement.find(".btn-danger");
    confirmButton.off("click");
    const data = {
        symbol: symbol,
        side: side,
    }
    modalElement.keypress((e) => {
        if(e.which === 13) {
            handle_close_confirm(modalElement, confirmButton, data, update_url);
        }
    });
    confirmButton.click(() => {
        handle_close_confirm(modalElement, confirmButton, data, update_url);
    });
}

const handle_close_confirm = (modalElement, confirmButton, data, update_url) => {
    send_and_interpret_bot_update(data, update_url, null, orders_request_success_callback, position_request_failure_callback);
    modalElement.unbind("keypress");
    modalElement.modal("hide");
}

const handle_confirm = (modalElement, confirmButton, data, update_url, disable_cancel_buttons) => {
    if (disable_cancel_buttons){
        disable_cancel_all_buttons();
    }
    send_and_interpret_bot_update(data, update_url, null, orders_request_success_callback, orders_request_failure_callback);
    modalElement.unbind("keypress");
    modalElement.modal("hide");
}

const add_cancel_individual_orders_buttons = () => {
    $("button[action=cancel_order]").each((_, element) => {
        $(element).off("click");
        $(element).on("click", (event) => {
            cancel_after_confirm($('#CancelOrderModal'), $(event.currentTarget).attr("order_desc"), $(event.currentTarget).attr(update_url_attr));
        });
    });
}

const disable_cancel_all_buttons = () => {
    $("#cancel_all_orders").prop("disabled",true);
    $("#cancel_order_progress_bar").show();
    const cancelIcon = $("#cancel_all_icon");
    cancelIcon.removeClass("fas fa-ban");
    cancelIcon.addClass("fa fa-spinner fa-spin");
    $("button[action=cancel_order]").each((_, jsElement) => {
        $(jsElement).prop("disabled",true);
    });
}

const orders_request_success_callback = (updated_data, update_url, dom_root_element, msg, status) => {
    if(msg.hasOwnProperty("title")){
        create_alert("success", msg["title"], msg["details"]);
    }else{
        create_alert("success", msg, "");
    }
    debouncedReloadDisplay();
}

const orders_request_failure_callback = (updated_data, update_url, dom_root_element, msg, status) => {
    create_alert("error", msg.responseText, "");
    debouncedReloadDisplay();
}

const position_request_failure_callback = (updated_data, update_url, dom_root_element, msg, status) => {
    create_alert("error", msg.responseText, "");
}

const async_get_data_from_url = async (element) => {
    const url = element.data("url");
    if(typeof url === "undefined"){
        return [];
    }
    return await async_send_and_interpret_bot_update(null, url, null, "GET", true)
}

const reload_positions = async (update) => {
    const table = $("#positions-table");
    const closePositionUrl = table.data("close-url");
    const positions = await async_get_data_from_url(table)
    $("#positions-waiter").hide();
    displayPositionsTable("positions-table", positions, closePositionUrl, update);
}

const reload_trades = async (update) => {
    const table = $("#trades-table");
    const refMarket = table.data("reference-market");
    const trades = await async_get_data_from_url(table)
    $("#trades-waiter").hide();
    return displayTradesTable("trades-table", trades, refMarket, update);
}

const reload_orders = async (update) => {
    const table = $("#orders-table");
    const cancelOrderUrl = table.data("cancel-url");
    const orders = await async_get_data_from_url(table)
    $("#orders-waiter").hide();
    displayOrdersTable("orders-table", orders, cancelOrderUrl, update);
}

const registerScaleSelector = () => {
    $('a[data-action="change-scale"]').on("click", (event) => {
        const selector = $(event.currentTarget);
        if(!selector.hasClass("active")){
            selector.addClass("active");
            $('a[data-action="change-scale"]').each((_, jselement) => {
                const element = $(jselement);
                if(element.data("scale") !== selector.data("scale")){
                    element.removeClass("active");
                }
            })
            reload_pnl(true);
        }
    })
}
const registerSymbolSelector = () => {
    $("#symbol-select").on("change", () => {
        reload_pnl(true);
    })
}
const registerFilterSelectors = () => {
    registerScaleSelector();
    registerSymbolSelector();
}
const getScale = () => {
    return $('a.nav-link.scale-selector.active').data("scale");
}
const getSymbol = () => {
    return $("#symbol-select").val();
}
const updateTradesCount = (pnlHistory) => {
    $("#match-trades-count").text(pnlHistory.reduce((sum, element) => sum + element.tc, 0));
}
const reload_pnl = async (update) => {
    if ($("#pnl_historyChart").length){
        const pnlHistory = await fetchPnlHistory(getScale(), getSymbol());
        loadPnlFullChartHistory(pnlHistory, update);
        loadPnlTableHistory(pnlHistory, update);
        updateTradesCount(pnlHistory);
        $("#pnl-waiter").hide();
    }
}

const resizePnlChart = () => {
    Plotly.Plots.resize("pnl_historyChart")
}

const ordersNotificationCallback = (title, _) => {
    if(title.toLowerCase().indexOf("order") !== -1){
        debouncedReloadDisplay();
    }
}

function debouncedReloadDisplay(){
    debounce(
        () => reloadDisplay(true),
        500
    );
}

const reloadDisplay = async (update) => {
    if(!update){
        await reload_pnl(update);
    }
    await reload_orders(update);
    await reload_positions(update);
    if(await reload_trades(update) && update){
        // only update pnl when a new trade appeared
        await reload_pnl(update);
    }
}

const onPnlTabShow = (e) => {
    resizePnlChart();
}

const registerOnTabShownEvents = () => {
    $("#panel-pnl-tab").on("shown.bs.tab", (e) => onPnlTabShow(e));
}

const registerTableButtonsEvents = () => {
    $("#positions-table").on("draw.dt", () => {
        handle_close_buttons();
    });
    $("#orders-table").on("draw.dt row-reordered", () => {
        if($("#orders-table").data("cancel-url") === undefined){
            return
        }
        add_cancel_individual_orders_buttons();
        const cancelIcon = $("#cancel_all_icon");
        $("#cancel_order_progress_bar").hide();
        if(cancelIcon.hasClass("fa-spinner")){
            cancelIcon.removeClass("fa fa-spinner fa-spin");
            cancelIcon.addClass("fas fa-ban");
        }
        if ($("button[action=cancel_order]").length === 0){
            $("#cancel_all_orders").prop("disabled", true);
        }else{
            $("#cancel_all_orders").prop("disabled", false);
        }
    });
}

const refreshTables = async () => {
    if (!initializedTables){
        await reloadDisplay(true);
        initializedTables = true
    }
}

let initializedTables = false

selectFirstTab();
registerFilterSelectors();
registerTableButtonsEvents();
update_pairs_colors();
$(".watched_element").each((_, element) => {
    $(element).click(addOrRemoveWatchedSymbol);
});
handle_cancel_buttons();
handleClearButton();
register_notification_callback(ordersNotificationCallback);
await reloadDisplay(false);
registerOnTabShownEvents();
handle_rounded_numbers_display();
try {
    if(registerGraphUpdateCallback !== undefined){
        registerGraphUpdateCallback(refreshTables);
    }
} catch (error){
    // nothing to do, registerGraphUpdateCallback doesn't exist
}
});
