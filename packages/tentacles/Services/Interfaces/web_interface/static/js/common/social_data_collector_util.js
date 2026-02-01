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

function lock_social_collector_ui(lock=true){
    if(lock){
        $(`#${socialCollectorMainProgressBar}`).show();
        // reset progress bar
        $("#social_total_progess_bar_anim").css('width', 0+'%').attr("aria-valuenow", 0);
    }else if(socialCollectorHideProgressBarWhenFinished){
        $(`#${socialCollectorMainProgressBar}`).hide();
    }
    $('#collect_social_data').prop('disabled', lock);
    $('#stop_collect_social_data').prop('disabled', !lock);
}

function _refreshSocialDataCollectorStatus(socket){
    socket.emit('social_data_collector_status');
}

function updateSocialDataCollectorProgress(current_progress, total_progress){
    if(current_progress === 0){
        $("#social_progress_bar_anim-container").hide();
    }else{
        $("#social_progress_bar_anim-container").show();
    }
    $("#social_current_progess_bar_anim").css('width', (current_progress === 0 ? 100 : current_progress)+'%').attr("aria-valuenow", current_progress);
    $("#social_total_progess_bar_anim").css('width', total_progress+'%').attr("aria-valuenow", total_progress);
}

function init_social_data_collector_status_websocket(){
    const socket = get_websocket("/social_data_collector");
    socket.on('social_data_collector_status', function(social_data_collector_status_data) {
        _handle_social_data_collector_status(social_data_collector_status_data, socket);
    });
}

function _handle_social_data_collector_status(social_data_collector_status_data, socket){
    const social_data_collector_status = social_data_collector_status_data["status"];
    const progress_data = social_data_collector_status_data["progress"];
    const current_progress = progress_data["current_step_percent"] || 0;
    const total_steps = progress_data["total_steps"] || 1;
    const current_step = progress_data["current_step"] || 0;
    const total_progress = total_steps > 0 ? Math.round((current_step / total_steps) * 100) : 0;

    if(social_data_collector_status === "collecting" || social_data_collector_status === "starting"){
        lock_social_collector_ui(true);
        updateSocialDataCollectorProgress(current_progress, total_progress);
        SocialDataCollectorCollectingCallbacks.forEach((callback) => callback());
        // re-schedule progress refresh
        setTimeout(function () {_refreshSocialDataCollectorStatus(socket);}, 100);
    }
    else{
        lock_social_collector_ui(false);
        SocialDataCollectorDoneCallbacks.forEach((callback) => callback());
    }
    socialCollectorBacktestingStatus = social_data_collector_status;
}

const SocialDataCollectorDoneCallbacks = [];
const SocialDataCollectorCollectingCallbacks = [];
let socialCollectorBacktestingStatus = undefined;
let socialCollectorHideProgressBarWhenFinished = true;
let socialCollectorMainProgressBar = "social_collector_operation";
