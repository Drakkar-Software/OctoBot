function get_update(){
    $.ajax({
      url: "/update"
    }).done(function(data) {
        unlock_ui();

    }).fail(function(data) {
        lock_ui();

    }).always(function(data) {
        manage_alert(data);
  });
}

function manage_alert(data){
    try{
        const errors_count = data["errors_count"];
        if(errors_count > 0){
            $("#errors-count-badge").text(errors_count);
        }else{
            $("#errors-count-badge").cleanData();
        }
        $.each(data["notifications"], function(i, item) {
            create_alert(item["Level"], item["Title"], item["Message"]);
        })
    }
    catch(error) {}
}

function handle_route_button(){
    $(".btn").click(function(){
        const button = $(this);
        if (button[0].hasAttribute('route')){
            const command = button.attr('route');
            const origin_val = button.text();
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
                error_callback(updated_data, update_url, dom_root_element, result, status, error);
            }
        }
    })
}

const update_rate_millis = 1000;

$(document).ready(function () {
    handle_route_button();
    setInterval(function(){ get_update(); }, update_rate_millis);
});
