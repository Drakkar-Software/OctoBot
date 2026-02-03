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

function trigger_trader_state(element) {
    let updated_config = {};
    const update_url = element.attr(update_url_attr);
    const config_key = element.attr(config_key_attr);
    const config_type = element.attr(config_type_attr);
    const set_to_activated = element.attr(current_value_attr).toLowerCase() === "true";

    if (config_key === "trader_enabled") {
        updated_config = {
            [config_type]: {
                "trader_enabled": set_to_activated,
                "trader-simulator_enabled": !set_to_activated,
            }
        }
    } else {
        updated_config = {
            [config_type]: {
                "trader_enabled": !set_to_activated,
                "trader-simulator_enabled": set_to_activated,
            }
        }
    }

    updated_config["restart_after_save"] = true;

    // send update

    function post_trading_state_update_success_callback(updated_data, update_url, dom_root_element, msg, status){
        create_alert("success", "Trader switched" , "");
        hideTradingStateModal()
    }

    function post_trading_state_update_error_callback(updated_data, update_url, dom_root_element, result, status, error){
        create_alert("error", "Error when switching trader : "+result.responseText, "");
        hideTradingStateModal()
    }
    send_and_interpret_bot_update(updated_config, update_url, null, post_trading_state_update_success_callback, post_trading_state_update_error_callback);
}

function displayTradingStateModal() {
    showModalIfAny($("#tradingSwitchModal"))
}

function hideTradingStateModal() {
    hideModalIfAny($("#tradingSwitchModal"))
}

$(document).ready(function() {
    $("#switchTradingState").click(function(){
        displayTradingStateModal()
    });
    $(".trading-mode-switch-button").click(function(){
        trigger_trader_state($(this))
    });
});
