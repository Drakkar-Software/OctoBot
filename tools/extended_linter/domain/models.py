import dataclasses
import typing


@dataclasses.dataclass(frozen=True)
class Violation:
    rule_id: str
    file: str
    line: typing.Optional[int]
    hint: str
    detail: str = ""

    def to_dict(self) -> dict[str, typing.Any]:
        return dataclasses.asdict(self)
