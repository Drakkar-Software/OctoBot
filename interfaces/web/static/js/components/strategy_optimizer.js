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

function recompute_nb_iterations(){
    const nb_eval_iter = Math.pow(2, $("#evaluatorsSelect").find(":selected").length)-1;
    const nb_tf_iter = Math.pow(2, $("#timeFramesSelect").find(":selected").length)-1;
    const nb_selected = $("#risksSelect").find(":selected").length*nb_eval_iter*nb_tf_iter;
    $("#numberOfSimulatons").text(nb_selected);
}

function check_disabled(lock=false){
    if(lock){
        $("#startOptimizer").prop('disabled', true);
    }
    else if($("#strategySelect").find(":selected").length > 0 && $("#risksSelect").find(":selected").length  > 0 &&
        $("#timeFramesSelect").find(":selected").length > 0 && $("#evaluatorsSelect").find(":selected").length  > 0){
        $("#startOptimizer").prop('disabled', false);
    }else{
        $("#startOptimizer").prop('disabled', true);
    }
}

function start_optimizer(source){
    $("#progess_bar").show();
    $("#progess_bar_anim").css('width', '0%').attr("aria-valuenow", '0');
    source.prop('disabled', true);
    const update_url = source.attr(update_url_attr);
    const data = {};
    data["strategy"]=get_selected_options($("#strategySelect"));
    data["time_frames"]=get_selected_options($("#timeFramesSelect"));
    data["evaluators"]=get_selected_options($("#evaluatorsSelect"));
    data["risks"]=get_selected_options($("#risksSelect"));
    send_and_interpret_bot_update(data, update_url, source, start_optimizer_success_callback, start_optimizer_error_callback);
}

function lock_inputs(lock=true){
    const disabled_attr = 'disabled';
    if ( $("#strategySelect").prop(disabled_attr) !== lock){
        $("#strategySelect").prop(disabled_attr, lock);
    }
    if ( $("#timeFramesSelect").prop(disabled_attr) !== lock){
        $("#timeFramesSelect").prop(disabled_attr, lock);
    }
    if ( $("#evaluatorsSelect").prop(disabled_attr) !== lock){
        $("#evaluatorsSelect").prop(disabled_attr, lock);
    }
    if ( $("#risksSelect").prop(disabled_attr) !== lock){
        $("#risksSelect").prop(disabled_attr, lock);
    }
    if(!($("#progess_bar").is(":visible")) && lock){
        $("#progess_bar_anim").css('width', '0%').attr("aria-valuenow", '0');
        $("#progess_bar").show();
    }
    else if (!lock){
        $("#progess_bar_anim").css('width', '100%').attr("aria-valuenow", '100');
        $("#progess_bar").hide();
    }
    check_disabled(lock);

}

function start_optimizer_success_callback(data, update_url, source, msg, status){
    create_alert("success", msg, "");
    lock_inputs();
}

function start_optimizer_error_callback(data, update_url, source, result, status, error){
    source.prop('disabled', false);
    $("#progess_bar").hide();
    create_alert("error", "Error when starting optimizer: "+result.responseText, "");
}

function populate_select(element, options){
    element.empty(); // remove old options
    $.each(options, function(key, value) {
        if (key === 0){
            element.append($('<option selected = "selected" value="' + value + '" ></option>').attr("value", value).text(value));
        }else{
            element.append($('<option value="' + value + '" ></option>').attr("value", value).text(value));
        }
    });
}

function update_strategy_params(url, strategy){
    var data = {strategy_name: strategy};
    $.get(url, data, function(data, status){
        populate_select($("#evaluatorsSelect"), data["evaluators"]);
        populate_select($("#timeFramesSelect"), data["time_frames"]);
    });
}

function update_progress(progress, overall_progress){
    $("#progess_bar_anim").css('width', progress+'%').attr("aria-valuenow", progress);

    const nb_progress = Number(overall_progress);

    if(isDefined(progressChart)){
        update_circular_progress_doughnut(progressChart, nb_progress, 100 - nb_progress);
        $("#optimize_doughnutChart_progress").html(nb_progress.toString()+"%");
    }
}

