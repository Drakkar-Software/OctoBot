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

function manage_alert(raw_data){
    try{
        data = JSON.parse(raw_data)
        $.each(data, function(i, item) {
            create_alert(data[i].Level, data[i].Title, data[i].Message);
        })
    }
    catch{}
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
                    button.html("<i class='fa fa-circle-notch fa-spin'></i>");
                },
                complete: function() {
                   button.html(origin_val);
                }
            });
         }
    });
}

function send_and_interpret_bot_update(updated_data, update_url, dom_root_element, success_callback, error_callback){
    $.ajax({
        url: update_url,
        type: "POST",
        dataType: "json",
        contentType: 'application/json',
        data: JSON.stringify(updated_data),
        success: function(msg, status){
            if(typeof success_callback === "undefined") {
                update_dom(dom_root_element, msg);
            }
            else{
                success_callback(updated_data, update_url, dom_root_element, msg, status)
            }
        },
        error: function(result, status, error){
            window.console&&console.error(result);
            window.console&&console.error(status);
            window.console&&console.error(error);
            if(typeof error_callback === "undefined") {
                create_alert("error", "Error when handling action: "+result.responseText+".", "");
            }
            else{
                error_callback(updated_data, update_url, dom_root_element, result, status, error)
            }
        },
    })
}

$(document).ready(function () {
    handle_route_button();
    setInterval(function(){ get_update(); }, 500);
});
