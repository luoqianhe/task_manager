# Required imports
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QPushButton, QLabel, QHeaderView, QKeySequenceEdit, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence

# Import debug utilities
from utils.debug_logger import get_debug_logger
from utils.debug_decorator import debug_method

# Get debug logger instance
debug = get_debug_logger()

class KeyboardShortcutsDialog(QDialog):
    """Dialog for editing keyboard shortcuts"""
    
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    def __init__(self, settings, main_window, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.main_window = main_window
        self.settings = settings
        self.shortcuts_data = {}
        self.modified_shortcuts = {}
        
        self.setWindowTitle("Edit Keyboard Shortcuts")
        self.setModal(True)
        self.resize(500, 400)
        
        self.setup_ui()
        self.load_current_shortcuts()
        
    @debug_method
    def setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)
        
        # Shortcuts table - REMOVED HEADERS AND ROW NUMBERS
        self.shortcuts_table = QTableWidget()
        self.shortcuts_table.setColumnCount(3)
        # Remove column headers
        self.shortcuts_table.horizontalHeader().setVisible(False)
        # Remove row numbers (vertical header)
        self.shortcuts_table.verticalHeader().setVisible(False)
        
        # Set column widths
        header = self.shortcuts_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.shortcuts_table.setColumnWidth(1, 150)
        self.shortcuts_table.setColumnWidth(2, 80)
        
        layout.addWidget(self.shortcuts_table)
        
        # Bottom buttons layout - ALL ON SAME ROW
        button_layout = QHBoxLayout()
        
        # Reset to Defaults button
        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_button)
        
        # Add stretch to push Save/Cancel to the right
        button_layout.addStretch()
        
        # Save button
        self.save_button = QPushButton("Save")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.save_shortcuts)
        button_layout.addWidget(self.save_button)
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
    @debug_method
    def populate_table(self):
        """Populate the shortcuts table"""
        self.shortcuts_table.setRowCount(len(self.shortcuts_data))
        
        for row, (key, data) in enumerate(self.shortcuts_data.items()):
            # Action description
            desc_item = QTableWidgetItem(data["description"])
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.shortcuts_table.setItem(row, 0, desc_item)
            
            # Current shortcut
            shortcut_item = QTableWidgetItem(data["sequence"])
            shortcut_item.setFlags(shortcut_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.shortcuts_table.setItem(row, 1, shortcut_item)
            
            # Change button (replacing Edit button)
            change_button = QPushButton("Change")
            change_button.setProperty("fontSettings", True)  # Use same styling as font settings
            change_button.clicked.connect(lambda checked, k=key: self.edit_shortcut(k))
            self.shortcuts_table.setCellWidget(row, 2, change_button)
            
    @debug_method
    def get_default_shortcuts(self):
        """Get the default keyboard shortcuts based on OS"""
        import platform
        
        # Determine modifier key based on OS
        if platform.system() == "Darwin":  # macOS
            modifier = "Cmd"
        else:  # Windows and Linux
            modifier = "Ctrl"
        
        return {
            "new_task": {"sequence": f"{modifier}+N", "description": "Add New Task", "action": "show_add_dialog"},
            "edit_task": {"sequence": f"{modifier}+E", "description": "Edit Selected Task", "action": "edit_selected_task"},
            "settings": {"sequence": f"{modifier}+S", "description": "Open Settings", "action": "show_settings"},
            "import_csv": {"sequence": f"{modifier}+I", "description": "Import from CSV", "action": "import_from_csv"},
            "export_csv": {"sequence": f"{modifier}+X", "description": "Export to CSV", "action": "export_to_csv"},
            "tab_current": {"sequence": f"{modifier}+1", "description": "Current Tasks Tab", "action": "lambda: self.tabs.setCurrentIndex(0)"},
            "tab_backlog": {"sequence": f"{modifier}+2", "description": "Backlog Tab", "action": "lambda: self.tabs.setCurrentIndex(1)"},
            "tab_completed": {"sequence": f"{modifier}+3", "description": "Completed Tasks Tab", "action": "lambda: self.tabs.setCurrentIndex(2)"},
            "delete_task": {"sequence": "Del", "description": "Delete Selected Task", "action": "delete_selected_task"},
            "refresh": {"sequence": "F5", "description": "Refresh Task List", "action": "refresh_tasks"},
        }
    
    @debug_method
    def load_current_shortcuts(self):
        """Load current shortcuts from settings"""
        default_shortcuts = self.get_default_shortcuts()
        
        # Load saved shortcuts or use defaults
        for key, data in default_shortcuts.items():
            saved_sequence = self.settings.get_setting(f"shortcut_{key}", data["sequence"])
            self.shortcuts_data[key] = {
                "sequence": saved_sequence,
                "description": data["description"],
                "action": data["action"]
            }
        
        self.populate_table()
        
    @debug_method
    def edit_shortcut(self, shortcut_key):
        """Edit a specific shortcut"""
        debug.debug(f"Editing shortcut: {shortcut_key}")
        
        current_sequence = self.shortcuts_data[shortcut_key]["sequence"]
        description = self.shortcuts_data[shortcut_key]["description"]
        
        # Create edit dialog
        edit_dialog = QDialog(self)
        edit_dialog.setWindowTitle(f"Edit Shortcut - {description}")
        edit_dialog.setModal(True)
        edit_dialog.resize(350, 150)
        
        layout = QVBoxLayout(edit_dialog)
        
        # Description
        desc_label = QLabel(f"Set keyboard shortcut for: {description}")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Key sequence editor
        key_edit = QKeySequenceEdit()
        key_edit.setKeySequence(QKeySequence(current_sequence))
        layout.addWidget(key_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(lambda: key_edit.setKeySequence(QKeySequence()))
        
        ok_button = QPushButton("OK")
        ok_button.setDefault(True)
        ok_button.clicked.connect(edit_dialog.accept)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(edit_dialog.reject)
        
        button_layout.addWidget(clear_button)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        if edit_dialog.exec() == QDialog.DialogCode.Accepted:
            new_sequence = key_edit.keySequence().toString()
            
            # Check for conflicts
            if self.check_shortcut_conflict(shortcut_key, new_sequence):
                return
                
            # Update the shortcut
            self.shortcuts_data[shortcut_key]["sequence"] = new_sequence
            self.modified_shortcuts[shortcut_key] = new_sequence
            self.populate_table()
            
            debug.debug(f"Updated shortcut {shortcut_key} to {new_sequence}")
            
    @debug_method
    def check_shortcut_conflict(self, current_key, new_sequence):
        """Check if the new shortcut conflicts with existing ones"""
        if not new_sequence:  # Empty sequence is OK
            return False
            
        for key, data in self.shortcuts_data.items():
            if key != current_key and data["sequence"] == new_sequence:
                QMessageBox.warning(
                    self,
                    "Shortcut Conflict",
                    f"The shortcut '{new_sequence}' is already used for '{data['description']}'.\n\n"
                    "Please choose a different shortcut."
                )
                return True
        return False
        
    @debug_method
    def reset_to_defaults(self):
        """Reset all shortcuts to defaults"""
        reply = QMessageBox.question(
            self,
            "Reset Shortcuts",
            "Are you sure you want to reset all keyboard shortcuts to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            default_shortcuts = self.get_default_shortcuts()
            for key, data in default_shortcuts.items():
                self.shortcuts_data[key]["sequence"] = data["sequence"]
                self.modified_shortcuts[key] = data["sequence"]
            
            self.populate_table()
            debug.debug("Reset all shortcuts to defaults")
    
    @debug_method
    def save_shortcuts(self):
        """Save modified shortcuts to settings"""
        debug.debug("Saving shortcuts to settings")
        
        for key, sequence in self.modified_shortcuts.items():
            self.settings.set_setting(f"shortcut_{key}", sequence)
            debug.debug(f"Saved shortcut {key}: {sequence}")
        
        # Notify parent to update shortcuts if there's a method for it
        if hasattr(self.parent(), 'update_shortcuts'):
            self.parent().update_shortcuts()
        
        self.accept()