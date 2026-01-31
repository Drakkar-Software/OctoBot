/*
 * Drakkar-Software OctoBot-Tentacles
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

const mardownConverter = new showdown.Converter();
const currentURL = `${window.location.protocol}//${window.location.host}`;

function markdown_to_html(text) {
    return mardownConverter.makeHtml(
        text?.trim().replaceAll("<br><br>", "\n\n")
    )
}

function fetch_images() {
    $(".product-logo").each(function () {
        const element = $(this);
        if(element.attr("src") === ""){
            $.get(`${currentURL}/${element.attr("url")}`, function(data) {
                element.attr("src", data["image"]);
                element.removeClass(hidden_class)
                const parentLink = element.parent("a");
                if (parentLink.attr("href") === ""){
                    parentLink.attr("href", data["url"]);
                }
            });
        }
    });
}

function handleDefaultImage(element, url){
    const imgSrc = element.attr("src");
    element.on("error",function () {
        if (imgSrc !== url){
            element.attr("src", url);
        }
    });
    if (((element[0].complete && element[0].naturalHeight === 0) && imgSrc !== url) || imgSrc.endsWith(currencyLoadingImageName)){
        element.attr("src", url);
    }
}

let currencyIdByName = undefined;
let currencyIdBySymbol = undefined;
let currencyDetails = []
let currencyLogoById = {};
let fetchedCurrencyIds = false;

const currencyLoadingImageName = "loading_currency.svg";
const currencyDefaultImage = `${currentURL}/static/img/svg/default_currency.svg`;
const currencyListURL = `${currentURL}/api/currency_list`;
const currencyLogoURL = `${currentURL}/currency_logos`;


function fetchCurrencyIds(){
    currencyIdByName = {};
    currencyIdBySymbol = {};
    $.get({
        url: currencyListURL,
        dataType: "json",
        success: function (data) {
            data.forEach((element) => {
                const name = element["n"].toLowerCase();
                if(!currencyIdByName.hasOwnProperty(name)){
                    // in case of conflicts, keep the first one as top 250 is first in list
                    currencyIdByName[name] = element["i"];
                }
                const symbol = element["s"].toLowerCase();
                if(!currencyIdBySymbol.hasOwnProperty(symbol)){
                    // in case of conflicts, keep the first one as top 250 is first in list
                    currencyIdBySymbol[symbol] = element["i"];
                }
            });
            currencyDetails = data;
            fetchedCurrencyIds = true;
            // refresh images
            handleDefaultImages();
        },
        error: function (result, status) {
            window.console && console.error(`Impossible to get currency list from coingecko.com: ${result.responseText} (${status})`);
        }
    });
}

function handleDefaultImages(){
    const applyImage = (element, logoUrl) => {
        if(!element.hasClass("default")){
            element.attr("src", logoUrl);
        }
    }
    const useLogo = (element, currencyId) => {
        let logoUrl = currencyLogoById[currencyId]
        if (logoUrl === null){
            logoUrl = currencyDefaultImage;
        }
        applyImage(element, logoUrl);
    }
    const fetchLogos = (currencyIds) => {
        const successcb = (updated_data, update_url, dom_root_element, msg, status) => {
            msg.forEach((dataElement) => {
                currencyLogoById[dataElement.id] = dataElement.logo;
            })
            displayImages(false);
        }
        const errorcb = (result, status, error) => {
            window.console && console.error(`Impossible to get currency logos: ${result.responseText} (${status})`);
        }
        send_and_interpret_bot_update({currency_ids: [... currencyIds]}, currencyLogoURL,
            null, successcb, errorcb);
    }
    const displayImages = (shouldFetch) => {
        try {
            const currencyIds = new Set();
            $(".currency-image").each((_, jselement) => {
                const element = $(jselement);
                const imgSrc = element.attr("src");
                if (imgSrc === "" || imgSrc.endsWith(currencyLoadingImageName)) {
                    if (jselement.hasAttribute("data-currency-id")) {
                        const currencyId = element.attr("data-currency-id").toLowerCase();
                        if(currencyLogoById.hasOwnProperty(currencyId)){
                            useLogo(element, currencyId);
                        }else{
                            currencyIds.add(currencyId);
                        }
                    } else if (jselement.hasAttribute("data-name")) {
                        const name = element.attr("data-name").toLowerCase();
                        if (typeof currencyIdByName === "undefined") {
                            fetchCurrencyIds();
                        } else if (fetchedCurrencyIds) {
                            if (currencyIdByName.hasOwnProperty(name)) {
                                const currencyId = currencyIdByName[name];
                                if(currencyLogoById.hasOwnProperty(currencyId)){
                                    useLogo(element, currencyId);
                                }else{
                                    currencyIds.add(currencyId);
                                }
                            } else {
                                handleDefaultImage(element, currencyDefaultImage);
                            }
                        }
                    } else if (jselement.hasAttribute("data-symbol")) {
                        const symbol = element.attr("data-symbol").toLowerCase();
                        if (typeof currencyIdBySymbol === "undefined") {
                            fetchCurrencyIds();
                        } else if (fetchedCurrencyIds) {
                            if (currencyIdBySymbol.hasOwnProperty(symbol)) {
                                const currencyId = currencyIdBySymbol[symbol];
                                if(currencyLogoById.hasOwnProperty(currencyId)){
                                    useLogo(element, currencyId);
                                }else{
                                    currencyIds.add(currencyId);
                                }
                            } else {
                                handleDefaultImage(element, currencyDefaultImage);
                            }
                        }
                    }
                }
            });
            if(shouldFetch && currencyIds.size){
                fetchLogos(currencyIds);
            }
        } catch {
            // fetching currency ids
        }
    }
    displayImages(true);
}

function handle_copy_to_clipboard() {
    $("[data-role=\"copy-to-clipboard\"]").on("click", (event) => {
        const element = $(event.currentTarget);
        copyToClipBoard(element.data("name"), element.data("value"));
    })
}


$(document).ready(function() {
    // register error listeners as soon as possible
    handleDefaultImages();
    handle_copy_to_clipboard();
    $(".markdown-content").each(function () {
        const element = $(this);
        element.html(markdown_to_html(element.text()));
    });
    fetch_images();
});
