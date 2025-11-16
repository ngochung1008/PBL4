# common_network/constants.py

# Các loại PDU
PDU_TYPE_FULL = 1
PDU_TYPE_RECT = 2
PDU_TYPE_CONTROL = 3
PDU_TYPE_INPUT = 4

# Định dạng header chung
# seq (I - 4 bytes), timestamp_ms (Q - 8 bytes), type (B - 1 byte), flags (B - 1 byte)
SHARE_CTRL_HDR_FMT = ">IQBB"

# TPKT 
TPKT_HEADER_FMT = ">BBH"
# version (B - 1 byte), reserved (B - 1 byte), length (H - 2 bytes)
TPKT_OVERHEAD = 4 
MAX_TPKT_LENGTH = 65535 # 2 byte