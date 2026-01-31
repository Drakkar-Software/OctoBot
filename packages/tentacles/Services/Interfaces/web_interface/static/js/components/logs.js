function handleLogsExporter(){
    trigger_file_downloader_on_click($(".export-logs-button"));
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
});