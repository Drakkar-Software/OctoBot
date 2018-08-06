function handle_data_files_buttons(){
    $(".delete_data_file").unbind('click');
    $('.delete_data_file').click(function () {
        var request = $(this).attr("data-file");
        var update_url = $("#dataFilesTable").attr(update_url_attr);
        send_and_interpret_bot_update(request, update_url, $(this), delete_success_callback, delete_error_callback)
    });
}

function delete_success_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", msg, "");
    var row = dataFilesTable.row( dom_root_element.parents('tr') );
    dataFilesTable.row( dom_root_element.parents('tr') )
        .remove()
        .draw();
}

function delete_error_callback(updated_data, update_url, dom_root_element, result, status, error){
    create_alert("error", result.responseText, "");
}

function lock_collector_ui(lock=true){
    if(lock){
        $("#collector_operation").show();
    }else{
        $("#collector_operation").hide();
    }
    $('#collect_data').prop('disabled', lock);
}

function start_collector(){
    lock_collector_ui();
    var request = {}
    request["exchange"] = $('#exchangeSelect').val();
    request["symbol"] = $('#symbolSelect').val();
    var update_url = $("#collect_data").attr(update_url_attr);
    send_and_interpret_bot_update(request, update_url, $(this), collector_success_callback, collector_error_callback)
}

function collector_success_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", msg, "");
    lock_collector_ui(false);
    $("#collector_data").load(location.href + " #collector_data",function(){
        dataFilesTable = $('#dataFilesTable').DataTable();
        handle_data_files_buttons();
    });
}

function collector_error_callback(updated_data, update_url, dom_root_element, result, status, error){
    create_alert("error", result.responseText, "");
    lock_collector_ui(false);
}

function update_symbol_list(url, exchange){
    var data = {exchange: exchange};
    $.get(url, data, function(data, status){
        var symbolSelect = $("#symbolSelect");
        symbolSelect.empty(); // remove old options
        $.each(data, function(key,value) {
          symbolSelect.append($("<option></option>")
             .attr("value", value).text(value));
        });
    });
}

var dataFilesTable = $('#dataFilesTable').DataTable();

$(document).ready(function() {
    handle_data_files_buttons();
    $('#dataFilesTable').on("draw.dt", function(){
        handle_data_files_buttons();
    });
    $('#exchangeSelect').on('input', function() {
        update_symbol_list($('#symbolSelect').attr(update_url_attr), $('#exchangeSelect').val())
    });
    $('#collect_data').click(function(){
        start_collector();
    });
});
