#  Drakkar-Software OctoBot-Sync
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import json
import typing

import octobot_commons.logging as commons_logging

import octobot_sync.sync.collection_backend.state_model as state_model


logger = commons_logging.get_logger("TolerantStateLoading")

ModelSanitizer = typing.Callable[[dict[str, typing.Any]], dict[str, typing.Any]]
ModelFallback = typing.Callable[[], typing.Any]


class TolerantStateLoader:
    """
    Lenient parser for encrypted collection state payloads.

    Parses list items individually (skipping invalid entries), sanitizes dicts
    using optional per-model hooks, and can rebuild pydantic models via
    ``model_validate`` when ``from_dict`` fails on nested fields.
    """

    def __init__(
        self,
        state_class: typing.Optional[type[state_model.StateModel]] = None,
        *,
        collection: str,
        model_sanitizers: typing.Optional[dict[type, ModelSanitizer]] = None,
        model_fallbacks: typing.Optional[dict[type, ModelFallback]] = None,
    ) -> None:
        self.state_class = state_class
        self.collection = collection
        self.model_sanitizers = model_sanitizers or {}
        self.model_fallbacks = model_fallbacks or {}

    def from_json(self, json_str: str) -> state_model.StateModel:
        if self.state_class is None:
            raise ValueError("state_class is required for from_json")
        raw_state = json.loads(json_str)
        parsed_state = self.from_dict(raw_state)
        if parsed_state is None:
            raise ValueError(
                f"Decrypted {self.collection} payload did not produce a state model"
            )
        return parsed_state

    def from_dict(
        self,
        raw_dict: typing.Any,
    ) -> typing.Optional[state_model.StateModel]:
        if self.state_class is None:
            raise ValueError("state_class is required for from_dict")
        if raw_dict is None:
            return None
        if not isinstance(raw_dict, dict):
            return _parse_model_strict(self.state_class, raw_dict)

        parsed_state_dict = dict(raw_dict)
        list_item_types_by_field = _list_field_item_types(self.state_class)
        for field_name, item_model_class in list_item_types_by_field.items():
            raw_items = parsed_state_dict.get(field_name)
            if not isinstance(raw_items, list):
                continue
            lenient_items = []
            for raw_item in raw_items:
                parsed_item = self.model_from_dict_lenient(
                    item_model_class,
                    raw_item,
                    context=f"{self.collection}.{field_name}",
                    allow_skip=True,
                )
                if parsed_item is not None:
                    lenient_items.append(parsed_item)
            parsed_state_dict[field_name] = lenient_items

        try:
            return _parse_model_strict(self.state_class, parsed_state_dict)
        except Exception as strict_error:
            sanitized_state_dict = self.sanitize_model_dict(
                self.state_class,
                parsed_state_dict,
            )
            try:
                return _parse_model_strict(self.state_class, sanitized_state_dict)
            except Exception as retry_error:
                raise retry_error from strict_error

    def model_from_dict_lenient(
        self,
        model_class: type,
        raw_dict: typing.Any,
        *,
        context: str,
        allow_skip: bool,
    ) -> typing.Any | None:
        if not isinstance(raw_dict, dict):
            if allow_skip:
                logger.warning(
                    "Skipping %s item in %s: expected dict, got %s",
                    model_class.__name__,
                    context,
                    type(raw_dict).__name__,
                )
                return None
            raise ValueError(
                f"Expected dict for {model_class.__name__} in {context}, "
                f"got {type(raw_dict).__name__}"
            )

        item_identifier = raw_dict.get("id")
        try:
            return _parse_model_strict(model_class, raw_dict)
        except Exception as strict_error:
            sanitized_dict = self.sanitize_model_dict(model_class, raw_dict)
            try:
                return _parse_model_strict(model_class, sanitized_dict)
            except Exception as retry_error:
                try:
                    return self._rebuild_model_from_sanitized_dict(
                        model_class,
                        sanitized_dict,
                        context=context,
                    )
                except Exception as rebuild_error:
                    retry_error = rebuild_error
                fallback_factory = self.model_fallbacks.get(model_class)
                if fallback_factory is not None:
                    logger.warning(
                        "Using fallback %s for item id=%r in %s after parse failure: %s",
                        model_class.__name__,
                        item_identifier,
                        context,
                        retry_error,
                    )
                    return fallback_factory()
                if allow_skip:
                    logger.warning(
                        "Skipping invalid %s item id=%r in %s after parse failure: %s",
                        model_class.__name__,
                        item_identifier,
                        context,
                        retry_error,
                    )
                    return None
                raise retry_error from strict_error

    def sanitize_model_dict(
        self,
        model_class: type,
        raw_dict: dict[str, typing.Any],
    ) -> dict[str, typing.Any]:
        model_sanitizer = self.model_sanitizers.get(model_class)
        sanitized_dict = (
            model_sanitizer(raw_dict) if model_sanitizer is not None else dict(raw_dict)
        )
        if not hasattr(model_class, "model_fields"):
            return sanitized_dict

        json_schema = model_class.model_json_schema()
        sanitized_dict = _strip_invalid_values_from_schema(sanitized_dict, json_schema)

        for field_name, field_info in model_class.model_fields.items():
            if field_name not in sanitized_dict:
                continue
            field_value = sanitized_dict[field_name]
            if not isinstance(field_value, dict):
                continue
            nested_model_class = _annotation_to_model_class(field_info.annotation)
            if nested_model_class is None:
                continue
            sanitized_dict[field_name] = self.sanitize_model_dict(
                nested_model_class,
                field_value,
            )

        return sanitized_dict

    def _rebuild_model_from_sanitized_dict(
        self,
        model_class: type,
        sanitized_dict: dict[str, typing.Any],
        *,
        context: str,
    ) -> typing.Any:
        if not hasattr(model_class, "model_fields"):
            raise ValueError(
                f"Cannot rebuild {model_class.__name__} from dict: not a pydantic model"
            )

        field_values: dict[str, typing.Any] = {}
        for field_name, field_info in model_class.model_fields.items():
            raw_value = sanitized_dict.get(field_name)
            nested_model_class = _annotation_to_model_class(field_info.annotation)
            if isinstance(raw_value, dict) and nested_model_class is not None:
                parsed_nested = self.model_from_dict_lenient(
                    nested_model_class,
                    raw_value,
                    context=f"{context}.{field_name}",
                    allow_skip=False,
                )
                if parsed_nested is None:
                    nested_fallback = self.model_fallbacks.get(nested_model_class)
                    if nested_fallback is None:
                        raise ValueError(
                            f"Failed to parse nested {nested_model_class.__name__} "
                            f"for {model_class.__name__} in {context}"
                        )
                    parsed_nested = nested_fallback()
                field_values[field_name] = parsed_nested
            else:
                field_values[field_name] = raw_value

        return model_class.model_validate(field_values)


