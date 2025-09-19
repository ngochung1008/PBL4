# ui_components.py
from PyQt6.QtWidgets import (
    QPushButton, QLineEdit, QFrame, QVBoxLayout,
    QLabel, QHBoxLayout, QListWidget, QTextEdit
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

SPOTIFY_GREEN = "#1DB954"
DARK_BG       = "#121212"
CARD_BG       = "#181818"
TEXT_LIGHT    = "#FFFFFF"
SUBTEXT       = "#B3B3B3"

DEFAULT_FONT  = QFont("Segoe UI", 10)


# Nút Back
def create_back_button():
    btn = QPushButton("< Back")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(40)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {SPOTIFY_GREEN};
            color: {DARK_BG};
            font-size: 14px;
            border-radius: 8px;
            border: 1px solid {SPOTIFY_GREEN};
            padding: 4px 16px;
            margin-left: 16px;
            font-weight: bold;
            margin-top: 16px;
        }}
        QPushButton:hover {{
            background-color: #1ed760;
        }}
    """)
    return btn


# Tiêu đề
def create_title(text: str, size: int = 22):
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(f"""
        color: {TEXT_LIGHT};
        font-size: {size}px;
        font-weight: bold;
    """)
    return lbl


# Thanh tìm kiếm
def create_search_bar(placeholder="Search by username or IP"):
    container = QFrame()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    icon = QLabel("🔍")
    icon.setStyleSheet(f"color: {SUBTEXT}; font-size: 14pt; margin-left: 8px;")
    layout.addWidget(icon)

    edit = QLineEdit()
    edit.setPlaceholderText(placeholder)
    edit.setMinimumHeight(34)
    edit.setStyleSheet(f"""
        QLineEdit {{
            background-color: {CARD_BG};
            color: {TEXT_LIGHT};
            padding: 5px 8px;
            border-radius: 8px;
            font-size: 11pt;
        }}
    """)
    layout.addWidget(edit)
    return container, edit


# Khung Card mặc định
def create_card(centered=True, half_size=True):
    frame = QFrame()
    frame.setStyleSheet(f"background-color: {CARD_BG}; border-radius: 12px;")
    if centered:
        frame.setMinimumWidth(400)
        if half_size:
            frame.setMaximumWidth(500)
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(28, 28, 28, 28)
    lay.setSpacing(16)
    return frame, lay


# Ô nhập văn bản
def create_input(placeholder: str, password: bool = False):
    edit = QLineEdit()
    edit.setPlaceholderText(placeholder)
    edit.setFixedHeight(40)
    if password:
        edit.setEchoMode(QLineEdit.EchoMode.Password)
    edit.setStyleSheet(f"""
        QLineEdit {{
            background-color: #0f0f0f;
            color: {TEXT_LIGHT};
            border: none;
            padding: 8px 10px;
            border-radius: 8px;
            font-size: 10.5pt;
        }}
        QLineEdit:focus {{
            border: 1px solid {SPOTIFY_GREEN};
        }}
    """)
    return edit


# Button chính
def create_primary_button(text: str):
    btn = QPushButton(text)
    btn.setFixedHeight(42)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {SPOTIFY_GREEN};
            color: {DARK_BG};
            border-radius: 10px;
            font-weight: bold;
            font-size: 11pt;
        }}
        QPushButton:hover {{
            background-color: #1ed760;
        }}
    """)
    return btn


# Nút option
def create_option_button(text: str):
    btn = QPushButton(text)
    btn.setFixedHeight(46)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {CARD_BG};
            color: {TEXT_LIGHT};
            border-radius: 8px;
            font-size: 12pt;
            padding-left: 12px;
            text-align: left;
        }}
        QPushButton:hover {{
            background-color: #2a2a2a;
        }}
    """)
    return btn


# Nút profile
def create_profile_button():
    btn = QPushButton("👤")
    btn.setFixedSize(38, 38)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            font-size: 16pt;
            border: none;
        }}
        QPushButton:hover {{ color: {SPOTIFY_GREEN}; }}
    """)
    return btn


def create_client_list():
    """
    Danh sách client cho server (QListWidget).
    """
    lst = QListWidget()
    lst.setStyleSheet(f"""
        QListWidget {{
            background-color: {CARD_BG};
            color: {TEXT_LIGHT};
            border-radius: 8px;
            padding: 6px;
        }}
        QListWidget::item:hover {{
            background-color: #2a2a2a;
        }}
        QListWidget::item:selected {{
            background-color: {SPOTIFY_GREEN};
            color: {DARK_BG};
        }}
    """)
    return lst


def create_info_box():
    """
    Hộp hiển thị thông tin client.
    """
    txt = QTextEdit()
    txt.setReadOnly(True)
    txt.setStyleSheet(f"""
        QTextEdit {{
            background-color: {CARD_BG};
            color: {TEXT_LIGHT};
            border-radius: 8px;
            font-size: 10.5pt;
            padding: 6px;
        }}
    """)
    return txt


def create_control_button(text: str):
    """
    Nút điều khiển (View Screen, Control, History…).
    """
    btn = QPushButton(text)
    btn.setFixedHeight(36)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {CARD_BG};
            color: {TEXT_LIGHT};
            border-radius: 6px;
            font-size: 10.5pt;
            padding: 4px 10px;
        }}
        QPushButton:hover {{
            background-color: {SPOTIFY_GREEN};
            color: {DARK_BG};
        }}
    """)
    return btn

def center_widget(widget):
    outer = QVBoxLayout()
    outer.addStretch()
    outer.addWidget(widget, alignment=Qt.AlignmentFlag.AlignHCenter)
    outer.addStretch()
    return outer
