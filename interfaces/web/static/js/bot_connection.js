function get_update(){
    $.ajax({
      url: "/update",
    }).done(function() {
        unlock_ui();
        console.log("success");

    }).fail(function() {
        lock_ui();

    }).always(function() {
        console.log("updated");
  });
}

function lock_ui(){
    $(".nav-link").addClass("disabled");
    update_status(false);
}

function unlock_ui(){
    $(".nav-link").removeClass("disabled");
    update_status(true);
}

function update_status(status){
    // update central status
    icon_status = $("#navbar-bot-status")
    if (status){
        icon_status.removeClass("fa-times-circle icon-red");
        icon_status.addClass("fa-check-circle icon-green");
    }else{
        icon_status.removeClass("fa-check-circle icon-green");
        icon_status.addClass("fa-times-circle icon-red");
    }

    // update reboot status
    icon_reboot = $("#navbar-bot-reboot")
    if (status){
        icon_reboot.removeClass("fa-spin");
    }else{
        icon_reboot.addClass("fa-spin");
    }
}

// Updater
$(document).ready(function () {
    setInterval(function(){ get_update(); }, 1000);
});