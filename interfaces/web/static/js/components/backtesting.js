
function start_backtesting(){
    $("#backtesting_progress_bar").show();
    lock_interface();
    var request = get_selected_files()
    var update_url = $("#startBacktesting").attr("start-url");
    send_and_interpret_bot_update(request, update_url, null, start_success_callback, start_error_callback)
}

function start_success_callback(updated_data, update_url, dom_root_element, msg, status){
    $("#progess_bar_anim").css('width', 0+'%').attr("aria-valuenow", 0)
    create_alert("success", msg, "");
}

function start_error_callback(updated_data, update_url, dom_root_element, result, status, error){
    create_alert("error", result.responseText, "");
    $("#backtesting_progress_bar").hide();
    lock_interface(false);
}

function get_selected_files(){
    var selected_modules = []
    $("#dataFilesTable").find("input[type='checkbox']:checked").each(function(){
        selected_modules.push($(this).attr("data-file"));
    });
    return selected_modules
}

function lock_interface(lock=true){
    $('#startBacktesting').prop('disabled', get_selected_files() <= 0);
}

function handle_backtesting_buttons(){
    $("#startBacktesting").click(function(){
        start_backtesting();
    });
}

function load_report(){
    url = $("#backtestingReport").attr(update_url_attr);
    $.get(url,function(data, status){
        $("#bProf").html(data["bot_report"]["profitability"]);
        $("#mProf").html(JSON.stringify(data["symbol_report"][0]));
        $("#maProf").html(data["bot_report"]["market_average_profitability"]);
        $("#refM").html(data["bot_report"]["reference_market"]);
        $("#ePort").html(JSON.stringify(data["bot_report"]["end_portfolio"]));
    });
}

function check_backtesting_state(){
    url = $("#backtestingPage").attr(update_url_attr);
    $.get(url,function(data, status){
        var status = data["status"];
        var progress = data["progress"]
        if(status == "computing"){
            $("#backtesting_progress_bar").show();
            $("#progess_bar_anim").css('width', progress+'%').attr("aria-valuenow", progress)
            first_refresh_state = status;
            if($("#backtestingReport").is(":visible")){
                $("#backtestingReport").hide();
            }
        }
        else{
            lock_interface(false);
            $("#backtesting_progress_bar").hide();
            if(status == "finished"){
                if(!$("#backtestingReport").is(":visible")){
                    $("#backtestingReport").show();
                    load_report();
                }
                if(first_refresh_state != "" && first_refresh_state != "finished"){
                    create_alert("success", "Backtesting finished.", "");
                    first_refresh_state="finished";
                }
            }
        }
        if(first_refresh_state == ""){
            first_refresh_state = status;
        }
    });
}

function handle_file_selection(){
    $('.selectable_datafile').click(function () {
        // use parent not to trigger selection on button column use
        row = $(this)
        if (row.hasClass(selected_item_class)){
            row.removeClass(selected_item_class);
            row.find(".dataFileCheckbox").prop('checked', false);
        }else{
            row.toggleClass(selected_item_class);
            row.find(".dataFileCheckbox").prop('checked', true);
        }
        lock_interface();
    });
}

var first_refresh_state = ""

$(document).ready(function() {
    handle_backtesting_buttons();
    handle_file_selection();
    lock_interface();

    var table = $('#dataFilesTable').DataTable()

    setInterval(function(){refresh_status();}, 1000);
    function refresh_status(){
        check_backtesting_state();
    }
});
