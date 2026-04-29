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

$(document).ready(function() {
    // for some reason this is not always working when leaving it to bootstrap
    const ensureModals = () => {
        $('button[data-toggle="modal"]').each((_, element) => {
            $(element).click((event) => {
                const events = jQuery._data(event.currentTarget, "events" )
                // One event means bootstrap did not register this click event
                if(typeof events !== "undefined" && typeof events.click !== "undefined"
                    && events.click.length === 1){
                    const element = $(event.currentTarget);
                    element.parent().children(element.data("target")).modal();
                }
            })
        })
    }

    ensureModals();
});
