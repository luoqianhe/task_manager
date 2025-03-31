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
        
        # Database section
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
        layout.addWidget(db_group)
        
        # Backup settings
        backup_group = QGroupBox("Backup Settings")
        backup_layout = QFormLayout()
        
        # Auto backup option
        self.auto_backup = QCheckBox("Enable automatic backups")
        self.auto_backup.setChecked(self.settings.get_setting("auto_backup", False))
        self.auto_backup.toggled.connect(self.toggle_backup_options)
        backup_layout.addRow(self.auto_backup)
        
        # Backup interval
        self.backup_interval = QSpinBox()
        self.backup_interval.setMinimum(1)
        self.backup_interval.setMaximum(90)
        self.backup_interval.setValue(self.settings.get_setting("backup_interval_days", 7))
        self.backup_interval.setEnabled(self.auto_backup.isChecked())
        backup_layout.addRow("Backup interval (days):", self.backup_interval)
        
        # Manual backup button
        manual_backup_btn = QPushButton("Backup Now")
        manual_backup_btn.setFixedHeight(30)
        manual_backup_btn.clicked.connect(self.perform_backup)
        backup_layout.addRow(manual_backup_btn)
        
        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)
        
        # CSV Buttons group
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
        layout.addWidget(csv_group)
        
        # Add stretch to push Done button to bottom
        layout.addStretch()
        
        # Save and Done buttons
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Save Settings")
        save_button.setFixedHeight(30)
        save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
    
    def toggle_backup_options(self, enabled):
        self.backup_interval.setEnabled(enabled)
    
    def save_settings(self):
        # Save backup settings
        self.settings.set_setting("auto_backup", self.auto_backup.isChecked())
        self.settings.set_setting("backup_interval_days", self.backup_interval.value())
        
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
    
    def perform_backup(self):
        source_path = Path(self.settings.get_setting("database_path"))
        
        if not source_path.exists():
            QMessageBox.warning(self, "Backup Failed", "Database file not found.")
            return
        
        # Ask user for backup location
        backup_dir = QFileDialog.getExistingDirectory(
            self, "Select Backup Directory", str(source_path.parent))
        
        if backup_dir:
            try:
                from datetime import datetime
                # Create timestamped backup
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = f"task_manager_backup_{timestamp}.db"
                backup_path = Path(backup_dir) / backup_file
                
                # Copy the database file
                shutil.copy2(source_path, backup_path)
                
                QMessageBox.information(self, "Backup Successful", 
                                       f"Database backed up to {backup_path}")
            except Exception as e:
                QMessageBox.critical(self, "Backup Failed", str(e))