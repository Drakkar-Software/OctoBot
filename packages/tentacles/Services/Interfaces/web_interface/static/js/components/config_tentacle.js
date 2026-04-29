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

function apply_evaluator_default_config(element) {
    const default_config = element.attr("default-elements").replace(new RegExp("'","g"),'"');
    const update_url = $("#defaultConfigDiv").attr(update_url_attr);
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
    location.reload();
}

function updateTentacleConfig(updatedConfig, update_url){
    send_and_interpret_bot_update(updatedConfig, update_url, null, handle_tentacle_config_update_success_callback, handle_tentacle_config_update_error_callback);
}

function factory_reset(update_url){
    send_and_interpret_bot_update(null, update_url, null, handle_tentacle_config_reset_success_callback, handle_tentacle_config_update_error_callback);
}

function handle_tentacle_config_reset_success_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", "Configuration reset", msg);
    initConfigEditor(false);
}

function handle_tentacle_config_update_success_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", "Configuration saved", msg);
    initConfigEditor(false);
}

function handle_tentacle_config_update_error_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("error", "Error when updating config", msg.responseText);
}

function handleConfigDisplay(success){
    $("#editor-waiter").hide();
    if(success){
        $("#configErrorDetails").hide();
        if(canEditConfig()) {
            $("#saveConfigFooter").show();
            $("button[data-role='saveConfig']").removeClass(hidden_class).unbind("click").click(function (event) {
                const errorsDesc = validateJSONEditor(configEditor);
                if (errorsDesc.length) {
                    create_alert("error", "Error when saving configuration",
                        `Invalid configuration data: ${errorsDesc}.`);
                } else{
                    const url = $(event.currentTarget).attr(update_url_attr)
                    updateTentacleConfig(configEditor.getValue(), url);
                }
            });
        }else{
            $("#noConfigMessage").show();
        }
    }else{
        $("#configErrorDetails").show();
    }
}

function get_config_value_changed(element, new_value) {
    let new_value_str = new_value.toString().toLowerCase();
    return new_value_str !== element.attr(config_value_attr).toLowerCase();
}

function handle_save_buttons_success_callback(updated_data, update_url, dom_root_element, msg, status){
    update_dom(dom_root_element, msg);
    create_alert("success", "Configuration successfully updated", "Restart OctoBot for changes to be applied.");
}

function send_command_success_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", `${updated_data.subject} command sent`, "");
}

function handle_save_button(){
    $("#saveActivationConfig").click(function() {
        const full_config = $("#activatedElementsBody");
        const updated_config = {};
        const update_url = $("#saveActivationConfig").attr(update_url_attr);

        full_config.find("."+config_element_class).each(function(){
            const config_type = $(this).attr(config_type_attr);

            if(!(config_type in updated_config)){
                updated_config[config_type] = {};
            }

            const new_value = parse_new_value($(this));
            const config_key = get_config_key($(this));

            if(get_config_value_changed($(this), new_value)){
                updated_config[config_type][config_key] = new_value;
            }
        });

        // send update
        send_and_interpret_bot_update(updated_config, update_url, full_config, handle_save_buttons_success_callback);
    })
}

function handleUserCommands(){
    $(".user-command").click(function () {
        const button = $(this);
        const update_url = button.attr("update-url");
        const commandData = {};
        button.parents(".modal-content").find(".command-param").each(function (){
            const element = $(this);
            commandData[element.data("param-name")] = element.val();
        })
        const data = {
            action: button.data("action"),
            subject: button.data("subject"),
            data: commandData,
        };
        send_and_interpret_bot_update(data, update_url, null, send_command_success_callback);
    });
}

function handleButtons() {
    handle_save_button();
    handleUserCommands();

    $("#applyDefaultConfig").click(function () {
        const tentacle_name = $(this).attr("tentacle");
        apply_evaluator_default_config($("#" + tentacle_name));
    });

    $("#startBacktesting").click(function(){
        if(!check_date_range()){
            create_alert("error", "Invalid date range.", "");
            return;
        }
        $("#backtesting_progress_bar").show();
        lock_interface();
        const request = {};
        request["files"] = get_selected_files();
        const startDate = $("#startDate");
        const endDate = $("#endDate");
        request["start_timestamp"] = startDate.val().length ? (new Date(startDate.val()).getTime()) : null;
        request["end_timestamp"] = endDate.val().length ? (new Date(endDate.val()).getTime()) : null;
        const update_url = $("#startBacktesting").attr("start-url");
        start_backtesting(request, update_url);
    });

    $("button[data-role='factoryResetConfig']").click(function(){
        if (confirm("Reset this tentacle configuration to its default values ?") === true) {
            factory_reset($("button[data-role='factoryResetConfig']").attr("update-url"));
        }
    });
    
    $("#reloadBacktestingPart").click(function () {
        window.location.hash = "backtestingInputPart";
        location.reload();
    })
}
function check_date_range(){
    const start_date = new Date($("#startDate").val());
    const end_date = new Date($("#endDate").val());
    return (!isNaN(start_date) && !isNaN(end_date)) ? start_date < end_date : true;
}

