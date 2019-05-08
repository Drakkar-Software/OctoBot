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

function update_badge(badge, new_text, new_class){
    badge.removeClass(secondary_badge);
    badge.removeClass(warning_badge);
    badge.removeClass(success_badge);
    badge.removeClass(primary_badge);
    badge.removeClass(modified_badge);
    badge.addClass(new_class);
    if (new_class === primary_badge){
        badge.addClass(modified_badge);
    }
    badge.html(new_text);
}

function update_list_item(list_item, new_class){
    list_item.removeClass(light_list_item);
    list_item.removeClass(success_list_item);
    list_item.addClass(new_class);
}

function update_element_required_marker_and_usability(element, display_marker) {
    const marker = element.children("[role='required-flag']");
    if(display_marker){
        marker.removeClass(hidden_class);
        element.removeClass(disabled_class);
        element.removeClass(disabled_item_class);
    }else{
        marker.addClass(hidden_class);
        element.addClass(disabled_class);
        element.addClass(disabled_item_class);
    }
}

function update_element_temporary_look(element){
    const set_to_activated = element.attr(current_value_attr).toLowerCase() === "true";
    const set_to_temporary = element.attr(current_value_attr).toLowerCase() !== element.attr(config_value_attr).toLowerCase();
    const is_back_to_startup_value = element.attr(startup_value_attr).toLowerCase() === element.attr(config_value_attr).toLowerCase();
    if(element.hasClass("list-group-item")){
        // list item
        const list_class = (set_to_activated ? success_list_item : light_list_item);
        update_list_item(element, list_class);
    }
    const badge = element.find(".badge");
    if(typeof badge !== "undefined") {
        if(set_to_temporary){
            update_badge(badge, unsaved_setting, primary_badge);
        }else{
            if(set_to_activated){
                if (!is_back_to_startup_value){
                    update_badge(badge, activation_pending, warning_badge);
                }else{
                    update_badge(badge, activated, success_badge);
                }
            }else{
                if (!is_back_to_startup_value){
                    update_badge(badge, deactivation_pending, warning_badge);
                }else{
                    update_badge(badge, deactivated, secondary_badge);
                }
            }
        }
    }
}

function change_boolean(to_update_element, new_value, new_value_string){
    const badge = to_update_element.find(".badge");
    const startup_value = to_update_element.attr(startup_value_attr).toLowerCase();
    const is_back_to_startup_value = startup_value === new_value_string;
    if(new_value){
        update_list_item(to_update_element, success_list_item);
        if (!is_back_to_startup_value){
            update_badge(badge, activation_pending, warning_badge);
        }else{
            update_badge(badge, activated, success_badge);
        }
    }else{
        update_list_item(to_update_element, light_list_item);
        if (!is_back_to_startup_value){
            update_badge(badge, deactivation_pending, warning_badge);
        }else{
            update_badge(badge, deactivated, secondary_badge);
        }
    }
}

function update_activated_deactivated_tentacles(root_element, message, element_type){
    const config_value_attr = "config-value";

    for (const conf_key in message[element_type]) {
        const new_value = message[element_type][conf_key];
        const new_value_type = "boolean";
        const new_value_string = new_value.toString();
        const to_update_element = root_element.find("#"+conf_key);

        const attr = to_update_element.attr(config_value_attr);

        if (isDefined(attr)) {
            if (attr.toLowerCase() !== new_value_string){
                to_update_element.attr(config_value_attr, new_value_string);
                if(new_value_type === "boolean"){
                    const bool_val = new_value.toLowerCase() === "true";
                    change_boolean(to_update_element, bool_val, new_value_string);
                }

            }
        }else{
            // todo find cards to update using returned data
            to_update_element.removeClass(modified_class);
        }

    }
}

function update_dom(root_element, message){
    // update global configuration
    const super_container = $("#super-container");
    confirm_all_modified_classes(super_container);

    // update evaluators config
    update_activated_deactivated_tentacles(root_element, message, "evaluator_updated_config");

    // update trading config
    update_activated_deactivated_tentacles(root_element, message, "trading_updated_config");
}

function create_alert(a_level, a_title, a_msg, url="_blank"){
    toastr[a_level](a_msg, a_title);

    toastr.options = {
      "closeButton": false,
      "debug": false,
      "newestOnTop": false,
      "progressBar": false,
      "positionClass": "toast-top-right",
      "preventDuplicates": false,
      "onclick": null,
      "showDuration": 300,
      "hideDuration": 1000,
      "timeOut": 5000,
      "extendedTimeOut": 1000,
      "showEasing": "swing",
      "hideEasing": "linear",
      "showMethod": "fadeIn",
      "hideMethod": "fadeOut"
    }
}

function lock_ui(){
    $(".nav-link").addClass("disabled");
    update_status(false);
}

function unlock_ui(){
    $(".nav-link").removeClass("disabled");
    update_status(true);
}

function update_status(status){
    const icon_status = $("#navbar-bot-status");
    const icon_reboot = $("#navbar-bot-reboot");

    // create alert if required
    if (status && icon_status.hasClass("fa-times-circle")){
        create_alert("success", "Reconnected to Octobot", "");
    }else if(!status && icon_status.hasClass("fa-check")){
        create_alert("error", "Connection lost with Octobot", "Reconnecting...");
    }

    // update central status
    if (status){
        icon_status.removeClass("fa-times-circle icon-black");
        icon_status.addClass("fa-check");
        icon_status.attr("title","OctoBot operational");
    }else{
        icon_status.removeClass("fa-check");
        icon_status.addClass("fa-times-circle icon-black");
        icon_status.attr("title","OctoBot offline");
    }

    // update reboot status
    if (status){
        icon_reboot.removeClass("fa-spin");
    }else{
        icon_reboot.addClass("fa-spin");
    }
}

function register_exit_confirm_function(check_function) {
    const exit_event = 'beforeunload';
    $(window).bind(exit_event, function(){
      if(check_function()){
          return "Exit without saving ?";
      }
    });
}

function remove_exit_confirm_function(){
    const exit_event = 'beforeunload';
    $(window).off(exit_event);
}


function confirm_all_modified_classes(container){
    container.find("."+deck_container_modified_class).each(function () {
        toggle_class($(this), deck_container_modified_class, false);
    });
    container.find("."+card_class_modified).each(function () {
        toggle_class($(this), card_class_modified, false);
    });
    container.find("."+added_class).each(function () {
        toggle_class($(this), added_class, false);
    });
}

function toggle_class(elem, class_type, toogle=true){
    if(toogle && !elem.hasClass(class_type)){
        elem.addClass(class_type, 500);
    }else if(!toogle && elem.hasClass(class_type)){
        elem.removeClass(class_type);
    }
}

function toogle_deck_container_modified(container, modified=true) {
    toggle_class(container, deck_container_modified_class, modified);
}

function toogle_card_modified(card, modified=true) {
    toggle_class(card, card_class_modified, modified);
}
