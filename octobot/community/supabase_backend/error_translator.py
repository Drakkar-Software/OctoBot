#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.


EMAIL_NOT_CONFIRMED_ERROR = "email_not_confirmed"

AUTH_ERROR_TRANSLATIONS = {
    "generic-error": "Something went wrong. Please try again later.",
    "anonymous_provider_disabled": "You cannot sign in anonymously because this option is disabled.",
    "bad_code_verifier": "An error occurred during code verification. Please try again or contact support.",
    "bad_json": "The request sent is incorrect. Please try again or contact support.",
    "bad_jwt": "Your session is not valid. Please sign in again.",
    "bad_oauth_callback": "A problem occurred with the login provider. Please try again or contact support.",
    "bad_oauth_state": "The login via the provider failed. Please try again or contact support.",
    "captcha_failed": "CAPTCHA verification failed. Please try again.",
    "conflict": "An error occurred due to simultaneous actions. Please try again later.",
    "email_address_invalid": "Your email address is not valid. Please use a different address.",
    "email_address_not_authorized": "You cannot send emails to this address. Contact the administrator to set up a custom email service.",
    "email_conflict_identity_not_deletable": "You cannot delete this identity as it would cause a conflict with another email address. Contact support to merge your accounts.",
    "email_exists": "This email address is already in use. Please choose another or sign in.",
    EMAIL_NOT_CONFIRMED_ERROR: "You must confirm your email address before signing in. Check your inbox.",
    "email_provider_disabled": "Sign-up with email and password is disabled. Use another sign-in method.",
    "flow_state_expired": "Your session has expired. Please sign in again.",
    "flow_state_not_found": "Your session no longer exists. Please sign in again.",
    "hook_payload_invalid_content_type": "A technical error occurred. Please try again or contact support.",
    "hook_payload_over_size_limit": "The data sent is too large. Please try again or contact support.",
    "hook_timeout": "The request took too long. Please try again.",
    "hook_timeout_after_retry": "Unable to process the request after multiple attempts. Please try again later.",
    "identity_already_exists": "This identity is already associated with an account. Please use a different identity.",
    "identity_not_found": "The requested identity does not exist. Please check your information.",
    "insufficient_aal": "You must enable two-factor authentication (MFA) to continue. Follow the instructions to set up MFA.",
    "invite_not_found": "Your invitation has expired or has already been used. Request a new invitation.",
    "invalid_credentials": "Your login credentials are incorrect. Please check and try again.",
    "manual_linking_disabled": "Manual account linking is disabled. Contact support for assistance.",
    "mfa_challenge_expired": "Your MFA challenge has expired. Please request a new challenge.",
    "mfa_factor_name_conflict": "You cannot use the same name for multiple MFA factors. Choose a different name.",
    "mfa_factor_not_found": "The requested MFA factor no longer exists. Please set up a new one.",
    "mfa_ip_address_mismatch": "The IP address changed during MFA setup. Please start over.",
    "mfa_phone_enroll_not_enabled": "Phone authentication enrollment is disabled. Choose another MFA method.",
    "mfa_phone_verify_not_enabled": "Phone verification is disabled. Use another sign-in method.",
    "mfa_totp_enroll_not_enabled": "TOTP authentication enrollment is disabled. Choose another MFA method.",
    "mfa_totp_verify_not_enabled": "TOTP verification is disabled. Use another sign-in method.",
    "mfa_verification_failed": "The TOTP code entered is incorrect. Please try again.",
    "mfa_verification_rejected": "Your MFA verification attempt was rejected. Please try again or contact support.",
    "mfa_verified_factor_exists": "A verified phone number is already associated with your account. Remove it to add a new one.",
    "mfa_web_authn_enroll_not_enabled": "WebAuthn authentication enrollment is disabled. Choose another MFA method.",
    "mfa_web_authn_verify_not_enabled": "WebAuthn verification is disabled. Use another sign-in method.",
    "no_authorization": "You must be authenticated to perform this action. Please sign in.",
    "not_admin": "You do not have the necessary permissions for this action. Contact an administrator.",
    "oauth_provider_not_supported": "This login provider is not available. Choose another sign-in method.",
    "otp_disabled": "Sign-in with magic link or email code is disabled. Use another method.",
    "otp_expired": "Your sign-in code has expired. Please request a new code.",
    "over_email_send_rate_limit": "Too many emails have been sent to your address. Please wait a few minutes before trying again.",
    "over_request_rate_limit": "You have sent too many requests. Please wait a few minutes before trying again.",
    "over_sms_send_rate_limit": "Too many SMS have been sent to your number. Please wait a few minutes before trying again.",
    "phone_exists": "This phone number is already in use. Please choose another or sign in.",
    "phone_not_confirmed": "You must confirm your phone number before signing in. Check your messages.",
    "phone_provider_disabled": "Sign-up with phone and password is disabled. Use another sign-in method.",
    "provider_disabled": "This login provider is disabled. Choose another method.",
    "provider_email_needs_verification": "You must verify your email address. A verification email has been sent to you.",
    "reauthentication_needed": "You must reauthenticate to change your password. Please confirm your identity.",
    "reauthentication_not_valid": "The reauthentication code is incorrect. Please enter a new code.",
    "refresh_token_not_found": "Your session no longer exists. Please sign in again.",
    "refresh_token_already_used": "Your session has been revoked. Please sign in again.",
    "request_timeout": "The request took too long. Please try again.",
    "same_password": "Your new password must be different from the current one. Choose another password.",
    "session_expired": "Your session has expired. Please sign in again.",
    "session_not_found": "Your session no longer exists. Please sign in again.",
    "signup_disabled": "New sign-ups are disabled. Contact the administrator for more information.",
    "single_identity_not_deletable": "You cannot delete your only identity. Add another identity before deleting this one.",
    "sms_send_failed": "SMS sending failed. Please try again or contact support.",
    "too_many_enrolled_mfa_factors": "You have reached the maximum number of MFA factors. Remove an existing factor to add a new one.",
    "unexpected_audience": "A technical error occurred. Please try again or contact support.",
    "unexpected_failure": "An unexpected error occurred. Please try again or contact support.",
    "user_already_exists": "This email address is already associated with an account. Please sign in to continue.",
    "user_banned": "Your account is temporarily banned. Please wait or contact support.",
    "user_not_found": "Your account no longer exists. Please create a new account.",
    "validation_failed": "The provided information is incorrect. Please check and try again.",
    "weak_password": "Your password is too weak. Use a stronger password with more characters, numbers, and symbols."
  }


def translate_error_code(error_code: str):
    try:
        return AUTH_ERROR_TRANSLATIONS[error_code]
    except KeyError:
        if error_code is None:
            return "No error code"
        return f"Unknown error code: {error_code}"
