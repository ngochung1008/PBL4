# client_network/mcs_layer.py

# MCS-lite: chỉ định một virtual channel ID để tách luồng dữ liệu
class MCSLite:
    def __init__(self):
        self.channel_id = 1001

    def get_channel_id(self):
        return self.channel_id
