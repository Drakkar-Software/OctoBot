function get_update(){
    $.ajax({
      url: "/update",
    }).done(function(data) {
        unlock_ui();

    }).fail(function(data) {
        lock_ui();

    }).always(function(data) {
        manage_alert(data);
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

function manage_alert(raw_data){
    data = JSON.parse(raw_data)
    $.each(data, function(i, item) {
        create_alert(data[i].Level, data[i].Title, data[i].Message);
    })
}

function handle_route_button(){
    $(".btn").click(function(){
        button = $(this)
        if (button[0].hasAttribute('route')){
            command = button.attr('route');
            origin_val = button.text();
            $.ajax({
                url: command,
                beforeSend: function() {
                    button.html("<i class='fas fa-circle-notch fa-spin'></i>");
                },
                complete: function() {
                   button.html(origin_val);
                }
            });
         }
    });
}

function change_boolean(to_update_element, new_value){
    var badge = to_update_element.find(".badge")
    if(new_value){
        to_update_element.removeClass("list-group-item-light")
        to_update_element.addClass("list-group-item-success")
        badge.removeClass("badge-secondary")
        badge.addClass("badge-success")
        badge.html("Activated")
    }else{
        to_update_element.removeClass("list-group-item-success")
        to_update_element.addClass("list-group-item-light")
        badge.removeClass("badge-success")
        badge.addClass("badge-secondary")
        badge.html("Deactivated")
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
                change_boolean(to_update_element, new_value)
            }

        }
    }
}

function handle_configuration_editor(){
    $(".config-element").click(function(){
        var element = $(this);
        var config_key_attr = "config-key";
        var config_value_attr = "config-value";
        var update_url_attr = "update-url";
        var config_element_class = "config-element";
        if (element.hasClass(config_element_class)){
            var full_config_root = element.parents(".config-root");
            if (full_config_root[0].hasAttribute(update_url_attr)){

                // build data update
                var config_elements = full_config_root.find("."+config_element_class);
                var updated_config = {};
                new_value = element.attr(config_value_attr)
                var current_value = element.attr(config_value_attr).toLowerCase()
                if (current_value == "true" || current_value == "false"){
                    // boolean
                    if (new_value.toLowerCase() == "true"){
                        new_value = "false"
                    }else{
                        new_value = "true"
                    }
                }

                updated_config[element.attr(config_key_attr)]=new_value;

                // send update
                var update_url = full_config_root.attr(update_url_attr)
                $.ajax({
                    url: update_url,
                    type: "POST",
                    dataType: "json",
                    contentType: 'application/json',
                    data: JSON.stringify(updated_config),
                    success: function(msg, status){
                        update_dom(full_config_root, msg);
                    },
                    error: function(result, status, error){
                        window.console&&console.error(result);
                        window.console&&console.error(status);
                        window.console&&console.error(error);
                        create_alert("danger", "Error when updating value.", error);
                    },
                })
            }
        }
    });
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


$(document).ready(function () {
    handle_configuration_editor();
    handle_route_button();
    setInterval(function(){ get_update(); }, 500);
});