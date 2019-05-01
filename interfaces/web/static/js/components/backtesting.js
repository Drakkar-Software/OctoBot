
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
    const selected_modules = [];
    dataFilesTable.rows(
        function ( idx, data, node ) {
            return $(node).find("input[type='checkbox']:checked").length > 0;
        }
    ).eq(0).each(function( index ) {
        selected_modules.push(dataFilesTable.row( index ).data()[1]);
    });
    return selected_modules;
}

function handle_backtesting_buttons(){
    $("#startBacktesting").click(function(){
        $("#backtesting_progress_bar").show();
        lock_interface();
        const request = get_selected_files();
        const update_url = $("#startBacktesting").attr("start-url");
        start_backtesting(request, update_url);
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
            const symbol = checkbox.attr("symbol");
            const data_file = checkbox.attr("data-file");
            checkbox.prop('checked', true);
            // uncheck same symbols from other rows if any
            $("#dataFilesTable").find("input[type='checkbox']:checked").each(function(){
                if($(this).attr("symbol") === symbol && !($(this).attr("data-file") === data_file)){
                    $(this).parent().parent().removeClass(selected_item_class);
                    $(this).prop('checked', false);
                }
            });
        }
        lock_interface(false);
    });
}

const dataFilesTable = $('#dataFilesTable').DataTable();

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

    setInterval(function(){refresh_status();}, 300);
    function refresh_status(){
        check_backtesting_state();
    }
});
