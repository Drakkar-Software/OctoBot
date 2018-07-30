function get_active_tab_config(){
    return $(document).find("." + config_root_class + ".active").find("." + config_container_class);
}

function get_tabs_config(){
    return $(document).find("." + config_root_class + " ." + config_container_class);
}


function handle_reset_buttons(){
    $("#reset-config").click(function() {
        reset_configuration_element($(this));
    })
}

function handle_remove_buttons(){
    // Card deck removing
    $(document).on("click", ".remove-btn", function() {
        $(this).closest(".card").fadeOut("normal", function() {
            $(this).remove();
        });
    });
}

function handle_add_buttons(){
    // Card deck adding
    $(".add-btn").click(function() {

        var button_id = $(this).attr("id")

        var deck = $(this).parents("." + config_root_class).find(".card-deck");
        var select_input = $("#" + button_id + "Select");
        var select_value = select_input.val();
        var target_template = $("#" + button_id + "-template-default")

        // currencies
        var select_symbol = select_input.children("[data-tokens='"+select_value+"']").attr("symbol");
        var reference_market = select_input.attr("reference_market");

        //services
        if (button_id == "AddService"){
            target_template = $("#" + button_id + "-template-default-"+select_value);
        }

        // check if not already added
        if(deck.find("div[name='"+select_value+"']").length == 0){
            var template_default = target_template.html().replace(new RegExp(config_default_value,"g"), select_value);
            template_default = template_default.replace(new RegExp("card-text symbols default","g"), "card-text symbols")
            if(isDefined(select_symbol)){
                template_default = template_default.replace(new RegExp(config_default_symbol + ".png","g"), select_symbol.toLowerCase() + ".png")
            }
            deck.append(template_default).hide().fadeIn();
            handle_editable();

            // select options with reference market if any
            $('.multi-select-element').each(function () {
                if ($(this).siblings('.select2').length == 0 && !$(this).parent().hasClass('default')){
                    $(this).children("option").each(function () {
                        var symbols = $(this).attr("value").split("/");
                        if (symbols[0] == select_symbol && symbols[1] == reference_market){
                            $(this).attr("selected", "selected");
                        }
                    });
                }
            });


            // add select2 selector
            $('.multi-select-element').each(function () {
                if ($(this).siblings('.select2').length == 0 && !$(this).parent().hasClass('default')){
                    $(this).select2({
                        width: 'resolve', // need to override the changed default
                        tags: true
                    });
                }
            });
        }

    });
}

function parse_new_value(element){
    var raw_data = replace_spaces(replace_break_line(element.text()));

    // simple case
    if(element[0].hasAttribute(current_value_attr)){
        value = replace_spaces(replace_break_line(element.attr(current_value_attr)));
        if(element[0].hasAttribute(config_data_type_attr)){
            switch(element.attr(config_data_type_attr)) {
                case "bool":
                    return value == true || value == "true";
                    break;
                case "number":
                    return Number(value);
                    break;
                default:
                    return value;
                    break;
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
                break;
            case "list":
                var new_value = [];
                element.find(":selected").each(function(index, value){
                    new_value.splice(index, 0, replace_spaces(replace_break_line(value.text)));
                });
                return new_value;
                break;
            case "number":
                return Number(raw_data);
                break;
            default:
                return raw_data;
                break;
        }

    // without information
    }else{
        return raw_data;
    }
}

function handle_save_buttons(){
    $("#save-config").click(function() {
        var full_config = get_active_tab_config();
        var updated_config = {};
        var update_url = full_config.attr(update_url_attr);

        get_tabs_config().each(function(){
            $(this).find("."+config_element_class).each(function(){
                var config_type = $(this).attr(config_type_attr);

                if(!(config_type in updated_config)){
                    updated_config[config_type] = {};
                }

                var new_value = parse_new_value($(this));

                var new_value_str = new_value.toString();
                if(new_value instanceof Array && new_value.length > 0){
                    //need to format array to match python string representation of config
                    var str_array = []
                    $.each(new_value, function(i, val) {
                        str_array.push("'"+val+"'");
                    });
                    new_value_str = "[" + str_array.join(", ") + "]";
                }

                if(new_value_str.toLowerCase() != $(this).attr(config_value_attr).toLowerCase() ){
                    updated_config[config_type][$(this).attr(config_key_attr)] = new_value;
                }
            })
        })

        // send update
        send_and_interpret_bot_update(updated_config, update_url, full_config, handle_save_buttons_success_callback);

        add_or_remove_confirm_before_exit_page(false);
    })
}

function handle_save_buttons_success_callback(updated_data, update_url, dom_root_element, msg, status){
    update_dom(dom_root_element, msg);
    refresh_buttons_lock(get_active_tab_config(), $('#save-config'), $('#reset-config'))
    create_alert("success", "Configuration successfully updated.", "");
}

function handle_configuration_editor(){
    $(".config-element").click(function(){
        var element = $(this);

        if (element.hasClass(config_element_class)){
            var full_config = get_active_tab_config();
            if (full_config[0].hasAttribute(update_url_attr)){

                if (element[0].hasAttribute(config_type_attr) && element.attr(config_type_attr) == evaluator_config_type){

                    // build data update
                    var updated_config = {};
                    new_value = parse_new_value(element);

                    try {
                        var current_value = element.attr(current_value_attr).toLowerCase();
                    }
                    catch {
                        var current_value = element.attr(current_value_attr);
                    }

                    // todo
                    if (current_value == "true"){
                        new_value = "false";
                    }else if(current_value == "false"){
                        new_value = "true";
                    }

                    // update current value
                    element.attr(current_value_attr, new_value);

                    //update dom
                    update_element_temporary_look(element);
                }

                //add or remove exit confirm if necessary
                add_or_remove_exit_confirm_if_necessary(full_config, 'Are you sure you want to exit configuration without saving ?');
            }
        }
    });
}

function reset_configuration_element(element){
    var full_config = get_active_tab_config();
    full_config.find("."+ config_element_class).each(function(){
        if($(this).attr(current_value_attr).toLowerCase() != $(this).attr(config_value_attr).toLowerCase() ){
            // update current value
            $(this).attr(current_value_attr, $(this).attr(config_value_attr));
            //update dom
            update_element_temporary_look($(this));
        }
    });
    refresh_buttons_lock(get_active_tab_config(), $('#save-config'), $('#reset-config'))

    //add or remove exit confirm if necessary
    add_or_remove_exit_confirm_if_necessary(full_config, 'Are you sure you want to exit configuration without saving ?');
}

function refresh_buttons_lock(root_element, button1, button2){
    var should_unlock = !at_least_one_temporary_element(root_element);
    button1.prop('disabled', should_unlock);
    button2.prop('disabled', should_unlock);
}
