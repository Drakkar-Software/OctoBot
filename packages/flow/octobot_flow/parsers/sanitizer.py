import decimal
import typing

import octobot_commons.signals as commons_signals
import octobot_commons.enums as common_enums
import octobot_commons.dataclasses as commons_dataclasses


def _get_sanitized_value(value):
    if isinstance(value, (list, dict)):
        return sanitize(value)
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, commons_signals.SignalBundle):
        return {common_enums.CommunityFeedAttrs.VALUE.value: sanitize(value.to_dict())}
    return value


def sanitize(values: typing.Any) -> typing.Any:
    if isinstance(values, (list, tuple)):
        return type(values)(
            sanitize(val)
            for val in values
        )
    elif isinstance(values, dict):
        for key, val in values.items():
            values[key] = _get_sanitized_value(val)
    elif isinstance(values, commons_dataclasses.FlexibleDataclass):
        for field in values.get_field_names():
            setattr(values, field, sanitize(getattr(values, field)))
    return values
