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


const sidebarNavLinks = $(".sidebar").find(".nav-link[role='tab']:not(.dropdown-toggle)");

function handle_nested_sidenav(){
    sidebarNavLinks.each(function (){
        $(this).on("click",function (e){
            e.preventDefault();
            activate_tab($(this), sidebarNavLinks);
        });
    });
}

function get_tabs_config(){
    return $(document).find("." + config_root_class + " ." + config_container_class);
}


function handle_reset_buttons(){
    $("#reset-config").click(function() {
        reset_configuration_element();
    })
}

function handle_remove_buttons(){
    // Card deck removing
    $(document).on("click", ".remove-btn", function() {
        const deleted_element_key = get_card_config_key($(this));
        const deck = get_deck_container($(this));
        const card = get_card_container($(this));
        if ($.inArray(deleted_element_key, deleted_global_config_elements) === -1 && !card.hasClass(added_class)){
            deleted_global_config_elements.push(deleted_element_key);
        }
        $(this).closest(".card").fadeOut("normal", function() {
            $(this).remove();
            check_deck_modifications(deck);
        });
    });
}

function handle_buttons() {
    $("button[action=post]").each(function () {
        $(this).click(function () {
            send_and_interpret_bot_update(null, $(this).attr(update_url_attr), null, generic_request_success_callback, generic_request_failure_callback);
        });
    });
}

function check_deck_modifications(deck){
    if(deck.find("."+added_class).length > 0 || deleted_global_config_elements.length > 0){
        toogle_deck_container_modified(deck);
    }else{
        toogle_deck_container_modified(deck, false);
    }
}

function handle_add_buttons(){
    handleCardDecksAddButtons();
    handleEditableAddButtons();
}

function handleEditableAddButtons(){
    $("button[data-role='editable-add']").click((jsElement) => {
        const button = $(jsElement.currentTarget);
        const parentContainer = button.parent();
        const targetTemplate = parentContainer.find(`span[data-add-template-for='${button.attr("data-add-template-target")}']`);
        const selectedValue = button.data("default-key");
        let newEditable = targetTemplate.html().replace(new RegExp("Empty","g"), selectedValue);
        button.before(newEditable);
        handle_editable();
        register_edit_events();
    })
}

function handleEditableRenameIfNotAlready(e, params){
    const element = $(e.target);
    // 0. update key-value config to use the new key
    const previousKey = element.text().trim();
    let newKey = element.text().trim();
    if(isDefined(params) && isDefined(params["newValue"])){
        newKey = params["newValue"];
    }
    const previousConfigKey = element.attr("data-label-for");
    const valueToUpdate = element.parent().parent().find(`a[config-key=${previousConfigKey}]`);
    const newConfigKey = previousConfigKey.replace(new RegExp(previousKey,"g"), newKey);
    element.attr("data-label-for", newConfigKey)
    valueToUpdate.attr("config-key", newConfigKey)
    // 1. force change to the associated value to save it
    valueToUpdate.data("changed", true);
    // 2. add previous key to deleted values unless it's the default key
    deleted_global_config_elements.push(previousConfigKey);
    const card_container = get_card_container(element);
    toogle_card_modified(card_container, true);
}

function registerHandleEditableRenameIfNotAlready(element, events, handler){
    if(typeof element.data("label-for") !== "undefined"){
        events.forEach((event) => {
            if(!check_has_event_using_handler(element, event, handler)){
                element.on(event, handler);
            }
        })
    }
}