function check_optimizer_state(reportTable){
    const url = $("#strategyOptimizerInputs").attr(update_url_attr);
    $.get(url,function(data, request_status){
        const status = data["status"];
        const progress = data["progress"];
        const overall_progress = data["overall_progress"];
        const errors = data["errors"];
        const error_div = $("#error_info");
        const error_text_div = $("#error_info_text");
        const report_datatable_card = $("#report_datatable_card");
        const has_errors = errors !== null;
        let alert_type = "success";
        let alert_additional_text = "Strategy optimized finished simulations.";
        if(has_errors){
            error_text_div.text(errors);
            error_div.show();
            alert_type = "error";
            alert_additional_text = "Strategy optimized finished simulations with error(s)."
        }else{
            error_text_div.text("");
            error_div.hide();
        }
        if(status === "computing"){
            lock_inputs();
            update_progress(progress, overall_progress);
            first_refresh_state = status;
            if(report_datatable_card.is(":visible")){
                report_datatable_card.hide();
                reportTable.clear();
            }
        }
        else{
            lock_inputs(false);
            if(status === "finished"){
                if(!report_datatable_card.is(":visible")){
                    report_datatable_card.show();
                }
                if(reportTable.rows().count() === 0){
                    reportTable.ajax.reload( null, false);
                }
                if((first_refresh_state !== "" || has_errors) && first_refresh_state !== "finished"){
                    create_alert(alert_type, alert_additional_text, "");
                    first_refresh_state="finished";
                }
            }
        }
        if(first_refresh_state === ""){
            first_refresh_state = status;
        }
    });
}

const iterationColumnsDef = [
    {
        "title": "#",
        "targets": 0,
        "data": "id",
        "name": "id",
        "render": function(data, type, row, meta){
            return data;
        }
    },
    {
        "title": "Evaluator(s)",
        "targets": 1,
        "data": "evaluators",
        "name": "evaluators",
        "render": function(data, type, row, meta){
            return data;
        }
    },
    {
        "title": "Time Frame(s)",
        "targets": 2,
        "data": "time_frames",
        "name": "time_frames",
        "render": function(data, type, row, meta){
            return data;
        }
    },
    {
        "title": "Risk",
        "targets": 3,
        "data": "risk",
        "name": "risk",
        "render": function(data, type, row, meta){
            return data;
        }
    },
    {
        "title": "Average trades count",
        "targets": 4,
        "data": "average_trades",
        "name": "average_trades",
        "render": function(data, type, row, meta){
            return data;
        }
    },
    {
        "title": "Score: the higher the better",
        "targets": 5,
        "data": "score",
        "name": "score",
        "render": function(data, type, row, meta){
            return data;
        }
    }
];

const reportColumnsDef = [
    {
        "title": "#",
        "targets": 0,
        "data": "id",
        "name": "id",
        "render": function(data, type, row, meta){
            return data;
        }
    },
    {
        "title": "Evaluator(s)",
        "targets": 1,
        "data": "evaluators",
        "name": "evaluators",
        "render": function(data, type, row, meta){
            return data;
        }
    },
    {
        "title": "Risk",
        "targets": 2,
        "data": "risk",
        "name": "risk",
        "render": function(data, type, row, meta){
            return data;
        }
    },
    {
        "title": "Average trades count",
        "targets": 3,
        "data": "average_trades",
        "name": "average_trades",
        "render": function(data, type, row, meta){
            return data;
        }
    },
    {
        "title": "Comparative score: the lower the better",
        "targets": 4,
        "data": "score",
        "name": "score",
        "render": function(data, type, row, meta){
            return data;
        }
    }
];
let first_refresh_state = "";

const progressChart = create_circular_progress_doughnut($("#optimize_doughnutChart")[0]);

$(document).ready(function() {

    check_disabled();

    $('#strategySelect').on('input', function() {
        update_strategy_params($('#strategySelect').attr(update_url_attr), $('#strategySelect').val());
    });

    $(".multi-select-element").select2({
        dropdownAutoWidth : true,
        multiple: true,
        closeOnSelect: false
    });
    $(".multi-select-element").on('change', function (e) {
        recompute_nb_iterations();
        check_disabled();
    });
    $("#startOptimizer").click(function(){
        start_optimizer($(this));
    });

    const reportTable = $("#report_datatable").DataTable({
        ajax: {
            "url": $("#report_datatable").attr(update_url_attr),
            "dataSrc": ""
        },
        deferRender: true,
        autoWidth: true,
        autoFill: true,
        columnDefs: reportColumnsDef
    });

    const iterationTable = $("#results_datatable").DataTable({
        ajax: {
            "url": $("#results_datatable").attr(update_url_attr),
            "dataSrc": ""
        },
        deferRender: true,
        autoWidth: true,
        autoFill: true,
        columnDefs: iterationColumnsDef
    });


    setInterval(function(){refresh_message_table(iterationTable,reportTable);}, 1500);
    function refresh_message_table(iterationTable, reportTable){
        iterationTable.ajax.reload( null, false );
        if(iterationTable.rows().count() > 0){
            $("#results_datatable_card").show();
        }
        check_optimizer_state(reportTable);
    }
});