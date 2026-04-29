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

$(document).ready(function() {
    const showModalIfNecessary = () => {
        $(".modal").each((_, element) => {
            const jqueryelement = $(element);
            if (jqueryelement.data("show-by-default") == "True") {
                jqueryelement.modal();
            }
        })
    }

    const handlePaymentWaiter = async () => {
        const waiterModal = $("#waiting-for-owned-packages-to-install-modal");
        if(waiterModal && waiterModal.data("show-by-default") == "True"){
            const url = waiterModal.data("url");
            let hasExtension = false;
            while (!hasExtension){
                const has_open_source_package_resp = await async_send_and_interpret_bot_update(null, url, null)
                if(has_open_source_package_resp.has_open_source_package){
                    hasExtension = true
                    document.location.href = window.location.href.replace("&loop=true", "").replace("?refresh_packages=true", "");
                } else {
                    await new Promise(r => setTimeout(r, 3000));
                }
            }
        }
    }

    const registerTriggerCheckout = () => {
        $("button[data-role=\"open-package-purchase\"]").click(() => {
            $("#select-payment-method-modal").modal();
        })
        $("button[data-role=\"restart\"]").click(() => {
            $("#select-payment-method-modal").modal();
        })
        $("button[data-role=\"open-checkout\"]").click(async (event) => {
            const button = $(event.currentTarget);
            const checkoutButtons = $("button[data-role=\"open-checkout\"]");
            const origin_val = button.text();
            const paymentMethod = button.data("payment-method")
            const url = button.data("checkout-api-url")
            const data = {
                paymentMethod: paymentMethod,
                redirectUrl: `${window.location.href}?refresh_packages=true&loop=true`
            }
            let fetchedCheckoutUrl = null;
            try {
                checkoutButtons.addClass("disabled");
                button.html("<i class='fa fa-circle-notch fa-spin'></i> Loading checkout");
                const checkoutUrl = await async_send_and_interpret_bot_update(data, url, null)
                if(checkoutUrl.url === null){
                    create_alert("success", "User already owns this extension", "");
                } else {
                    fetchedCheckoutUrl = checkoutUrl.url;
                    $("p[data-role=\"checkout-url-fallback-part\"]").removeClass("d-none");
                    const checkoutUrlFallbackLink = $("a[data-role=\"checkout-url-fallback\"]");
                    checkoutUrlFallbackLink.attr("href", fetchedCheckoutUrl);
                    checkoutUrlFallbackLink.text(fetchedCheckoutUrl);
                    document.location.href = fetchedCheckoutUrl;
                }
            } finally {
                if(fetchedCheckoutUrl === null){
                    checkoutButtons.removeClass("disabled");
                }
                button.html(origin_val);
            }
        })
    }

    showModalIfNecessary();
    registerTriggerCheckout();
    handlePaymentWaiter();
});