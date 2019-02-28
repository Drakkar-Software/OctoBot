/*
 * Drakkar-Software OctoBot
 * Copyright (c) Drakkar-Software, All rights reserved.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3.0 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.
 */

function handle_data_files_buttons(){
    $(".delete_data_file").unbind('click');
    $('.delete_data_file').click(function () {
        const request = $(this).attr("data-file");
        const update_url = $("#dataFilesTable").attr(update_url_attr);
        send_and_interpret_bot_update(request, update_url, $(this), delete_success_callback, delete_error_callback)
    });

}

function handle_file_selection(){
    const input_elem = $('#inputFile');
    const file_name = input_elem.val().split('\\').pop();
    $('#inputFileLabel').html(file_name);
    const has_valid_name = file_name.indexOf(".data") !== -1;
    $('#importFileButton').attr('disabled', !has_valid_name);
}

function delete_success_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", msg, "");
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

function reload_table(){
    $("#collector_data").load(location.href.split("?")[0] + " #collector_data",function(){
        dataFilesTable = $('#dataFilesTable').DataTable();
        handle_data_files_buttons();
        dataFilesTable.on("draw.dt", function(){
            handle_data_files_buttons();
        });
    });
}

function start_collector(){
    lock_collector_ui();
    const request = {};
    request["exchange"] = $('#exchangeSelect').val();
    request["symbol"] = $('#symbolSelect').val();
    const update_url = $("#collect_data").attr(update_url_attr);
    send_and_interpret_bot_update(request, update_url, $(this), collector_success_callback, collector_error_callback)
}

function collector_success_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", msg, "");
    lock_collector_ui(false);
    reload_table();
}

function collector_error_callback(updated_data, update_url, dom_root_element, result, status, error){
    create_alert("error", result.responseText, "");
    lock_collector_ui(false);
}

function display_alert(success, message){
    if(success === "True"){
        create_alert("success", message, "");
    }else{
        create_alert("error", message, "");
    }
}

function update_symbol_list(url, exchange){
    const data = {exchange: exchange};
    $.get(url, data, function(data, status){
        const symbolSelect = $("#symbolSelect");
        symbolSelect.empty(); // remove old options
        $.each(data, function(key,value) {
          symbolSelect.append($("<option></option>")
             .attr("value", value).text(value));
        });
        symbolSelect.selectpicker('refresh');
    });
}

let dataFilesTable = $('#dataFilesTable').DataTable();

$(document).ready(function() {
    handle_data_files_buttons();
    $('#importFileButton').attr('disabled', true);
    dataFilesTable.on("draw.dt", function(){
        handle_data_files_buttons();
    });
    $('#exchangeSelect').on('change', function() {
        update_symbol_list($('#symbolSelect').attr(update_url_attr), $('#exchangeSelect').val())
    });
    $('#collect_data').click(function(){
        start_collector();
    });
    $('#inputFile').on('change',function(){
        handle_file_selection();
    });
});
