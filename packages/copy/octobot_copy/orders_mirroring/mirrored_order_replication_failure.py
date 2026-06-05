import dataclasses
import decimal


@dataclasses.dataclass(frozen=True)
class MirroredOrderReplicationFailure:
    symbol: str
    side: str
    price: decimal.Decimal
    reference_order_id: str
    short_reason: str
