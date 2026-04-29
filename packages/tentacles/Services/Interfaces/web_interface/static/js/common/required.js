// Functions required in each page

$(document).ready(function() {
    const initTooltips = () => {
        $('[data-toggle="tooltip"]').tooltip();
    }

    const registerThemeSwitch = async () => {
        $("#theme-switch").click(async () => {
            const url = $("#theme-switch").data("update-url")
            const otherColorMode = $("html").data("mdb-theme") === "light" ? "dark" : "light"
            const data = {
                "color_mode": otherColorMode
            }
            await async_send_and_interpret_bot_update(data, url)
            location.reload();
        })
    }

    initTooltips();
    registerThemeSwitch();
});
