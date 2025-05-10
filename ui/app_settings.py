# src/ui/app_settings.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QFileDialog, QMessageBox, QLabel, QCheckBox, 
                           QGroupBox, QFormLayout, QLineEdit, QSpinBox)
from pathlib import Path
import json
import shutil
import sqlite3
import sys

# Import the debug logger
from utils.debug_logger import get_debug_logger
debug = get_debug_logger()

class SettingsManager:
    def __init__(self):
        debug.debug("Initializing SettingsManager")
        # Define the settings file location in the user's home directory
        self.settings_dir = Path.home() / ".task_organizer"
        self.settings_file = self.settings_dir / "settings.json"
        debug.debug(f"Settings file: {self.settings_file}")
        
        # Default settings
        self.default_settings = {
            "database_path": str(Path.home() / "Documents" / "TaskOrganizer" / "task_manager.db"),
            "theme": "light",
            "auto_backup": False,
            "backup_interval_days": 7,
            "left_panel_contents": [],
            "right_panel_contents": [],
            "left_panel_width": 100,
            "right_panel_width": 100,
            "left_panel_sections": 2,
            "right_panel_sections": 2,
            "debug_enabled": False  # Added debug_enabled setting with default value
        }
        debug.debug(f"Default settings: {self.default_settings}")
        
        # Ensure settings directory exists
        debug.debug(f"Ensuring settings directory exists: {self.settings_dir}")
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or create settings
        debug.debug("Loading settings")
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Load settings from the JSON file or create default settings if the file doesn't exist."""
        debug.debug(f"Loading settings from {self.settings_file}")
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    debug.debug(f"Settings loaded successfully: {settings}")
                    return settings
            except json.JSONDecodeError as e:
                debug.error(f"Error loading settings file (JSON decode error): {e}")
                # Additional details for debugging
                import traceback
                traceback.print_exc()
                # If settings file is corrupted, use defaults
                debug.debug("Using default settings due to JSON decode error")
                return self.default_settings
            except IOError as e:
                debug.error(f"Error loading settings file (IO error): {e}")
                # Additional details for debugging
                import traceback
                traceback.print_exc()
                # If settings file can't be read, use defaults
                debug.debug("Using default settings due to IO error")
                return self.default_settings
        else:
            # Create new settings file with defaults
            debug.debug("Settings file doesn't exist, creating with defaults")
            self.save_settings(self.default_settings)
            return self.default_settings
    
    def save_settings(self, settings):
        """Save settings to the JSON file."""
        debug.debug(f"Saving settings to {self.settings_file}")
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            
            debug.debug(f"Settings values: left_panel_contents={settings.get('left_panel_contents', [])}, right_panel_contents={settings.get('right_panel_contents', [])}")
            debug.debug(f"Settings saved to {self.settings_file}")
            return True
        except IOError as e:
            debug.error(f"Error saving settings: {e}")
            return False
    
    def get_setting(self, key, default=None):
        """Get a setting value by key."""
        value = self.settings.get(key, default)
        debug.debug(f"Getting setting: {key} = {value}")
        return value
    
    def set_setting(self, key, value):
        """Set a setting value and save to file."""
        debug.debug(f"Setting setting: {key} = {value}")
        self.settings[key] = value
        debug.debug(f"Settings after update: {self.settings}")
        return self.save_settings(self.settings)
    
    def prompt_for_database_location(self, parent_widget=None):
        """
        Prompt the user to choose a database location if not already set.
        Returns the database path.
        """
        debug.debug("Prompting for database location")
        # Check if this is first run (no database path set or default still being used)
        db_path = Path(self.get_setting("database_path"))
        default_db_path = Path(self.default_settings["database_path"])
        
        if db_path == default_db_path and not db_path.exists():
            debug.debug("First run detected, prompting for location")
            # First run, prompt for location
            msg = "Choose where to store your tasks database. Choose a location that's backed up regularly."
            QMessageBox.information(parent_widget, "Database Location", msg)
            
            # Get directory from user
            suggested_dir = db_path.parent
            debug.debug(f"Suggesting directory: {suggested_dir}")
            db_dir = QFileDialog.getExistingDirectory(
                parent_widget, 
                "Select Database Directory", 
                str(suggested_dir)
            )
            
            if db_dir:  # User selected a directory
                debug.debug(f"User selected directory: {db_dir}")
                # Create full path including filename
                new_db_path = Path(db_dir) / "task_manager.db"
                
                # Save the new path
                debug.debug(f"Saving new database path: {new_db_path}")
                self.set_setting("database_path", str(new_db_path))
                
                # Create directory if it doesn't exist
                debug.debug(f"Ensuring parent directory exists: {new_db_path.parent}")
                new_db_path.parent.mkdir(parents=True, exist_ok=True)
                
                return str(new_db_path)
            else:  # User cancelled, use default
                debug.debug("User cancelled, using default path")
                # Create directory if it doesn't exist
                debug.debug(f"Ensuring parent directory exists: {db_path.parent}")
                db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Return the current path
        debug.debug(f"Using database path: {db_path}")
        return str(db_path)


