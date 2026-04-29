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

function disablePackagesOperations(should_lock=true){
    const disabled_attr = 'disabled';
    $("[data-role=\"install-strategy\"]").prop(disabled_attr, should_lock);
}

function reloadTable(){
    $('.table').each(function () {
        $(this).DataTable({
            paging: false
        });
    });
    registerPackagesEvents();
}

function registerPackagesEvents(){
    $("[data-role=\"install-strategy\"]").click(function (){
        const element = $(this);
        const update_url = element.attr(update_url_attr);
        const data = {
            "strategy_id": element.data("strategy-id"),
            "name": element.data("strategy-name"),
            "description": element.data("description"),
        };
        disablePackagesOperations();
        send_and_interpret_bot_update(data, update_url, element, packagesOperationSuccessCallback, packagesOperationErrorCallback);
    });
}

function selectProfile(profileId) {
    if(profileId.length){
        const changeProfileURL = $("#cloud-strategies-selector").data("select-profile-url").replace("PROFILE_ID", profileId);
        window.location.replace(changeProfileURL);
    }
}

function packagesOperationSuccessCallback(updated_data, update_url, dom_root_element, msg, status){
    disablePackagesOperations(false);
    const postInstallActions = dom_root_element.data("post-install-action")
    if(postInstallActions === "select-profile"){
        selectProfile(msg.profile_id)
    }else{
        create_alert("success", "Strategy operation", msg.text);
    }
}

function packagesOperationErrorCallback(updated_data, update_url, dom_root_element, result, status, error){
    disablePackagesOperations(false);
    create_alert("error", "Error during strategy operation: "+result.responseText, "");
}

function displayBotSelectorWhenNoSelectedBot(){
    if($("#bot-selector").find("button[data-role='selected-bot']").length === 0) {
        // no selected bot, force selection
        $('#bot-select-modal').modal({backdrop: 'static', keyboard: false})
    }
}

function disableBotsSelectAndCreate(disabled){
    $("#bot-selector").find("button[data-role='select-bot']").attr("disabled", disabled);
    $("#create-new-bot").attr("disabled", disabled);
}

function initBotsCallbacks(){
    $("#bot-selector").find("button[data-role='select-bot']").click((element) => {
        const selectButton = $(element.target);
        const data = selectButton.data("bot-id")
        disableBotsSelectAndCreate(true);
        selectButton.html("<i class='fa fa-spinner fa-spin'></i>")
        const update_url = $("#bot-selector").data("update-url");
        send_and_interpret_bot_update(data, update_url, null,
            botOperationSuccessCallback, botOperationErrorCallback);

    })
    $("#create-new-bot").click((element) => {
        const createButton = $(element.target);
        const update_url = createButton.data("update-url");
        disableBotsSelectAndCreate(true);
        createButton.html("<i class='fa fa-spinner fa-spin'></i> Creating ...")
        send_and_interpret_bot_update({}, update_url, null,
            botOperationSuccessCallback, botOperationErrorCallback);
    })
}

function botOperationSuccessCallback(updated_data, update_url, dom_root_element, result, status, error){
    // reload the page to retest bots
    window.location.reload();
}

function botOperationErrorCallback(updated_data, update_url, dom_root_element, result, status, error){
    create_alert("error", "Error when managing bots: "+result.responseText, "");
}

function initLoginSubmit(){
    $("form[name=community-login]").on("submit", () => {
        $("input[type=submit]").addClass(hidden_class).attr("disabled", true);
        $("#login-waiter").removeClass(hidden_class);
    });
}

$(document).ready(function() {
    reloadTable();
    displayBotSelectorWhenNoSelectedBot();
    initBotsCallbacks();
    initLoginSubmit();
});
