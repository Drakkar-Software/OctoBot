// Functions required in each page

const onPageLoad = () => {
    // should be run before document is ready
    const updateStartupMessages = () => {
        if(!isMobileDisplay()){
            $("#startup-messages-collapse-control").attr("aria-expanded", "true");
            $("#startup-messages-collapse").addClass("show");
        }
    }
    updateStartupMessages();
}
onPageLoad();
