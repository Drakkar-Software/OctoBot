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

function get_websocket(namespace){
    // Connect to the Socket.IO server.
    // The connection URL has the following format, relative to the current page:
    //     http[s]://<domain>:<port>[/<namespace>]
    return io(
        namespace,
        {
            reconnectionDelay: 2000, // Prevent unexpected disconnection on slow loading pages (ex: first config load)
            transports: ["polling", "websocket"], // update polling to ws when possible
        });
}

function getAudioMediaUrl(mediaName){
    const baseUrl = $("#resources-urls").data("audio-media-url")
    return `${baseUrl}${mediaName}`
}

function setup_editable(){
    $.fn.editable.defaults.mode = 'inline';
}

function get_color(index){
    let color_index = index % (material_colors.length);
    return material_colors[color_index];
}

function get_dark_color(index){
    let color_index = index % (material_dark_colors.length);
    return material_dark_colors[color_index];
}

function handle_editable(){
    const elements = []
    $(".editable").each(function(){
        elements.push($(this).editable());
    });
    return elements
}

function hide_editables(elements){
    elements.forEach((element) => {
        element.editable('hide');
        // element.destroy();
    })
}

function trigger_file_downloader_on_click(element){
    if(element.length){
        element.click(function (){
            window.window.location  = $(this).attr("data-url");
        });
    }
}

function replace_break_line(str, replacement=""){
    return str.replace(/(?:\r\n|\r|\n)/g, replacement);
}

function replace_spaces(str, replacement=""){
    return str.replace(/ /g, replacement);
}

function get_selected_options(element){
    const selected_options = [];
    element.find(":selected").each(function(){
        selected_options.push($(this).val());
    });
    return selected_options;
}


// utility functions
function isDefined(thing){
    return (typeof thing !== "undefined" && thing !== false && thing !==null);
}

function log(...texts){
    if(window.console){
        console.log(...texts);
    }
}

function get_events(elem, event_type){
    const events = $._data( elem[0], 'events' );
    if(typeof events === "undefined"){
        return [];
    }
    return $._data( elem[0], 'events' )[event_type];
}

function add_event_if_not_already_added(elem, event_type, handler){
    if(!check_has_event_using_handler(elem, event_type, handler)){
        elem.on(event_type, handler);
    }
}

function updateProgressBar(elementId, progress){
    $(document.getElementById(elementId)).css('width', progress+'%').attr("aria-valuenow", progress);
}

function check_has_event_using_handler(elem, event_type, handler){
    const events = get_events(elem, event_type);
    let has_events = false;
    $.each(events, function () {
        if($(this)[0]["handler"] === handler){
            has_events = true;
        }
    });
    return has_events;
}

function generic_request_success_callback(updated_data, update_url, dom_root_element, msg, status) {
    if(msg.hasOwnProperty("title")){
        create_alert("success", msg["title"], msg["details"]);
    }else{
        create_alert("success", msg, "");
    }
}

function generic_request_failure_callback(updated_data, update_url, dom_root_element, msg, status) {
    if(isBotDisconnected()){
        create_alert("error", "Can't connect to OctoBot", "Your OctoBot might be offline.");
    }else{
        create_alert("error", msg.responseText, "");
    }
}

function isMobileDisplay() {
    return $(window).width() < mobile_width_breakpoint;
}

function isMediumDisplay() {
    return $(window).width() < medium_width_breakpoint;
}

const getTextColor = () => {
    return getComputedStyle(document.body).getPropertyValue('--mdb-primary-text-emphasis')
}

const getTextColorRGB = () => {
    return getComputedStyle(document.body).getPropertyValue('--mdb-emphasis-color-rgb')
}

const isDarkTheme = () => {
    return $("html").data("mdb-theme") === "dark"
}

const handle_rounded_numbers_display = () => {
    $(".rounded-number").each(function (){
        const text = $(this).text().trim();
        if (!isNaN(text)){
            const value = Number(text);
            const decimal = value > 1 ? 3 : 8;
            $(this).text(handle_numbers(round_digits(text, decimal)));
        }
    });
}

function round_digits(number, decimals) {
    const rounded = Number(Math.round(`${number}e${decimals}`) + `e-${decimals}`);
    if(isNaN(rounded)){
        const n = Number(`${number}`);
        return n.toFixed(decimals);
    }
    return rounded;
}

