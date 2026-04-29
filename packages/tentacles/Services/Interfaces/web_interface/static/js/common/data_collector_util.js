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

function lock_collector_ui(lock=true){
    if(lock){
        $(`#${collectorMainProgressBar}`).show();
        // reset progress bar
        $("#total_progess_bar_anim").css('width', 0+'%').attr("aria-valuenow", 0);
    }else if(collectorHideProgressBarWhenFinished){
        $(`#${collectorMainProgressBar}`).hide();
    }
    $('#collect_data').prop('disabled', lock);
    $('#stop_collect_data').prop('disabled', !lock);
}

function _refreshDataCollectorStatus(socket){
    socket.emit('data_collector_status');
}

function updateDataCollectorProgress(current_progress, total_progress){
    if(current_progress === 0){
        $("#progress_bar_anim-container").hide();
    }else{
        $("#progress_bar_anim-container").show();
    }
    $("#current_progess_bar_anim").css('width', (current_progress === 0 ? 100 : current_progress)+'%').attr("aria-valuenow", current_progress);
    $("#total_progess_bar_anim").css('width', total_progress+'%').attr("aria-valuenow", total_progress);
    $("#progess_bar_anim").css('width', current_progress+'%').attr("aria-valuenow", current_progress);
}

function init_data_collector_status_websocket(){
    const socket = get_websocket("/data_collector");
    socket.on('data_collector_status', function(data_collector_status_data) {
        _handle_data_collector_status(data_collector_status_data, socket);
    });
}

function _handle_data_collector_status(data_collector_status_data, socket){
    const data_collector_status = data_collector_status_data["status"];
    const current_progress = data_collector_status_data["progress"]["current_step_percent"];
    const total_progress = Math.round((data_collector_status_data["progress"]["current_step"] 
                                    / data_collector_status_data["progress"]["total_steps"]) * 100);
    const stopButton = $("#collector-stop-button");

    if(data_collector_status === "collecting" || data_collector_status === "starting"){
        if(stopButton.length){
            stopButton.removeClass(hidden_class);
        }
        lock_collector_ui(true);
        updateDataCollectorProgress(current_progress, total_progress);
        DataCollectorCollectingCallbacks.forEach((callback) => callback());
        // re-schedule progress refresh
        setTimeout(function () {_refreshDataCollectorStatus(socket);}, 100);
    }
    else{
        if(stopButton.length){
            stopButton.addClass(hidden_class);
        }
        lock_collector_ui(false);
        DataCollectorDoneCallbacks.forEach((callback) => callback());
    }
    collectorBacktestingStatus = data_collector_status;
}

const DataCollectorDoneCallbacks = [];
const DataCollectorCollectingCallbacks = [];
let collectorBacktestingStatus = undefined;
let collectorHideProgressBarWhenFinished = true;
let collectorMainProgressBar = "collector_operation";