function get_config_key(elem){
    return elem.attr(config_key_attr);
}

function parse_new_value(element) {
    return element.attr(current_value_attr).toLowerCase();
}

function handle_evaluator_configuration_editor(){
    $(".config-element").click(function(e){
        if (isDefined($(e.target).attr(no_activation_click_attr))){
            // do not trigger when click on items with no_activation_click_attr set
            return;
        }
        const element = $(this);

        if (element.hasClass(config_element_class)){

            if (element[0].hasAttribute(config_type_attr) && (element.attr(config_type_attr) === evaluator_config_type || element.attr(config_type_attr) === trading_config_type)){

                // build data update
                let new_value;
                let current_value = parse_new_value(element);

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

function something_is_unsaved(){
    let edited_config = canEditConfig() ? getValueChangedFromRef(
        configEditor.getValue(), savedConfig, true
    ) : false;
    return (
        edited_config
        || $("#super-container").find("."+modified_badge).length > 0
    )
}

function get_selected_files(){
    return [$("#dataFileSelect").val()];
}


function canEditConfig() {
    return parsedConfigSchema && parsedConfigValue
}

let configEditor = null;
let configEditorChangeEventCallbacks = [];
let savedConfig = null;
let parsedConfigSchema = null;
let parsedConfigValue = null;
let startingConfigValue = null;

function _addGridDisplayOptions(schema){
    if(typeof schema.properties === "undefined" && typeof schema.items === "undefined"){
        return;
    }
    // display user inputs as grid
    // if(typeof schema.format === "undefined") {
    //     schema.format = "grid";
    // }
    if(typeof schema.options === "undefined"){
        schema.options = {};
    }
    schema.options.grid_columns = 6;
    if(typeof schema.properties !== "undefined"){
        Object.values(schema.properties).forEach (property => {
            _addGridDisplayOptions(property)
        });
    }
    if(typeof schema.items !== "undefined"){
        _addGridDisplayOptions(schema.items)
    }
}

function initConfigEditor(showWaiter) {
    if(showWaiter){
        $("#editor-waiter").show();
    }
    const configEditorBody = $("#configEditorBody");

    function editDetailsSuccess(updated_data, update_url, dom_root_element, msg, status){
        const inputs = msg["displayed_elements"]["data"]["elements"];
        if(inputs.length === 0){
            handleConfigDisplay(true);
            return;
        }
        parsedConfigValue = msg["config"];
        savedConfig = parsedConfigValue
        parsedConfigSchema = inputs[0]["schema"];
        parsedConfigSchema.id = "tentacleConfig"
        if(configEditor !== null){
            configEditor.destroy();
        }
        if (canEditConfig()){
            fix_config_values(parsedConfigValue, parsedConfigSchema)
        }
        _addGridDisplayOptions(parsedConfigSchema);
        const settingsRoot = $("#configEditor");
        configEditor = canEditConfig() ? (new JSONEditor(settingsRoot[0],{
            schema: parsedConfigSchema,
            startval: parsedConfigValue,
            no_additional_properties: true,
            prompt_before_delete: true,
            disable_array_reorder: true,
            disable_collapse: true,
            disable_properties: true,
            disable_edit_json: true,
        })) : null;
        settingsRoot.find("select[multiple=\"multiple\"]").select2({
            width: 'resolve', // need to override the changed default
            closeOnSelect: false,
            placeholder: "Select values to use"
        });
        const configEditorButtons = $("#configEditorButtons");
        if(configEditor !== null){
            configEditor.on("change", editorChangeCallback);
            if(configEditorButtons.length){
                configEditorButtons.removeClass(hidden_class);
            }
        } else {
            if(configEditorButtons.length){
                configEditorButtons.addClass(hidden_class);
            }
        }
        handleConfigDisplay(true);
    }

    const editDetailsFailure = (updated_data, update_url, dom_root_element, msg, status) => {
        create_alert("error", "Error when fetching tentacle config", msg.responseText);
        handleConfigDisplay(false);
    }


    send_and_interpret_bot_update(null, configEditorBody.data("edit-details-url"), null,
        editDetailsSuccess, editDetailsFailure, "GET");
}

function editorChangeCallback(){
    if(validateJSONEditor(configEditor) === "" && something_is_unsaved()){
        configEditorChangeEventCallbacks.forEach((callback) => {
            callback(configEditor.getValue());
        });
    }
}

function addEditorChangeEventCallback(callback){
    configEditorChangeEventCallbacks.push(callback)
}

$(document).ready(function() {
    initConfigEditor(true);
    handleButtons();
    if(typeof lock_interface !== "undefined"){
        lock_interface(false);
    }

    handle_evaluator_configuration_editor();

    if(typeof init_backtesting_status_websocket !== "undefined"){
        init_backtesting_status_websocket();
    }

    register_exit_confirm_function(something_is_unsaved);
});
