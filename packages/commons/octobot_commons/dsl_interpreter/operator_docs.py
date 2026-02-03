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
import dataclasses


import octobot_commons.dsl_interpreter.operator_parameter as dsl_interpreter_operator_parameter


@dataclasses.dataclass
class OperatorDocs:
    """
    Operator documentation class, used to store operators metadata to
    generate an operator documentation.
    """

    name: str
    description: str
    type: str
    example: str
    parameters: list[dsl_interpreter_operator_parameter.OperatorParameter]

    def to_json(self) -> dict:
        """
        Convert the operator documentation to a JSON serializable dict.
        """
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "example": self.example,
            "parameters": [parameter.to_json() for parameter in self.parameters],
        }
