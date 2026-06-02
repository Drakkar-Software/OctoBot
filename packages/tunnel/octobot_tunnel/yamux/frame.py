import struct
from dataclasses import dataclass, field

from octobot_tunnel.yamux.constants import (
    HEADER_FORMAT,
    HEADER_SIZE,
    YAMUX_VERSION,
    FRAME_TYPE_DATA,
    FRAME_TYPE_WINDOW_UPDATE,
    FRAME_TYPE_PING,
    FRAME_TYPE_GO_AWAY,
)


@dataclass
class Frame:
    frame_type: int
    flags: int
    stream_id: int
    # For DATA frames: the actual payload bytes.
    # For WINDOW_UPDATE / PING / GO_AWAY: an integer value carried in the length field.
    data: bytes = field(default=b"")
    length: int = field(default=0)

    def encode(self) -> bytes:
        if self.frame_type == FRAME_TYPE_DATA:
            payload = self.data
            length = len(payload)
        else:
            payload = b""
            length = self.length
        header = struct.pack(HEADER_FORMAT, YAMUX_VERSION, self.frame_type, self.flags, self.stream_id, length)
        return header + payload

    @staticmethod
    def decode(raw: bytes) -> "Frame":
        if len(raw) < HEADER_SIZE:
            raise ValueError(f"frame too short: {len(raw)} < {HEADER_SIZE}")
        version, frame_type, flags, stream_id, length = struct.unpack_from(HEADER_FORMAT, raw, 0)
        if version != YAMUX_VERSION:
            raise ValueError(f"unsupported yamux version: {version}")
        if frame_type == FRAME_TYPE_DATA:
            data = raw[HEADER_SIZE: HEADER_SIZE + length]
            return Frame(frame_type=frame_type, flags=flags, stream_id=stream_id, data=data, length=length)
        else:
            return Frame(frame_type=frame_type, flags=flags, stream_id=stream_id, data=b"", length=length)
