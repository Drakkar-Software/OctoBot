function update_badge(badge, new_text, new_class){
    badge.removeClass(secondary_badge);
    badge.removeClass(warning_badge);
    badge.removeClass(success_badge);
    badge.removeClass(primary_badge);
    badge.addClass(new_class);
    badge.html(new_text);
}

function update_list_item(list_item, new_class){
    list_item.removeClass(light_list_item);
    list_item.removeClass(success_list_item);
    list_item.addClass(new_class);
}

function update_element_temporary_look(element){
    var set_to_activated = element.attr(current_value_attr).toLowerCase() == "true";
    var set_to_temporary = element.attr(current_value_attr).toLowerCase() != element.attr(config_value_attr).toLowerCase();
    var is_back_to_startup_value = element.attr(startup_value_attr).toLowerCase() == element.attr(config_value_attr).toLowerCase();
    log("set_to_activated: "+set_to_activated)
    log("set_to_temporary: "+set_to_temporary)
    log("startup_value_attr: "+element.attr(startup_value_attr).toLowerCase())
    log("config_value_attr: "+element.attr(config_value_attr.toLowerCase()))
    log("current_value_attr: "+element.attr(current_value_attr.toLowerCase()))
    if(element.hasClass("list-group-item")){
        // list item
        list_class = (set_to_activated ? success_list_item : light_list_item);
        update_list_item(element, list_class);
    }
    var badge = element.find(".badge");
    if(typeof badge != "undefined") {
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

function at_least_one_temporary_element(root_element){
    at_least_one_element = false;
    log(root_element);
    root_element.find("."+config_element_class).each(function(){
        if($(this).attr(current_value_attr).toLowerCase() != $(this).attr(config_value_attr).toLowerCase() ){
            at_least_one_element = true;
            return false;
        }
    });
    return at_least_one_element;
}

function add_or_remove_exit_confirm_if_necessary(root_element, message){
    if(at_least_one_temporary_element(root_element)){
        add_or_remove_confirm_before_exit_page(true, message);
    }
    else{
        add_or_remove_confirm_before_exit_page(false);
    }
}

function change_boolean(to_update_element, new_value, new_value_string){
    var badge = to_update_element.find(".badge");
    var startup_value = to_update_element.attr(startup_value_attr).toLowerCase();
    var is_back_to_startup_value = startup_value == new_value_string;
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

function update_dom(root_element, message){
    var config_value_attr = "config-value"
    for (var conf_key in message) {
        var new_value = message[conf_key];
        new_value_type = typeof(new_value);
        new_value_string = new_value.toString();
        var to_update_element = root_element.find("#"+conf_key);
        if (to_update_element.attr(config_value_attr).toLowerCase() != new_value_string){
            to_update_element.attr(config_value_attr, new_value_string);
            if(new_value_type == "boolean"){
                change_boolean(to_update_element, new_value, new_value_string);
            }

        }
    }
}

function create_alert(a_level, a_title, a_msg, url="_blank"){
    $.notify({
        title: a_title,
        message: a_msg
    },{
        element: "body",
	    position: null,
        type: a_level,
        allow_dismiss: true,
	    newest_on_top: true,
	    placement: {
            from: "top",
            align: "right"
	    },
	    showProgressbar: false,
	    offset: 20,
        spacing: 10,
        z_index: 1031,
        url_target: url,
	    delay: 5000,
	    timer: 1000,
	    animate: {
            enter: "animated fadeInDown",
            exit: "animated fadeOutUp"
	    }
    });
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
    icon_status = $("#navbar-bot-status")
    icon_reboot = $("#navbar-bot-reboot")

    // if refreshed page
    if (icon_status.hasClass("fa-spinner")){
        icon_status.removeClass("fa-spinner fa-spin")
    }

    // create alert if required
    if (status && icon_status.hasClass("icon-red")){
        create_alert("success", "Connected with Octobot", "");
    }else if(!status && icon_status.hasClass("icon-green")){
        create_alert("danger", "Connection lost with Octobot", "<br>Reconnecting...");
    }

    // update central status
    if (status){
        icon_status.removeClass("fa-times-circle icon-red");
        icon_status.addClass("fa-check-circle icon-green");
    }else{
        icon_status.removeClass("fa-check-circle icon-green");
        icon_status.addClass("fa-times-circle icon-red");
    }

    // update reboot status
    if (status){
        icon_reboot.removeClass("fa-spin");
    }else{
        icon_reboot.addClass("fa-spin");
    }
}

function add_or_remove_confirm_before_exit_page(add, message){
    event = 'beforeunload'
    if(add){
        $(window).bind(event, function(){
          return message;
        });
    }else{
        $(window).off(event);
    }
}
