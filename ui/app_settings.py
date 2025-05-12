# src/ui/app_settings.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QFileDialog, QMessageBox, QLabel, QCheckBox, 
                           QGroupBox, QFormLayout, QLineEdit, QSpinBox, QApplication)
from pathlib import Path
import json
import shutil
import sqlite3
import sys
import platform

from ui.os_style_manager import OSStyleManager


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
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Top Save/Cancel buttons
        top_button_layout = QHBoxLayout()
        save_btn_top = QPushButton("Save Settings")
        save_btn_top.setFixedHeight(30)
        save_btn_top.setMinimumWidth(120)  # Set a consistent minimum width
        save_btn_top.clicked.connect(self.save_settings)
        save_btn_top.setProperty("primary", True)  # Add the primary property
        save_btn_top.setDefault(True)

        cancel_btn_top = QPushButton("Cancel")
        cancel_btn_top.setFixedHeight(30)
        cancel_btn_top.setMinimumWidth(120)  # Set a consistent minimum width
        cancel_btn_top.setProperty("secondary", True)  # Add the secondary property
        cancel_btn_top.clicked.connect(self.main_window.show_task_view)

        # Add buttons to the top_button_layout
        top_button_layout.addWidget(save_btn_top)
        top_button_layout.addWidget(cancel_btn_top)
        top_button_layout.addStretch()  # This pushes buttons to the left

        # Add the top_button_layout to the main layout
        layout.addLayout(top_button_layout)
        
        # Create a horizontal layout for the two main panels
        panels_layout = QHBoxLayout()
        
        # Left panel: Database location
        db_group = QGroupBox("Database")
        db_layout = QFormLayout()
        
        # Go to File Location button (above Change Location button)
        goto_file_btn = QPushButton("Go to File Location")
        goto_file_btn.setFixedHeight(30)
        goto_file_btn.setProperty("secondary", True)  # Mark as secondary
        goto_file_btn.clicked.connect(self.open_database_location)
        db_layout.addRow(goto_file_btn)
        
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
        csv_layout.addRow("Get import template (CSV):", template_button)
        
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
        
        # Create a horizontal layout for Application Style and Bee API Settings
        style_bee_layout = QHBoxLayout()
        
        # Add Style Preferences group
        style_prefs_group = QGroupBox("Application Style")
        style_prefs_layout = QVBoxLayout()
        
        # Add OS detection info
        os_name = platform.system()
        os_label = QLabel(f"Detected Operating System: <b>{os_name}</b>")
        style_prefs_layout.addWidget(os_label)
        
        # Get current style from app property
        app = QApplication.instance()
        current_style = "Default"
        if app.property("style_manager"):
            current_style = app.property("style_manager").current_style
        style_label = QLabel(f"Current Style: <b>{current_style}</b>")
        style_prefs_layout.addWidget(style_label)
        
        # Style preferences button
        style_prefs_button = QPushButton("Style Preferences...")
        style_prefs_button.clicked.connect(self.show_style_preferences)
        style_prefs_layout.addWidget(style_prefs_button)
        
        style_prefs_group.setLayout(style_prefs_layout)
        
        # Bee API Settings group
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
        
        # Add both groups to the horizontal layout
        style_bee_layout.addWidget(style_prefs_group)
        style_bee_layout.addWidget(bee_api_group)
        
        # Add the style_bee_layout to the main layout
        layout.addLayout(style_bee_layout)
        
        # Debug Settings group with distinct background color
        debug_group = QGroupBox("Debug Settings")
        # Set a light yellow background color to make it stand out
        debug_group.setStyleSheet("QGroupBox { background-color: #FFFDE7; border: 1px solid #E0E0E0; border-radius: 5px; margin-top: 1ex; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }")
        
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
        
        # Add stretch to push Done button to bottom
        layout.addStretch()
        
        # Add Save and Cancel buttons at the bottom
        bottom_button_layout = QHBoxLayout()
        save_button = QPushButton("Save Settings")
        save_button.setFixedHeight(30)
        save_button.setMinimumWidth(120)
        save_button.clicked.connect(self.save_settings)
        save_button.setProperty("primary", True)  # Add the primary property
        save_button.setDefault(True)

        cancel_button = QPushButton("Cancel")
        cancel_button.setFixedHeight(30)
        cancel_button.setMinimumWidth(120)
        cancel_button.clicked.connect(self.main_window.show_task_view)
        cancel_button.setProperty("secondary", True)  # Add the secondary property
        
        bottom_button_layout.addWidget(save_button)
        bottom_button_layout.addWidget(cancel_button)
        bottom_button_layout.addStretch()
        layout.addLayout(bottom_button_layout)
        debug.debug("AppSettingsWidget UI setup complete")    

    def open_database_location(self):
        debug.debug("Opening database location")
        import os
        import platform
        import subprocess
        
        # Get the current database path
        db_path = Path(self.settings.get_setting("database_path"))
        
        # Make sure the parent directory exists
        if not db_path.parent.exists():
            debug.debug(f"Parent directory doesn't exist, creating: {db_path.parent}")
            db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get the parent directory path
        dir_path = str(db_path.parent)
        debug.debug(f"Opening directory: {dir_path}")
        
        # Open the directory based on the OS
        system = platform.system()
        try:
            if system == 'Windows':
                os.startfile(dir_path)
                debug.debug("Opened directory with Windows startfile")
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', dir_path])
                debug.debug("Opened directory with macOS 'open' command")
            else:  # Linux and others
                subprocess.run(['xdg-open', dir_path])
                debug.debug("Opened directory with Linux 'xdg-open' command")
        except Exception as e:
            debug.error(f"Error opening directory: {e}")
            QMessageBox.warning(self, "Error", f"Could not open database location: {str(e)}")
    
    def save_settings(self):
        debug.debug("Saving settings")
        
        # Get current debug checkbox state and save it
        debug_enabled = self.debug_checkbox.isChecked()
        self.settings.set_setting("debug_enabled", debug_enabled)
        debug.debug(f"Saved debug_enabled setting: {debug_enabled}")
    
    def show_style_preferences(self):
        """Show the style preferences dialog"""
        from ui.style_preferences_dialog import StylePreferencesDialog
        dialog = StylePreferencesDialog(self.settings, self)
        dialog.exec()
    
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