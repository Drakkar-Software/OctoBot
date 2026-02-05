#  Drakkar-Software OctoBot-Tentacles
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
import datetime


@dataclasses.dataclass
class CoindeskNews:
    id: str
    guid: str
    published_on: datetime.datetime
    image_url: str
    title: str
    url: str
    source_id: str
    body: str
    keywords: str
    lang: str
    upvotes: int
    downvotes: int
    score: int
    sentiment: str  # POSITIVE, NEGATIVE, NEUTRAL
    status: str
    source_name: str
    source_key: str
    source_url: str
    source_lang: str
    source_type: str
    categories: str


@dataclasses.dataclass
class CoindeskMarketcap:
    timestamp: datetime.datetime
    open: float
    close: float
    high: float
    low: float
    top_tier_volume: float
