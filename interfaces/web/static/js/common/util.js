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

function setup_editable(){
    $.fn.editable.defaults.mode = 'inline';
}

function get_color(index){
    let color_index = index % (material_colors.length);
    return material_colors[color_index];
}

function get_dark_color(index){
    let color_index = index % (material_dark_colors.length);
    return material_dark_colors[color_index];
}

function handle_editable(){
    $(".editable").each(function(){
        $(this).editable();
    });
}

function replace_break_line(str, replacement=""){
    return str.replace(/(?:\r\n|\r|\n)/g, replacement);
}

function replace_spaces(str, replacement=""){
    return str.replace(/ /g, replacement);
}

function get_selected_options(element){
    const selected_options = [];
    element.find(":selected").each(function(){
        selected_options.push($(this).val())
    });
    return selected_options
}


// utility functions
function isDefined(thing){
    return (typeof thing !== typeof undefined && thing !== false && thing !==null)
}

function log(text){
    window.console&&console.log(text);
}

function get_events(elem, event_type){
    return $._data( elem[0], 'events' )[event_type];
}

function add_event_if_not_already_added(elem, event_type, handler){
    if(!check_has_event_using_handler(elem, event_type, handler)){
        elem.on(event_type, handler);
    }
}

function check_has_event_using_handler(elem, event_type, handler){
    const events = get_events(elem, event_type);
    let has_events = false;
    $.each(events, function () {
        if($(this)[0]["handler"] === handler){
            has_events = true;
        }
    });
    return has_events;
}
