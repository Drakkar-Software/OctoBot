// dom data attributes and classes
var config_key_attr = "config-key";
var config_value_attr = "config-value";
var current_value_attr = "current-value";
var startup_value_attr = "startup-config-value";
var update_url_attr = "update-url";
var config_type_attr = "config_type";
var config_root_class = "config-root";
var config_container_class = "config-container";
var config_element_class = "config-element";
var config_default_value = "@default_value";

// dom display classes
var success_badge = "badge-success";
var warning_badge = "badge-warning";
var secondary_badge = "badge-secondary";
var primary_badge = "badge-primary";

var light_list_item = "list-group-item-light";
var success_list_item = "list-group-item-success";

var activation_pending = "Activation pending restart";
var deactivation_pending = "Deactivation pending restart";
var unsaved_setting = "Unsaved setting";
var activated = "Activated";
var deactivated = "Deactivated";

// utility functions
function log(text){
    window.console&&console.log(text);
}

function replace_eol_by_html(str){
    return str.replace(/(?:\r\n|\r|\n)/g, '<br />');
}