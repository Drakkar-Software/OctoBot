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

function updateTentacleConfig(updatedConfig){
    const update_url = $("#saveConfig").attr(update_url_attr);
    send_and_interpret_bot_update(updatedConfig, update_url, null, handle_tentacle_config_update_success_callback, handle_tentacle_config_update_error_callback);
}

function factory_reset(update_url){
    send_and_interpret_bot_update(null, update_url, null, handle_tentacle_config_reset_success_callback, handle_tentacle_config_update_error_callback);
}

function handle_tentacle_config_reset_success_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", "Configuration saved", msg);
    location.reload();
}

function handle_tentacle_config_update_success_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", "Configuration saved", msg);
    savedConfig = configEditor.getValue();
}

function handle_tentacle_config_update_error_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("error", "Error when updating config", msg.responseText);
}

function handleConfigDisplay(){

    if(canEditConfig()){
        $("#saveConfigFooter").show();
        $("#saveConfig").click(function() {
            updateTentacleConfig(configEditor.getValue());
        });
    }else{
        $("#noConfigMessage").show();
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

function handleButtons() {

    handleConfigDisplay();
    handle_save_button();

    $("#applyDefaultConfig").click(function () {
        const tentacle_name = $(this).attr("tentacle");
        apply_evaluator_default_config($("#" + tentacle_name));
    });

    $("#startBacktesting").click(function(){
        $("#backtesting_progress_bar").show();
        lock_interface();
        const request = get_selected_files();
        const update_url = $("#startBacktesting").attr("start-url");
        start_backtesting(request, update_url);
    });

    $("#factoryResetConfig").click(function(){
        if (confirm("Reset this tentacle configuration to its default values ?") === true) {
            factory_reset($("#factoryResetConfig").attr("update-url"));
        }
    });
    
    $("#reloadBacktestingPart").click(function () {
        window.location.hash = "backtestingInputPart";
        location.reload();
    })
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
    let edited_config = canEditConfig() ? getValueChangedFromRef(configEditor.getValue(), savedConfig) : false;
    return (
        edited_config
        || $("#super-container").find("."+modified_badge).length > 0
    )
}

function get_selected_files(){
    return [$("#dataFileSelect").val()];
}

const configEditorBody = $("#configEditorBody");
const configSchema = configEditorBody.attr("schema");
const configValue = configEditorBody.attr("config");

const parsedConfigSchema = configSchema !== "None" ? $.parseJSON(configSchema) : null;
const parsedConfigValue = configValue !== "None" ? $.parseJSON(configValue) : null;
if (canEditConfig){
    fix_config_values(parsedConfigValue)
}

let savedConfig = parsedConfigValue;

function canEditConfig() {
    return parsedConfigSchema && parsedConfigValue
}

const configEditor = canEditConfig() ? (new JSONEditor($("#configEditor")[0],{
    schema: parsedConfigSchema,
    startval: parsedConfigValue,
    no_additional_properties: true,
    prompt_before_delete: true,
    disable_array_reorder: true,
    disable_collapse: true,
    disable_properties: true
})) : null;

$(document).ready(function() {
    handleButtons();
    lock_interface(false);

    handle_evaluator_configuration_editor();

    setInterval(function(){refresh_status();}, 300);
    function refresh_status(){
        check_backtesting_state();
    }

    register_exit_confirm_function(something_is_unsaved);
});
