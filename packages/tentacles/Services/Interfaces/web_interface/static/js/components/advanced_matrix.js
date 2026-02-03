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

 function init_select_filter(){
    let evaluators_array = [];
    let timeframes_array = [];
    let symbols_array = [];
    let exchanges_array = [];
    $.each(matrix_table.rows().data(), function(index, data) {
        evaluators_array.push(data[matrix_table_evaluator_index]);
        timeframes_array.push(data[matrix_table_timeframe_index]);
        symbols_array.push(data[matrix_table_symbol_index]);
        exchanges_array.push(data[matrix_table_exchange_index]);
    });
    evaluators_array = unique(evaluators_array);
    timeframes_array = unique(timeframes_array);
    symbols_array = unique(symbols_array);
    exchanges_array = unique(exchanges_array);

    let evaluators_select = $("#evaluatorsSelect").select2({
        closeOnSelect: false,
        placeholder: "Evaluators"
    });
    $.each(evaluators_array, function(index, value) {
        evaluators_select[0].add(new Option(value,value));
    });
    evaluators_select.on('change', function(){
        evaluators_selected = evaluators_select.val();
        matrix_table.columns(matrix_table_evaluator_index).search(
            evaluators_selected.length ? ('^(' + evaluators_selected.join("|") + ')$') : '', true, false
        ).draw();
    });

    let timeframes_select = $("#timeframesSelect").select2({
        closeOnSelect: false,
        placeholder: "Timeframes"
    });
    $.each(timeframes_array, function(index, value) {
        timeframes_select[0].add(new Option(value,value));
    });
    timeframes_select.on('change', function(){
        timeframes_selected = timeframes_select.val();
        matrix_table.columns(matrix_table_timeframe_index).search(
            timeframes_selected.length ? ('^(' + timeframes_selected.join("|") + ')$') : '', true, false
        ).draw();
    });

    let symbols_select = $("#symbolsSelect").select2({
        closeOnSelect: false,
        placeholder: "Symbols"
    });
    $.each(symbols_array, function(index, value) {
        symbols_select[0].add(new Option(value,value));
    });
    symbols_select.on('change', function(){
        symbols_selected = symbols_select.val();
        matrix_table.columns(matrix_table_symbol_index).search(
            symbols_selected.length ? ('^(' + symbols_selected.join("|") + ')$') : '', true, false
        ).draw();
    });

    let exchanges_select = $("#exchangesSelect").select2({
        closeOnSelect: false,
        placeholder: "Exchanges"
    });
    $.each(exchanges_array, function(index, value) {
        exchanges_select[0].add(new Option(value,value));
    });
    exchanges_select.on('change', function(){
        exchanges_selected = exchanges_select.val();
        matrix_table.columns(matrix_table_exchange_index).search(
            exchanges_selected.length ? ('^(' + exchanges_selected.join("|") + ')$') : '', true, false
        ).draw();
    });
}
const matrix_table = $('#matrixDataTable').DataTable();

const matrix_table_evaluator_index = 0;
const matrix_table_timeframe_index = 2;
const matrix_table_symbol_index = 3;
const matrix_table_exchange_index = 4;

$(document).ready(function() {
    init_select_filter();
});
