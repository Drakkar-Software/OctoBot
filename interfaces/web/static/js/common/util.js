function setup_editable(){
    $.fn.editable.defaults.mode = 'inline';
}

function handle_editable(){
    $(".editable").each(function(){
        $(this).editable();
    });
}