function handleCardDecksAddButtons(){
    // Card deck adding
    $(".add-btn").click(function() {

        const button_id = $(this).attr("id");

        const deck = $(this).parents("." + config_root_class).find(".card-deck");
        const select_input = $("#" + button_id + "Select");
        let select_value = select_input.val();

        // currencies
        const currencyDetails = currencyDetailsById[select_value];
        let select_symbol = "";
        let currency_id = undefined;
        if(isDefined(currencyDetails)){
            currency_id = select_value;
            select_value = currencyDetails.n;
            select_symbol = currencyDetails.s
        }

        // exchanges
        let has_websockets = false;
        const ws_attr = select_input.find("[data-tokens='"+select_value+"']").attr("data-ws");
        if(isDefined(ws_attr)){
            has_websockets = ws_attr === "True";
        }

        const editable_selector = "select[editable_config_id=\"multi-select-element-" + select_value + "\"]:first";
        let target_template = $("#" + button_id + "-template-default");

        //services
        const in_services = button_id === "AddService";
        if (in_services){
            target_template = $("#" + button_id + "-template-default-"+select_value);
        }

        // check if not already added
        if(deck.find("div[name='"+select_value+"']").length === 0){
            let template_default = target_template.html().replace(new RegExp(config_default_value,"g"), select_value);
            template_default = template_default.replace(new RegExp("card-text symbols default","g"), "card-text symbols");
            template_default = template_default.replace(new RegExp("card-img-top currency-image default","g"), "card-img-top currency-image");
            if(isDefined(currency_id)){
                template_default = template_default.replace(new RegExp(`data-currency-id="${config_default_value.toLowerCase()}"`), `data-currency-id="${currency_id}"`);
            }
            if(has_websockets){
                // all exchanges cards
                template_default = template_default.replace(new RegExp("data-role=\"websocket-mark\" class=\"d-none "), "data-role=\"websocket-mark\" class=\"");
            }
            deck.append(template_default).hide().fadeIn();

            handle_editable();

            // select options with reference market if any
            $(editable_selector).each(function () {
                if (
                    $(this).siblings('.select2').length === 0
                    && !$(this).parent().hasClass('default')
                ){
                    $(this).find("option").each(function () {
                        const option = $(this);
                        const symbols = option.attr("value").split("/");
                        const reference_market = select_input.attr("reference_market").toUpperCase();
                        if (symbols[0] === select_symbol && symbols[1] === reference_market){
                            option.attr("selected", "selected");
                        }
                        // remove options without this currency symbol
                        if (!(symbols[0] === select_symbol || symbols[1] === select_symbol)){
                            option.detach();
                        }
                    });
                }
            });

            let placeholder = "";
            if(select_symbol){
                placeholder = "Select trading pair(s)";
            }else if(in_services){
                // telegram is the only service with a select2 element
                placeholder = "Add user(s) in whitelist";
            }

            // add select2 selector
            $(editable_selector).each(function () {
                if (
                    $(this).siblings('.select2').length === 0
                    && !$(this).parent().hasClass('default')
                ) {
                    $(this).select2({
                        width: 'resolve', // need to override the changed default
                        tags: true,
                        placeholder: placeholder,
                    });
                }
            });

            toogle_deck_container_modified(get_deck_container($(this)));
            // refresh images if required
            fetch_images();
            handleDefaultImages();

            register_edit_events();
        }

    });
}

function handle_special_values(currentElem){
    if (currentElem.is(traderSimulatorCheckbox) || currentElem.is(traderCheckbox)){
        if (currentElem.is(":checked")){
            const otherElem = currentElem.is(traderCheckbox) ? traderSimulatorCheckbox : traderCheckbox;
            otherElem.prop('checked', false);
            otherElem.trigger("change");
        }
    } else if(currentElem.is(tradingReferenceMarket)) {
        display_generic_modal("Change reference market",
            "Do you want to adapt the reference market for all your configured pairs ?",
            "",
            function () {
                let url = "/api/change_reference_market_on_config_currencies";
                let data = {};
                data["old_base_currency"] = tradingReferenceMarket.attr(config_value_attr);
                data["new_base_currency"] = tradingReferenceMarket.text();
                send_and_interpret_bot_update(data, url, null, generic_request_success_callback, generic_request_failure_callback);
            },
            null);
    } else if(currentElem.data("summary-field") === "radio-select"){
        currentElem.find('input[type="radio"]').each((index, element) => {
            const parsedElement = $(element);
            if(parsedElement.is(":checked")){
                currentElem.attr("current-value", parsedElement.attr("value"));
            }
        })
    }
}

