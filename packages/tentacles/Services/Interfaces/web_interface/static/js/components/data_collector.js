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

function reload_table(){
    $("#collector_data").load(location.href.split("?")[0] + " #collector_data",function(){
        dataFilesTable = $('#dataFilesTable').DataTable({
            "order": [],
            "columnDefs": [
              { "width": "20%", "targets": 1 },
              { "width": "8%", "targets": 4 },
            ],
        });
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
    request["symbols"] = $('#symbolsSelect').val();
    request["time_frames"] = $('#timeframesSelect').val().length ? $('#timeframesSelect').val() : null;
    request["startTimestamp"] = is_full_candle_history_exchanges() ? (new Date($("#startDate").val()).getTime()) : null;
    request["endTimestamp"] = is_full_candle_history_exchanges() ? (new Date($("#endDate").val()).getTime()) : null;
    const update_url = $("#collect_data").attr(update_url_attr);
    send_and_interpret_bot_update(request, update_url, $(this), collector_success_callback, collector_error_callback);
}

function stop_collector(){
    const update_url = $("#stop_collect_data").attr(update_url_attr);
    send_and_interpret_bot_update({}, update_url, $(this), collector_success_callback, collector_error_callback);
}

function collector_success_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", msg, "");
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
        const symbolSelect = $("#symbolsSelect");
        symbolSelect.empty(); // remove old options
        const symbolSelectBox = symbolSelect[0];
        $.each(data, function(key,value) {
            symbolSelectBox.append(new Option(value,value));
        });
        symbolSelect.trigger('change');
    });
}

function update_available_timeframes_list(url, exchange){
    const data = {exchange: exchange};
    $.get(url, data, function(data, status){
        const timeframeSelect = $("#timeframesSelect");
        timeframeSelect.empty(); // remove old options
        const timeframeSelectBox = timeframeSelect[0];
        $.each(data, function(key,value) {
            timeframeSelectBox.append(new Option(value,value));
        });
        timeframeSelect.trigger('change');
    });
}

function check_date_input(){
    const startDate = new Date($("#startDate").val());
    const enddate = new Date($("#endDate").val());
    const startDateMax = new Date( $("#startDate")[0].max);
    const endDateMin = new Date( $("#endDate")[0].min);
    if(isNaN(startDate) && isNaN(enddate)){
        return true;
    }else if (!isNaN(enddate) && isNaN(startDate)){
        create_alert("error", "You should specify a start date.", "");
        return false;
    }else if((!isNaN(startDate) && startDate > startDateMax) || (!isNaN(enddate) && enddate < endDateMin)){
        create_alert("error", "Invalid date range.", "");
        return false;
    }else{
        return true;
    }
}
function is_full_candle_history_exchanges(){
    const full_history_exchanges = $('#exchangeSelect > optgroup')[0].children;
    const selected_exchange = $('#exchangeSelect').find(":selected")[0];
    return $.inArray(selected_exchange, full_history_exchanges) !== -1;
}

let dataFilesTable = $('#dataFilesTable').DataTable({"order": [[ 1, 'desc' ]]});


function handleSelects(){
    createSelect2();
    $('#exchangeSelect').on('change', function() {
        update_symbol_list($('#symbolsSelect').attr(update_url_attr), $('#exchangeSelect').val());
        update_available_timeframes_list($('#timeframesSelect').attr(update_url_attr), $('#exchangeSelect').val());
        is_full_candle_history_exchanges() ? $("#collector_date_range").show() : $("#collector_date_range").hide();
    });
    $('#collect_data').click(function(){
        if(check_date_input()){
            start_collector();
        }
    });
    $('#stop_collect_data').click(function(){
        stop_collector();
    });
    $('#inputFile').on('change',function(){
        handle_file_selection();
    });
    $("#endDate").on('change', function(){
        let endDate = new Date(this.value);
        if(!isNaN(endDate)){
            const endDateMax = new Date();
            endDateMax.setDate(endDateMax.getDate() - 1);
            endDate.setDate(endDate.getDate() - 1);
            if(endDate > endDateMax){
                this.value = endDateMax.toISOString().split("T")[0];
                endDate = endDateMax;
            }
            $("#startDate")[0].max = endDate.toISOString().split("T")[0];
        }
    });
    $("#startDate").on('change', function(){
        const startDate = new Date(this.value);
        if(!isNaN(startDate)){
            const startDateMax = new Date();
            startDateMax.setDate(startDateMax.getDate() - 2);
            startDate.setDate(startDate.getDate() + 1);
            $("#endDate")[0].min = startDate.toISOString().split("T")[0];
        }
    });

    const endDateMax = new Date();
    endDateMax.setDate(endDateMax.getDate() - 1);
    $("#endDate")[0].max = endDateMax.toISOString().split("T")[0];
    const startDateMax = new Date();
    startDateMax.setDate(startDateMax.getDate() - 2);
    $("#startDate")[0].max = startDateMax.toISOString().split("T")[0];
}


function createSelect2(){
    $("#symbolsSelect").select2({
        closeOnSelect: false,
        placeholder: "Symbol"
    });
    $("#timeframesSelect").select2({
        closeOnSelect: false,
        placeholder: "All Timeframes"
    });
}


$(document).ready(function() {
    handle_data_files_buttons();
    is_full_candle_history_exchanges() ? $("#collector_date_range").show() : $("#collector_date_range").hide();
    $('#importFileButton').attr('disabled', true);
    dataFilesTable.on("draw.dt", function(){
        handle_data_files_buttons();
    });
    handleSelects();
    DataCollectorDoneCallbacks.push(reload_table);
    init_data_collector_status_websocket();
});
