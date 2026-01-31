# pylint: disable=R0913,R0914,R0902,W0622,C0103
#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.
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
import contextlib

import octobot_commons.logging as logging
import octobot_commons.constants as constants
import octobot_commons.enums as enums


class DisplayTranslator:
    """
    Interface for simplifying displayed elements translation
    """

    INPUT_TYPE_TO_SCHEMA_TYPE = {
        enums.UserInputTypes.INT.value: "number",
        enums.UserInputTypes.FLOAT.value: "number",
        enums.UserInputTypes.BOOLEAN.value: "boolean",
        enums.UserInputTypes.TEXT.value: "text",
        enums.UserInputTypes.OPTIONS.value: "options",
        enums.UserInputTypes.MULTIPLE_OPTIONS.value: "array",
        enums.UserInputTypes.OBJECT_ARRAY.value: "array",
        enums.UserInputTypes.STRING_ARRAY.value: "array",
        enums.UserInputTypes.OBJECT.value: "object",
        constants.NESTED_TENTACLE_CONFIG: "object",
    }
    JSON_PROPERTY_AUTO_ORDER_START = 500
    DEFAULT_NUMBER_MULTIPLIER = 0.00000001

    def __init__(self, element_type=enums.DisplayedElementTypes.CHART.value):
        self.logger = logging.get_logger(self.__class__.__name__)
        self.nested_elements = {}
        self.elements = []
        self.type: str = element_type

    def to_json(self, name="root") -> dict:
        """
        Return the json representation of this display
        :param name: name of the root element
        :return: the json compatible dict representation of this display
        """
        return {
            enums.PlotAttributes.NAME.value: name,
            enums.PlotAttributes.TYPE.value: self.type,
            enums.PlotAttributes.DATA.value: {
                enums.PlotAttributes.SUB_ELEMENTS.value: [
                    element.to_json(key)
                    for key, element in self.nested_elements.items()
                    if not element.is_empty()
                ],
                enums.PlotAttributes.ELEMENTS.value: [
                    element.to_json()
                    for element in self.elements
                    if not element.is_empty()
                ],
            },
        }

    def add_parts_from_other(self, other_element):
        """
        Adds the given "other_element" to the local nested elements
        """
        self.nested_elements.update(other_element.nested_elements)

    def is_empty(self):
        """
        :return: True if there is no element in self.elements or self.nested_elements
        """
        return not (self.nested_elements or self.elements)

    @contextlib.contextmanager
    def part(self, name, element_type=enums.DisplayedElementTypes.CHART.value):
        """
        Adds a part to this display
        :param name: name of the part
        :param element_type: type of the part to add
        """
        element = self.__class__(element_type=element_type)
        self.nested_elements[name] = element
        yield element

    def add_user_inputs(self, inputs, part=None, config_by_tentacles=None):
        """
        add user inputs to the given part or self
        """
        has_forced_config = config_by_tentacles is not None
        config_by_tentacles = config_by_tentacles or {}
        config_schema_by_tentacles = {}
        tentacle_type_by_tentacles = {}
        shown_tentacles = {}
        nested_user_inputs_by_tentacle = self._extract_nested_user_inputs(inputs)
        tentacle = None
        for user_input_element in inputs:
            try:
                tentacle = user_input_element["tentacle"]
                if user_input_element["is_nested_config"]:
                    # Do not display nested user input config as regular user inputs.
                    # These are mere models that are used in association with
                    # nested user inputs, which are used in the context of a
                    # nested tentacle configuration
                    if tentacle not in shown_tentacles:
                        shown_tentacles[tentacle] = False
                else:
                    shown_tentacles[tentacle] = True
                tentacle_type_by_tentacles[tentacle] = user_input_element[
                    "tentacle_type"
                ]
                if tentacle not in config_schema_by_tentacles:
                    config_schema_by_tentacles[tentacle] = self._base_schema(tentacle)
                    if not has_forced_config:
                        config_by_tentacles[tentacle] = {}
                if tentacle not in config_by_tentacles:
                    config_by_tentacles[tentacle][
                        user_input_element["name"].replace(" ", "_")
                    ] = user_input_element["value"]
                if user_input_element["parent_input_name"] is None:
                    # user input with parent_input_name are added alongside their parents, only add top
                    # level user inputs in schema
                    self._generate_schema(
                        config_schema_by_tentacles[tentacle],
                        user_input_element,
                        nested_user_inputs_by_tentacle,
                    )
            except KeyError as err:
                self.logger.error(
                    f"Error when loading user inputs for {tentacle}: missing {err}"
                )
        for tentacle, schema in config_schema_by_tentacles.items():
            (part or self).add_user_inputs_element(
                "Inputs",
                config_by_tentacles[tentacle],
                schema,
                tentacle,
                tentacle_type_by_tentacles[tentacle],
                not shown_tentacles[tentacle],
            )

    def _base_schema(self, tentacle):
        return {
            "type": "object",
            "title": f"{tentacle} configuration",
            "properties": {},
        }

    def _extract_nested_user_inputs(self, inputs):
        user_inputs_by_tentacles = {}
        for user_input in inputs:
            if user_input["is_nested_config"] or user_input["parent_input_name"]:
                tentacle = user_input["tentacle"]
                if tentacle not in user_inputs_by_tentacles:
                    user_inputs_by_tentacles[tentacle] = {}
                if user_input["is_nested_config"]:
                    user_inputs_by_tentacles[tentacle][
                        user_input["name"].replace(" ", "_")
                    ] = user_input
                else:
                    user_inputs_by_tentacles[tentacle][
                        len(user_inputs_by_tentacles[tentacle])
                    ] = user_input
        return user_inputs_by_tentacles

    def _init_schema_properties(self, main_schema, user_input_element, title, def_val):
        properties = {
            "options": {
                "in_summary": user_input_element.get("in_summary", True),
                "in_optimizer": user_input_element.get("in_optimizer", True),
                "custom_path": user_input_element.get("path", None),
            }
        }
        # prioritize user defined order, otherwise keep the order inputs are saved
        property_order = user_input_element.get("order", None)
        properties["propertyOrder"] = (
            len(main_schema["properties"]) + self.JSON_PROPERTY_AUTO_ORDER_START
            if property_order is None
            else property_order
        )
        name = user_input_element["name"]
        properties["options"]["name"] = name.replace(" ", "_")
        properties["title"] = name
        if title:
            # use title if available
            properties["title"] = title
        properties["default"] = def_val
        min_val = user_input_element.get("min_val")
        if min_val is not None:
            properties["minimum"] = min_val
        max_val = user_input_element.get("max_val")
        if max_val is not None:
            properties["maximum"] = max_val
        if editor_options := user_input_element.get("editor_options"):
            properties["options"].update(editor_options)
            if (
                enums.UserInputOtherSchemaValuesTypes.DEPENDENCIES.value
                in editor_options
            ):
                other_values = user_input_element.get("other_schema_values", {}) or {}
                # when using dependencies, set field as not required as it might not be set
                other_values["required"] = other_values.get("required", False)
                user_input_element["other_schema_values"] = other_values
                # waiting for fixes on
                # - https://github.com/json-editor/json-editor/issues/1559
                # - https://github.com/json-editor/json-editor/issues/1621
                to_remove = []
                for key, val in editor_options[
                    enums.UserInputOtherSchemaValuesTypes.DEPENDENCIES.value
                ].items():
                    if val is False:
                        # for now remove unsupported dependency
                        to_remove.append(key)
                for key in to_remove:
                    editor_options[
                        enums.UserInputOtherSchemaValuesTypes.DEPENDENCIES.value
                    ].pop(key)
                    self.logger.debug(
                        f"Removing unsupported 'False' dependency value for {key}"
                    )
        if other_schema_values := user_input_element.get("other_schema_values"):
            properties.update(other_schema_values)
        return properties

    def _adapt_to_input_type(
        self,
        user_input_element,
        nested_user_inputs_by_tentacle,
        properties,
        input_type,
        title,
        def_val,
    ):
        try:
            schema_type = self.INPUT_TYPE_TO_SCHEMA_TYPE[input_type]
            if schema_type == "boolean":
                properties["format"] = "checkbox"
            elif schema_type == "number":
                if input_type == enums.UserInputTypes.INT.value:
                    properties["multipleOf"] = 1
            elif input_type in (
                enums.UserInputTypes.STRING_ARRAY.value,
                enums.UserInputTypes.OBJECT_ARRAY.value,
            ):
                self._adapt_to_specific_array_user_input(
                    user_input_element,
                    nested_user_inputs_by_tentacle,
                    properties,
                    input_type,
                )
            elif schema_type in ("options", "array"):
                options = user_input_element.get("options", [])
                default_value = (
                    def_val if def_val is not None else options[0] if options else None
                )
                if schema_type == "options":
                    properties["default"] = (default_value,)
                    properties["format"] = "select"
                    properties["enum"] = options
                    # override schema_type as we couldn't know it before
                    schema_type = self._get_element_schema_type(options)
                elif schema_type == "array":
                    properties["format"] = "select2"
                    properties["minItems"] = properties.get("minItems", 1)
                    properties["uniqueItems"] = True
                    properties["items"] = {
                        "title": title,
                        "type": self._get_element_schema_type(options),
                        "default": default_value,
                        "enum": options,
                    }
            elif schema_type == "object":
                self._adapt_to_object_user_input(
                    user_input_element, nested_user_inputs_by_tentacle, properties
                )
            elif schema_type == "text":
                schema_type = "string"
                properties["minLength"] = properties.get("minLength", 1)
            properties["type"] = schema_type
        except KeyError as err:
            self.logger.exception(err, True, f"Unknown input type: {err}")

    def _adapt_to_specific_array_user_input(
        self,
        user_input_element,
        nested_user_inputs_by_tentacle,
        properties,
        input_type,
    ):
        # nested object in array, insert array first
        properties["items"] = {
            "type": (
                "object"
                if input_type == enums.UserInputTypes.OBJECT_ARRAY.value
                else "string"
            ),
            "properties": {},
        }
        if item_title := user_input_element.get("item_title"):
            properties["items"]["title"] = item_title
        if input_type == enums.UserInputTypes.OBJECT_ARRAY.value:
            for associated_user_input in self._get_associated_user_input(
                user_input_element, nested_user_inputs_by_tentacle
            ):
                self._generate_schema(
                    properties["items"],
                    associated_user_input,
                    nested_user_inputs_by_tentacle,
                )

    def _adapt_to_object_user_input(
        self,
        user_input_element,
        nested_user_inputs_by_tentacle,
        properties,
    ):
        properties["properties"] = {}
        nested_tentacle = user_input_element["nested_tentacle"]
        if nested_tentacle:
            for user_input_name in user_input_element["value"]:
                properties["options"]["is_nested_tentacle"] = True
                try:
                    self._generate_schema(
                        properties,
                        nested_user_inputs_by_tentacle[nested_tentacle][
                            user_input_name
                        ],
                        nested_user_inputs_by_tentacle,
                    )
                except KeyError as err:
                    self.logger.warning(
                        f"Missing user input model for {err}. This element might not be "
                        f"associated to a tentacle"
                    )
        else:
            for associated_user_input in self._get_associated_user_input(
                user_input_element, nested_user_inputs_by_tentacle
            ):
                self._generate_schema(
                    properties,
                    associated_user_input,
                    nested_user_inputs_by_tentacle,
                )

    def _generate_schema(
        self, main_schema, user_input_element, nested_user_inputs_by_tentacle
    ):
        title = user_input_element.get("title")
        def_val = user_input_element.get("def_val")
        properties = self._init_schema_properties(
            main_schema, user_input_element, title, def_val
        )
        if input_type := user_input_element.get("input_type"):
            self._adapt_to_input_type(
                user_input_element,
                nested_user_inputs_by_tentacle,
                properties,
                input_type,
                title,
                def_val,
            )
        main_schema["properties"][properties["options"]["name"]] = properties

    def _get_associated_user_input(self, user_input, nested_user_inputs_by_tentacle):
        # include all user input associated to this one (same parent_input_name and tentacle)
        return (
            associated_user_input
            for associated_user_input in nested_user_inputs_by_tentacle[
                user_input["tentacle"]
            ].values()
            if associated_user_input["tentacle"] == user_input["tentacle"]
            and associated_user_input["parent_input_name"] == user_input["name"]
        )

    def _get_element_schema_type(self, options):
        default_type = "string"
        try:
            if isinstance(options[0], int):
                return self.INPUT_TYPE_TO_SCHEMA_TYPE[enums.UserInputTypes.INT.value]
            if isinstance(options[0], float):
                return self.INPUT_TYPE_TO_SCHEMA_TYPE[enums.UserInputTypes.FLOAT.value]
            if isinstance(options[0], bool):
                return self.INPUT_TYPE_TO_SCHEMA_TYPE[
                    enums.UserInputTypes.BOOLEAN.value
                ]
            if isinstance(options[0], str):
                return default_type
        except IndexError:
            pass
        except TypeError as error:
            raise TypeError("a user input element is malformed.") from error
        return default_type

    def add_user_inputs_element(
        self,
        name,
        config_values,
        schema,
        tentacle,
        tentacle_type,
        is_hidden,
    ):
        """
        Add a user input type element to self.elements
        """
        element = Element(
            None,
            None,
            None,
            title=name,
            schema=schema,
            config_values=config_values,
            tentacle=tentacle,
            tentacle_type=tentacle_type,
            is_hidden=is_hidden,
            type=enums.DisplayedElementTypes.INPUT.value,
        )
        self.elements.append(element)


