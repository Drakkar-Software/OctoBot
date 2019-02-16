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

function register_and_install_package(){
    disable_packages_operations();
    $("#register_and_install_package_progess_bar").show();
    const element = $("#register_and_install_package_input");
    const input_text = element.val();
    const request = {};
    request[$.trim(input_text)] = "description";
    const full_config_root = element.parents("."+config_root_class);
    const update_url = full_config_root.attr(update_url_attr);
    send_and_interpret_bot_update(request, update_url, full_config_root, register_and_install_package_success_callback, register_and_install_package_error_callback)
}

function disable_packages_operations(should_lock=true){
    const disabled_attr = 'disabled';
    $("#update_tentacles_packages").prop(disabled_attr, should_lock);
    $("#install_tentacles_packages").prop(disabled_attr, should_lock);
    $("#reset_tentacles_packages").prop(disabled_attr, should_lock);
    const register_and_install_package_input = $("#register_and_install_package_input");
    register_and_install_package_input.prop(disabled_attr, should_lock);
    if(register_and_install_package_input.val() !== ""){
        $("#register_and_install_package_button").prop(disabled_attr, should_lock);
    }
    const should_disable_buttons = get_selected_modules() <= 0;
    $('#uninstall_selected_tentacles').prop(disabled_attr, should_disable_buttons);
    $('#update_selected_tentacles').prop(disabled_attr, should_disable_buttons);

}

function update(module){
    perform_modules_operation([module], "update");
}

function uninstall(module){
    if(confirm("Uninstall this tentacle ? This will delete the associated tentacle file if any.")) {
        perform_modules_operation([module], "uninstall");
    }
}

function perform_modules_operation(modules, operation){
    const dom_root_element = $("#module-table");
    const update_url = dom_root_element.attr(operation+"-"+update_url_attr);
    disable_packages_operations();
    send_and_interpret_bot_update(modules, update_url, dom_root_element, modules_operation_success_callback, modules_operation_error_callback)
}

function perform_packages_operation(source){
    $("#packages_action_progess_bar").show();
    const update_url = source.attr(update_url_attr);
    disable_packages_operations();
    send_and_interpret_bot_update({}, update_url, source, packages_operation_success_callback, packages_operation_error_callback)
}

function modules_operation_success_callback(updated_data, update_url, dom_root_element, msg, status){
    disable_packages_operations(false);
    $("#table-span").load(location.href + " #table-span",function(){
        disable_select_action_buttons();
        $('#tentacles_modules_table').DataTable({
            "paging":   false,
        });
    });
    $("#selected_tentacles_operation").hide();
    create_alert("success", "Tentacle operation success", msg);
}

function modules_operation_error_callback(updated_data, update_url, dom_root_element, result, status, error){
    disable_packages_operations(false);
    $("#table-span").load(location.href + " #table-span",function(){
        disable_select_action_buttons();
        $('#tentacles_modules_table').DataTable({
            "paging":   false,
        });
    });
    $("#selected_tentacles_operation").hide();
    create_alert("error", "Error when managing modules: "+result.responseText, "");
}

function packages_operation_success_callback(updated_data, update_url, dom_root_element, msg, status){
    disable_packages_operations(false);
    $("#tentacles_modules_table").load(location.href + " #tentacles_modules_table",function(){
        disable_select_action_buttons();
    });
    $("#packages_action_progess_bar").hide();
    create_alert("success", "Packages operation success", msg);
}

function packages_operation_error_callback(updated_data, update_url, dom_root_element, result, status, error){
    disable_packages_operations(false);
    $("#tentacles_modules_table").load(location.href + " #tentacles_modules_table",function(){
        disable_select_action_buttons();
    });
    $("#packages_action_progess_bar").hide();
    create_alert("error", "Error when managing packages: "+result.responseText, "");
}

