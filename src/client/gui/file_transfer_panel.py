"""
Client File Transfer Panel
Giao diện để client gửi và nhận file
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFileDialog, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import os
from datetime import datetime


class ClientFileTransferPanel(QWidget):
    """Panel để client gửi và nhận file"""
    
    # Signal để gửi file
    file_send_requested = pyqtSignal(str, str)  # (target_id, filepath)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_file = None
        # Sử dụng đường dẫn tuyệt đối
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.received_files_dir = os.path.join(base_dir, "src", "client", "file_transfer", "received")
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(self.received_files_dir, exist_ok=True)
        self.init_ui()
        self.load_received_files()
        
    def init_ui(self):
        """Khởi tạo giao diện"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # === SEND FILE SECTION ===
        send_section = QWidget()
        send_layout = QVBoxLayout()
        send_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        send_title = QLabel("📤 Send File to Manager")
        send_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        send_title.setStyleSheet("color: #1DB954; margin-bottom: 10px;")
        send_layout.addWidget(send_title)
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("""
            QLabel {
                background-color: #282828;
                color: #B3B3B3;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #404040;
            }
        """)
        file_layout.addWidget(self.file_label, 1)
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1ED760;
            }
            QPushButton:pressed {
                background-color: #169C46;
            }
        """)
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_btn)
        
        send_layout.addLayout(file_layout)
        
        # Send button
        self.send_btn = QPushButton("Send File")
        self.send_btn.setEnabled(False)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover:enabled {
                background-color: #1ED760;
            }
            QPushButton:pressed:enabled {
                background-color: #169C46;
            }
            QPushButton:disabled {
                background-color: #404040;
                color: #808080;
            }
        """)
        self.send_btn.clicked.connect(self.send_file)
        send_layout.addWidget(self.send_btn)
        
        # Status label (thay thế progress bar)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #1DB954;
                font-size: 11pt;
                padding: 8px;
                font-weight: bold;
            }
        """)
        send_layout.addWidget(self.status_label)
        
        send_section.setLayout(send_layout)
        send_section.setStyleSheet("""
            QWidget {
                background-color: #181818;
                border-radius: 8px;
            }
        """)
        layout.addWidget(send_section)
        
        # === RECEIVED FILES SECTION ===
        received_section = QWidget()
        received_layout = QVBoxLayout()
        received_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        received_title = QLabel("📥 Received Files")
        received_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        received_title.setStyleSheet("color: #1DB954; margin-bottom: 10px;")
        received_layout.addWidget(received_title)
        
        # Files list
        self.files_list = QListWidget()
        self.files_list.setStyleSheet("""
            QListWidget {
                background-color: #282828;
                border: 1px solid #404040;
                border-radius: 4px;
                color: #B3B3B3;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px;
            }
            QListWidget::item:hover {
                background-color: #333333;
            }
            QListWidget::item:selected {
                background-color: #1DB954;
                color: white;
            }
        """)
        received_layout.addWidget(self.files_list)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        self.open_file_btn = QPushButton("Open File")
        self.open_file_btn.setEnabled(False)
        self.open_file_btn.setStyleSheet(self._get_button_style())
        self.open_file_btn.clicked.connect(self.open_selected_file)
        buttons_layout.addWidget(self.open_file_btn)
        
        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.setStyleSheet(self._get_button_style())
        self.open_folder_btn.clicked.connect(self.open_received_folder)
        buttons_layout.addWidget(self.open_folder_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet(self._get_button_style())
        self.refresh_btn.clicked.connect(self.load_received_files)
        buttons_layout.addWidget(self.refresh_btn)
        
        received_layout.addLayout(buttons_layout)
        
        received_section.setLayout(received_layout)
        received_section.setStyleSheet("""
            QWidget {
                background-color: #181818;
                border-radius: 8px;
            }
        """)
        layout.addWidget(received_section)
        
        # Connect list selection
        self.files_list.itemSelectionChanged.connect(self._on_file_selected)
        
        self.setLayout(layout)
        
    def _get_button_style(self):
        """Style cho buttons"""
        return """
            QPushButton {
                background-color: #404040;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #505050;
            }
            QPushButton:pressed:enabled {
                background-color: #303030;
            }
            QPushButton:disabled {
                background-color: #282828;
                color: #606060;
            }
        """
        
    def browse_file(self):
        """Chọn file để gửi"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Send",
            "",
            "All Files (*.*)"
        )
        
        if file_path:
            self.selected_file = file_path
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            size_str = self._format_file_size(file_size)
            self.file_label.setText(f"{filename} ({size_str})")
            self.send_btn.setEnabled(True)
            
    def send_file(self):
        """Gửi file đã chọn"""
        if not self.selected_file:
            return
        
        # Target ID = "server" (server sẽ forward đến manager hiện tại)
        target_id = "server"
        
        # Lưu tên file trước khi reset
        filename = os.path.basename(self.selected_file)
        
        # Emit signal để gửi file
        self.file_send_requested.emit(target_id, self.selected_file)
        
        # Hiển thị thành công ngay lập tức
        self.status_label.setStyleSheet("color: #1DB954; font-size: 11pt; padding: 8px; font-weight: bold;")
        self.status_label.setText(f"✅ Đã gửi: {filename}")
        
        # Reset form
        self.file_label.setText("No file selected")
        self.selected_file = None
        self.send_btn.setEnabled(False)
        
    def update_progress(self, progress: int):
        """Cập nhật trạng thái gửi file"""
        if progress >= 100:
            # Gửi thành công
            self.status_label.setStyleSheet("color: #1DB954; font-size: 11pt; padding: 8px; font-weight: bold;")
            self.status_label.setText("✅ Gửi file thành công!")
            self.send_btn.setEnabled(True)
            self.file_label.setText("No file selected")
            self.selected_file = None
    
    def show_error(self, error_msg: str):
        """Hiển thị lỗi"""
        self.status_label.setStyleSheet("color: #FF4444; font-size: 11pt; padding: 8px; font-weight: bold;")
        self.status_label.setText(f"❌ Lỗi: {error_msg}")
        self.send_btn.setEnabled(True)
            
    def load_received_files(self):
        """Load danh sách file đã nhận"""
        self.files_list.clear()
        
        if not os.path.exists(self.received_files_dir):
            os.makedirs(self.received_files_dir, exist_ok=True)
            return
        
        files = []
        for filename in os.listdir(self.received_files_dir):
            filepath = os.path.join(self.received_files_dir, filename)
            if os.path.isfile(filepath):
                size = os.path.getsize(filepath)
                mtime = os.path.getmtime(filepath)
                files.append((filename, size, mtime, filepath))
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x[2], reverse=True)
        
        for filename, size, mtime, filepath in files:
            size_str = self._format_file_size(size)
            time_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            
            item = QListWidgetItem(f"📄 {filename}\n   {size_str} • {time_str}")
            item.setData(Qt.ItemDataRole.UserRole, filepath)
            self.files_list.addItem(item)
            
    def _on_file_selected(self):
        """Khi chọn file trong list"""
        self.open_file_btn.setEnabled(len(self.files_list.selectedItems()) > 0)
        
    def open_selected_file(self):
        """Mở file đã chọn"""
        items = self.files_list.selectedItems()
        if not items:
            return
        
        filepath = items[0].data(Qt.ItemDataRole.UserRole)
        if os.path.exists(filepath):
            os.startfile(filepath)
            
    def open_received_folder(self):
        """Mở thư mục chứa file đã nhận"""
        if os.path.exists(self.received_files_dir):
            os.startfile(self.received_files_dir)
        else:
            os.makedirs(self.received_files_dir, exist_ok=True)
            os.startfile(self.received_files_dir)
            
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def add_received_file(self, filename: str):
        """Thêm file mới vào list"""
        self.load_received_files()
