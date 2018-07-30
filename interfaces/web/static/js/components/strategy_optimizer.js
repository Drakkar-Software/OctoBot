function recompute_nb_iterations(){
    var nb_selected = 0;
    nb_selected = $("#risksSelect").find(":selected").length*Math.pow($("#timeFramesSelect").find(":selected").length, 2)*Math.pow($("#evaluatorsSelect").find(":selected").length,2);
    $("#numberOfSimulatons").text(nb_selected);
}

$(document).ready(function() {
    $(".multi-select-element").select2({
        dropdownAutoWidth : true,
        multiple: true,
        closeOnSelect: false
    });
    $(".multi-select-element").on('change', function (e) {
        recompute_nb_iterations()
    });
});