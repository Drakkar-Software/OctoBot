#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.

import dataclasses
import typing

import octobot_protocol.models as protocol_models
from ..hollaex.hollaex_exchange import hollaex


@dataclasses.dataclass(frozen=True)
class CustomExchangeAvailability:
    name: str
    api_url: str
    internal_name: str = hollaex.get_name()
    logo: typing.Optional[str] = None
    register_url: typing.Optional[str] = None
    available_trading_types: tuple[protocol_models.TradingType, ...] = dataclasses.field(
        default_factory=lambda: (protocol_models.TradingType.SPOT,)
    )
    support_type: protocol_models.ExchangeSupportStatus = dataclasses.field(
        default=protocol_models.ExchangeSupportStatus.OFFICIALLY_SUPPORTED
    )
    sandboxable: bool = False
    broker_enabled: bool = False

    def to_exchange_availability(self) -> protocol_models.ExchangeAvailability:
        return protocol_models.ExchangeAvailability(
            internal_name=self.internal_name,
            name=self.name,
            logo=self.logo,
            available_trading_types=list(self.available_trading_types),
            support_type=self.support_type,
            sandboxable=self.sandboxable,
            broker_enabled=self.broker_enabled,
            register_url=self.register_url,
            api_url=self.api_url,
        )


_CUSTOM_EXCHANGE_AVAILABILITIES: tuple[CustomExchangeAvailability, ...] = (
    CustomExchangeAvailability(
        name="Earn Curve",
        api_url="https://www.earncurve.com.au/api/",
    ),
)
