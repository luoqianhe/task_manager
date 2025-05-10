# src/ui/bee_api_dialog.py

# Import the debug utilities
from utils.debug_logger import get_debug_logger
from utils.debug_decorator import debug_method
from os_style_manager import OSStyleManager

# Initialize the debugger
debug = get_debug_logger()
debug.debug("Loading bee_api_dialog.py module")

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit,
                            QPushButton, QFormLayout, QHBoxLayout)
from PyQt6.QtCore import Qt

class BeeApiKeyDialog(QDialog):
    """Dialog to prompt the user for a Bee API key"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Key Required")
        self.setMinimumWidth(400)
        
        # Detect OS
        import platform
        self.os_name = platform.system()
        debug.debug(f"BeeApiKeyDialog detected OS: {self.os_name}")
        
        # Setup UI and apply appropriate styling
        self.setup_ui()
        self.apply_os_style()  
        
    @debug_method
    def setup_ui(self):
        debug.debug("Setting up BeeApiKeyDialog UI")
        layout = QVBoxLayout(self)
        
        # Header
        debug.debug("Creating header label")
        header_label = QLabel("Bee API Key Required")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header_label)
        
        # Description
        debug.debug("Creating description label")
        desc_label = QLabel("Please enter your Bee API key to access your To-Do items.")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Form
        debug.debug("Creating form layout")
        form_layout = QFormLayout()
        
        # API Key input
        debug.debug("Creating API key input field")
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter your Bee API key")
        form_layout.addRow("API Key:", self.api_key_input)
        
        # Key Label input (optional)
        debug.debug("Creating key label input field")
        self.key_label_input = QLineEdit()
        self.key_label_input.setPlaceholderText("Optional descriptive label")
        form_layout.addRow("Key Label:", self.key_label_input)
        
        layout.addLayout(form_layout)
        
        # Help text for label
        debug.debug("Creating help text label")
        label_help = QLabel("(Optional descriptive label)")
        label_help.setStyleSheet("color: #666666; font-style: italic;")
        layout.addWidget(label_help)
        
        # Buttons
        debug.debug("Creating buttons")
        button_layout = QHBoxLayout()
        
        debug.debug("Creating Cancel button")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("secondary", True)  # Mark as secondary button
        cancel_btn.clicked.connect(self.handle_cancel)
        
        debug.debug("Creating Save button")
        save_btn = QPushButton("Save API Key")
        save_btn.setDefault(True)  # Set as default button
        save_btn.clicked.connect(self.handle_save)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        layout.addSpacing(10)
        layout.addLayout(button_layout)
        debug.debug("BeeApiKeyDialog UI setup complete")
        
    def apply_os_style(self):
        """Apply OS-specific styling"""
        
        if self.os_name == "Darwin":  # macOS
            self.apply_macos_style()
        elif self.os_name == "Windows":
            self.apply_windows_style()
        else:  # Linux or other
            self.apply_linux_style()   
    
    @debug_method
    def apply_macos_style(self):
        """Apply macOS-specific styling to the dialog"""
        # Set macOS-style rounded corners and styling
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F7;
                border-radius: 10px;
            }
            QLabel {
                font-family: -apple-system, '.AppleSystemUIFont', 'SF Pro Text';
                color: #1D1D1F;
            }
            QLabel[title="true"] {
                font-weight: 500;
                font-size: 15px;
            }
            QLineEdit {
                border: 1px solid #D2D2D7;
                border-radius: 5px;
                background-color: white;
                padding: 5px 8px;
                height: 24px;
                font-family: -apple-system, '.AppleSystemUIFont';
                selection-background-color: #0071E3;
            }
            QLineEdit:focus {
                border: 1px solid #0071E3;
            }
            QPushButton {
                background-color: #E5E5EA;
                color: #1D1D1F;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                min-width: 80px;
                height: 24px;
                font-family: -apple-system, '.AppleSystemUIFont';
            }
            QPushButton:hover {
                background-color: #D1D1D6;
            }
            QPushButton:pressed {
                background-color: #C7C7CC;
            }
            QPushButton[primary="true"], QPushButton:default {
                background-color: #0071E3;
                color: white;
                font-weight: 500;
            }
            QPushButton[primary="true"]:hover, QPushButton:default:hover {
                background-color: #0077ED;
            }
            QPushButton[primary="true"]:pressed, QPushButton:default:pressed {
                background-color: #0068D1;
            }
        """)
        
        # Adjust content margins for macOS
        self.layout().setContentsMargins(20, 20, 20, 20)
        self.layout().setSpacing(12)
        
        # Make the Save button the default button with primary styling
        save_btn = self.findChild(QPushButton, "", Qt.FindChildOption.FindChildrenRecursively)
        for button in self.findChildren(QPushButton):
            if "Save" in button.text():
                button.setProperty("primary", True)
                button.setDefault(True)
                button.style().unpolish(button)
                button.style().polish(button)

    def apply_windows_style(self):
        """Apply Windows-specific styling to the dialog"""
        # Set Windows-style styling
        self.setStyleSheet("""
            QDialog {
                background-color: #F0F0F0;
            }
            QLabel {
                font-family: 'Segoe UI', sans-serif;
                color: #000000;
            }
            QLabel[title="true"] {
                font-weight: 600;
                font-size: 12px;
            }
            QLineEdit {
                border: 1px solid #CCCCCC;
                border-radius: 2px;
                background-color: white;
                padding: 4px 6px;
                height: 24px;
                font-family: 'Segoe UI';
                selection-background-color: #0078D7;
            }
            QLineEdit:focus {
                border: 1px solid #0078D7;
            }
            QPushButton {
                background-color: #E1E1E1;
                color: #000000;
                border: 1px solid #ADADAD;
                border-radius: 2px;
                padding: 5px 10px;
                min-width: 80px;
                height: 28px;
                font-family: 'Segoe UI';
            }
            QPushButton:hover {
                background-color: #E5F1FB;
                border: 1px solid #0078D7;
            }
            QPushButton:pressed {
                background-color: #CCE4F7;
                border: 1px solid #0078D7;
            }
            QPushButton:default {
                background-color: #0078D7;
                color: white;
                border: 1px solid #0078D7;
            }
            QPushButton:default:hover {
                background-color: #106EBE;
                border: 1px solid #106EBE;
            }
            QPushButton:default:pressed {
                background-color: #005A9E;
                border: 1px solid #005A9E;
            }
        """)
        
        # Adjust content margins for Windows
        self.layout().setContentsMargins(15, 15, 15, 15)
        self.layout().setSpacing(8)

    def apply_linux_style(self):
        """Apply Linux-specific styling to the dialog"""
        # Set Linux (GNOME-inspired) styling
        self.setStyleSheet("""
            QDialog {
                background-color: #F6F5F4;
            }
            QLabel {
                font-family: 'Ubuntu', 'Noto Sans', sans-serif;
                color: #3D3D3D;
            }
            QLabel[title="true"] {
                font-weight: 500;
                font-size: 13px;
            }
            QLineEdit {
                border: 1px solid #C6C6C6;
                border-radius: 4px;
                background-color: white;
                padding: 5px 8px;
                height: 24px;
                font-family: 'Ubuntu', 'Noto Sans';
                selection-background-color: #3584E4;
            }
            QLineEdit:focus {
                border: 1px solid #3584E4;
            }
            QPushButton {
                background-color: #FFFFFF;
                color: #3D3D3D;
                border: 1px solid #C6C6C6;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 80px;
                height: 30px;
                font-family: 'Ubuntu', 'Noto Sans';
            }
            QPushButton:hover {
                background-color: #F2F2F2;
                border: 1px solid #B8B8B8;
            }
            QPushButton:pressed {
                background-color: #E6E6E6;
                border: 1px solid #B8B8B8;
            }
            QPushButton:default {
                background-color: #3584E4;
                color: white;
                border: 1px solid #1E65BD;
            }
            QPushButton:default:hover {
                background-color: #3176CC;
                border: 1px solid #1E65BD;
            }
            QPushButton:default:pressed {
                background-color: #2C68B5;
                border: 1px solid #1E65BD;
            }
        """)
        
        # Adjust content margins for Linux
        self.layout().setContentsMargins(18, 18, 18, 18)
        self.layout().setSpacing(10)    

    
    def get_api_key(self):
        """Get the entered API key"""
        api_key = self.api_key_input.text().strip()
        debug.debug(f"Returning API key (length: {len(api_key)})")
        return api_key
    
    @debug_method
    def get_key_label(self):
        """Get the entered key label"""
        label = self.key_label_input.text().strip()
        debug.debug(f"Returning key label: '{label}'")
        return label

    @debug_method
    def handle_save(self, checked=False):
        """Handle the Save button click"""
        debug.debug("Save button clicked")
        api_key = self.get_api_key()
        
        if not api_key:
            debug.debug("API key is empty, showing warning")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, 
                "Missing API Key", 
                "Please enter a valid API key to continue."
            )
            return
            
        debug.debug("API key provided, accepting dialog")
        self.accept()
        
    @debug_method
    def handle_cancel(self):
        """Handle the Cancel button click"""
        debug.debug("Cancel button clicked")
        self.reject()
        
    @debug_method
    def keyPressEvent(self, event):
        """Handle key press events"""
        debug.debug(f"Key press event: {event.key()}")
        
        # Check for Enter key
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            debug.debug("Enter key pressed, checking API key")
            api_key = self.get_api_key()
            
            if api_key:
                debug.debug("API key provided, accepting dialog")
                self.accept()
            else:
                debug.debug("API key is empty, showing warning")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self, 
                    "Missing API Key", 
                    "Please enter a valid API key to continue."
                )
        # Check for Escape key
        elif event.key() == Qt.Key.Key_Escape:
            debug.debug("Escape key pressed, rejecting dialog")
            self.reject()
        else:
            debug.debug("Passing key event to parent")
            super().keyPressEvent(event)