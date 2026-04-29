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
function register_exchanges_checks(check_existing_accounts){
    const update_exchanges_details = (exchangeCard, exchangeData) => {
        const unloggedSupportingIcon = $(exchangeCard.find("[data-role=supporting-exchange]"));
        const supportingIcon = $(exchangeCard.find("[data-role=supporting-account]"));
        const validIcon = $(exchangeCard.find("[data-role=valid-account]"));
        const warnDetailsWrapper = $(exchangeCard.find("[data-role=account-warning-details-wrapper]"));
        const warnDetails = $(exchangeCard.find("[data-role=account-warning-details]"));

        warnDetailsWrapper.addClass(hidden_class);
        const exchangeType = exchangeData["exchange_type"]
        const newToolTip = `Login successful using ${exchangeType} account`
        // both have to be changed
        validIcon.attr("title", newToolTip)
        validIcon.attr("data-original-title", newToolTip)


        if(exchangeData["supporting_exchange"]){
            if(exchangeData["auth_success"]){
                supportingIcon.removeClass(hidden_class);
                unloggedSupportingIcon.addClass(hidden_class);
            }else{
                supportingIcon.addClass(hidden_class);
                unloggedSupportingIcon.removeClass(hidden_class);
            }
        }
        if(exchangeData["auth_success"]){
            validIcon.removeClass(hidden_class);
        }else{
            validIcon.addClass(hidden_class);
            if(exchangeData["configured_account"]) {
                warnDetailsWrapper.removeClass(hidden_class);
                warnDetails.text(exchangeData["error_message"]);
            }
        }
    }

    const check_accounts = (exchangeCards) => {
        const exchangesReq = {};
        const apiKey = "Empty";
        const apiSecret = apiKey;
        const apiPassword = apiKey;
        exchangeCards.forEach((exchangeCard) => {
            const exchange = exchangeCard.find(".card-body").attr("name");
            if(exchange !== config_default_value && typeof exchange !== "undefined") {
                exchangesReq[exchange] = {
                    exchange: exchange,
                    apiKey: apiKey,
                    apiSecret: apiSecret,
                    apiPassword: apiPassword,
                    sandboxed: exchangeCard.find(`#exchange_${exchange}_sandboxed`).is(':checked')
                };
            }
        })
        if(!Object.keys(exchangesReq).length){
            return;
        }
        $.post({
            url: $("#exchange-container").attr(update_url_attr),
            data: JSON.stringify(exchangesReq),
            contentType: 'application/json',
            dataType: "json",
            success: function(data, status){
                exchangeCards.forEach((exchangeCard) => {
                    const exchange = exchangeCard.find(".card-body").attr("name");
                    if(typeof data[exchange] !== "undefined"){
                        update_exchanges_details(exchangeCard, data[exchange]);
                    }
                });
            },
            error: function(result, status, error){
                window.console&&console.error(`Impossible to check the exchange accounts compatibility: ${result.responseText}. More details in logs.`);
            }
        })
    }


    const check_account = (exchangeCard, source, newValue) => {
        const exchange = exchangeCard.find(".card-body").attr("name");
        if(exchange !== config_default_value && exchangeCard.find("#exchange_api-key").length > 0){
            const apiKey = source.attr("id") === "exchange_api-key" ? newValue : exchangeCard.find("#exchange_api-key").editable('getValue', true).trim();
            const apiSecret = source.attr("id") === "exchange_api-secret" ? newValue : exchangeCard.find("#exchange_api-secret").editable('getValue', true).trim();
            const apiPassword = source.attr("id") === "exchange_api-password" ? newValue : exchangeCard.find("#exchange_api-password").editable('getValue', true).trim();
            const sandboxed = exchangeCard.find(`#exchange_${exchange}_sandboxed`).is(':checked');
            $.post({
                url: $("#exchange-container").attr(update_url_attr),
                data: JSON.stringify({
                    exchange: {
                        "exchange": exchange,
                        "apiKey": apiKey,
                        "apiSecret": apiSecret,
                        "apiPassword": apiPassword,
                        "sandboxed": sandboxed,
                    }
                }),
                contentType: 'application/json',
                dataType: "json",
                success: function(data, status){
                    update_exchanges_details(exchangeCard, data[exchange]);
                },
                error: function(result, status, error){
                    window.console&&console.error(`Impossible to check the exchange account compatibility: ${result.responseText}. More details in logs.`);
                }
            })
        }
    }

    const exchange_account_check = (e, params) => {
        const element = $(e.target);
        element.data("changed", true);
        check_account(element.parents("div[data-role=exchange]"), element,
            typeof params === "undefined" ? null : params.newValue);
    }

    const register_edit_events = () => {
        const cards = [];
        $("div[data-role=exchange]").each(function (){
            const card = $(this);
            const inputs = card.find("a[data-type=text]");
            if(inputs.length){
                add_event_if_not_already_added(inputs, 'save', exchange_account_check);
            }
            const bools = card.find("input[data-type=bool]");
            if(bools.length){
                add_event_if_not_already_added(bools, 'change', exchange_account_check);
            }
            cards.push(card);
        });
        if(check_existing_accounts){
            check_accounts(cards);
        }
    }

    register_edit_events(check_existing_accounts);
}
