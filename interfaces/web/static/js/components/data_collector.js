function handle_recording_buttons(){
    $(".delete_data_file").unbind('click');
    $('.delete_data_file').click(function () {
        var request = $(this).attr("data-file");
        var update_url = $("#dataFilesTable").attr("update-url");
        send_and_interpret_bot_update(request, update_url, $(this), delete_success_callback, delete_error_callback)
    });
}

function delete_success_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", msg, "");
    log(dom_root_element)
    var row = dataFilesTable.row( dom_root_element.parents('tr') );
    dataFilesTable.row( dom_root_element.parents('tr') )
        .remove()
        .draw();
}

function delete_error_callback(updated_data, update_url, dom_root_element, result, status, error){
    create_alert("error", result.responseText, "");
}

var dataFilesTable = $('#dataFilesTable').DataTable();

$(document).ready(function() {
    handle_recording_buttons();
    $('#dataFilesTable').on("draw.dt", function(){
        handle_recording_buttons();
    });
});
