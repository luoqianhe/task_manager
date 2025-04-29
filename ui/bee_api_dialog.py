# src/ui/bee_api_dialog.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit,
                            QPushButton, QFormLayout, QHBoxLayout)
from PyQt6.QtCore import Qt

class BeeApiKeyDialog(QDialog):
    """Dialog to prompt the user for a Bee API key"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Key Required")
        self.setMinimumWidth(400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Bee API Key Required")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header_label)
        
        # Description
        desc_label = QLabel("Please enter your Bee API key to access your To-Do items.")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Form
        form_layout = QFormLayout()
        
        # API Key input
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter your Bee API key")
        form_layout.addRow("API Key:", self.api_key_input)
        
        # Key Label input (optional)
        self.key_label_input = QLineEdit()
        self.key_label_input.setPlaceholderText("Optional descriptive label")
        form_layout.addRow("Key Label:", self.key_label_input)
        
        layout.addLayout(form_layout)
        
        # Help text for label
        label_help = QLabel("(Optional descriptive label)")
        label_help.setStyleSheet("color: #666666; font-style: italic;")
        layout.addWidget(label_help)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Save API Key")
        save_btn.clicked.connect(self.accept)
        save_btn.setDefault(True)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        layout.addSpacing(10)
        layout.addLayout(button_layout)
    
    def get_api_key(self):
        """Get the entered API key"""
        return self.api_key_input.text().strip()
    
    def get_key_label(self):
        """Get the entered key label"""
        return self.key_label_input.text().strip()