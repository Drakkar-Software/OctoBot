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
    const saveConfig = async (saveUrl) => {
        try {
            validateConfig();
            const updatedConfig = getConfigUpdate();
            const resp = await async_send_and_interpret_bot_update(updatedConfig, saveUrl, null);
            create_alert("success", "Configuration saved", resp);
            lastSavedConfig = updatedConfig
            configEditor.validate()
        } catch (error) {
            create_alert("error", "Impossible to save config", error)
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
        const referenceMarket = editorDiv.data("reference-market");
        let currenciesList = Array.isArray(currencies) ? [...currencies] : [];
        if (referenceMarket && currenciesList.indexOf(referenceMarket) === -1) {
            currenciesList.push(referenceMarket);
        }
        value.forEach((val) => {
            if (val && val.asset && currenciesList.indexOf(val.asset) === -1) {
                currenciesList.push(val.asset);
            }
        })
        if (currenciesList.length) {
            schema.items.properties.asset.enum = currenciesList.sort();
        }
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
            return errors;
        });
    }

    const getSelectableExchange = () => {
        if(exchangesEditor === undefined){
            return []
        }
        return exchangesEditor.getValue().map(value => value.name)
    }

    const getTradingModeName = () => {
        return $("#trading-mode-config-editor").data("trading-mode-name")
    }

    const validateConfig = () => {
        const tradingModeConfig = normalizeTradingModeConfig();
        normalizeSimulatedPortfolioConfig();
        [configEditor, tradingSimulatorEditor, simulatedPortfolioEditor, exchangesEditor].forEach((editor) => {
            if (editor === undefined) {
                throw "Editors are loading"
            }
            let errors = editor.validate();
            if (editor === configEditor && errors.length) {
                const optionalNumberKeys = new Set([
                    "min_unrealized_pnl_percent",
                    "max_unrealized_pnl_percent",
                    "min_mark_price",
                    "max_mark_price",
                ]);
                errors = errors.filter((err) => {
                    const key = err.path.replace("root.", "");
                    return !(optionalNumberKeys.has(key) && !(key in tradingModeConfig));
                });
            }
            if (errors.length) {
                throw JSON.stringify(errors.map(
                    err => `${err.path.replace('root.', '')}: ${err.message}`
                ).join(", "))
            }
        });
    }

    const normalizeTradingModeConfig = () => {
        const tradingModeConfig = configEditor.getValue();
        [
            "min_unrealized_pnl_percent",
            "max_unrealized_pnl_percent",
            "min_mark_price",
            "max_mark_price",
        ].forEach((key) => normalize_optional_number_field(tradingModeConfig, key));
        configEditor.setValue(tradingModeConfig);
        return tradingModeConfig;
    }

    const normalizeSimulatedPortfolioConfig = () => {
        if (simulatedPortfolioEditor === undefined) {
            return [];
        }
        const editorDiv = $("#simulated-portfolio-editor");
        const referenceMarket = editorDiv.data("reference-market");
        const portfolio = simulatedPortfolioEditor.getValue();
        let updated = false;
        portfolio.forEach((row) => {
            if (!row || !referenceMarket) {
                return;
            }
            const assetValue = row.asset;
            if (assetValue === undefined || assetValue === null || `${assetValue}`.trim() === "") {
                row.asset = referenceMarket;
                updated = true;
            }
        });
        if (updated) {
            simulatedPortfolioEditor.setValue(portfolio);
        }
        return portfolio;
    }

    const getEnabledExchangeFromConfig = () => {
        const exchanges = getSelectableExchange();
        return exchanges.length ? exchanges[0] : null;
    }

    const getConfigUpdate = () => {
        const tradingModeConfig = normalizeTradingModeConfig();
        const simulatedPortfolioConfig = normalizeSimulatedPortfolioConfig();
        return {
            exchange: getEnabledExchangeFromConfig(),
            tradingPair: null,
            tradingModeName: getTradingModeName(),
            tradingModeConfig: tradingModeConfig,
            tradingSimulatorConfig: tradingSimulatorEditor.getValue(),
            simulatedPortfolioConfig: simulatedPortfolioConfig,
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
    refreshPortfolioEditor();
    initUIWhenPossible();
    addCustomValidator();
    register_exit_confirm_function(hasPendingUpdates)
    startTutorialIfNecessary("pm:configuration");
});
