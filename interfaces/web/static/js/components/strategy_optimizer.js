function recompute_nb_iterations(){
    var nb_selected = 0;
    nb_selected = $("#risksSelect").find(":selected").length*Math.pow($("#timeFramesSelect").find(":selected").length, 2)*Math.pow($("#evaluatorsSelect").find(":selected").length,2);
    $("#numberOfSimulatons").text(nb_selected);
}

function check_disabled(){
    if($("#strategySelect").find(":selected").length > 0 && $("#risksSelect").find(":selected").length  > 0 &&
        $("#timeFramesSelect").find(":selected").length > 0 && $("#evaluatorsSelect").find(":selected").length  > 0){
        $("#startOptimizer").prop('disabled', false);
    }else{
        $("#startOptimizer").prop('disabled', true);
    }
}

function start_optimizer(source){
    $("#progess_bar").show();
    $("#progess_bar_anim").css('width', '0%').attr("aria-valuenow", '0')
    source.prop('disabled', true);
    var update_url = source.attr(update_url_attr);
    var data = {};
    data["strategy"]=get_selected_options($("#strategySelect"));
    data["time_frames"]=get_selected_options($("#timeFramesSelect"));
    data["evaluators"]=get_selected_options($("#evaluatorsSelect"));
    data["risks"]=get_selected_options($("#risksSelect"));
    send_and_interpret_bot_update(data, update_url, source, start_optimizer_success_callback, start_optimizer_error_callback);
}

function lock_inputs(lock=true){
    if ( $("#strategySelect").prop('disabled') != lock){
        $("#strategySelect").prop('disabled', lock);
    }
    if ( $("#timeFramesSelect").prop('disabled') != lock){
        $("#timeFramesSelect").prop('disabled', lock);
    }
    if ( $("#evaluatorsSelect").prop('disabled') != lock){
        $("#evaluatorsSelect").prop('disabled', lock);
    }
    if ( $("#risksSelect").prop('disabled') != lock){
        $("#risksSelect").prop('disabled', lock);
    }
    if(!($("#progess_bar").is(":visible")) && lock){
        $("#progess_bar_anim").css('width', '0%').attr("aria-valuenow", '0')
        $("#progess_bar").show();
    }
    else if (!lock){
        $("#progess_bar_anim").css('width', '100%').attr("aria-valuenow", '100')
        $("#progess_bar").hide();
    }

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

function update_progress(progress, overall_progress){
    $("#progess_bar_anim").css('width', progress+'%').attr("aria-valuenow", progress)

    nb_progress = Number(overall_progress)

    if(isDefined(progressChart)){
        progressChart.data.datasets[0].data[0] = nb_progress;
        progressChart.data.datasets[0].data[1] = 100 - nb_progress;
        progressChart.update();
    }
}

function check_optimizer_state(reportTable){
    url = $("#strategyOptimizerInputs").attr(update_url_attr);
    $.get(url,function(data, status){
        var status = data["status"];
        var progress = data["progress"];
        var overall_progress = data["overall_progress"];
        if(status == "computing"){
            lock_inputs();
            update_progress(progress, overall_progress)
            first_refresh_state = status;
            if($("#report_datatable_card").is(":visible")){
                $("#report_datatable_card").hide();
            }
        }
        else{
            lock_inputs(false);
            if(status == "finished"){
                if(!$("#report_datatable_card").is(":visible")){
                    $("#report_datatable_card").show();
                }
                if(reportTable.rows().count() == 0){
                    reportTable.ajax.reload( null, false );
                }
                if(first_refresh_state != "" && first_refresh_state != "finished"){
                    create_alert("success", "Strategy optimized finished simulations.", "");
                    first_refresh_state="finished";
                }
            }
        }
        if(first_refresh_state == ""){
            first_refresh_state = status;
        }
    });
}

var iterationColumnsDef = [
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

var reportColumnsDef = [
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
var first_refresh_state = ""

var progressChart = new Chart($("#optimize_doughnutChart")[0].getContext('2d'), {
    type: 'doughnut',
    data: {
        labels: ["Done", "Remaining"],
        datasets: [
            {
                data: [0, 100],
                backgroundColor: ["#F7464A","#949FB1"],
                hoverBackgroundColor: ["#FF5A5E", "#A8B3C5"]
            }
        ]
    },
    options: {
        responsive: true
    }
});

$(document).ready(function() {

    check_disabled();

    $(".multi-select-element").select2({
        dropdownAutoWidth : true,
        multiple: true,
        closeOnSelect: false
    });
    $(".multi-select-element").on('change', function (e) {
        recompute_nb_iterations()
        check_disabled()
    });
    $("#startOptimizer").click(function(){
        start_optimizer($(this));
    });

    var reportTable = $("#report_datatable").DataTable({
        ajax: {
            "url": $("#report_datatable").attr(update_url_attr),
            "dataSrc": ""
        },
        deferRender: true,
        autoWidth: true,
        autoFill: true,
        columnDefs: reportColumnsDef
    })

    var iterationTable = $("#results_datatable").DataTable({
        ajax: {
            "url": $("#results_datatable").attr(update_url_attr),
            "dataSrc": ""
        },
        deferRender: true,
        autoWidth: true,
        autoFill: true,
        columnDefs: iterationColumnsDef
    })


    setInterval(function(){refresh_message_table(iterationTable,reportTable);}, 1500);
    function refresh_message_table(iterationTable, reportTable){
        iterationTable.ajax.reload( null, false );
        if(iterationTable.rows().count() > 0){
            $("#results_datatable_card").show();
        }
        check_optimizer_state(reportTable);
    }
});