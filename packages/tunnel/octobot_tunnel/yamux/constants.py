import struct

YAMUX_VERSION = 0

# Frame types
FRAME_TYPE_DATA = 0x0
FRAME_TYPE_WINDOW_UPDATE = 0x1
FRAME_TYPE_PING = 0x2
FRAME_TYPE_GO_AWAY = 0x3

# Flags
FLAG_SYN = 0x0001
FLAG_ACK = 0x0002
FLAG_FIN = 0x0004
FLAG_RST = 0x0008

# GoAway error codes (carried in the length field)
GO_AWAY_NORMAL = 0x0
GO_AWAY_PROTO_ERR = 0x1
GO_AWAY_INTERNAL_ERR = 0x2

# Frame header: version(B) type(B) flags(H) stream_id(I) length(I)
HEADER_FORMAT = ">BBHII"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 12 bytes

# Flow-control defaults (match HashiCorp/yamux defaults)
DEFAULT_WINDOW_SIZE = 256 * 1024  # 256 KB
DEFAULT_ACCEPT_BACKLOG = 256
