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
        $("#progess_bar").show();
    }
    else if (!lock){
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



function check_optimizer_state(){
    url = $("#strategyOptimizerInputs").attr(update_url_attr);
    $.get(url,function(data, status){
        if(data == "computing"){
            lock_inputs();
            first_refresh_state = data;
        }
        else{
            lock_inputs(false);
            if(data == "finished" && first_refresh_state != "" && first_refresh_state != "finished"){
                create_alert("success", "Strategy optimized finished simulations.", "");
                first_refresh_state="finished";
            }
        }
        if(first_refresh_state == ""){
            first_refresh_state = data;
        }
    });
}

var columnsDef = [
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
        "title": "Evaluators",
        "targets": 1,
        "data": "evaluators",
        "name": "evaluators",
        "render": function(data, type, row, meta){
            return data;
        }
    },
    {
        "title": "Time Frames",
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
        "title": "Score",
        "targets": 4,
        "data": "score",
        "name": "score",
        "render": function(data, type, row, meta){
            return data;
        }
    },
    {
        "title": "Average trades count",
        "targets": 5,
        "data": "average_trades",
        "name": "average_trades",
        "render": function(data, type, row, meta){
            return data;
        }
    }
];

var first_refresh_state = ""

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

    var table = $("#results_datatable").DataTable({
        ajax: {
            "url": $("#results_datatable").attr(update_url_attr),
            "dataSrc": ""
        },
        deferRender: true,
        autoWidth: true,
        autoFill: true,
        columnDefs: columnsDef
    })


    setInterval(function(){refresh_message_table(table);}, 500);
    function refresh_message_table(table){
        table.ajax.reload( null, false );
        if(table.rows().count() > 0){
            $("#results_datatable_card").show();
        }
        check_optimizer_state();
    }
});