
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
    dataFilesTable.rows(
        function ( idx, data, node ) {
            return $(node).find("input[type='checkbox']:checked").length > 0 ? true : false;
        }
    ).eq(0).each(function( index ) {
        selected_modules.push(dataFilesTable.row( index ).data()[1]);
    });
    return selected_modules
}

function lock_interface(lock=true){
    var should_lock = lock;
    if(!should_lock){
        should_lock = get_selected_files() <= 0;
    }
    $('#startBacktesting').prop('disabled', should_lock);
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
        $("#maProf").html(data["bot_report"]["market_average_profitability"]);
        var symbol_reports = []
        $.each( data["symbol_report"], function( index, value ) {
            $.each( value, function( symbol, profitability ) {
                symbol_reports.push(symbol+": "+profitability);
            });
        });
        $("#sProf").html(symbol_reports.join(", "));
        $("#refM").html(data["bot_report"]["reference_market"]);
        var portfolio_reports = []
            $.each( data["bot_report"]["end_portfolio"], function( symbol, holdings ) {
                portfolio_reports.push(symbol+": "+holdings["total"]);
            });
        $("#ePort").html(portfolio_reports.join(", "));
    });
}

function update_progress(progress){
    $("#progess_bar_anim").css('width', progress+'%').attr("aria-valuenow", progress)
}

function check_backtesting_state(){
    url = $("#backtestingPage").attr(update_url_attr);
    $.get(url,function(data, status){
        var status = data["status"];
        var progress = data["progress"]
        if(status == "computing"){
            $("#backtesting_progress_bar").show();
            update_progress(progress);
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
    $(".selectable_datafile").unbind('click');
    $('.selectable_datafile').click(function () {
        row = $(this)
        if (row.hasClass(selected_item_class)){
            row.removeClass(selected_item_class);
            row.find(".dataFileCheckbox").prop('checked', false);
        }else{
            row.toggleClass(selected_item_class);
            var checkbox = row.find(".dataFileCheckbox");
            var symbol = checkbox.attr("symbol");
            var data_file = checkbox.attr("data-file");
            checkbox.prop('checked', true);
            // uncheck same symbols from other rows if any
            $("#dataFilesTable").find("input[type='checkbox']:checked").each(function(){
                if($(this).attr("symbol") == symbol && !($(this).attr("data-file") == data_file)){
                    $(this).parent().parent().removeClass(selected_item_class);
                    $(this).prop('checked', false);
                }
            });
        }
        lock_interface(false);
    });
}

var first_refresh_state = "";

var dataFilesTable = $('#dataFilesTable').DataTable();

$(document).ready(function() {
    handle_backtesting_buttons();
    handle_file_selection();
    $('#dataFilesTable').on("draw.dt", function(){
        handle_file_selection();
    });
    lock_interface();

    setInterval(function(){refresh_status();}, 1000);
    function refresh_status(){
        check_backtesting_state();
    }
});
