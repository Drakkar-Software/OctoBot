import octobot_commons.constants as commons_constants


def get_exchange_key(exchange_name: str, exchange_type: str, sandboxed: bool) -> str:
    return f"{exchange_name}_{exchange_type or commons_constants.CONFIG_EXCHANGE_SPOT}_{sandboxed}"