class AppSettingsWidget(QWidget):
    def __init__(self, main_window):
        debug.debug("Initializing AppSettingsWidget")
        super().__init__()
        self.main_window = main_window
        self.settings = main_window.settings
        self.setup_ui()
    
    def setup_ui(self):
        debug.debug("Setting up AppSettingsWidget UI")
        layout = QVBoxLayout(self)
        
        # Create a horizontal layout for the two main panels
        panels_layout = QHBoxLayout()
        
        # Left panel: Database location
        db_group = QGroupBox("Database")
        db_layout = QFormLayout()
        
        # Current database location
        current_db = self.settings.get_setting("database_path")
        debug.debug(f"Current database path: {current_db}")
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
        
        # Debug Settings group - NEW
        debug_group = QGroupBox("Debug Settings")
        debug_layout = QVBoxLayout()
        
        # Get debug enabled setting
        debug_enabled = self.settings.get_setting("debug_enabled", False)
        debug.debug(f"Debug enabled from settings: {debug_enabled}")
        
        # Debug checkbox
        self.debug_checkbox = QCheckBox("Enable Debug Logging")
        self.debug_checkbox.setChecked(debug_enabled)
        self.debug_checkbox.toggled.connect(self.toggle_debug_logging)
        debug_layout.addWidget(self.debug_checkbox)
        
        # Add description
        debug_description = QLabel("Enabling debug logging will create detailed log files in the application's data directory. This can be useful for troubleshooting problems.")
        debug_description.setWordWrap(True)
        debug_layout.addWidget(debug_description)
        
        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)
        
        # Bee API Settings group
        if hasattr(self.main_window, 'settings'):
            debug.debug("Setting up Bee API settings group")
            bee_container = QHBoxLayout()
            
            bee_api_group = QGroupBox("Bee API Settings")
            bee_api_layout = QVBoxLayout()
            
            # Get API key and label from settings
            api_key = self.settings.get_setting("bee_api_key", "")
            api_key_label = self.settings.get_setting("bee_api_key_label", "")
            debug.debug(f"API key configured: {bool(api_key)}, Label: {api_key_label}")
            
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
            
            # Add the Bee API group to a container with less additional space to make it 2x width
            # Remove the stretch that was making it half-width
            bee_container.addWidget(bee_api_group)
            layout.addLayout(bee_container)
            
            bee_api_group.setLayout(bee_api_layout)
            
            # Add the Bee API group to a container with additional space to make it half-width
            bee_container.addWidget(bee_api_group)
            # bee_container.addStretch()  # This makes the group take only half the width
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
        
        button_layout.addStretch()  # This pushes buttons to the left by placing stretch AFTER the buttons
        
        layout.addLayout(button_layout)
        debug.debug("AppSettingsWidget UI setup complete")
    
    def save_settings(self):
        debug.debug("Saving settings")
        
        # Get current debug checkbox state and save it
        debug_enabled = self.debug_checkbox.isChecked()
        self.settings.set_setting("debug_enabled", debug_enabled)
        debug.debug(f"Saved debug_enabled setting: {debug_enabled}")
        
        QMessageBox.information(self, "Settings Saved", "Your settings have been saved.")
    
    def toggle_debug_logging(self, enabled):
        """Handle toggling debug logging"""
        debug.debug(f"Debug logging toggled: {enabled}")
        
        # Configure the debug logger
        from utils.debug_init import init_debugger
        from argparse import Namespace
        
        # Create arguments object
        args = Namespace()
        args.debug = enabled
        args.debug_file = enabled  # Enable file logging when debug is enabled
        args.debug_console = enabled  # Enable console logging when debug is enabled
        args.debug_all = True  # Debug all classes/methods
        
        # Initialize the debugger with our args
        init_debugger(args)
        
        # Save the setting (will be saved permanently when clicking Save)
        self.settings.settings["debug_enabled"] = enabled
        debug.debug(f"Updated debug_enabled in settings: {enabled}")
    
    def change_database_location(self):
        debug.debug("Changing database location")
        current_path = Path(self.settings.get_setting("database_path"))
        debug.debug(f"Current database path: {current_path}")
        
        db_dir = QFileDialog.getExistingDirectory(
            self, "Select Database Directory", str(current_path.parent))
        
        if db_dir:
            debug.debug(f"User selected directory: {db_dir}")
            new_path = Path(db_dir) / current_path.name
            debug.debug(f"New database path: {new_path}")
            
            # Ask if user wants to copy existing database
            if current_path.exists():
                debug.debug("Existing database found, asking about copying")
                reply = QMessageBox.question(self, 'Move Database', 
                                            'Do you want to copy the existing database to the new location?',
                                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    try:
                        # Create directory if it doesn't exist
                        debug.debug(f"Creating directory: {new_path.parent}")
                        new_path.parent.mkdir(parents=True, exist_ok=True)
                        # Copy database
                        debug.debug(f"Copying database from {current_path} to {new_path}")
                        shutil.copy2(current_path, new_path)
                    except Exception as e:
                        debug.error(f"Failed to copy database: {e}")
                        QMessageBox.critical(self, "Error", f"Failed to copy database: {str(e)}")
                        return
            
            # Save the new database location
            debug.debug(f"Saving new database path: {new_path}")
            self.settings.set_setting("database_path", str(new_path))
            
            # Update UI
            debug.debug("Database location updated, showing notification")
            QMessageBox.information(self, "Database Location Changed", 
                                   "Database location has been changed. The application will need to be restarted.")       
    
    def delete_bee_api_key(self):
        """Delete the stored Bee API key"""
        debug.debug("Deleting Bee API key")
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
            debug.debug("User confirmed deletion of Bee API key")
            # Delete key from settings
            self.settings.set_setting("bee_api_key", "")
            self.settings.set_setting("bee_api_key_label", "")
            
            # Refresh the UI
            debug.debug("Refreshing UI after key deletion")
            self.setup_ui()
            
            QMessageBox.information(self, "API Key Deleted", "Your Bee API key has been deleted.")
        else:
            debug.debug("User cancelled Bee API key deletion")

    def add_bee_api_key(self):
        """Add a new Bee API key"""
        debug.debug("Adding Bee API key")
        from ui.bee_api_dialog import BeeApiKeyDialog
        
        dialog = BeeApiKeyDialog(self)
        if dialog.exec():
            debug.debug("Bee API key dialog accepted")
            # Get key and label
            api_key = dialog.get_api_key()
            key_label = dialog.get_key_label()
            
            if api_key:
                debug.debug(f"Saving Bee API key (label: {key_label})")
                # Save to settings
                self.settings.set_setting("bee_api_key", api_key)
                if key_label:
                    self.settings.set_setting("bee_api_key_label", key_label)
                
                # Refresh the UI
                debug.debug("Refreshing UI after adding API key")
                self.setup_ui()
            else:
                debug.debug("No API key provided")
        else:
            debug.debug("Bee API key dialog cancelled")