class Element:
    def __init__(
        self,
        kind,
        x,
        y,
        open=None,
        high=None,
        low=None,
        close=None,
        volume=None,
        x_type=None,
        y_type=None,
        title=None,
        text=None,
        mode=None,
        line_shape=None,
        own_xaxis=False,
        own_yaxis=False,
        value=None,
        config_values=None,
        schema=None,
        tentacle=None,
        tentacle_type=None,
        columns=None,
        rows=None,
        searches=None,
        is_hidden=None,
        type=enums.DisplayedElementTypes.CHART.value,
        color=None,
        html=None,
        size=None,
        symbol=None,
    ):
        self.kind = kind
        self.x = x
        self.y = y
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.x_type = x_type
        self.y_type = y_type
        self.title = title
        self.text = text
        self.mode = mode
        self.line_shape = line_shape
        self.own_xaxis = own_xaxis
        self.own_yaxis = own_yaxis
        self.value = value
        self.config_values = config_values
        self.schema = schema
        self.tentacle = tentacle
        self.tentacle_type = tentacle_type
        self.columns = columns
        self.rows = rows
        self.searches = searches
        self.is_hidden = is_hidden
        self.type = type
        self.color = color
        self.html = html
        self.size = size
        self.symbol = symbol

    def to_json(self):
        """
        :return: the json representation of self
        """
        return {
            enums.PlotAttributes.KIND.value: self.kind,
            enums.PlotAttributes.X.value: self.x,
            enums.PlotAttributes.Y.value: self.y,
            enums.PlotAttributes.OPEN.value: self.open,
            enums.PlotAttributes.HIGH.value: self.high,
            enums.PlotAttributes.LOW.value: self.low,
            enums.PlotAttributes.CLOSE.value: self.close,
            enums.PlotAttributes.VOLUME.value: self.volume,
            enums.PlotAttributes.X_TYPE.value: self.x_type,
            enums.PlotAttributes.Y_TYPE.value: self.y_type,
            enums.PlotAttributes.TITLE.value: self.title,
            enums.PlotAttributes.TEXT.value: self.text,
            enums.PlotAttributes.MODE.value: self.mode,
            enums.PlotAttributes.LINE_SHAPE.value: self.line_shape,
            enums.PlotAttributes.OWN_XAXIS.value: self.own_xaxis,
            enums.PlotAttributes.OWN_YAXIS.value: self.own_yaxis,
            enums.PlotAttributes.VALUE.value: self.value,
            enums.PlotAttributes.CONFIG.value: self.config_values,
            enums.PlotAttributes.SCHEMA.value: self.schema,
            enums.PlotAttributes.TENTACLE.value: self.tentacle,
            enums.PlotAttributes.TENTACLE_TYPE.value: self.tentacle_type,
            enums.PlotAttributes.COLUMNS.value: self.columns,
            enums.PlotAttributes.ROWS.value: self.rows,
            enums.PlotAttributes.SEARCHES.value: self.searches,
            enums.PlotAttributes.IS_HIDDEN.value: self.is_hidden,
            enums.PlotAttributes.TYPE.value: self.type,
            enums.PlotAttributes.COLOR.value: self.color,
            enums.PlotAttributes.HTML.value: self.html,
            enums.PlotAttributes.SIZE.value: self.size,
            enums.PlotAttributes.SYMBOL.value: self.symbol,
        }

    def is_empty(self):
        """
        :return: False
        """
        return False

    @staticmethod
    def to_list(array, multiplier=1):
        """
        :return: a new array in which each value is multiplied by multiplier
        """
        if array is None:
            return None
        return [e * multiplier for e in array]
