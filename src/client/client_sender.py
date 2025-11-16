from common_network.pdu_builder import PDUBuilder

class ClientSender:
    """Đóng gói frame chụp được thành PDU rồi gửi qua network"""
    def __init__(self, network):
        self.network = network

    def send_frame(self, width, height, jpg_bytes, bbox, seq, ts_ms):
        """
        Gửi frame (full hoặc delta) kèm theo thứ tự (seq) và timestamp (ts_ms)
        """
        if bbox is None:
            # Full frame
            pdu = PDUBuilder.build_full_frame_pdu(seq, jpg_bytes, width, height, ts_ms)
        else:
            # Delta frame
            left, top, right, bottom = bbox
            pdu = PDUBuilder.build_rect_pdu(seq, jpg_bytes, left, top, right, bottom, ts_ms)

        # Gửi PDU qua kênh "screen"
        self.network.send_pdu("screen", pdu)
