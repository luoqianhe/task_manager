# src/ui/app_settings.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QFileDialog, QMessageBox, QLabel, QCheckBox, 
                           QGroupBox, QFormLayout, QLineEdit, QSpinBox)
from pathlib import Path
import json
import shutil
import sqlite3
import sys

class SettingsManager:
    def __init__(self):
        # Define the settings file location in the user's home directory
        self.settings_dir = Path.home() / ".task_organizer"
        self.settings_file = self.settings_dir / "settings.json"
        
        # Default settings
        self.default_settings = {
            "database_path": str(Path.home() / "Documents" / "TaskOrganizer" / "task_manager.db"),
            "theme": "light",
            "auto_backup": False,
            "backup_interval_days": 7
        }
        
        # Ensure settings directory exists
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or create settings
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Load settings from the JSON file or create default settings if the file doesn't exist."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # If settings file is corrupted, use defaults
                return self.default_settings
        else:
            # Create new settings file with defaults
            self.save_settings(self.default_settings)
            return self.default_settings
    
    def save_settings(self, settings):
        """Save settings to the JSON file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            return True
        except IOError:
            return False
    
    def get_setting(self, key, default=None):
        """Get a setting value by key."""
        return self.settings.get(key, default)
    
    def set_setting(self, key, value):
        """Set a setting value and save to file."""
        self.settings[key] = value
        return self.save_settings(self.settings)
    
    def prompt_for_database_location(self, parent_widget=None):
        """
        Prompt the user to choose a database location if not already set.
        Returns the database path.
        """
        # Check if this is first run (no database path set or default still being used)
        db_path = Path(self.get_setting("database_path"))
        default_db_path = Path(self.default_settings["database_path"])
        
        if db_path == default_db_path and not db_path.exists():
            # First run, prompt for location
            msg = "Choose where to store your tasks database. Choose a location that's backed up regularly."
            QMessageBox.information(parent_widget, "Database Location", msg)
            
            # Get directory from user
            suggested_dir = db_path.parent
            db_dir = QFileDialog.getExistingDirectory(
                parent_widget, 
                "Select Database Directory", 
                str(suggested_dir)
            )
            
            if db_dir:  # User selected a directory
                # Create full path including filename
                new_db_path = Path(db_dir) / "task_manager.db"
                
                # Save the new path
                self.set_setting("database_path", str(new_db_path))
                
                # Create directory if it doesn't exist
                new_db_path.parent.mkdir(parents=True, exist_ok=True)
                
                return str(new_db_path)
            else:  # User cancelled, use default
                # Create directory if it doesn't exist
                db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Return the current path
        return str(db_path)


class AppSettingsWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.settings = main_window.settings
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create a horizontal layout for the two main panels
        panels_layout = QHBoxLayout()
        
        # Left panel: Database location
        db_group = QGroupBox("Database")
        db_layout = QFormLayout()
        
        # Current database location
        current_db = self.settings.get_setting("database_path")
        db_location = QLabel(f"Current location: {current_db}")
        db_layout.addRow(db_location)
        
        # Change location button
        change_db_btn = QPushButton("Change Database Location")
        change_db_btn.setFixedHeight(30)
        change_db_btn.clicked.connect(self.change_database_location)
        db_layout.addRow(change_db_btn)
        
        db_group.setLayout(db_layout)
        
        # Right panel: Import/Export
        csv_group = QGroupBox("Import/Export")
        csv_layout = QFormLayout()
        
        template_button = QPushButton("Import Template")
        template_button.setFixedHeight(30)
        template_button.clicked.connect(self.main_window.save_template)
        csv_layout.addRow("Get template CSV:", template_button)
        
        export_button = QPushButton("Export to CSV")
        export_button.setFixedHeight(30)
        export_button.clicked.connect(self.main_window.export_to_csv)
        csv_layout.addRow("Export tasks:", export_button)
        
        import_button = QPushButton("Import from CSV")
        import_button.setFixedHeight(30)
        import_button.clicked.connect(self.main_window.import_from_csv)
        csv_layout.addRow("Import tasks:", import_button)
        
        csv_group.setLayout(csv_layout)
        
        # Add both panels to the horizontal layout
        panels_layout.addWidget(db_group)
        panels_layout.addWidget(csv_group)
        
        # Add the panels layout to the main layout
        layout.addLayout(panels_layout)
        
        # Bee API Settings group with reduced width
        if hasattr(self.main_window, 'settings'):
            bee_container = QHBoxLayout()
            
            bee_api_group = QGroupBox("Bee API Settings")
            bee_api_layout = QVBoxLayout()
            
            # Get API key and label from settings
            api_key = self.settings.get_setting("bee_api_key", "")
            api_key_label = self.settings.get_setting("bee_api_key_label", "")
            
            if api_key:
                # Display API key label or a default message
                display_text = f'API Key: "{api_key_label}"' if api_key_label else "API Key: [Configured]"
                key_label = QLabel(display_text)
                bee_api_layout.addWidget(key_label)
                
                # Delete button
                delete_btn = QPushButton("Delete API Key")
                delete_btn.setFixedHeight(30)
                delete_btn.clicked.connect(self.delete_bee_api_key)
                bee_api_layout.addWidget(delete_btn)
            else:
                # No API key configured
                key_label = QLabel("No Bee API key configured")
                bee_api_layout.addWidget(key_label)
                
                # Add button
                add_btn = QPushButton("Add API Key")
                add_btn.setFixedHeight(30)
                add_btn.clicked.connect(self.add_bee_api_key)
                bee_api_layout.addWidget(add_btn)
            
            bee_api_group.setLayout(bee_api_layout)
            
            # Add the Bee API group to a container with additional space to make it half-width
            bee_container.addWidget(bee_api_group)
            bee_container.addStretch()  # This makes the group take only half the width
            layout.addLayout(bee_container)
        
        # Add stretch to push Done button to bottom
        layout.addStretch()
        
        # Save and Cancel buttons - keep these at the bottom
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Save Settings")
        save_button.setFixedHeight(30)
        save_button.setMinimumWidth(120)  # Make sure buttons are the same size
        save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(save_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setFixedHeight(30)
        cancel_button.setMinimumWidth(120)  # Make sure buttons are the same size
        cancel_button.clicked.connect(self.main_window.show_task_view)  # Go back without saving
        button_layout.addWidget(cancel_button)
        
        button_layout.addStretch()  # This pushes buttons to the left
        
        layout.addLayout(button_layout)
    
    def save_settings(self):
        QMessageBox.information(self, "Settings Saved", "Your settings have been saved.")
    
    def change_database_location(self):
        current_path = Path(self.settings.get_setting("database_path"))
        db_dir = QFileDialog.getExistingDirectory(
            self, "Select Database Directory", str(current_path.parent))
        
        if db_dir:
            new_path = Path(db_dir) / current_path.name
            
            # Ask if user wants to copy existing database
            if current_path.exists():
                reply = QMessageBox.question(self, 'Move Database', 
                                            'Do you want to copy the existing database to the new location?',
                                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    try:
                        # Create directory if it doesn't exist
                        new_path.parent.mkdir(parents=True, exist_ok=True)
                        # Copy database
                        shutil.copy2(current_path, new_path)
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to copy database: {str(e)}")
                        return
            
            # Save the new database location
            self.settings.set_setting("database_path", str(new_path))
            
            # Update UI
            QMessageBox.information(self, "Database Location Changed", 
                                   "Database location has been changed. The application will need to be restarted.")       
    
    def delete_bee_api_key(self):
        """Delete the stored Bee API key"""
        from PyQt6.QtWidgets import QMessageBox
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete your Bee API key? " +
            "You'll need to enter it again to access your Bee To-Dos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Delete key from settings
            self.settings.set_setting("bee_api_key", "")
            self.settings.set_setting("bee_api_key_label", "")
            
            # Refresh the UI
            self.setup_ui()
            
            QMessageBox.information(self, "API Key Deleted", "Your Bee API key has been deleted.")

    def add_bee_api_key(self):
        """Add a new Bee API key"""
        from ui.bee_api_dialog import BeeApiKeyDialog
        
        dialog = BeeApiKeyDialog(self)
        if dialog.exec():
            # Get key and label
            api_key = dialog.get_api_key()
            key_label = dialog.get_key_label()
            
            if api_key:
                # Save to settings
                self.settings.set_setting("bee_api_key", api_key)
                if key_label:
                    self.settings.set_setting("bee_api_key_label", key_label)
                
                # Refresh the UI
                self.setup_ui()