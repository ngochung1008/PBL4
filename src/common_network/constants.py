# common_network/constants.py

import struct

# Các loại PDU
PDU_TYPE_FULL = 1
PDU_TYPE_RECT = 2
PDU_TYPE_CONTROL = 3
PDU_TYPE_INPUT = 4
PDU_TYPE_CURSOR = 5

# File transfer PDUs
PDU_TYPE_FILE_START = 10 # báo hiệu bắt đầu truyền file
PDU_TYPE_FILE_CHUNK = 11 # gửi 1 chunk (mẫu dữ liệu) của file
PDU_TYPE_FILE_END = 12 # báo hiệu đã gửi xong chunk cuối cùng
PDU_TYPE_FILE_ACK = 13 # xác nhận đã nhận file thành công
PDU_TYPE_FILE_NAK = 14 # thông báo lỗi khi nhận file

# Định dạng header chung
# seq (I - 4 bytes), timestamp_ms (Q - 8 bytes), type (B - 1 byte), flags (B - 1 byte)
SHARE_CTRL_HDR_FMT = ">IQBB" # dùng để mã hóa/gỡ header chung của PDU
SHARE_HDR_SIZE = struct.calcsize(SHARE_CTRL_HDR_FMT) # kích thước header chung
# Fragment flag 
FRAGMENT_FLAG = 0x01 # bit flag (1) đánh dấu PDU bị phân mảnh
FRAGMENT_HDR_FMT = ">QI" # fragment header: total_size (Q - 8 bytes), offset (I - 4 bytes)
FRAGMENT_HDR_SIZE = struct.calcsize(FRAGMENT_HDR_FMT) # kích thước fragment header

# TPKT 
TPKT_HEADER_FMT = ">BBH" # TPKT header format: version (B - 1 byte), reserved (B - 1 byte), length (H - 2 bytes)
TPKT_OVERHEAD = 4 # TPKT header size in bytes
MAX_TPKT_LENGTH = 65535 # maximum TPKT length

# Event types (input)
class EventType:
    MOUSE_MOVE = "mouse_move"
    MOUSE_CLICK = "mouse_click"
    MOUSE_SCROLL = "mouse_scroll"
    KEY_PRESS = "key_press"
    KEY_RELEASE = "key_release"

# MCS Layer
MCS_HDR_FMT = ">HH" # 2-bytes channel id & 2-bytes payload_length
MCS_HDR_SIZE = struct.calcsize(MCS_HDR_FMT) # = 4 bytes
MAX_CHANNEL_BUFFER = 2 * 1024 * 1024

# Các hằng số đảm bảo PDUParser hoạt động an toàn 
FRAGMENT_ASSEMBLY_TIMEOUT = 30.0 # Thời gian chờ lắp ráp tối đa 
MAX_FRAGMENTS_PER_SEQ = 10000 # Giới hạn số fragment tối đa cho mỗi seq
MAX_BUFFERED_BYTES_PER_SEQ = 50 * 1024 * 1024  # = 50 MB. Giới hạn tổng dung lượng (bytes) tối đa cho một PDU
