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
    const getAvailableCurrencies = () => {
        const currencies = new Set()
        exchangeSymbols.forEach(symbol => {
            const baseAndQuote = symbol.split("/");
            currencies.add(baseAndQuote[0]);
            currencies.add(baseAndQuote[1]);
        })
        return Array.from(currencies);
    }

    const fetchExchangeSymbols = async (exchange) => {
        const url = $("#traded-symbol-selector").data("update-url")
        const allSymbols = await async_send_and_interpret_bot_update(
            null, `${url}/${exchange}`, null, "GET"
        )
        exchangeSymbols = allSymbols.filter(symbol => {
            // ignore non spot symbols
            return symbol.indexOf(":") === -1;
        })
    }

    const saveConfig = async (saveUrl) => {
        try {
            validateConfig();
            const updatedConfig = getConfigUpdate();
            const resp = await async_send_and_interpret_bot_update(updatedConfig, saveUrl, null);
            create_alert("success", "Configuration saved", resp);
            refreshExchangeSelector()
            lastSavedConfig = updatedConfig
            configEditor.validate()
        } catch (error) {
            create_alert("error", "Impossible to save config", error)
        }
    }

    const updateSymbols = async (exchange) => {
        const previouslySelectedSymbol = getSelectedPair();
        clearSymbolSelector();
        await fetchExchangeSymbols(exchange);
        const currencies = getAvailableCurrencies();
        refreshSymbolSelector(previouslySelectedSymbol);
        refreshPortfolioEditor(currencies);
    }

    const clearSymbolSelector = () => {
        $("#traded-symbol-selector").empty()
    }

    const refreshSymbolSelector = (previouslySelectedSymbol) => {
        const symbolSelector = $("#traded-symbol-selector");
        let options = []
        const profilePair = symbolSelector.data("selected-pair");
        const selectedValue = previouslySelectedSymbol === null ? profilePair: previouslySelectedSymbol;
        options = options.concat(exchangeSymbols.sort().map((symbol) => {
            return new Option(symbol, symbol, false, symbol===selectedValue);
        }));
        clearSymbolSelector()
        symbolSelector.append(...options);
    }

    const refreshExchangeSelector = () => {
        const exchanges = getSelectableExchange();
        const exchangeSelector = $("#main-exchange-selector");
        const profileExchange = exchangeSelector.data("selected-exchange");
        const selectedValue = exchangeSelector.val() === null ? profileExchange: exchangeSelector.val();
        const options = exchanges.map((exchange) => {
            return new Option(exchange, exchange, false, exchange===selectedValue);
        });
        if(selectedValue !== null && exchanges.indexOf(selectedValue) === -1){
            // previously selected value is not available anymore: select 1st value by default
            options[0].selected = true;
            onSelectedExchange(options[0].value);
        }
        exchangeSelector.empty()
        exchangeSelector.append(...options);
    }

    const onSelectedExchange = async (exchange) => {
        if(typeof exchange === "string") {
            await updateSymbols(exchange);
        }
    }

    const refreshPortfolioEditor = (currencies) => {
        const editorDiv = $("#simulated-portfolio-editor");
        let value = editorDiv.data("config");
        if(typeof value === "undefined"){
            return
        }
        const schema = editorDiv.data("schema");
        if(simulatedPortfolioEditor !== undefined) {
            value = simulatedPortfolioEditor.getValue();
            simulatedPortfolioEditor.destroy();
        }
        value.forEach((val) => {
            if(currencies.indexOf(val.asset) === -1){
                currencies.push(val.asset)
            }
        })
        schema.items.properties.asset.enum = currencies.sort();
        simulatedPortfolioEditor = new JSONEditor(editorDiv[0],{
            schema: schema,
            startval: value,
            no_additional_properties: true,
            prompt_before_delete: true,
            disable_array_reorder: true,
            disable_array_delete: false,
            disable_array_delete_last_row: true,
            disable_array_delete_all_rows: true,
            disable_collapse: true,
            disable_edit_json: true,
            disable_properties: true,
        })
        simulatedPortfolioEditor.on('ready', () => {
            readyEditors.portfolio = true
            initLastSavedConfig();
        })
    }

    const refreshTradingSimulatorEditor = () => {
        const editorDiv = $("#trading-simulator-editor");
        let value = editorDiv.data("config");
        if(typeof value === "undefined"){
            return
        }
        const schema = editorDiv.data("schema");
        if(tradingSimulatorEditor !== undefined) {
            value = tradingSimulatorEditor.getValue();
            tradingSimulatorEditor.destroy();
        }
        schema.options = {
            titleHidden: true
        }
        tradingSimulatorEditor = new JSONEditor(editorDiv[0],{
            schema: schema,
            startval: value,
            disable_collapse: true,
            disable_edit_json: true,
            disable_properties: true,
        })
        tradingSimulatorEditor.on('ready', () => {
            readyEditors.simulator = true
            initLastSavedConfig();
        })
    }

    const refreshExchangesEditor = () => {
        const editorDiv = $("#exchanges-editor");
        let value = editorDiv.data("config");
        if(typeof value === "undefined"){
            return
        }
        const schema = editorDiv.data("schema");
        if(exchangesEditor !== undefined) {
            exchangesEditor.destroy();
        }
        schema.options = {
            titleHidden: true
        }
        const selectableExchanges = schema.items.properties.name.enum;
        value.forEach((val) => {
            if(selectableExchanges.indexOf(val.name) === -1){
                selectableExchanges.push(val.name)
            }
        })
        schema.id="exchangesConfig"
        exchangesEditor = new JSONEditor(editorDiv[0],{
            schema: schema,
            startval: value,
            no_additional_properties: true,
            prompt_before_delete: true,
            disable_array_reorder: true,
            disable_array_delete: false,
            disable_array_delete_last_row: true,
            disable_array_delete_all_rows: true,
            disable_collapse: true,
            disable_edit_json: true,
            disable_properties: true,
        })
    }

    const addCustomValidator = () => {
        // Custom validators must return an array of errors or an empty array if valid
        JSONEditor.defaults.custom_validators.push((schema, value, path) => {
            const errors = [];
            if (schema.id === "exchangesConfig" && path === "root") {
                const newNames = value.map(value => value.name);
                const duplicates = newNames.filter(
                    (value, index) => newNames.indexOf(value) !== index && newNames.lastIndexOf(value) === index
                );
                if (duplicates.length) {
                    // Errors must be an object with `path`, `property`, and `message`
                    errors.push({
                        path: path,
                        property: '',
                        message: `Each exchanges can only be listed once. Exchanges listed more than once: ${duplicates}.`
                    });
                }
            }
            if (schema.id === "tentacleConfig" && path === "root") {
                const referenceExchange = value.reference_exchange;
                if (referenceExchange !== undefined) {
                    try {
                        // in try catch in case getSelectableExchange is not yet available
                        const listedExchanges = getSelectableExchange();
                        if (listedExchanges.concat(["local"]).indexOf(referenceExchange) === -1){
                            // Errors must be an object with `path`, `property`, and `message`
                            errors.push({
                                path: path,
                                property: 'reference_exchange',
                                message: `Reference exchange must be listed in exchange configurations or equal to "local". Listed exchanges are ${listedExchanges.join(', ')}.`
                            });
                        }
                        if (referenceExchange === getSelectedExchange()){
                            // "local" must be used to use the same exchange to trade and as reference price
                            errors.push({
                                path: path,
                                property: 'reference_exchange',
                                message: `Reference exchange must be set to "local" when equal to your selected exchange.`
                            });
                        }
                    } catch (err) {
                        console.error(err)
                    }
                }
                const minSpread = value.min_spread;
                const maxSpread = value.max_spread;
                if(minSpread !== undefined && maxSpread !== undefined && minSpread >= maxSpread){
                    errors.push({
                        path: path,
                        property: 'max_spread',
                        message: `Max spread % must be larger than Min spread %.`
                    });
                }
            }
            return errors;
        });
    }

    const initSelectedExchange = async () => {
        refreshExchangeSelector();
        await onSelectedExchange(getSelectedExchange())
    }

    const getSelectableExchange = () => {
        if(exchangesEditor === undefined){
            return []
        }
        return exchangesEditor.getValue().map(value => value.name)
    }
    const getSelectedExchange = () => {
        return $("#main-exchange-selector").val()
    }

    const getSelectedPair = () => {
        return $("#traded-symbol-selector").val()
    }

    const getTradingModeName = () => {
        return $("#trading-mode-config-editor").data("trading-mode-name")
    }

    const registerEvents = () => {
         $("#main-exchange-selector").on(
             "change", () => onSelectedExchange(getSelectedExchange())
         )
    }

    const validateConfig = () => {
        [configEditor, tradingSimulatorEditor, simulatedPortfolioEditor, exchangesEditor].forEach((editor) => {
            if (editor === undefined) {
                throw "Editors are loading"
            }
            const errors = editor.validate();
            if (errors.length) {
                throw JSON.stringify(errors.map(
                    err => `${err.path.replace('root.', '')}: ${err.message}`
                ).join(", "))
            }
        });
        const exchange = getSelectedExchange()
        if(exchange === undefined || exchange === null || !exchange.length){
            throw "No selected exchange"
        }
        const pair = getSelectedPair()
        if(pair === undefined || pair === null || !pair.length){
            // can happen, don't prevent saving
            create_alert("error", "Action required", "Please select a trading pair to start your strategy");
        }
    }

    const getConfigUpdate = () => {
        return {
            exchange: getSelectedExchange(),
            tradingPair: getSelectedPair(),
            tradingModeName: getTradingModeName(),
            tradingModeConfig: configEditor.getValue(),
            tradingSimulatorConfig: tradingSimulatorEditor.getValue(),
            simulatedPortfolioConfig: simulatedPortfolioEditor.getValue(),
            exchangesConfig: exchangesEditor.getValue(),
        }
    }

    const initLastSavedConfig = () => {
        if (
            readyEditors.exchanges
            && readyEditors.simulator
            && readyEditors.portfolio
            && lastSavedConfig === undefined
        ) {
            lastSavedConfig = getConfigUpdate()
        }
    }

    const initUIWhenPossible = () => {
        exchangesEditor.on('ready', () => {
            initSelectedExchange();
            registerEvents();
            readyEditors.exchanges = true
            initLastSavedConfig();
        })
        $("[data-role=save]").on("click", (event) => {
            saveConfig($(event.currentTarget).data("update-url"))
        })
    }

    const hasPendingUpdates = () => {
        if (tradingSimulatorEditor === undefined
            || simulatedPortfolioEditor === undefined
            || exchangesEditor === undefined
            || lastSavedConfig === undefined
        ) {
            return false;
        }
        return getValueChangedFromRef(
            getConfigUpdate(), lastSavedConfig, true
        )
    }

    let exchangeSymbols = [];
    let tradingSimulatorEditor = undefined;
    let simulatedPortfolioEditor = undefined;
    let exchangesEditor = undefined;
    let lastSavedConfig = undefined
    const readyEditors = {
        exchanges: false,
        simulator: false,
        portfolio: false,
    }


    refreshExchangesEditor();
    refreshTradingSimulatorEditor();
    initUIWhenPossible();
    addCustomValidator();
    register_exit_confirm_function(hasPendingUpdates)
    startTutorialIfNecessary("mm:configuration");
});