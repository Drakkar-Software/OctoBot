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

function addOrRemoveWatchedSymbol(event){
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

function watched_symbols_success_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", msg, "");
    if(updated_data["action"] === "add"){
        dom_root_element.removeClass("far");
        dom_root_element.addClass("fas");
    }else{
        dom_root_element.removeClass("fas");
        dom_root_element.addClass("far");
    }
}

function watched_symbols_error_callback(updated_data, update_url, dom_root_element, result, status, error){
    create_alert("error", result.responseText, "");
}

function update_pairs_colors(){
    $(".pair_status_card").each(function () {
        const first_eval = $(this).find(".status");
        const status = first_eval.attr("status");
        if(status.toLowerCase().includes("long")){
            $(this).addClass("card-long");
        }else if(status.toLowerCase().includes("short")){
            $(this).addClass("card-short");
        }
    })
}

function handle_cancel_buttons() {
    $("#cancel_all_orders").click(function () {
        cancel_after_confirm($('#CancelAllOrdersModal'), null, $(this).attr(update_url_attr));
    });
    add_cancel_individual_orders_button();
}

function cancel_after_confirm(modalElement, data, update_url){
    modalElement.modal("toggle");
    const confirmButton = modalElement.find(".btn-danger");
    confirmButton.off("click");
    modalElement.keypress(function(e) {
        if(e.which === 13) {
            handle_confirm(modalElement, confirmButton, data, update_url);
        }
    });
    confirmButton.click(function () {
        handle_confirm(modalElement, confirmButton, data, update_url);
    });
}

function handle_confirm(modalElement, confirmButton, data, update_url){
    send_and_interpret_bot_update(data, update_url, null, orders_request_success_callback, orders_request_failure_callback);
    modalElement.unbind("keypress");
    modalElement.modal("hide");
}

function add_cancel_individual_orders_button(){
    $("button[action=cancel_order]").each(function () {
        $(this).click(function () {
            cancel_after_confirm($('#CancelOrderModal'), $(this).attr("order_desc"), $(this).attr(update_url_attr));
        });
    });
}

function orders_request_success_callback(updated_data, update_url, dom_root_element, msg, status) {
    if(msg.hasOwnProperty("title")){
        create_alert("success", msg["title"], msg["details"]);
    }else{
        create_alert("success", msg, "");
    }
    reload_orders();
}

function orders_request_failure_callback(updated_data, update_url, dom_root_element, msg, status) {
    create_alert("error", msg.responseText, "");
    reload_orders();
}

function reload_orders(){
    $("#openOrderTable").load(location.href + " #openOrderTable",function(){
        $('#open_orders_datatable').DataTable({
            "paging":   false,
        });
        add_cancel_individual_orders_button();
        if ($("button[action=cancel_order]").length === 0){
            $("#cancel_all_orders").prop("disabled",true);
        }
    });
}

$(document).ready(function() {
    update_pairs_colors();
    $(".watched_element").each(function () {
        $(this).click(addOrRemoveWatchedSymbol);
    });
    $('#open_orders_datatable').DataTable({
        "paging":   false,
    });
    handle_cancel_buttons();
});
