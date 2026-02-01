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

function start_social_collector(){
    lock_social_collector_ui();
    const request = {};
    request["social_name"] = $('#socialNameSelect').val();
    request["sources"] = $('#sourcesSelect').val();
    request["startTimestamp"] = $("#startDate").val() ? new Date($("#startDate").val()).getTime() : null;
    request["endTimestamp"] = $("#endDate").val() ? new Date($("#endDate").val()).getTime() : null;
    const update_url = $("#collect_social_data").attr(update_url_attr);
    send_and_interpret_bot_update(request, update_url, $(this), social_collector_success_callback, social_collector_error_callback);
}

function stop_social_collector(){
    const update_url = $("#stop_collect_social_data").attr(update_url_attr);
    send_and_interpret_bot_update({}, update_url, $(this), social_collector_success_callback, social_collector_error_callback);
}

function social_collector_success_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", msg, "");
}

function social_collector_error_callback(updated_data, update_url, dom_root_element, result, status, error){
    create_alert("error", result.responseText, "");
    lock_social_collector_ui(false);
}

function check_social_date_input(){
    const startDate = new Date($("#startDate").val());
    const enddate = new Date($("#endDate").val());
    const startDateMax = new Date( $("#startDate")[0].max);
    const endDateMin = new Date( $("#endDate")[0].min);
    if(isNaN(startDate)){
        create_alert("error", "Start date is required for social history collection.", "");
        return false;
    }
    if((!isNaN(startDate) && startDate > startDateMax) || (!isNaN(enddate) && enddate < endDateMin)){
        create_alert("error", "Invalid date range.", "");
        return false;
    }
    return true;
}

function update_available_services_list(url){
    $.get(url, {}, function(data, status){
        const serviceSelect = $("#socialNameSelect");
        serviceSelect.empty(); // remove old options
        const serviceSelectBox = serviceSelect[0];
        $.each(data, function(key,value) {
            serviceSelectBox.append(new Option(value,value));
        });
        if (data && data.length > 0) {
            serviceSelect.val(data[0]);
        }
        serviceSelect.selectpicker('refresh');
        serviceSelect.trigger('change');
    });
}

function update_sources_list(service_name){
    const sourcesSelect = $("#sourcesSelect");
    sourcesSelect.empty();
    const sourcesSelectBox = sourcesSelect[0];
    
    // Fetch service-specific sources from backend
    const url = $("#sourcesSelect").attr(update_url_attr);
    if (url && service_name) {
        $.get(url, {service_name: service_name}, function(data, status){
            if (data && data.length > 0) {
                $.each(data, function(key,value) {
                    sourcesSelectBox.append(new Option(value,value));
                });
            } else {
                // Fallback to common sources if service doesn't provide specific ones
                const commonSources = ["topic_news", "topic_marketcap"];
                $.each(commonSources, function(key,value) {
                    sourcesSelectBox.append(new Option(value,value));
                });
            }
            sourcesSelect.trigger('change');
        });
    } else {
        // Fallback to common sources
        const commonSources = ["topic_news", "topic_marketcap"];
        $.each(commonSources, function(key,value) {
            sourcesSelectBox.append(new Option(value,value));
        });
        sourcesSelect.trigger('change');
    }
}

function handleSocialSelects(){
    createSocialSelect2();
    
    // Load available services on page load
    update_available_services_list($('#socialNameSelect').attr(update_url_attr));
    
    $('#socialNameSelect').on('change', function() {
        update_sources_list($('#socialNameSelect').val());
    });
    
    $('#collect_social_data').click(function(){
        if(check_social_date_input()){
            start_social_collector();
        }
    });
    
    $('#stop_collect_social_data').click(function(){
        stop_social_collector();
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

function createSocialSelect2(){
    $("#sourcesSelect").select2({
        closeOnSelect: false,
        placeholder: "Sources/Topics"
    });
}

$(document).ready(function() {
    $('#collect_social_data').attr('disabled', true);
    $('#stop_collect_social_data').attr('disabled', true);
    // Always show date range for social collectors (timestamps are required)
    $("#social_collector_date_range").show();
    handleSocialSelects();
    SocialDataCollectorDoneCallbacks.push(function() {
        // Reload or update UI when collection is done
    });
    init_social_data_collector_status_websocket();
});
