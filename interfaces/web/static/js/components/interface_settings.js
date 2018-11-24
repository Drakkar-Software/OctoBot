function addOrRemoveWatchedSymbol(event){
    const sourceElement = $(event.target);
    const symbol = sourceElement.attr("symbol");
    let action = "add";
    if(sourceElement.hasClass("fas")){
        action = "remove";
    }
    const request = {};
    request["action"]=action;
    request["symbol"]=symbol;
    const update_url = sourceElement.attr("update_url");
    send_and_interpret_bot_update(request, update_url, sourceElement, watched_symbols_success_callback, watched_symbols_error_callback)
}

function watched_symbols_success_callback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", msg, "");
    if(updated_data["action"] === "add"){
        dom_root_element.removeClass("far");
        dom_root_element.addClass("fas");
    }else{
        dom_root_element.removeClass("fas");
        dom_root_element.addClass("far");
    }
}

function watched_symbols_error_callback(updated_data, update_url, dom_root_element, result, status, error){
    create_alert("error", result.responseText, "");
}

function update_pairs_colors(){
    $(".pair_status_card").each(function () {
        const first_eval = $(this).find(".status");
        const status = first_eval.attr("status");
        if(status === "LONG"){
            $(this).addClass("card-long");
        }else if(status === "SHORT"){
            $(this).addClass("card-short");
        }
    })
}

$(document).ready(function() {
    update_pairs_colors();
    $(".watched_element").each(function () {
        $(this).click(addOrRemoveWatchedSymbol);
    })
});
