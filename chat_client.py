import sys
import threading
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

global token
token = None

def check_login(win):
    while not win.token:
        pass
    print(f"Received token: {win.token}")
    global token
    token = win.token
    QTimer.singleShot(0, win.dong)
        
if __name__ == "__main__":
    
    from src.gui.signin import SignInWindow
    app = QApplication(sys.argv)
    win = SignInWindow()
    threading.Thread(target=check_login, args=(win, ), daemon=True).start()
    win.showMaximized()
    sys.exit(app.exec())
    print("Application closed")
    while token is None:
        pass
    print(f"Final token: {token}")

