/*
 * Drakkar-Software OctoBot
 * Copyright (c) Drakkar-Software, All rights reserved.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3.0 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.
 */


const showVerifCodeError = (errorDetails) => {
    $("[data-role='verification-code-waiter']").addClass(hidden_class)
    $("[data-role='verification-code-received']").addClass(hidden_class)
    $("[data-role='verification-code-error']").removeClass(hidden_class)
    $("#verification-code-error-content").text(errorDetails)
}
const showVerifCodeWaiter = () => {
    $("[data-role='verification-code-waiter']").removeClass(hidden_class)
    $("[data-role='verification-code-received']").addClass(hidden_class)
    $("[data-role='verification-code-error']").addClass(hidden_class)
}
const showVerifCodeReceived = (confirmEmailContent) => {
    $("[data-role='verification-code-waiter']").addClass(hidden_class)
    $("[data-role='verification-code-received']").removeClass(hidden_class)
    $("#verification-code-received-content").text(confirmEmailContent)
    $("[data-role='verification-code-error']").addClass(hidden_class)
}


const triggerEmailConfirmWaiter = async () => {
    const stepperElement = $("#config-stepper");
    try {
        await async_send_and_interpret_bot_update(null, stepperElement.data("trigger-verif-code-waiter"), null, "POST", true)
        let confirmEmailContent = null;
        const timeout = 5 * 60 * 1000;
        const t0 = new Date().getTime();
        while (confirmEmailContent === null) {
            if (new Date().getTime() - t0 > timeout){
                showVerifCodeError("");
            } else {
                showVerifCodeWaiter();
            }
            confirmEmailContent = await async_send_and_interpret_bot_update(null, stepperElement.data("get-verif-code-content"), null, "GET", true)
            await sleep(2000)
        }
        if (confirmEmailContent === null) {
            // error: email was not received within given time
            showVerifCodeError();
        }
        else {
            showVerifCodeReceived(confirmEmailContent);
        }
    } catch(error) {
        showVerifCodeError(error.responseText)
    }

}