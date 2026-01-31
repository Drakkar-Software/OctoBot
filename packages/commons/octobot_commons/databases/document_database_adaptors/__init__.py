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


from octobot_commons.databases.document_database_adaptors import (
    abstract_document_database_adaptor,
)
from octobot_commons.databases.document_database_adaptors import tinydb_adaptor


from octobot_commons.databases.document_database_adaptors.abstract_document_database_adaptor import (
    AbstractDocumentDatabaseAdaptor,
)
from octobot_commons.databases.document_database_adaptors.tinydb_adaptor import (
    TinyDBAdaptor,
)


__all__ = [
    "AbstractDocumentDatabaseAdaptor",
    "TinyDBAdaptor",
]