function register_edit_events(){
    $('.config-element').each(function (){
        const element = $(this);
        if(typeof element.data("label-for") === "undefined"){
            add_event_if_not_already_added(element, 'save', card_edit_handler);
            add_event_if_not_already_added(element, 'change', card_edit_handler);
        }else{
            registerHandleEditableRenameIfNotAlready(element, ['save', 'change'], handleEditableRenameIfNotAlready)
        }
    });
    register_exchanges_checks(false);
}

function card_edit_handler(e, params){
    const current_elem = $(this);

    handle_special_values(current_elem);

    let new_value = parse_new_value(current_elem);
    if(isDefined(params) && isDefined(params["newValue"])){
        new_value = params["newValue"];
    }
    const config_key = get_config_key(current_elem);
    const card_container = get_card_container(current_elem);

    const other_config_elements = card_container.find("."+config_element_class);
    let something_changed = get_config_value_changed(current_elem, new_value, config_key);

    if(!something_changed){
        // if nothing changed on the current field, check other fields of the card
        $.each(other_config_elements, function () {
            if ($(this)[0] !== current_elem[0]){
                var elem_new_value = parse_new_value($(this));
                var elem_config_key = get_config_key($(this));
                something_changed = something_changed || get_config_value_changed($(this), elem_new_value, elem_config_key);
            }

        });
    }

    toogle_card_modified(card_container, something_changed);

}

function something_is_unsaved(){

    const config_root = $("#super-container");
    return (
        config_root.find("."+card_class_modified).length > 0
            || config_root.find("."+deck_container_modified_class).length > 0
            || config_root.find("."+modified_badge).length > 0
    )
}

