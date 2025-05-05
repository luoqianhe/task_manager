# src/ui/bee_api_dialog.py

# Import the debug utilities
from utils.debug_logger import get_debug_logger
from utils.debug_decorator import debug_method

# Initialize the debugger
debug = get_debug_logger()
debug.debug("Loading bee_api_dialog.py module")

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit,
                            QPushButton, QFormLayout, QHBoxLayout)
from PyQt6.QtCore import Qt

class BeeApiKeyDialog(QDialog):
    """Dialog to prompt the user for a Bee API key"""
    
    @debug_method
    def __init__(self, parent=None):
        debug.debug("Initializing BeeApiKeyDialog")
        super().__init__(parent)
        self.setWindowTitle("API Key Required")
        self.setMinimumWidth(400)
        debug.debug("Setting up UI components")
        self.setup_ui()
        debug.debug("BeeApiKeyDialog initialization complete")
        
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
        cancel_btn.clicked.connect(self.handle_cancel)
        
        debug.debug("Creating Save button")
        save_btn = QPushButton("Save API Key")
        save_btn.clicked.connect(self.handle_save)
        save_btn.setDefault(True)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        layout.addSpacing(10)
        layout.addLayout(button_layout)
        debug.debug("BeeApiKeyDialog UI setup complete")
    
    @debug_method
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
    def handle_save(self):
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