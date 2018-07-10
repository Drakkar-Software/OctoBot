function handle_reset_buttons(){
    $("#reset-evaluator-config").click(function() {
        reset_configuration_element($(this));
    })
}

function handle_configuration_editor(){
    $(".config-element").click(function(){
        var element = $(this);
        if (element.hasClass(config_element_class)){
            var full_config_root = element.parents(".config-root");
            if (full_config_root[0].hasAttribute(update_url_attr)){

                // build data update
                var config_elements = full_config_root.find("."+config_element_class);
                var updated_config = {};
                new_value = element.attr(config_value_attr);
                var current_value = element.attr(config_value_attr).toLowerCase();
                if (current_value == "true" || current_value == "false"){
                    // boolean
                    if (new_value.toLowerCase() == "true"){
                        new_value = "false"
                    }else{
                        new_value = "true"
                    }
                }

                updated_config[element.attr(config_key_attr)]=new_value;
                var update_url = full_config_root.attr(update_url_attr);

                // send update
                send_and_interpret_bot_update(updated_config, update_url, full_config_root);

            }
        }
    });
}

function reset_configuration_element(element){
    var full_config_root = element.parents(".config-root");
    if (full_config_root[0].hasAttribute(update_url_attr)){
        var update_url = full_config_root.attr(update_url_attr);
        // send update
        send_and_interpret_bot_update("reset", update_url, full_config_root);
    }
}

$(document).ready(function () {
    handle_reset_buttons();
    handle_configuration_editor();
});