function parse_new_value(element){
    const raw_data = element.text().trim();

    // simple case
    if(element[0].hasAttribute(current_value_attr)){
        const value = element.attr(current_value_attr).trim();
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
                    new_value.splice(index, 0, value.text.trim());
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

function _save_config(element, restart_after_save) {
    const full_config = $("#super-container");
    const updated_config = {};
    const update_url = element.attr(update_url_attr);

    // take all tabs into account
    get_tabs_config().each(function(){
        $(this).find("."+config_element_class).each(function(){
            const configElement = $(this)
            if(configElement.parent().parent().hasClass(hidden_class)
               || typeof configElement.attr("data-label-for") !== "undefined"){
                // do not add hidden elements (add templates)
                // do not add element labels
                return
            }
            const config_type = configElement.attr(config_type_attr);
            if(config_type !== evaluator_list_config_type) {

                if (!(config_type in updated_config)) {
                    updated_config[config_type] = {};
                }

                const new_value = parse_new_value(configElement);
                const config_key = get_config_key(configElement);

                if (get_config_value_changed(configElement, new_value, config_key)
                    && !config_key.endsWith("_Empty")) {
                    updated_config[config_type][config_key] = new_value;
                }
            }
        })
    });

    // take removed elements into account
    updated_config["removed_elements"] = deleted_global_config_elements;

    updated_config["restart_after_save"] = restart_after_save;

    // send update
    send_and_interpret_bot_update(updated_config, update_url, full_config, handle_save_buttons_success_callback);
}

function handle_save_buttons(){
    $("#save-config").click(function() {
        _save_config($(this), false);
    })
    $("#save-config-and-restart").click(function() {
        _save_config($(this), true);
    })
}

function get_config_key(elem){
    return elem.attr(config_key_attr);
}

function get_card_config_key(card_component, config_type="global_config"){
    const element_with_config = card_component.parent(".card-body");
    return get_config_key(element_with_config);
}

function get_deck_container(elem) {
    return elem.parents("."+deck_container_class);
}

function get_card_container(elem) {
    return elem.parents("."+config_card_class);
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
    return get_value_changed(new_value_str, element.attr(config_value_attr).trim(), config_key)
        || element.data("changed") === true;
}

function get_value_changed(new_val, dom_conf_val, config_key){
    const lower_case_val = new_val.toLowerCase();
    if(is_different_value(new_val, lower_case_val, dom_conf_val)){
        // only push update if the new value is not the previously updated one
        if (has_element_already_been_updated(config_key)) {
            return !has_update_already_been_applied(lower_case_val, config_key);
        }
        return true;
    }else{
        // nothing changed in DOM but the previously updated value might be different (ex: back on initial value)
        // only push update if the new value is not the previously updated one
        if (has_element_already_been_updated(config_key)) {
            return !has_update_already_been_applied(lower_case_val, config_key);
        }
        return false;
    }
}

function is_different_value(new_val, lower_case_new_val, dom_conf_val){
    return !(lower_case_new_val === dom_conf_val.toLowerCase() ||
        ((Number(new_val) === Number(dom_conf_val) && $.isNumeric(new_val))));
}

function has_element_already_been_updated(config_key){
    return config_key in validated_updated_global_config;
}

function has_update_already_been_applied(lower_case_val, config_key){
    return lower_case_val === validated_updated_global_config[config_key].toString().toLowerCase();
}

function handle_save_buttons_success_callback(updated_data, update_url, dom_root_element, msg, status){
    updated_validated_updated_global_config(msg["global_updated_config"]);
    update_dom(dom_root_element, msg);
    create_alert("success", "Configuration successfully updated", "Restart OctoBot for changes to be applied.");
}

function apply_evaluator_default_config(element) {
    const default_config = element.attr("default-elements").replace(new RegExp("'","g"),'"');
    const update_url = $("#save-config").attr(update_url_attr);
    const updated_config = {};
    const config_type = element.attr(config_type_attr);
    updated_config[config_type] = {};

    $.each($.parseJSON(default_config), function (i, config_key) {
        updated_config[config_type][config_key] = "true";
    });

    updated_config["deactivate_others"] = true;

    // send update
    send_and_interpret_bot_update(updated_config, update_url, null, handle_apply_evaluator_default_config_success_callback);
}

function handle_apply_evaluator_default_config_success_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", "Evaluators activated", "Restart OctoBot for changes to be applied");
}

function other_element_activated(root_element){
    let other_activated_modes_count = root_element.children("."+success_list_item).length;
    return other_activated_modes_count > 1;
}

function deactivate_other_elements(element, root_element) {
    const element_id = element.attr("id");
    root_element.children("."+success_list_item).each(function () {
        const element = $(this);
        if(element.attr("id") !== element_id){
            element.attr(current_value_attr, "false");
            update_element_temporary_look(element);
        }
    })
}

function updateTradingModeSummary(selectedElement){
    const elementDocModal = $(`#${selectedElement.attr("name")}Modal`);
    const elementDoc = elementDocModal.find(".modal-body").text().trim();
    const blocks = elementDoc.trim().split(".\n");
    let summaryBlocks = `${blocks[0]}.`;
    if (summaryBlocks.length < 80 && blocks.length > 1){
        summaryBlocks = `${summaryBlocks} ${blocks[1]}.`;
    }
    $("#selected-trading-mode-summary").html(summaryBlocks);
}

function updateStrategySelector(required_elements){
    const noStrategyInfo = $("#no-strategy-info");
    const strategyConfig = $("#evaluator-config-root");
    const strategyConfigFooter = $("#evaluator-config-root-footer");
    if (required_elements.length > 1) {
        noStrategyInfo.addClass(hidden_class);
        strategyConfig.removeClass(hidden_class);
        strategyConfigFooter.removeClass(hidden_class);
    } else {
        noStrategyInfo.removeClass(hidden_class);
        strategyConfig.addClass(hidden_class);
        strategyConfigFooter.addClass(hidden_class);
    }
}

function update_requirement_activation(element) {
    const required_elements = element.attr("requirements").split("'");
    const default_elements = element.attr("default-elements").split("'");
    $("#evaluator-config-root").children(".config-element").each(function () {
        const element = $(this);
        if(required_elements.indexOf(element.attr("id")) !== -1){
            if(default_elements.indexOf(element.attr("id")) !== -1){
                element.attr(current_value_attr, "true");
            }
            update_element_temporary_look(element);
            update_element_required_marker_and_usability(element, true);
        }else{
            element.attr(current_value_attr, "false");
            update_element_temporary_look(element);
            update_element_required_marker_and_usability(element, false);
        }
    });
    updateStrategySelector(required_elements);
}

function get_activated_strategies_count() {
    return $("#evaluator-config-root").children("."+success_list_item).length
}

function get_activated_trading_mode_min_strategies(){
    const activated_trading_modes = $("#trading-modes-config-root").children("."+success_list_item);
    if(activated_trading_modes.length > 0) {
        return parseInt(activated_trading_modes.attr("requirements-min-count"));
    }else{
        return 1;
    }
}

function check_evaluator_configuration() {
    const trading_modes = $("#trading-modes-config-root");
    if(trading_modes.length) {
        const activated_trading_modes = trading_modes.children("." + success_list_item);
        if (activated_trading_modes.length) {
            const required_elements = activated_trading_modes.attr("requirements").split("'");
            let at_least_one_activated_element = false;
            $("#evaluator-config-root").children(".config-element").each(function () {
                const element = $(this);
                if (required_elements.indexOf(element.attr("id")) !== -1) {
                    at_least_one_activated_element = true;
                    update_element_required_marker_and_usability(element, true);
                } else {
                    update_element_required_marker_and_usability(element, false);
                }
            });
            if (required_elements.length > 1 && !at_least_one_activated_element) {
                create_alert("error", "Trading modes require at least one strategy to work properly, please activate the " +
                    "strategy(ies) you want for the selected mode.", "");
            }
           updateStrategySelector(required_elements);
           updateTradingModeSummary(activated_trading_modes);
        } else {
            create_alert("error", "No trading mode activated, OctoBot need at least one trading mode.", "");
        }
    }
}

function handle_activation_configuration_editor(){
    $(".config-element").click(function(e){
        if (isDefined($(e.target).attr(no_activation_click_attr))){
            // do not trigger when click on items with no_activation_click_attr set
            return;
        }
        const element = $(this);

        if (element.hasClass(config_element_class) && ! element.hasClass(disabled_class)){

            if (element[0].hasAttribute(config_type_attr)) {
                if(element.attr(config_type_attr) === evaluator_config_type
                    || element.attr(config_type_attr) === trading_config_type
                    || element.attr(config_type_attr) === tentacles_config_type) {

                    const is_strategy = element.attr(config_type_attr) === evaluator_config_type;
                    const is_trading_mode = element.attr(config_type_attr) === trading_config_type;
                    const is_tentacle = element.attr(config_type_attr) === tentacles_config_type;
                    const allow_only_one_activated_element = is_trading_mode || is_tentacle;

                    // build data update
                    let new_value = parse_new_value(element);
                    let current_value;

                    try {
                        current_value = element.attr(current_value_attr).toLowerCase();
                    } catch (e) {
                        current_value = element.attr(current_value_attr);
                    }
                    let root_element = $("#trading-modes-config-root");
                    if (is_tentacle){
                        root_element = element.parent(".config-container");
                    }
                    if (current_value === "true") {
                        if (allow_only_one_activated_element && !other_element_activated(root_element)) {
                            create_alert("error", "Impossible to disable all options.", "");
                            return;
                        } else if (is_strategy) {
                            // strategy
                            const min_strategies = get_activated_trading_mode_min_strategies();
                            if (get_activated_strategies_count() <= min_strategies) {
                                create_alert("error", "This trading mode requires at least " + min_strategies + " activated strategies.", "");
                                return;
                            }
                        }
                        new_value = "false";
                    } else if (current_value === "false") {
                        new_value = "true";
                        if (allow_only_one_activated_element) {
                            deactivate_other_elements(element, root_element);
                        }
                    }
                    if (is_trading_mode) {
                        update_requirement_activation(element);
                        updateTradingModeSummary(element);
                    }

                    // update current value
                    element.attr(current_value_attr, new_value);

                    //update dom
                    update_element_temporary_look(element);
                }
                else if (element.attr(config_type_attr) === evaluator_list_config_type){
                    const strategy_name = element.attr("tentacle");
                    apply_evaluator_default_config($("a[name='"+strategy_name+"']"));
                }
            }
        }
    });
}


function handle_import_currencies(){
    $("#import-currencies-button").on("click", function(){
        $("#import-currencies-input").click();
    });
    $("#import-currencies-input").on("change", function () {
        var GetFile = new FileReader();
        GetFile.onload = function(){
            let update_url = $("#import-currencies-button").attr(update_url_attr);
            let data = {};
            data["action"] = "update";
            data["currencies"] = JSON.parse(GetFile.result);
            send_and_interpret_bot_update(data, update_url, null,
                handle_save_buttons_success_callback, generic_request_failure_callback);
        };
        GetFile.readAsText(this.files[0]);
    });
}


function handle_export_currencies_button(){
    $("#export-currencies-button").on("click", function(){
        update_url = $("#export-currencies-button").attr(update_url_attr);
        $.get(update_url, null, function(data, status){
            download_data(JSON.stringify(data), "currencies_export.json");
        });
    });
}


function reset_configuration_element(){
    remove_exit_confirm_function();
    location.reload();
}

function updated_validated_updated_global_config(updated_data){
    for (const conf_key in updated_data) {
        validated_updated_global_config[conf_key] = updated_data[conf_key];
    }
    const to_del_attr = [];
    $.each(deleted_global_config_elements, function (i, val) {
        for (const attribute in validated_updated_global_config) {
            if(attribute.startsWith(val)){
                to_del_attr.push(attribute);
            }
        }
    });
    $.each(to_del_attr, function (i, val) {
        delete validated_updated_global_config[val];
    });
    deleted_global_config_elements = [];
}

function fetch_currencies(){
    const maxDisplayedOptions = 2000;  // display only the first 2000 options to avoid select performance issues
    const getCurrencyOption = (addCurrencySelect, details) => {
        return new Option(`${details.n} - ${details.s}`, details.i, false, false);
    }
    if(!$("#AddCurrencySelect").length){
        return
    }
    $.get({
        url: $("#AddCurrencySelect").data("fetch-url"),
        dataType: "json",
        success: function (data) {
            const addCurrencySelect = $("#AddCurrencySelect");
            const options = [];
            data.slice(0, maxDisplayedOptions).forEach((element) => {
                if(!currencyDetailsById.hasOwnProperty(element.i)){
                    currencyDetailsById[element.i] = element
                }
                options.push(getCurrencyOption(addCurrencySelect, element))
            });
            addCurrencySelect.append(...options);
            // add selectpicker class at the last moment to avoid refreshing any existing one (slow)
            addCurrencySelect.addClass("selectpicker")
            addCurrencySelect.selectpicker('render');
            // paginatedSelect2(addCurrencySelect, options, pageSize)
        },
        error: function (result, status) {
            window.console && console.error(`Impossible to get currency list: ${result.responseText} (${status})`);
        }
    });
}

let validated_updated_global_config = {};
let deleted_global_config_elements = [];
let currencyDetailsById = {}

const traderSimulatorCheckbox = $("#trader-simulator_enabled");
const traderCheckbox = $("#trader_enabled");
const tradingReferenceMarket = $("#trading_reference-market");

$(document).ready(function() {
    handle_nested_sidenav();
    selectFirstTab(sidebarNavLinks);

    fetch_currencies();

    setup_editable();
    handle_editable();

    handle_reset_buttons();
    handle_save_buttons();

    handle_add_buttons();
    handle_remove_buttons();
    
    handle_buttons();

    handle_activation_configuration_editor();

    handle_import_currencies();
    handle_export_currencies_button();

    register_edit_events();

    register_exit_confirm_function(something_is_unsaved);

    check_evaluator_configuration();

    register_exchanges_checks(true);

    startTutorialIfNecessary("profile");
});
