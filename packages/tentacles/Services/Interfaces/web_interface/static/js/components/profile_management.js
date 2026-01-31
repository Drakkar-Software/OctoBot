function handleProfileActivator(){
    const profileActivatorButton = $(".activate-profile-button");
    if (profileActivatorButton.length){
        profileActivatorButton.click(function (){
            const changeProfileURL = $(this).attr("data-url");
            window.location.replace(changeProfileURL);
        });
    }
}

function onProfileEdit(isEditing, profileSave){
    // disable global save config button to avoid save buttons confusion
    $("#save-config").attr("disabled", isEditing);
    profileSave.attr("disabled", !isEditing);
}

function handleProfileEditor(){
    const saveProfile = $(".save-profile");
    const profileName = $('.profile-name-editor');
    const profileDescription = $('.profile-description-editor');
    const profileComplexity = $('.profile-complexity-selector');
    const profileRisk = $('.profile-risk-selector');
    profileName.on('save', function (){
        onProfileEdit(true, $(this).parents(".profile-details").find(".save-profile"));
    });
    profileDescription.on('save', function (){
        onProfileEdit(true, $(this).parents(".profile-details").find(".save-profile"));
    });
    profileComplexity.on('change', function (){
        onProfileEdit(true, $(this).parents(".profile-details").find(".save-profile"));
    });
    profileRisk.on('change', function (){
        onProfileEdit(true, $(this).parents(".profile-details").find(".save-profile"));
    });
    saveProfile.click(function (){
        onProfileEdit(false, $(this));
        $(this).tooltip("hide");
        const updateURL = $(this).attr("data-url");
        const profileDetails = $(this).parents(".profile-details");
        const data = {
            id: profileDetails.attr("data-id"),
            name: profileDetails.find(".profile-name-editor").editable("getValue", true),
            description: profileDetails.find(".profile-description-editor").editable("getValue", true),
            complexity: profileDetails.find(".profile-complexity-selector").val(),
            risk: profileDetails.find(".profile-risk-selector").val(),
        };
        send_and_interpret_bot_update(data, updateURL, null,
            saveCurrentProfileSuccessCallback, saveCurrentProfileFailureCallback);
    });
}

function saveCurrentProfileSuccessCallback(updated_data, update_url, dom_root_element, msg, status){
    create_alert("success", "Profile updated");
    $("[data-role=profile-name]").each(function (){
        const profileIdAttr = $(this).attr("data-profile-id");
        if(typeof profileIdAttr === "undefined" || profileIdAttr === updated_data["id"]){
            $(this).html(updated_data["name"]);
        }
    });
}


function saveCurrentProfileFailureCallback(updated_data, update_url, dom_root_element, msg, status) {
    $("#save-current-profile").attr("disabled", false);
    create_alert("error", msg.responseText, "");
}

function handleProfileCreator(){
    const createButton = $(".duplicate-profile");
    if(createButton.length){
        createButton.click(function (){
            send_and_interpret_bot_update({}, $(this).attr("data-url"), null,
                profileActionSuccessCallback, profileActionFailureCallback);
        });
    }
}

function profileActionSuccessCallback(updated_data, update_url, dom_root_element, msg, status){
    location.reload();
}


function profileActionFailureCallback(updated_data, update_url, dom_root_element, msg, status) {
    create_alert("error", msg.responseText, "");
}

function handleProfileImporter(){
    const importForm = $(".profile-import-form");
    const importButton = $(".import-profile-button");
    const profileInput = $(".profile-input");
    if(importForm.length && importButton.length && profileInput.length){
        importButton.click(function () {
            $(this).siblings(".profile-import-form").find(".profile-input").click();
        });
        profileInput.on("change", function () {
            $(this).parents(".profile-import-form").submit();
        });
    }
}

function handleProfileDownloader(){
    const downloadForm = $(".profile-download-form");
    const importButton = downloadForm.find('button[data-role="download-profile-button"]');
    const profileInput = $("#inputProfileLink");
    if(importButton.length && profileInput.length){
        importButton.click(function () {
            if($("#inputProfileLink").val()){
                $(this).parents(".profile-download-form").submit();
            }
        });
    }
}

function handleProfileExporter(){
    trigger_file_downloader_on_click($(".export-profile-button"));
}

function selectCurrentProfile(profileNameDisplay){
    $("#profilesSubmenu").collapse("show");
    const profileId = profileNameDisplay.attr("data-profile-id");
    activate_tab($(`#profile-${profileId}-tab`));
}

function handleProfileSelector(){
    const profileNameDisplay = $("a[data-role=current-profile-selector]");
    profileNameDisplay.click(function (){
        selectCurrentProfile(profileNameDisplay);
    });
    $("[data-role=current-profile-selector]").click(function (){
        selectCurrentProfile(profileNameDisplay);
    });
}

function handleProfileRemover(){
    const removeProfileButton = $(".remove-profile-button");
    if(removeProfileButton.length){
        removeProfileButton.click(function (){
            if (confirm("Delete this profile ?")) {
                const data = {id: $(this).attr("data-profile-id")};
                send_and_interpret_bot_update(data, $(this).attr("data-url"), null,
                    profileActionSuccessCallback, profileActionFailureCallback);
            }
        });
    }
}

$(document).ready(function() {
    handleProfileActivator();
    handleProfileSelector();
    handleProfileEditor();
    handleProfileCreator();
    handleProfileImporter();
    handleProfileDownloader();
    handleProfileExporter();
    handleProfileRemover();
});
