"""
Manager File Transfer Panel - Giao diện gửi và nhận file
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QFileDialog, QListWidget, QListWidgetItem, QMessageBox,
    QProgressBar, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal
from src.gui.ui_components import (
    CARD_BG, SUBTEXT, TEXT_LIGHT, SPOTIFY_GREEN,
    create_primary_button, create_back_button
)
from PyQt6.QtWidgets import QPushButton
import os


class ManagerFileTransferPanel(QWidget):
    """Panel for manager to send and receive files"""
    
    # Signals
    file_send_requested = pyqtSignal(str, str)  # (target_client_id, filepath)
    
    def __init__(self, parent=None):
        super().__init__()
        self.parent_window = parent
        self.selected_client_id = None
        self.selected_file_path = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("📁 File Transfer")
        title.setStyleSheet(f"""
            color: {TEXT_LIGHT};
            font-size: 20pt;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        # Client info
        self.client_label = QLabel("Client: Chưa chọn")
        self.client_label.setStyleSheet(f"""
            color: {SUBTEXT};
            font-size: 12pt;
        """)
        layout.addWidget(self.client_label)
        
        # === SEND FILE SECTION ===
        send_section = QWidget()
        send_layout = QVBoxLayout(send_section)
        send_layout.setContentsMargins(10, 10, 10, 10)
        send_section.setStyleSheet(f"""
            background-color: {CARD_BG};
            border-radius: 8px;
        """)
        
        send_title = QLabel("📤 Gửi File")
        send_title.setStyleSheet(f"""
            color: {TEXT_LIGHT};
            font-size: 14pt;
            font-weight: bold;
        """)
        send_layout.addWidget(send_title)
        
        # File selection
        file_select_layout = QHBoxLayout()
        
        self.file_path_label = QLabel("Chưa chọn file")
        self.file_path_label.setStyleSheet(f"""
            color: {SUBTEXT};
            font-size: 11pt;
            padding: 8px;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
        """)
        self.file_path_label.setWordWrap(True)
        file_select_layout.addWidget(self.file_path_label, stretch=1)
        
        self.browse_button = QPushButton("Chọn File")
        self.browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {SPOTIFY_GREEN};
                color: black;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                opacity: 0.85;
            }}
        """)
        self.browse_button.clicked.connect(self.browse_file)
        file_select_layout.addWidget(self.browse_button)
        
        send_layout.addLayout(file_select_layout)
        
        # Send button
        self.send_button = QPushButton("Gửi File")
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {SPOTIFY_GREEN};
                color: black;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 12pt;
            }}
            QPushButton:hover {{
                opacity: 0.85;
            }}
            QPushButton:disabled {{
                background-color: #555;
                color: #888;
            }}
        """)
        self.send_button.setEnabled(False)
        self.send_button.clicked.connect(self.send_file)
        send_layout.addWidget(self.send_button)
        
        # Progress bar
        self.send_progress = QProgressBar()
        self.send_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {SUBTEXT};
                border-radius: 4px;
                text-align: center;
                background-color: rgba(255, 255, 255, 0.05);
                color: {TEXT_LIGHT};
            }}
            QProgressBar::chunk {{
                background-color: {SPOTIFY_GREEN};
            }}
        """)
        self.send_progress.setVisible(False)
        send_layout.addWidget(self.send_progress)
        
        layout.addWidget(send_section)
        
        # === RECEIVED FILES SECTION ===
        receive_section = QWidget()
        receive_layout = QVBoxLayout(receive_section)
        receive_layout.setContentsMargins(10, 10, 10, 10)
        receive_section.setStyleSheet(f"""
            background-color: {CARD_BG};
            border-radius: 8px;
        """)
        
        receive_title = QLabel("📥 File Đã Nhận")
        receive_title.setStyleSheet(f"""
            color: {TEXT_LIGHT};
            font-size: 14pt;
            font-weight: bold;
        """)
        receive_layout.addWidget(receive_title)
        
        # List of received files
        self.received_files_list = QListWidget()
        self.received_files_list.setStyleSheet(f"""
            QListWidget {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid {SUBTEXT};
                border-radius: 4px;
                color: {TEXT_LIGHT};
                padding: 5px;
                font-size: 11pt;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {SUBTEXT};
            }}
            QListWidget::item:selected {{
                background-color: {SPOTIFY_GREEN};
                color: black;
            }}
        """)
        receive_layout.addWidget(self.received_files_list)
        
        # Buttons for received files
        received_buttons_layout = QHBoxLayout()
        
        self.open_file_button = QPushButton("Mở File")
        self.open_file_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_file_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {SPOTIFY_GREEN};
                color: black;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                opacity: 0.85;
            }}
        """)
        self.open_file_button.clicked.connect(self.open_received_file)
        received_buttons_layout.addWidget(self.open_file_button)
        
        self.open_folder_button = QPushButton("Mở Thư Mục")
        self.open_folder_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_folder_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {SPOTIFY_GREEN};
                color: black;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                opacity: 0.85;
            }}
        """)
        self.open_folder_button.clicked.connect(self.open_received_folder)
        received_buttons_layout.addWidget(self.open_folder_button)
        
        receive_layout.addLayout(received_buttons_layout)
        
        layout.addWidget(receive_section)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"""
            color: {SUBTEXT};
            font-size: 10pt;
            padding: 5px;
        """)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
    
    def set_client(self, client_id: str):
        """Set target client"""
        self.selected_client_id = client_id
        self.client_label.setText(f"Client: {client_id}")
        
        # Enable send button if file is selected
        if self.selected_file_path:
            self.send_button.setEnabled(True)
    
    def browse_file(self):
        """Browse for file to send"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn File",
            "",
            "All Files (*.*)"
        )
        
        if file_path:
            self.selected_file_path = file_path
            filename = os.path.basename(file_path)
            self.file_path_label.setText(f"📄 {filename}")
            
            # Enable send button if client is selected
            if self.selected_client_id:
                self.send_button.setEnabled(True)
            
            self.status_label.setText(f"Đã chọn: {filename}")
    
    def send_file(self):
        """Send selected file to client"""
        if not self.selected_file_path:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn file!")
            return
        
        if not self.selected_client_id:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn client!")
            return
        
        if not os.path.exists(self.selected_file_path):
            QMessageBox.warning(self, "Lỗi", "File không tồn tại!")
            return
        
        # Emit signal
        self.file_send_requested.emit(self.selected_client_id, self.selected_file_path)
        
        # Show progress bar
        self.send_progress.setVisible(True)
        self.send_progress.setValue(0)
        self.status_label.setText(f"Đang gửi: {os.path.basename(self.selected_file_path)}")
        self.send_button.setEnabled(False)
    
    def update_send_progress(self, progress):
        """Update send progress bar"""
        self.send_progress.setValue(progress)
        if progress >= 100:
            # Chỉ hiển thị "đang chờ xác nhận" - thông báo thành công thực sự sẽ đến từ file_transfer_complete
            self.status_label.setText("📤 Đã gửi dữ liệu, đang chờ xác nhận từ server...")
            # Không hide progress bar và reset form ở đây - đợi file_transfer_complete
    
    def on_send_complete(self, filename):
        """Called when server confirms file transfer complete"""
        self.status_label.setText(f"✅ Đã gửi thành công: {filename}")
        self.send_progress.setVisible(False)
        self.reset_send_form()
    
    def reset_send_form(self):
        """Reset send file form"""
        self.file_path_label.setText("Chưa chọn file")
        self.selected_file_path = None
        self.send_button.setEnabled(False)
    
    def add_received_file(self, filename, file_path, sender_id):
        """Add received file to list"""
        item = QListWidgetItem(f"📄 {filename} (từ {sender_id})")
        item.setData(Qt.ItemDataRole.UserRole, file_path)
        self.received_files_list.insertItem(0, item)  # Add to top
        self.status_label.setText(f"✅ Đã nhận: {filename} từ {sender_id}")
    
    def open_received_file(self):
        """Open selected received file"""
        current_item = self.received_files_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn file!")
            return
        
        file_path = current_item.data(Qt.ItemDataRole.UserRole)
        if os.path.exists(file_path):
            os.startfile(file_path)  # Windows specific
            self.status_label.setText("Đã mở file")
        else:
            QMessageBox.warning(self, "Lỗi", "File không tồn tại!")
    
    def open_received_folder(self):
        """Open folder containing received files"""
        current_item = self.received_files_list.currentItem()
        if not current_item:
            # Open default received folder
            folder_path = "manager_received_files"
            if os.path.exists(folder_path):
                os.startfile(folder_path)
                self.status_label.setText("Đã mở thư mục")
            else:
                QMessageBox.warning(self, "Lỗi", "Thư mục không tồn tại!")
            return
        
        file_path = current_item.data(Qt.ItemDataRole.UserRole)
        if os.path.exists(file_path):
            folder_path = os.path.dirname(file_path)
            os.startfile(folder_path)  # Windows specific
            self.status_label.setText("Đã mở thư mục")
        else:
            QMessageBox.warning(self, "Lỗi", "File không tồn tại!")
    
    def show_error(self, error_msg):
        """Show error message"""
        QMessageBox.critical(self, "Lỗi", error_msg)
        self.status_label.setText(f"❌ Lỗi: {error_msg}")
        self.send_progress.setVisible(False)
        self.send_button.setEnabled(True)
