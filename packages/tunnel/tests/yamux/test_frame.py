import struct
import pytest

from octobot_tunnel.yamux.constants import (
    HEADER_SIZE,
    YAMUX_VERSION,
    FRAME_TYPE_DATA,
    FRAME_TYPE_WINDOW_UPDATE,
    FRAME_TYPE_PING,
    FRAME_TYPE_GO_AWAY,
    FLAG_SYN,
    FLAG_ACK,
    FLAG_FIN,
    FLAG_RST,
    GO_AWAY_NORMAL,
    GO_AWAY_PROTO_ERR,
    GO_AWAY_INTERNAL_ERR,
    HEADER_FORMAT,
)
from octobot_tunnel.yamux.frame import Frame

pytestmark = pytest.mark.asyncio


class TestFrameEncode:
    def test_header_size_is_12(self):
        assert HEADER_SIZE == 12

    def test_encode_data_frame_empty_payload(self):
        f = Frame(frame_type=FRAME_TYPE_DATA, flags=0, stream_id=1, data=b"")
        raw = f.encode()
        assert len(raw) == HEADER_SIZE
        version, ftype, flags, sid, length = struct.unpack_from(HEADER_FORMAT, raw)
        assert version == YAMUX_VERSION
        assert ftype == FRAME_TYPE_DATA
        assert flags == 0
        assert sid == 1
        assert length == 0

    def test_encode_data_frame_with_payload(self):
        payload = b"hello world"
        f = Frame(frame_type=FRAME_TYPE_DATA, flags=0, stream_id=3, data=payload)
        raw = f.encode()
        assert len(raw) == HEADER_SIZE + len(payload)
        version, ftype, flags, sid, length = struct.unpack_from(HEADER_FORMAT, raw)
        assert ftype == FRAME_TYPE_DATA
        assert length == len(payload)
        assert raw[HEADER_SIZE:] == payload

    def test_encode_window_update_frame(self):
        delta = 65536
        f = Frame(frame_type=FRAME_TYPE_WINDOW_UPDATE, flags=0, stream_id=2, length=delta)
        raw = f.encode()
        assert len(raw) == HEADER_SIZE
        version, ftype, flags, sid, length = struct.unpack_from(HEADER_FORMAT, raw)
        assert ftype == FRAME_TYPE_WINDOW_UPDATE
        assert length == delta
        assert sid == 2

    def test_encode_ping_frame(self):
        f = Frame(frame_type=FRAME_TYPE_PING, flags=FLAG_SYN, stream_id=0, length=42)
        raw = f.encode()
        assert len(raw) == HEADER_SIZE
        version, ftype, flags, sid, length = struct.unpack_from(HEADER_FORMAT, raw)
        assert ftype == FRAME_TYPE_PING
        assert flags == FLAG_SYN
        assert sid == 0
        assert length == 42

    def test_encode_ping_ack_frame(self):
        f = Frame(frame_type=FRAME_TYPE_PING, flags=FLAG_ACK, stream_id=0, length=42)
        raw = f.encode()
        _, _, flags, _, _ = struct.unpack_from(HEADER_FORMAT, raw)
        assert flags == FLAG_ACK

    def test_encode_go_away_normal(self):
        f = Frame(frame_type=FRAME_TYPE_GO_AWAY, flags=0, stream_id=0, length=GO_AWAY_NORMAL)
        raw = f.encode()
        _, ftype, _, _, length = struct.unpack_from(HEADER_FORMAT, raw)
        assert ftype == FRAME_TYPE_GO_AWAY
        assert length == GO_AWAY_NORMAL

    def test_encode_go_away_proto_err(self):
        f = Frame(frame_type=FRAME_TYPE_GO_AWAY, flags=0, stream_id=0, length=GO_AWAY_PROTO_ERR)
        raw = f.encode()
        _, _, _, _, length = struct.unpack_from(HEADER_FORMAT, raw)
        assert length == GO_AWAY_PROTO_ERR

    def test_encode_go_away_internal_err(self):
        f = Frame(frame_type=FRAME_TYPE_GO_AWAY, flags=0, stream_id=0, length=GO_AWAY_INTERNAL_ERR)
        raw = f.encode()
        _, _, _, _, length = struct.unpack_from(HEADER_FORMAT, raw)
        assert length == GO_AWAY_INTERNAL_ERR

    def test_encode_syn_flag(self):
        f = Frame(frame_type=FRAME_TYPE_DATA, flags=FLAG_SYN, stream_id=1, data=b"")
        raw = f.encode()
        _, _, flags, _, _ = struct.unpack_from(HEADER_FORMAT, raw)
        assert flags & FLAG_SYN

    def test_encode_fin_flag(self):
        f = Frame(frame_type=FRAME_TYPE_DATA, flags=FLAG_FIN, stream_id=1, data=b"")
        raw = f.encode()
        _, _, flags, _, _ = struct.unpack_from(HEADER_FORMAT, raw)
        assert flags & FLAG_FIN

    def test_encode_rst_flag(self):
        f = Frame(frame_type=FRAME_TYPE_DATA, flags=FLAG_RST, stream_id=1, data=b"")
        raw = f.encode()
        _, _, flags, _, _ = struct.unpack_from(HEADER_FORMAT, raw)
        assert flags & FLAG_RST

    def test_encode_combined_flags(self):
        combined = FLAG_SYN | FLAG_ACK
        f = Frame(frame_type=FRAME_TYPE_DATA, flags=combined, stream_id=1, data=b"")
        raw = f.encode()
        _, _, flags, _, _ = struct.unpack_from(HEADER_FORMAT, raw)
        assert flags == combined

    def test_version_is_always_zero(self):
        for ftype in (FRAME_TYPE_DATA, FRAME_TYPE_WINDOW_UPDATE, FRAME_TYPE_PING, FRAME_TYPE_GO_AWAY):
            f = Frame(frame_type=ftype, flags=0, stream_id=0)
            raw = f.encode()
            version = raw[0]
            assert version == 0, f"frame type {ftype} has version {version}"


