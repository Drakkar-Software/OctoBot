function setup_editable(){
    $.fn.editable.defaults.mode = 'inline';
}

function handle_editable(){
    $(".editable").each(function(){
        $(this).editable();
    });
}

function replace_break_line(str, replacement=""){
    return str.replace(/(?:\r\n|\r|\n)/g, replacement);
}

function replace_spaces(str, replacement=""){
    return str.replace(/ /g, replacement);
}

function get_selected_options(element){
    var selected_options = []
    element.find(":selected").each(function(){
        selected_options.push($(this).val())
    });
    return selected_options
}


// utility functions
function isDefined(thing){
    return (typeof thing !== typeof undefined && thing !== false)
}

function log(text){
    window.console&&console.log(text);
}