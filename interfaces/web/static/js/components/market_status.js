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
    $('#open_order_datatable').DataTable();
});
