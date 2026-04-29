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

$(document).ready(function() {
    let portfolioEditor = null;
    let allEditables = [];
    let updateRequired = false;
    let initialPortfolioValue = null;
    let initiallySelectedExchange;

    const getSelectedExchange = () => {
        return $("#AddExchangeSelect").val();
    }
    const displayPortfolioEditor = (currencies) => {
        const editorDiv = $("#portfolio-editor");
        let value = editorDiv.data("portfolio");
        if(initialPortfolioValue === null){
            initialPortfolioValue = JSON.parse(JSON.stringify(value));  // deep copy initial value
        }
        if(typeof value === "undefined"){
            return
        }
        const schema = editorDiv.data("portfolio-schema");
        if(portfolioEditor !== null) {
            value = portfolioEditor.getValue();
            portfolioEditor.destroy();
        }
        value.forEach((val) => {
            if(currencies.indexOf(val.asset) === -1){
                currencies.push(val.asset)
            }
        })
        schema.items.properties.asset.enum = currencies.sort();
        portfolioEditor = new JSONEditor(editorDiv[0],{
            schema: schema,
            startval: value,
            no_additional_properties: true,
            prompt_before_delete: false,
            disable_array_reorder: true,
            disable_array_delete: false,
            disable_array_delete_last_row: false,
            disable_collapse: true,
            disable_edit_json: true,
            disable_properties: true,
        })
    }
    const updateCurrencySelector = () => {
        const editorDiv = $("#portfolio-editor");
        if(!editorDiv.length){
            return;
        }
        const currencies_url = `${editorDiv.data("currencies-url")}${getSelectedExchange()}`;
        const successCallback = (updated_data, update_url, dom_root_element, msg, status) => {
            displayPortfolioEditor(msg)
        }
        send_and_interpret_bot_update({}, currencies_url, null, successCallback, generic_request_failure_callback, "GET");
    }
    const updateSelectedExchange = () => {
        // update exchange api key form, logo & name
        const exchangeContent = $("#exchanges-tab-content");
        const previousExchangeName = exchangeContent.data("exchange-name");
        if(typeof previousExchangeName === "undefined"){
            log("undefined previous exchange name when updating selected exchange");
            return
        }
        // prevent editable to be stuck open
        hide_editables(allEditables);
        const newExchangeName = getSelectedExchange();
        // update exchange name
        exchangeContent.data("exchange-name", newExchangeName);
        exchangeContent.find(`[url="/exchange_logo/${previousExchangeName}"]`).attr("src", "").addClass(hidden_class);
        const toUpdateElements = [
            $("#simulated-config-header"),
            $("#exchange-container"),
        ];
        toUpdateElements.forEach((element) =>  {
            element.html(
                element.html().replace(new RegExp(previousExchangeName,"g"), newExchangeName)
            );
        })
        // update logo
        fetch_images();
        // trigger accounts check
        register_exchanges_checks(true);
        // update form
        handleEditables();
    }
    const registerUpdatesOnExchangeSelect = () => {
        $("#AddExchangeSelect").on("change", () => {
            updateCurrencySelector();
            updateSelectedExchange();
        })
    }
    const getConfigUpdate = (isRealTrading) => {
        const globalConfigUpdate = {}
        const removedElements = [];
        let simulatorEnabled = true;
        let realEnabled = false;
        const selectedExchange = getSelectedExchange();
        const getConfigPortfolioAssetKey = (portfolioAsset) => {
            return `trader-simulator_starting-portfolio_${portfolioAsset.asset}`;
        }
        if(selectedExchange !== initiallySelectedExchange){
            // update enabled exchange
            globalConfigUpdate[`exchanges_${initiallySelectedExchange}_enabled`] = false;
            globalConfigUpdate[`exchanges_${selectedExchange}_enabled`] = true;
        }
        if(isRealTrading){
            const hasValueChanged = (editableElement) => {
                return editableElement.data("changed") === true;
            }
            // update exchange api keys
            allEditables.forEach((editableElement) => {
                if(hasValueChanged(editableElement)){
                    globalConfigUpdate[editableElement.attr("config-key")] = editableElement.text().trim();
                }
            })
            realEnabled = true;
            simulatorEnabled = false;
        }else{
            // update simulated portfolio
            // trader-simulator_starting-portfolio_BTC
            const updatedPortfolio = portfolioEditor.getValue();
            if(initialPortfolioValue !== null &&
                getValueChangedFromRef(updatedPortfolio, initialPortfolioValue)) {
                const remainingElements = Array.from(updatedPortfolio, (element) => element.asset);
                initialPortfolioValue.forEach((portfolioAsset) => {
                    if(remainingElements.indexOf(portfolioAsset.asset) === -1){
                        removedElements.push(getConfigPortfolioAssetKey(portfolioAsset))
                    }
                });
                updatedPortfolio.forEach((portfolioAsset) => {
                    globalConfigUpdate[getConfigPortfolioAssetKey(portfolioAsset)] = portfolioAsset.value;
                });
            }
        }
        const hasRealTrader = $("#exchanges-tab-content").data("has-real-trader") === "True";
        if((hasRealTrader && !realEnabled) || (!hasRealTrader && !simulatorEnabled)){
            globalConfigUpdate["trader_enabled"] = realEnabled;
            globalConfigUpdate["trader-simulator_enabled"] = simulatorEnabled;
        }
        updateRequired = Object.keys(globalConfigUpdate).length + removedElements.length > 0;
        return {
            global_config: globalConfigUpdate,
            removed_elements: removedElements,
        }
    }
    const handleStartTradingButtons = () => {
        $("button[data-role=\"start-trading\"]").click((e) => {
            const startButton = $(e.currentTarget);
            const isRealTrading = startButton.data("trading-type") === "real";
            const configUpdate = getConfigUpdate(isRealTrading);
            if(!isRealTrading){
                const errorsDesc = validateJSONEditor(portfolioEditor);
                if (errorsDesc.length) {
                    create_alert("error", "Error in portfolio configuration", errorsDesc);
                    return;
                }
            }
            const rebootRequired = updateRequired || new URL(window.location.href).searchParams.get("reboot") === "True";
            const updateUrl = startButton.data("config-url");
            const startUrl = `${startButton.data("start-url")}${rebootRequired}`;
            const onSuccess = (updated_data, update_url, dom_root_element, msg, status) => {
                // redirect to start url
                window.location.href = startUrl;
            }
            if(updateRequired){
                // update is required before reboot
                send_and_interpret_bot_update(configUpdate, updateUrl, null,
                    onSuccess, generic_request_failure_callback);
            } else {
                // skip update
                onSuccess(null, null, null, null, null);
            }
        });
    }
    const handleEditables = () => {
        setup_editable();
        allEditables = handle_editable();
    }

    initiallySelectedExchange = getSelectedExchange();
    updateCurrencySelector();
    displayPortfolioEditor([]);
    registerUpdatesOnExchangeSelect();
    handleEditables();
    handleStartTradingButtons();
    register_exchanges_checks(true);
});
