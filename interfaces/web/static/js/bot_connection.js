function get_update(){
    $.ajax({
      url: "/update",
    }).done(function(data) {
        unlock_ui();

    }).fail(function(data) {
        lock_ui();

    }).always(function(data) {
        manage_alert(data);
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
    icon_status = $("#navbar-bot-status")
    icon_reboot = $("#navbar-bot-reboot")

    // if refreshed page
    if (icon_status.hasClass("fa-spinner")){
        icon_status.removeClass("fa-spinner fa-spin")
    }

    // create alert if required
    if (status && icon_status.hasClass("icon-red")){
        create_alert("success", "Connected with Octobot", "");
    }else if(!status && icon_status.hasClass("icon-green")){
        create_alert("danger", "Connection lost with Octobot", "<br>Reconnecting...");
    }

    // update central status
    if (status){
        icon_status.removeClass("fa-times-circle icon-red");
        icon_status.addClass("fa-check-circle icon-green");
    }else{
        icon_status.removeClass("fa-check-circle icon-green");
        icon_status.addClass("fa-times-circle icon-red");
    }

    // update reboot status
    if (status){
        icon_reboot.removeClass("fa-spin");
    }else{
        icon_reboot.addClass("fa-spin");
    }
}

function manage_alert(raw_data){
    data = JSON.parse(raw_data)
    $.each(data, function(i, item) {
        create_alert(data[i].Level, data[i].Title, data[i].Message);
    })
}

function create_alert(a_level, a_title, a_msg, url="_blank"){
    $.notify({
        title: a_title,
        message: a_msg
    },{
        element: "body",
	    position: null,
        type: a_level,
        allow_dismiss: true,
	    newest_on_top: true,
	    placement: {
            from: "top",
            align: "right"
	    },
	    showProgressbar: false,
	    offset: 20,
        spacing: 10,
        z_index: 1031,
        url_target: url,
	    delay: 5000,
	    timer: 1000,
	    animate: {
            enter: "animated fadeInDown",
            exit: "animated fadeOutUp"
	    }
    });
}

// Updater
$(document).ready(function () {
    setInterval(function(){ get_update(); }, 500);
});