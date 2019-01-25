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
    $.get({
        url: feedbackButton.attr(update_url_attr),
        dataType: "json",
        success: function(msg, status){
            feedbackButton.attr("href", msg);
            feedbackButton.removeClass("disabled");
        },
        error: function(result, status, error){
            feedbackButton.text("No feedback system available for now");
            window.console&&console.error("Impossible to get the current OctoBot feedback form: "+error);
        }
    })
}

$(document).ready(function() {
    load_commands_metadata();
});
