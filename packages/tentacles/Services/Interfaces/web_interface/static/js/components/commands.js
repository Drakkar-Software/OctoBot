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

function load_commands_metadata() {
    const feedbackButton = $("#feedbackButton");
    if(feedbackButton.length > 0){
        $.get({
            url: feedbackButton.attr(update_url_attr),
            dataType: "json",
            success: function(msg, status){
                if(msg) {
                    feedbackButton.attr("href", msg);
                    feedbackButton.removeClass("disabled");
                }else{
                    setNoFeedback(feedbackButton);
                }
            },
            error: function(result, status, error){
                setNoFeedback(feedbackButton);
                window.console&&console.error("Impossible to get the current OctoBot feedback form: "+error);
            }
        })
    }
}

function setNoFeedback(feedbackButton){
    feedbackButton.text("No feedback system available for now");
}

function update_metrics_option(){
    const metrics_input = $("#metricsCheckbox");
    function metrics_success_callback(updated_data, update_url, dom_root_element, msg, status) {
        if(updated_data){
            create_alert("success", "Anonymous statistics enabled", "Thank you for supporting OctoBot development!");
        }else{
            create_alert("success", "Anonymous statistics disabled", "");
        }
    }
    send_and_interpret_bot_update(metrics_input.is(':checked'), metrics_input.attr(update_url_attr), null,
        metrics_success_callback, update_failure_callback);
}

function update_beta_option(){
    function beta_success_callback(updated_data, update_url, dom_root_element, msg, status) {
        const details = "Please restart your OctoBot for it to take effect."
        if(updated_data){
            create_alert("success", "Beta environment enabled", details);
        }else{
            create_alert("success", "Beta environment disabled", details);
        }
    }
    const beta_input = $("#beta-checkbox");
    send_and_interpret_bot_update(beta_input.is(':checked'), beta_input.attr(update_url_attr), null,
        beta_success_callback, update_failure_callback);
}

function update_failure_callback(updated_data, update_url, dom_root_element, msg, status) {
    create_alert("error", msg.responseText, "");
}

$(document).ready(function() {
    load_commands_metadata();
    $("#metricsCheckbox").change(function(){
        update_metrics_option();
    });
    $("#beta-checkbox").change(function(){
        update_beta_option();
    });
});
