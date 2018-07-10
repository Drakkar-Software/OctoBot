function register_and_install_package(){
    $("#register_and_install_package_progess_bar").show();
    element = $("#register_and_install_package_input")
    var input_text = element.val()
    var request = {}
    request[$.trim(input_text)] = "description"
    var full_config_root = element.parents("."+config_root_class);
    var update_url = full_config_root.attr(update_url_attr);
    send_and_interpret_bot_update(request, update_url, full_config_root, register_and_install_package_success_callback, register_and_install_package_error_callback)
}

function register_and_install_package_success_callback(updated_data, update_url, dom_root_element, msg, status){
    if(confirm("Install " + msg["name"] + " tentacles package ?")) {
        var request = {}
        for(var attribute in updated_data) {
            request[attribute] = "register_and_install";
        }

        send_and_interpret_bot_update(request, update_url, dom_root_element, post_package_action_success_callback, post_package_action_error_callback)
    }else{
        $("#register_and_install_package_progess_bar").hide();
    }
}

function register_and_install_package_error_callback(updated_data, update_url, dom_root_element, result, status, error){
    create_alert("danger", "Error when getting package: "+result.responseText, "");
    $("#register_and_install_package_progess_bar").hide();
}

function post_package_action_success_callback(updated_data, update_url, dom_root_element, msg, status){
    package_path = ""
    for(var attribute in updated_data) {
        package_path = attribute;
    }
    create_alert("success", "Tentacles packages successfully installed from: "+package_path, "");
    location.reload();
}

function post_package_action_error_callback(updated_data, update_url, dom_root_element, result, status, error){
    $("#register_and_install_package_progess_bar").hide();
    create_alert("danger", "Error during package handling: "+result.responseText, "");
}

$(document).ready(function() {
 $('#register_and_install_package_button').prop('disabled', true);
 $('#register_and_install_package_input').keyup(function() {
   $('#register_and_install_package_button').prop('disabled', $(this).val() == '');
 });
});
