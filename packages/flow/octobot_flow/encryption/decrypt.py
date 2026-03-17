import contextlib

import octobot_flow.entities
import octobot_trading.exchanges.util.exchange_data as exchange_data_import


@contextlib.contextmanager
def decrypted_bots_configurations(
    automation_state: octobot_flow.entities.AutomationState
):
    try:
        if automation_state.exchange_account_details:
            _decrypt_exchange_credentials(automation_state.exchange_account_details.auth_details)
        yield automation_state
    finally:
        if automation_state.exchange_account_details:
            _clear_decrypted_exchange_credentials(automation_state.exchange_account_details.exchange_details)


def _decrypt_exchange_credentials(
    auth_details: exchange_data_import.ExchangeAuthDetails
):  # pylint: disable=undefined-variable
    if auth_details.encrypted:
        raise NotImplementedError("_decrypt_exchange_credentials not implemented")
        # todo
        message = pgpy.PGPMessage.from_blob(base64.b64decode(auth_details.encrypted))
        decrypted = json.loads(message.decrypt(api_key).message)
        auth_details.api_key = decrypted.get("apiKey", "")
        auth_details.api_secret = decrypted.get("apiSecret", "")
        auth_details.api_password = decrypted.get("password", "")
        auth_details.access_token = decrypted.get("accessToken", "")
    

def _clear_decrypted_exchange_credentials(
    auth_details: exchange_data_import.ExchangeAuthDetails
):
    auth_details.api_key = ""
    auth_details.api_secret = ""
    auth_details.api_password = ""
    auth_details.access_token = ""
