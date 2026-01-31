function displayFeedbackForm(formId, userId, updateUrl) {
    Tally.openPopup(
        formId,
        {
            hiddenFields: {
                userId: userId,
            },
            layout: "modal",
            hideTitle: true,
            width: 375,
            emoji: {
              text: "👋",
              animation: "wave"
            },
            autoClose: 0,
            onSubmit: (payload) => {
                const filedFormDetails = {
                    form_id: formId,
                    user_id: userId,
                }
                send_and_interpret_bot_update(filedFormDetails, updateUrl, null, generic_request_success_callback)
            },
        }
    );
}
