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
    const update_url = $("#saveConfig").attr(update_url_attr);
    const updated_config = {};
    const config_type = element.attr(config_type_attr);
    updated_config[config_type] = {};

    $.each($.parseJSON(default_config), function (i, config_key) {
        updated_config[config_type][config_key] = "true";
    });

    // send update
    send_and_interpret_bot_update(updated_config, update_url, null, handle_apply_evaluator_default_config_success_callback);
}

function handle_apply_evaluator_default_config_success_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", "Evaluators activated", "Restart OctoBot for changes to be applied");
}


function handleConfigDisplay(){

    if(canEditConfig()){
        $("#saveConfigFooter").show();
        $("#saveConfig").click(function() {
            log(configEditor.getValue());
        });
    }else{
        $("#noConfigMessage").show();
    }
}


function handleButtons() {

    handleConfigDisplay();

    $(".config-element").click(function () {
        const element = $(this);

        if (element.hasClass(config_element_class) && !element.hasClass(disabled_class)) {
            if (element[0].hasAttribute(config_type_attr)) {
                if (element.attr(config_type_attr) === evaluator_list_config_type) {
                    const strategy_name = element.attr("strategy");
                    apply_evaluator_default_config($("#" + strategy_name));
                }
            }
        }

    });

    $("#startBacktesting").click(function(){
        $("#backtesting_progress_bar").show();
        lock_interface();
        const request = get_selected_files();
        const update_url = $("#startBacktesting").attr("start-url");
        start_backtesting(request, update_url);
    });
}

function get_selected_files(){
    return [$("#dataFileSelect").val()];
}

const configEditorBody = $("#configEditorBody");
const configSchema = configEditorBody.attr("schema");
const configValue = configEditorBody.attr("config");

const parsedConfigSchema = configSchema !== "None" ? $.parseJSON(configSchema) : null;
const parsedConfigValue = configValue !== "None" ? $.parseJSON(configValue) : null;

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

    setInterval(function(){refresh_status();}, 300);
    function refresh_status(){
        check_backtesting_state();
    }
});
