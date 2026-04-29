
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


function get_selected_files(){
    const selected_files = [];
    const selectedRows = dataFilesTable.rows(
        function ( idx, data, node ) {
            return $(node).find("input[type='checkbox']:checked").length > 0;
        }
    ).eq(0);
    if(selectedRows){
        selectedRows.each(function( index ) {
            selected_files.push(dataFilesTable.row( index ).data()[7]);
        });
    }
    return selected_files;
}

function handle_backtesting_buttons(){
    $("#startBacktesting").click(function(){
        $("#backtesting_progress_bar").show();
        lock_interface();
        const request = {};
        request["files"] = get_selected_files();
        if(check_date_range_available()){
            if(!check_date_range()){
                create_alert("error", "Invalid date range.", "");
                return;
            }
            request["start_timestamp"] = startDate.val().length ? (new Date(startDate.val()).getTime()) : null;
            request["end_timestamp"] = endDate.val().length ? (new Date(endDate.val()).getTime()) : null;
        }
        const update_url = $("#startBacktesting").attr("start-url");
        const run_on_common_part_only = syncDataOnlyCheckbox.is(":checked");
        start_backtesting(request, `${update_url}&run_on_common_part_only=${run_on_common_part_only}`);
    });
}

function handle_file_selection(){
    const selectable_datafile = $(".selectable_datafile");
    selectable_datafile.unbind('click');
    selectable_datafile.click(function () {
        const row_element = $(this);
        if (row_element.hasClass(selected_item_class)){
            row_element.removeClass(selected_item_class);
            row_element.find(".dataFileCheckbox").prop('checked', false);
        }else{
            row_element.toggleClass(selected_item_class);
            const checkbox = row_element.find(".dataFileCheckbox");
            const symbols = checkbox.attr("symbols");
            const data_file = checkbox.attr("data-file");
            checkbox.prop('checked', true);
            // uncheck same symbols from other rows if any (skip for social files to allow multiple social selection)
            if (row_element.attr("data-file-type") !== "social") {
                $("#dataFilesTable").find("input[type='checkbox']:checked").each(function(){
                    if($(this).attr("symbols") === symbols && !($(this).attr("data-file") === data_file)){
                        $(this).closest('tr').removeClass(selected_item_class);
                        $(this).prop('checked', false);
                    }
                });
            }
        }
        if($("#dataFilesTable").find("input[type='checkbox']:checked").length > 1){
           syncDataOnlyDiv.removeClass(hidden_class);
        }else{
            syncDataOnlyDiv.addClass(hidden_class);
        }
        handle_date_selection();
        lock_interface(false);
    });
}

function check_date_range(){
    const start_date = new Date($("#startDate").val());
    const end_date = new Date($("#endDate").val());
    return (!isNaN(start_date) && !isNaN(end_date)) ? start_date < end_date : true;
}

function check_date_range_available() {
    const data_file_checked = $(".selectable_datafile").has("input[type='checkbox']:checked");
    return data_file_checked.length === data_file_checked.has("td[data-start-timestamp]").length;
}

function handle_date_selection(){
    if(!check_date_range_available()){
        startDate.prop("disabled", true);
        endDate.prop("disabled", true);
        return;
    }
    startDate.prop("disabled", false);
    endDate.prop("disabled", false);
    const data_file_checked_with_date_range = $(".selectable_datafile").has("input[type='checkbox']:checked")
                                                .has("td[data-end-timestamp]");
    if(data_file_checked_with_date_range.length === 0){
        return;
    }
    let end_timestamps = [];
    let start_timestamps = [];
    data_file_checked_with_date_range.find("[data-end-timestamp").each(function(){
        end_timestamps.push(parseInt($(this).attr("data-end-timestamp")));
        start_timestamps.push(parseInt($(this).attr("data-start-timestamp")));
    });
    const start_timestamp = syncDataOnlyCheckbox.prop("checked") ?
                                Math.max(...start_timestamps) : Math.min(...start_timestamps);
    const end_timestamp = syncDataOnlyCheckbox.prop("checked") ?
                                Math.min(...end_timestamps) : Math.max(...end_timestamps);

    const newStartDateTime = new Date(start_timestamp * 1000);
    const newEndDateTime = new Date(end_timestamp * 1000);
    const newStartDate = newStartDateTime.toISOString().split("T")[0];
    const newEndDate = newEndDateTime.toISOString().split("T")[0];
    if((new Date(startDate[0].value)) < newStartDateTime){
        startDate.val(newStartDate);
    }
    if((new Date(endDate[0].value)) > newEndDateTime){
        endDate.val(newEndDate);
    }
    startDate[0].min = newStartDate;
    startDate[0].max = newEndDate;
    endDate[0].max = newEndDate;
    endDate[0].min = newStartDate;
}

const dataFilesTable = $('#dataFilesTable').DataTable({
    "order": [[ 2, 'desc' ]],
    "columnDefs": [
      { "width": "20%", "targets": 2 },
      { "width": "8%", "targets": 5 },
      { "width": "12%", "targets": 6 },
    ],
    "destroy": true
});
const syncDataOnlyDiv = $("#synchronized-data-only-div");
const syncDataOnlyCheckbox = $("#synchronized-data-only-checkbox");
const startDate = $("#startDate");
const endDate = $("#endDate");

$(document).ready(function() {
    lock_interface_callbacks.push(function () {
        return get_selected_files() <= 0;
    });
    handle_backtesting_buttons();
    handle_file_selection();
    $('#dataFilesTable').on("draw.dt", function(){
        handle_file_selection();
    });
    lock_interface();

    init_backtesting_status_websocket();

    syncDataOnlyCheckbox.on("change", handle_date_selection);
});