function register_and_install_package_success_callback(updated_data, update_url, dom_root_element, msg, status){
    if(confirm("Install " + msg["name"] + " tentacles package ?")) {
        let request = {};
        for(const attribute in updated_data) {
            request[attribute] = "register_and_install";
        }

        send_and_interpret_bot_update(request, update_url, dom_root_element, post_package_action_success_callback, post_package_action_error_callback)
    }else{
        $("#register_and_install_package_progess_bar").hide();
        disable_packages_operations(false);
    }
}

function register_and_install_package_error_callback(updated_data, update_url, dom_root_element, result, status, error){
    create_alert("error", "Error when getting package: "+result.responseText, "");
    $("#register_and_install_package_progess_bar").hide();
    disable_packages_operations(false);
}

function post_package_action_success_callback(updated_data, update_url, dom_root_element, msg, status){
    let package_path;
    for(const attribute in updated_data) {
        package_path = attribute;
    }
    create_alert("success", "Tentacles successfully installed" , "Packages installed from: "+package_path);
    $("#tentacles_packages_table").load(location.href + " #tentacles_packages_table");
    $("#tentacles_modules_table").load(location.href + " #tentacles_modules_table",function(){
        disable_select_action_buttons();
    });
    $("#register_and_install_package_progess_bar").hide();
    disable_packages_operations(false);
}

function post_package_action_error_callback(updated_data, update_url, dom_root_element, result, status, error){
    create_alert("error", "Error during package handling: "+result.responseText, "");
    $("#tentacles_packages_table").load(location.href + " #tentacles_packages_table");
    $("#tentacles_modules_table").load(location.href + " #tentacles_modules_table",function(){
        disable_select_action_buttons();
    });
    $("#register_and_install_package_progess_bar").hide();
    disable_packages_operations(false);
}

function get_selected_modules(){
    const selected_modules = [];
    $("#module-table").find("input[type='checkbox']:checked").each(function(){
        selected_modules.push($(this).attr("module"));
    });
    return selected_modules
}

function handle_tentacles_buttons(){
    $("#install_tentacles_packages").click(function(){
        perform_packages_operation($(this));
    });
    $("#update_tentacles_packages").click(function(){
        perform_packages_operation($(this));
    });
    $("#reset_tentacles_packages").click(function(){
        if(confirm("Reset all installed tentacles ? This will delete all tentacle files and configuration in tentacles folder.")) {
            perform_packages_operation($(this));
        }
    });
    $("#uninstall_selected_tentacles").click(function(){
        const selected_modules = get_selected_modules();
        if(selected_modules.length > 0){
            if(confirm("Uninstall these tentacles ? This will delete all the associated tentacle files if any.")) {
                $("#selected_tentacles_operation").show();
                disable_packages_operations();
                perform_modules_operation(selected_modules,"uninstall");
            }
        }
    });
    $("#update_selected_tentacles").click(function(){
        const selected_modules = get_selected_modules();
        if(selected_modules.length > 0){
            $("#selected_tentacles_operation").show();
            disable_packages_operations();
            perform_modules_operation(selected_modules,"update");
        }
    });
}

function disable_select_action_buttons(){
    $('#update_selected_tentacles').prop('disabled', true);
    $('#uninstall_selected_tentacles').prop('disabled', true);
    $('.selectable_tentacle').click(function () {
        // use parent not to trigger selection on button column use
        const row = $(this).parent();
        if (row.hasClass(selected_item_class)){
            row.removeClass(selected_item_class);
            row.find(".tentacle-module-checkbox").prop('checked', false);
        }else{
            row.toggleClass(selected_item_class);
            row.find(".tentacle-module-checkbox").prop('checked', true);
        }
        const should_disable_buttons = get_selected_modules() <= 0;
        $('#uninstall_selected_tentacles').prop('disabled', should_disable_buttons);
        $('#update_selected_tentacles').prop('disabled', should_disable_buttons);
    });
}

$(document).ready(function() {
    handle_tentacles_buttons();
    $('#register_and_install_package_button').prop('disabled', true);
    $('#register_and_install_package_input').keyup(function() {
    $('#register_and_install_package_button').prop('disabled', $(this).val() === '');
    });
    disable_select_action_buttons();
    $('#tentacles_modules_table').DataTable({
        "paging":   false,
    });
});
