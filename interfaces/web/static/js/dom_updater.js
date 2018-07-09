var success_badge = "badge-success"
var warning_badge = "badge-warning"
var secondary_badge = "badge-secondary"

var light_list_item = "list-group-item-light"
var success_list_item = "list-group-item-success"

var activation_pending = "Activation pending restart"
var deactivation_pending = "Deactivation pending restart"
var activated = "Activated"
var deactivated = "Deactivated"


function update_badge(badge, new_text, new_class){
    badge.removeClass(secondary_badge)
    badge.removeClass(warning_badge)
    badge.removeClass(success_badge)
    badge.addClass(new_class)
    badge.html(new_text)
}

function update_list_item(list_item, new_class){
    list_item.removeClass(light_list_item)
    list_item.removeClass(success_list_item)
    list_item.addClass(new_class)
}


function change_boolean(to_update_element, new_value, new_value_string){
    var badge = to_update_element.find(".badge")
    var startup_value = to_update_element.attr("startup-config-value").toLowerCase()
    var is_back_to_startup_value = startup_value == new_value_string
    if(new_value){
        update_list_item(to_update_element, success_list_item)
        if (!is_back_to_startup_value){
            update_badge(badge, activation_pending, warning_badge)
        }else{
            update_badge(badge, activated, success_badge)
        }
    }else{
        update_list_item(to_update_element, light_list_item)
        if (!is_back_to_startup_value){
            update_badge(badge, deactivation_pending, warning_badge)
        }else{
            update_badge(badge, deactivated, secondary_badge)
        }
    }
}

function update_dom(root_element, message){
    var config_value_attr = "config-value"
    for (var conf_key in message) {
        var new_value = message[conf_key]
        new_value_type = typeof(new_value)
        new_value_string = new_value.toString()
        var to_update_element = root_element.find("#"+conf_key)
        if (to_update_element.attr(config_value_attr).toLowerCase() != new_value_string){
            to_update_element.attr(config_value_attr, new_value_string)
            if(new_value_type == "boolean"){
                change_boolean(to_update_element, new_value, new_value_string)
            }

        }
    }
}