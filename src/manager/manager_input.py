class ManagerInputHandler:
    """
    Lớp tiện ích để gửi input event qua ManagerApp.
    """

    def __init__(self, manager_app):
        # Lưu ý: nhận vào manager_app, không phải client
        self.manager_app = manager_app

    def send_event(self, event: dict):
        """
        Gửi input event. Không cần 'target' vì server đã biết
        manager đang ở trong phiên (session) nào.
        """
        if not self.manager_app:
            return False
        try:
            self.manager_app.send_input(event)
            return True
        except Exception as e:
            print(f"[ManagerInputHandler] Lỗi send_event: {e}")
            return False