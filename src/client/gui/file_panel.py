"""
File Transfer Panel - Manages file sending and receiving
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QFileDialog, QListWidget, QListWidgetItem, QMessageBox,
    QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from .components import (
    StyledButton, StyledLabel, StyledLineEdit, 
    StyledTextEdit, PanelFrame, StatusLabel
)
import os


class FileTransferPanel(QWidget):
    """Panel for file transfer functionality"""
    
    # Signals
    file_selected = pyqtSignal(str, str)  # Emits (target_id, file_path) to be sent
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.target_id = "server"  # Client sends to server, which forwards to manager
        self.received_files_dir = "src/client/file_transfer/received"
        self.init_ui()
    
    def init_ui(self):
        """Initialize file transfer panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title
        title = StyledLabel("Truyền File", style_type="title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Send file section
        send_frame = PanelFrame()
        send_layout = QVBoxLayout(send_frame)
        
        send_title = StyledLabel("Gửi File", style_type="subtitle")
        send_layout.addWidget(send_title)
        
        # File selection
        file_select_layout = QHBoxLayout()
        
        self.file_path_input = StyledLineEdit("Chọn file để gửi...")
        self.file_path_input.setReadOnly(True)
        file_select_layout.addWidget(self.file_path_input, stretch=1)
        
        self.browse_button = StyledButton("Chọn File", style_type="secondary")
        self.browse_button.clicked.connect(self.browse_file)
        self.browse_button.setFixedWidth(120)
        file_select_layout.addWidget(self.browse_button)
        
        send_layout.addLayout(file_select_layout)
        
        # Send button
        self.send_file_button = StyledButton("Gửi File", style_type="primary")
        self.send_file_button.clicked.connect(self.send_file)
        self.send_file_button.setEnabled(False)
        send_layout.addWidget(self.send_file_button)
        
        # Progress bar for sending
        self.send_progress = QProgressBar()
        self.send_progress.setVisible(False)
        send_layout.addWidget(self.send_progress)
        
        layout.addWidget(send_frame)
        
        # Receive file section
        receive_frame = PanelFrame()
        receive_layout = QVBoxLayout(receive_frame)
        
        receive_title = StyledLabel("File Đã Nhận", style_type="subtitle")
        receive_layout.addWidget(receive_title)
        
        # List of received files
        self.received_files_list = QListWidget()
        self.received_files_list.setMinimumHeight(150)
        self.received_files_list.setStyleSheet("""
            QListWidget {
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 5px;
                background-color: white;
            }
        """)
        receive_layout.addWidget(self.received_files_list)
        
        # Buttons for received files
        received_buttons_layout = QHBoxLayout()
        
        self.open_file_button = StyledButton("Mở File", style_type="secondary")
        self.open_file_button.clicked.connect(self.open_received_file)
        received_buttons_layout.addWidget(self.open_file_button)
        
        self.open_folder_button = StyledButton("Mở Thư Mục", style_type="secondary")
        self.open_folder_button.clicked.connect(self.open_received_folder)
        received_buttons_layout.addWidget(self.open_folder_button)
        
        receive_layout.addLayout(received_buttons_layout)
        
        layout.addWidget(receive_frame)
        
        # Status label
        self.status_label = StatusLabel()
        layout.addWidget(self.status_label)
        
        # Add stretch at the end
        layout.addStretch()
        
        # Store selected file path
        self.selected_file_path = None
    
    def browse_file(self):
        """Open file dialog to select file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn File",
            "",
            "All Files (*.*)"
        )
        
        if file_path:
            self.selected_file_path = file_path
            self.file_path_input.setText(file_path)
            self.send_file_button.setEnabled(True)
            self.status_label.show_normal(f"Đã chọn: {os.path.basename(file_path)}")
    
    def send_file(self):
        """Send selected file"""
        if not self.selected_file_path:
            self.status_label.show_error("Vui lòng chọn file!")
            return
        
        if not os.path.exists(self.selected_file_path):
            self.status_label.show_error("File không tồn tại!")
            return
        
        if not self.target_id:
            self.status_label.show_error("Chưa kết nối đến đích!")
            return
        
        # Emit signal with target_id and file_path
        self.file_selected.emit(self.target_id, self.selected_file_path)
        self.status_label.show_success(f"Đang gửi: {os.path.basename(self.selected_file_path)}")
        
        # Show progress bar
        self.send_progress.setVisible(True)
        self.send_progress.setValue(0)
    
    def update_send_progress(self, progress):
        """Update send progress bar"""
        self.send_progress.setValue(progress)
        if progress >= 100:
            self.status_label.show_success("Gửi file thành công!")
            self.send_progress.setVisible(False)
            self.reset_send_form()
    
    def reset_send_form(self):
        """Reset send file form"""
        self.file_path_input.clear()
        self.selected_file_path = None
        self.send_file_button.setEnabled(False)
    
    def add_received_file(self, filename, file_path=None):
        """Add received file to list"""
        # If file_path not provided, construct from received_files_dir
        if not file_path:
            file_path = os.path.join(self.received_files_dir, filename)
        
        item = QListWidgetItem(f"📄 {filename}")
        item.setData(Qt.ItemDataRole.UserRole, file_path)
        self.received_files_list.insertItem(0, item)  # Insert at top (newest first)
        self.status_label.show_success(f"Đã nhận: {filename}")
    
    def open_received_file(self):
        """Open selected received file"""
        current_item = self.received_files_list.currentItem()
        if not current_item:
            self.status_label.show_warning("Vui lòng chọn file!")
            return
        
        file_path = current_item.data(Qt.ItemDataRole.UserRole)
        if os.path.exists(file_path):
            os.startfile(file_path)  # Windows specific
            self.status_label.show_success("Đã mở file")
        else:
            self.status_label.show_error("File không tồn tại!")
    
    def open_received_folder(self):
        """Open folder containing received files"""
        current_item = self.received_files_list.currentItem()
        if not current_item:
            self.status_label.show_warning("Vui lòng chọn file!")
            return
        
        file_path = current_item.data(Qt.ItemDataRole.UserRole)
        if os.path.exists(file_path):
            folder_path = os.path.dirname(file_path)
            os.startfile(folder_path)  # Windows specific
            self.status_label.show_success("Đã mở thư mục")
        else:
            self.status_label.show_error("File không tồn tại!")
    
    def set_enabled(self, enabled):
        """Enable or disable file transfer controls"""
        self.browse_button.setEnabled(enabled)
        if self.selected_file_path and self.target_id:
            self.send_file_button.setEnabled(enabled)
        
        if not enabled:
            self.status_label.show_warning("Chưa kết nối đến server")
    
    def set_target(self, target_id: str):
        """Set target ID for file transfer"""
        self.target_id = target_id
        if self.selected_file_path:
            self.send_file_button.setEnabled(True)