function handle_numbers(number) {
    let regEx2 = /[0]+$/;
    let regEx3 = /[.]$/;
    const numb_repr = Number(number);
    const numb_str = numb_repr.toString();
    let numb_digits = numb_str.length;
    const exp_index = numb_str.indexOf('e-');
    if (exp_index > -1){
        let decimals = 0;
        if (numb_str.indexOf('.') > -1) {
            decimals = numb_str.substr(0, exp_index).split(".")[1].length;
        }
        numb_digits = Number(numb_str.split("e-")[1]) + decimals;
    }
    let numb = numb_repr.toFixed(numb_digits);

    if (numb.indexOf('.')>-1){
        numb = numb.replace(regEx2,'');  // Remove trailing 0's
    }
    return numb.replace(regEx3,'');  // Remove trailing decimal
}

function fix_config_values(config, schema){
    ensure_all_config_values(config, schema);
    $.each(config, function (key, val) {
        if(typeof val === "number"){
            config[key] = handle_numbers(val);
        }else if (val instanceof Object){
            fix_config_values(config[key], undefined);
        }
    });
}

const ensure_all_config_values = (config, schema) => {
    if(!isDefined(schema) || typeof schema.properties === "undefined"){
        return
    }
    // ensure each schema element has a value or there might be display issues
    Object.keys(schema.properties).forEach(key => {
        if(typeof config[key] === "undefined"){
            config[key] = schema.properties[key].default;
        }
    })
}

function getValueChangedFromRef(newObject, refObject, allowUndefinedValues=true) {
    let changes = false;
    if (newObject instanceof Array && newObject.length !== refObject.length){
        changes = true;
    }
    else{
        Object.keys(newObject).forEach((key) => {
            if(changes){
                return;
            }
            const val = newObject[key];
            const refVal = refObject[key];
            if (allowUndefinedValues && (typeof refVal === "undefined" || typeof val === "undefined")){
                // ignore missing values
                return;
            }
            else if (val instanceof Array || val instanceof Object){
                changes = getValueChangedFromRef(val, refVal, allowUndefinedValues);
            }
            else if (refObject[key] !== val){
                if (typeof val === "number"){
                    changes = Number(refVal) !== val;
                }else{
                    changes = true;
                }
            }
            if (changes){
                return;
            }
        });
    }
    return changes;
}

function historyGoBack() {
    window.history.back();
}

function showModalIfAny(element){
    if(element){
        element.modal();
    }
}

function hideModalIfAny(element){
    if(element){
        element.modal("hide");
    }
}

// Inspired from https://davidwalsh.name/javascript-debounce-function
// Function, that, as long as it continues to be invoked, will not
// be triggered. The function will be called after it stops being called for
// N milliseconds. If `immediate` is passed, trigger the function on the
// leading edge, instead of the trailing.
const debounce = (func, wait, immediate) => {
	let debounceTimeout;
	return () => {
        const context = this;
        const later = () => {
            debounceTimeout = null;
            if (!immediate) {
                func.apply(context);
            }
        };
        const callNow = immediate && !debounceTimeout;
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(later, wait);
        if (callNow) {
            func.apply(context);
        }
    }
}

function unique(array){
    return $.grep(array, function(el, index) {
        return index === $.inArray(el, array);
    });
}

