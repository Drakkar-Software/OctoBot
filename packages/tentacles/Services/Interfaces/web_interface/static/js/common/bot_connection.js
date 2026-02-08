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

function init_status_websocket(){
    const onBotReconnected = () => _reconnectedCallbacks.forEach((callback) => callback());
    const socket = get_websocket("/notifications");
    socket.on('update', (data) => {
        if(_isBotDisconnected){
            _isBotDisconnected = false;
            onBotReconnected();
        }
        unlock_ui();
        manage_alert(data);
    });
    socket.on('disconnect', async () => {
        if(!_isBotDisconnected && await checkDisconnected()){
            _isBotDisconnected = true;
            lock_ui();
        }
    });
}

function manage_alert(data){
    try{
        const errors_count = data["errors_count"];
        const errorBadge = $("#errors-count-badge");
        if(errorBadge.length){
            if(errors_count > 0){
                errorBadge.text(errors_count);
            }else{
                errorBadge.text("");
            }
        }
        const notifications = data["notifications"];
        const maxDisplayedNotifications = 10;
        // only display latest notifications when too many to display
        const displayedNotifications = (
            notifications.length > maxDisplayedNotifications ?
            notifications.slice(notifications.length - maxDisplayedNotifications, notifications.length): notifications
        );
        $.each(displayedNotifications, (i, item) => {
            const toastAlertLevel = item["Level"] === "critical" ? "error": item["Level"]
            create_alert(toastAlertLevel, item["Title"], item["Message"], "", item["Sound"]);
            $.each(notificationCallbacks, (_, callback) => {
               callback(item["Title"], item);
            });
        })
    }
    catch(error) {
        console.log(error);
    }
}

function handle_route_button(){
    $(".btn").each((_, jsButton) => {
        if(!jsButton.hasAttribute('route')){
            return;
        }
        $(jsButton).click((event) => {
            const button = $(event.currentTarget);
            if (button[0].hasAttribute('route')){
                const command = button.attr('route');
                const origin_val = button.text();
                $.ajax({
                    url: command,
                    beforeSend: function() {
                        button.html("<i class='fa fa-circle-notch fa-spin'></i>");
                    },
                    success: function() {
                        create_alert("info", "OctoBot is stopping", "");
                    },
                    complete: function() {
                       button.html(origin_val);
                    }
                });
             }
        });
    });
}

function send_and_interpret_bot_update(updated_data, update_url, dom_root_element, success_callback, error_callback, method="POST"){
    $.ajax({
        url: update_url,
        type: method,
        dataType: "json",
        contentType: 'application/json',
        data: JSON.stringify(updated_data),
        success: function(msg, status){
            if(typeof success_callback === "undefined") {
                if(dom_root_element != null){
                    update_dom(dom_root_element, msg);
                }
            }
            else{
                success_callback(updated_data, update_url, dom_root_element, msg, status)
            }
        },
        error: function(result, status, error){
            window.console&&console.error(result, status, error);
            if(typeof error_callback === "undefined") {
                let error_text = result.responseText.length > 1000 ? status : result.responseText;
                create_alert("error", "Error: "+error_text+".", "");
            }
            else{
                error_callback(updated_data, update_url, dom_root_element, result, status, error);
            }
        }
    })
}

const async_send_and_interpret_bot_update = async (updated_data, update_url, dom_root_element, method="POST", alertOnFailure=true) => {
    return new Promise((resolve, reject) => {
        const success = (updated_data, update_url, dom_root_element, msg, status) => {
            resolve(msg);
        }
        const failure = (updated_data, update_url, dom_root_element, msg, status) => {
            if(alertOnFailure){
                generic_request_failure_callback(updated_data, update_url, dom_root_element, msg, status)
            }
            reject(msg);
        }
        send_and_interpret_bot_update(updated_data, update_url, dom_root_element, success, failure, method);
    });
}

const notificationCallbacks = [];
const _reconnectedCallbacks = [];
let _isBotDisconnected = false;

function isBotDisconnected(){
    return _isBotDisconnected;
}

async function checkDisconnected(){
    try {
        await async_send_and_interpret_bot_update(null, $("#resources-urls").data("ping-url"), null, "GET", false);
        return false;
    } catch (err) {
        return true;
    }
}

function register_notification_callback(callback){
    notificationCallbacks.push(callback);
}

function registerReconnectedCallback(callback){
    _reconnectedCallbacks.push(callback);
}

$(document).ready(function () {
    handle_route_button();

    init_status_websocket();
});