def _parse_model_strict(model_class: type, raw_data: typing.Any) -> typing.Any:
    from_dict = getattr(model_class, "from_dict", None)
    if from_dict is not None:
        parsed_model = from_dict(raw_data)
        if parsed_model is None:
            raise ValueError(f"{model_class.__name__}.from_dict returned None")
        return parsed_model
    return model_class.model_validate(raw_data)


def _list_field_item_types(model_class: type) -> dict[str, type]:
    if not hasattr(model_class, "model_fields"):
        return {}
    list_item_types_by_field: dict[str, type] = {}
    for field_name, field_info in model_class.model_fields.items():
        item_model_class = _list_item_type_from_annotation(field_info.annotation)
        if item_model_class is not None:
            list_item_types_by_field[field_name] = item_model_class
    return list_item_types_by_field


def _list_item_type_from_annotation(annotation: typing.Any) -> typing.Optional[type]:
    annotation_origin = typing.get_origin(annotation)
    if annotation_origin is typing.Union:
        non_none_args = [
            union_arg for union_arg in typing.get_args(annotation) if union_arg is not type(None)
        ]
        if len(non_none_args) == 1:
            return _list_item_type_from_annotation(non_none_args[0])
        return None
    if annotation_origin is list:
        list_item_args = typing.get_args(annotation)
        if list_item_args and isinstance(list_item_args[0], type):
            return list_item_args[0]
    return None


def _annotation_to_model_class(annotation: typing.Any) -> typing.Optional[type]:
    annotation_origin = typing.get_origin(annotation)
    if annotation_origin is typing.Union:
        non_none_args = [
            union_arg for union_arg in typing.get_args(annotation) if union_arg is not type(None)
        ]
        if len(non_none_args) == 1:
            return _annotation_to_model_class(non_none_args[0])
        return None
    if isinstance(annotation, type):
        return annotation
    return None


def _strip_invalid_values_from_schema(
    raw_dict: dict[str, typing.Any],
    json_schema: dict[str, typing.Any],
) -> dict[str, typing.Any]:
    sanitized_dict = dict(raw_dict)
    properties = json_schema.get("properties", {})
    schema_definitions = json_schema.get("$defs", {})

    for property_name, property_schema in properties.items():
        if property_name not in sanitized_dict:
            continue
        property_value = sanitized_dict[property_name]
        if property_value is None:
            sanitized_dict.pop(property_name, None)
            continue
        resolved_schema = _resolve_schema(property_schema, schema_definitions)
        enum_values = resolved_schema.get("enum")
        if enum_values is not None and property_value not in enum_values:
            sanitized_dict.pop(property_name, None)
            continue
        if resolved_schema.get("type") == "object" and isinstance(property_value, dict):
            sanitized_dict[property_name] = _strip_invalid_values_from_schema(
                property_value,
                {"properties": resolved_schema.get("properties", {}), "$defs": schema_definitions},
            )
    return sanitized_dict


def _resolve_schema(
    property_schema: dict[str, typing.Any],
    schema_definitions: dict[str, typing.Any],
) -> dict[str, typing.Any]:
    schema_reference = property_schema.get("$ref")
    if schema_reference is None:
        return property_schema
    definition_key = schema_reference.rsplit("/", maxsplit=1)[-1]
    return schema_definitions.get(definition_key, property_schema)