function download_data(data, filename, content_type="application/json"){
    let a = window.document.createElement('a');
    a.href = window.URL.createObjectURL(new Blob([data], {type: content_type}));
    a.download = filename;

    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function display_generic_modal(title, content, warning, yes_button_callback, no_button_callback){
    let generic_modal = $("#genericModal");
    $("#genericModalTitle").text(title);
    $("#genericModalContent").text(content);
    if(warning !== ""){
        $("#genericModalWarning").removeClass(hidden_class);
        $("#genericModalWarningMessage").text(warning);
    }
    $("#genericModalButtonYes").on("click", function() {
        yes_button_callback();
        hideModalIfAny(generic_modal);
    });
    $("#genericModalButtonNo").on("click", function(){
        if(no_button_callback !== null){
            no_button_callback();
        }
        hideModalIfAny(generic_modal);
    });

    showModalIfAny(generic_modal);
    return generic_modal;
}

function updateInputIfValue(elementId, config, configKey, elementType){
    const value = config[configKey];
    if(typeof value !== "undefined" && value !== null && value !== ""){
        const element = $(document.getElementById(elementId));
        if(element.length){
            if(elementType === "date") {
                element.val(new Date(config[configKey]).toISOString().split('T')[0].slice(0, 10))
            } else if(elementType === "bool"){
                element.prop("checked", config[configKey]);
            }
            else {
                element.val(config[configKey]);
            }
        }
    }
}

function randomizeArray(array) {
    array.sort(() => Math.random() - 0.5);
}

function validateJSONEditor(editor) {
    const errors = editor.validate();
    let errorsDesc = "";
    if(errors.length) {
        window.console&&console.error("Errors when validating editor:", errors);
        errors.map((error) => {
            errorsDesc = `${errorsDesc}${error.path.split("root.")[1]} ${error.message}\n`
        })
    }
    return errorsDesc;
}

function normalize_optional_number_field(config, key) {
    if (!config || typeof config !== "object" || !(key in config)) {
        return;
    }
    const value = config[key];
    if (value === "" || value === null) {
        delete config[key];
        return;
    }
    if (typeof value === "string") {
        const parsed = Number(value);
        if (!Number.isNaN(parsed)) {
            config[key] = parsed;
        }
    }
}

function getWebsiteUrl() {
    return $("#global-urls").data("website-url");
}

function getDocsUrl() {
    return $("#global-urls").data("docs-url");
}

function getExchangesDocsUrl() {
    return $("#global-urls").data("exchanges-docs-url");
}

function paginatedSelect2(selectElement, options, pageSize){
    // WIP: issue: focus not working on options
    jQuery.fn.select2.amd.require(
        ["select2/data/array", "select2/utils"],
        (ArrayData, Utils) => {
            function CustomData($element, options) {
                CustomData.__super__.constructor.call(this, $element, options);
            }

            Utils.Extend(CustomData, ArrayData);

            CustomData.prototype.query = function (params, callback) {
                let results = [];
                if (typeof params.term !== "undefined" && params.term !== '') {
                    const toSearch = params.term.toUpperCase()
                    results = options.filter((option) => {
                        return option.text.toUpperCase().indexOf(toSearch) !== -1;
                    });
                } else {
                    results = options;
                }

                if (!("page" in params)) {
                    params.page = 1;
                }
                const data = {};
                data.results = results.slice((params.page - 1) * pageSize, params.page * pageSize);
                data.pagination = {};
                data.pagination.more = params.page * pageSize < results.length;
                callback(data);
            };
            // add select2 selector
            selectElement.select2({
                ajax: {},
                width: '200', // need to override the changed default
                tags: true,
                dataAdapter: CustomData
            });
        }
    );
}

const sortTimeFrames = (timeFrames) => {
    timeFrames.sort((a, b) => TimeFramesMinutes[a] - TimeFramesMinutes[b]);
    return timeFrames;
}

function activate_tab(tabElement, nestedNavBar=undefined){
    if(!tabElement.hasClass("active")){
        if(typeof nestedNavBar !== "undefined"){
            // manually handle sidebar navigation to work with nested elements
            nestedNavBar.each(function (){
                $(this).removeClass("active");
            })
        }
        tabElement.tab('show');
    }
}


function selectFirstTab(nestedNavBar=undefined){
    let activatedTab = false;
    const anchor = $(location).attr('hash');
    if (anchor){
        const tab = $(`${anchor}-tab`);
        if (typeof tab !== "undefined") {
            activate_tab(tab, nestedNavBar);
            activatedTab = true;
        }
    }
    if (!activatedTab){
        activate_tab($("[data-tab='default']"), nestedNavBar);
    }
}

function copyToClipBoard(name, value) {
    if(!navigator.clipboard){
        create_alert(
            "error",
            "Browser security is preventing copy. Please manually copy this value"
        );
    }
    navigator.clipboard.writeText(value);
    create_alert("success", `${name} copied to clipboard`);
}

async function sleep(milliseconds) {
    return new Promise(r => setTimeout(r, milliseconds))
}
