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

function get_tabs_config(){
    return $(document).find("." + config_root_class + " ." + config_container_class);
}

function handle_reset_buttons(){
    $("#reset-config").click(function() {
        reset_configuration_element();
    })
}

function something_is_unsaved(){

    const config_root = $("#super-container");
    return (
        config_root.find("."+card_class_modified).length > 0
            || config_root.find("."+deck_container_modified_class).length > 0
            || config_root.find("."+primary_badge).length > 0
    )
}

function parse_new_value(element){
    const raw_data = replace_spaces(replace_break_line(element.text()));

    // simple case
    if(element[0].hasAttribute(current_value_attr)){
        const value = replace_spaces(replace_break_line(element.attr(current_value_attr)));
        if(element[0].hasAttribute(config_data_type_attr)){
            switch(element.attr(config_data_type_attr)) {
                case "bool":
                    return value === true || value === "true";
                case "number":
                    return Number(value);
                default:
                    return value;
            }
        }else{
            return value;
        }
    }
    // with data type
    else if(element[0].hasAttribute(config_data_type_attr)){
        switch(element.attr(config_data_type_attr)) {
            case "bool":
                return element.is(":checked");
            case "list":
                const new_value = [];
                element.find(":selected").each(function(index, value){
                    new_value.splice(index, 0, replace_spaces(replace_break_line(value.text)));
                });
                return new_value;
            case "number":
                return Number(raw_data);
            default:
                return raw_data;
        }

    // without information
    }else{
        return raw_data;
    }
}

function handle_save_buttons(){
    $("#save-config").click(function() {
        const full_config = $("#super-container");
        const updated_config = {};
        const update_url = $("#save-config").attr(update_url_attr);

        // take all tabs into account
        get_tabs_config().each(function(){
            $(this).find("."+config_element_class).each(function(){
                const config_type = $(this).attr(config_type_attr);

                if(!(config_type in updated_config)){
                    updated_config[config_type] = {};
                }

                const new_value = parse_new_value($(this));
                const config_key = get_config_key($(this));

                if(get_config_value_changed($(this), new_value, config_key)){
                    updated_config[config_type][config_key] = new_value;
                }
            })
        });

        // send update
        send_and_interpret_bot_update(updated_config, update_url, full_config, handle_save_buttons_success_callback);
    })
}

function get_config_key(elem){
    return elem.attr(config_key_attr);
}

function get_config_value_changed(element, new_value, config_key) {
    let new_value_str = new_value.toString();
    if(new_value instanceof Array && new_value.length > 0){
        //need to format array to match python string representation of config
        var str_array = [];
        $.each(new_value, function(i, val) {
            str_array.push("'"+val+"'");
        });
        new_value_str = "[" + str_array.join(", ") + "]";
    }
    return get_value_changed(new_value_str, element.attr(config_value_attr), config_key);
}

function get_value_changed(new_val, dom_conf_val, config_key){
    const lower_case_val = new_val.toLowerCase();
    if(new_val.toLowerCase() !== dom_conf_val.toLowerCase()){
        return true;
    }else if (config_key in validated_updated_global_config){
        return lower_case_val !== validated_updated_global_config[config_key].toString().toLowerCase();
    }else{
        return false;
    }

}

function handle_save_buttons_success_callback(updated_data, update_url, dom_root_element, msg, status){
    update_dom(dom_root_element, msg);
    create_alert("success", "Configuration successfully updated", "Restart OctoBot for changes to be applied.");
}

function handle_evaluator_configuration_editor(){
    $(".config-element").click(function(e){
        if (isDefined($(e.target).attr(no_activation_click_attr))){
            // do not trigger when click on items with no_activation_click_attr set
            return;
        }
        const element = $(this);

        if (element.hasClass(config_element_class)){

            if (element[0].hasAttribute(config_type_attr) && element.attr(config_type_attr) === evaluator_config_type){

                // build data update
                let new_value = parse_new_value(element);
                let current_value;

                try {
                    current_value = element.attr(current_value_attr).toLowerCase();
                }
                catch(e) {
                    current_value = element.attr(current_value_attr);
                }

                // todo
                if (current_value === "true"){
                    new_value = "false";
                }else if(current_value === "false"){
                    new_value = "true";
                }

                // update current value
                element.attr(current_value_attr, new_value);

                //update dom
                update_element_temporary_look(element);
            }
        }
    });
}

function reset_configuration_element(){
    remove_exit_confirm_function();
    location.reload();
}

let validated_updated_global_config = {};

$(document).ready(function() {
    handle_reset_buttons();
    handle_save_buttons();

    handle_evaluator_configuration_editor();

    register_exit_confirm_function(something_is_unsaved);
});