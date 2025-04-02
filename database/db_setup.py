# src/database/db_setup.py

from pathlib import Path
import sqlite3
import sys
import os

# Import central database configuration
from database.db_config import db_config, ensure_db_exists

# Import settings manager
sys.path.append(str(Path(__file__).parent.parent))
from ui.app_settings import SettingsManager

def init_database():
    """Initialize the database with the required schema"""
    print(f"Initializing database at: {db_config.path}")
    
    # Use the centralized database creation method
    if db_config.create_database():
        print("Database initialized successfully")
        return True
    else:
        print("Failed to initialize database")
        return False

def setup_database(parent_widget=None):
    """Complete database setup process with user interaction"""
    # Use settings manager
    settings = SettingsManager()
    
    # Prompt for database location if needed
    db_path = Path(settings.prompt_for_database_location(parent_widget))
    
    # Set the path in our central configuration
    db_config.set_path(db_path)
    
    # Create the database if it doesn't exist
    if not db_config.database_exists():
        if not db_config.create_database():
            # Database creation failed
            return False
            
        # Database was successfully created
        if parent_widget:
            from PyQt6.QtWidgets import QMessageBox
            # Ask user if they want sample data
            reply = QMessageBox.question(
                parent_widget, 
                'Initialize Database',
                'Database created successfully. Would you like to add sample tasks?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    # Insert sample data
                    from database.insert_test_data import insert_test_tasks
                    insert_test_tasks()
                    print("Sample tasks added to database")
                except Exception as e:
                    print(f"Error adding sample data: {e}")
                    QMessageBox.warning(
                        parent_widget,
                        "Sample Data Error",
                        f"Could not add sample data: {e}\n\nThe database was created but will be empty."
                    )
    
    return True

if __name__ == "__main__":
    # When run directly, use settings manager
    settings = SettingsManager()
    db_path = Path(settings.prompt_for_database_location())
    
    # Update the path in our central configuration
    db_config.set_path(db_path)
    
    print("Initializing database...")
    init_database()
    print(f"Database initialized at: {db_path}")