class TestFrameDecode:
    def test_decode_data_frame(self):
        payload = b"test data"
        raw = struct.pack(HEADER_FORMAT, YAMUX_VERSION, FRAME_TYPE_DATA, 0, 5, len(payload)) + payload
        f = Frame.decode(raw)
        assert f.frame_type == FRAME_TYPE_DATA
        assert f.flags == 0
        assert f.stream_id == 5
        assert f.data == payload
        assert f.length == len(payload)

    def test_decode_window_update_frame(self):
        delta = 131072
        raw = struct.pack(HEADER_FORMAT, YAMUX_VERSION, FRAME_TYPE_WINDOW_UPDATE, 0, 7, delta)
        f = Frame.decode(raw)
        assert f.frame_type == FRAME_TYPE_WINDOW_UPDATE
        assert f.length == delta
        assert f.stream_id == 7

    def test_decode_ping_frame(self):
        raw = struct.pack(HEADER_FORMAT, YAMUX_VERSION, FRAME_TYPE_PING, FLAG_SYN, 0, 99)
        f = Frame.decode(raw)
        assert f.frame_type == FRAME_TYPE_PING
        assert f.flags == FLAG_SYN
        assert f.length == 99

    def test_decode_go_away_frame(self):
        raw = struct.pack(HEADER_FORMAT, YAMUX_VERSION, FRAME_TYPE_GO_AWAY, 0, 0, GO_AWAY_PROTO_ERR)
        f = Frame.decode(raw)
        assert f.frame_type == FRAME_TYPE_GO_AWAY
        assert f.length == GO_AWAY_PROTO_ERR

    def test_decode_raises_on_wrong_version(self):
        raw = struct.pack(HEADER_FORMAT, 99, FRAME_TYPE_DATA, 0, 1, 0)
        with pytest.raises(ValueError, match="version"):
            Frame.decode(raw)

    def test_decode_raises_on_too_short(self):
        with pytest.raises(ValueError, match="too short"):
            Frame.decode(b"\x00" * 5)

    def test_decode_all_flag_combinations(self):
        for flags in (FLAG_SYN, FLAG_ACK, FLAG_FIN, FLAG_RST, FLAG_SYN | FLAG_ACK, FLAG_FIN | FLAG_RST):
            raw = struct.pack(HEADER_FORMAT, YAMUX_VERSION, FRAME_TYPE_DATA, flags, 1, 0)
            f = Frame.decode(raw)
            assert f.flags == flags


class TestFrameRoundTrip:
    @pytest.mark.parametrize("frame_type,flags,stream_id,data,length", [
        (FRAME_TYPE_DATA, 0, 1, b"hello", 0),
        (FRAME_TYPE_DATA, FLAG_SYN, 3, b"", 0),
        (FRAME_TYPE_DATA, FLAG_FIN, 5, b"bye", 0),
        (FRAME_TYPE_WINDOW_UPDATE, 0, 2, b"", 65536),
        (FRAME_TYPE_WINDOW_UPDATE, FLAG_SYN, 4, b"", 0),
        (FRAME_TYPE_PING, FLAG_SYN, 0, b"", 12345),
        (FRAME_TYPE_PING, FLAG_ACK, 0, b"", 12345),
        (FRAME_TYPE_GO_AWAY, 0, 0, b"", GO_AWAY_NORMAL),
        (FRAME_TYPE_GO_AWAY, 0, 0, b"", GO_AWAY_PROTO_ERR),
        (FRAME_TYPE_GO_AWAY, 0, 0, b"", GO_AWAY_INTERNAL_ERR),
    ])
    def test_round_trip(self, frame_type, flags, stream_id, data, length):
        original = Frame(frame_type=frame_type, flags=flags, stream_id=stream_id, data=data, length=length)
        raw = original.encode()
        decoded = Frame.decode(raw)
        assert decoded.frame_type == original.frame_type
        assert decoded.flags == original.flags
        assert decoded.stream_id == original.stream_id
        if frame_type == FRAME_TYPE_DATA:
            assert decoded.data == original.data
            assert decoded.length == len(original.data)
        else:
            assert decoded.length == original.length
