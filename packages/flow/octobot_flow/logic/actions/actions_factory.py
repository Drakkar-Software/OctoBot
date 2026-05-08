import decimal
import enum
import json
import typing

import octobot_copy.entities as copy_entities
import octobot_flow.entities
import octobot_protocol.models as protocol_models


def _json_serialize_for_dsl(obj: typing.Any) -> typing.Any:
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def create_copy_exchange_account_action(
    strategy_id: str,
    reference_market: str,
    reference_account: protocol_models.CopiedAccount,
    account_copy_settings: typing.Optional[copy_entities.AccountCopySettings] = None,
) -> octobot_flow.entities.DSLScriptActionDetails:
    settings_dict = account_copy_settings.to_dict(include_default_values=False) if account_copy_settings else {}
    ref_json = reference_account.model_dump_json(exclude_defaults=True)
    settings_json = json.dumps(settings_dict, default=_json_serialize_for_dsl)
    dsl_script = (
        f"copy_exchange_account(strategy_id={json.dumps(strategy_id)}, reference_market='{reference_market}', "
        f"reference_account='{ref_json}', account_copy_settings='{settings_json}')"
    )
    return octobot_flow.entities.DSLScriptActionDetails(
        id="copy_exchange_account",
        dsl_script=dsl_script,
        resolved_dsl_script=dsl_script,
    )
