
function start_backtesting(){
    $("#backtesting_progress_bar").show();
    lock_interface();
    var request = get_selected_files()
    var update_url = $("#start-url").attr(update_url_attr);
    send_and_interpret_bot_update(request, update_url, null, start_success_callback, start_error_callback)
}

function start_success_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", result.responseText, "");
}

function start_error_callback(updated_data, update_url, dom_root_element, result, status, error){
    create_alert("error", result.responseText, "");
    $("#backtesting_progress_bar").show();
    lock_interface(false);
}

function get_selected_files(){
    var selected_modules = []
    $("#dataFilesTable").find("input[type='checkbox']:checked").each(function(){
        selected_modules.push($(this).attr("data-file"));
    });
    return selected_modules
}

function lock_interface(lock=true){
    $('#startBacktesting').prop('disabled', lock);
}

function handle_backtesting_buttons(){
    $("#startBacktesting").click(function(){
        start_backtesting();
    });
}

$(document).ready(function() {
    handle_backtesting_buttons();
    lock_interface();
    var table = $('#dataFilesTable').DataTable()
});
