function handleLogsExporter(){
    trigger_file_downloader_on_click($(".export-logs-button"));
}

function handleLogsSharer(){
    $(".share-logs-button").click(async function(){
        const button = $(this);
        const url = button.data("url");
        button.prop("disabled", true);
        const originalHtml = button.html();
        button.html('<i class="fas fa-spinner fa-spin"></i> <span class="d-none d-md-inline">Sharing...</span>');
        try {
            const data = await async_send_and_interpret_bot_update(null, url, null, "POST");
            if(data && data.success !== false){
                $("#share-logs-credentials").remove();
                const credentials = $(
                    '<div id="share-logs-credentials" class="alert alert-success mt-2 text-left">' +
                    '<strong>Logs shared successfully.</strong> Share these credentials with the OctoBot team:<br>' +
                    '<div class="mt-1"><strong>Error ID:</strong> <code>' + data.errorId + '</code></div>' +
                    '<div><strong>Error Secret:</strong> <code>' + data.errorSecret + '</code></div>' +
                    '</div>'
                );
                button.closest(".text-center").after(credentials);
            }else{
                create_alert("error", "Failed to share logs: " + (data && data.error || "unknown error"), "");
            }
        } catch(err) {
            create_alert("error", "Failed to share logs.", "");
        } finally {
            button.prop("disabled", false);
            button.html(originalHtml);
        }
    });
}

$(document).ready(function() {
    $('#logs_datatable').DataTable({
      // order by time: most recent first
      "order": [[ 0, "desc" ]]
    });
    $('#notifications_datatable').DataTable({
      // order by time: most recent first
      "order": [[ 0, "desc" ]]
    });
    handleLogsExporter();
    handleLogsSharer();
});
