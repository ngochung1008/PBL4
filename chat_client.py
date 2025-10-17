import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QMessageBox, QLabel, QPushButton, QSizePolicy
)
from src.gui.signin import  SignUpWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SignUpWindow()
    win.showMaximized()
    sys.exit(app.exec())
