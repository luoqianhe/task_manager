# src/database/db_setup.py

from pathlib import Path
import sqlite3
import sys
import os

# Import central database configuration
from database.db_config import db_config, ensure_db_exists

# Import debug logger
from utils.debug_logger import get_debug_logger
debug = get_debug_logger()

# Import settings manager
sys.path.append(str(Path(__file__).parent.parent))
from ui.app_settings import SettingsManager

def init_database():
    """Initialize the database with the required schema"""
    debug.debug(f"Initializing database at: {db_config.path}")
    
    # Use the centralized database creation method
    if db_config.create_database():
        debug.debug("Database initialized successfully")
        return True
    else:
        debug.error("Failed to initialize database")
        return False

def setup_database(parent_widget=None):
    """Complete database setup process with user interaction"""
    debug.debug("Setting up database with user interaction")
    # Use settings manager
    settings = SettingsManager()
    
    # Prompt for database location if needed
    debug.debug("Prompting for database location")
    db_path = Path(settings.prompt_for_database_location(parent_widget))
    debug.debug(f"Selected database path: {db_path}")
    
    # Set the path in our central configuration
    debug.debug("Setting database path in central configuration")
    db_config.set_path(db_path)
    
    # Create the database if it doesn't exist
    if not db_config.database_exists():
        debug.debug("Database doesn't exist, creating it")
        if not db_config.create_database():
            # Database creation failed
            debug.error("Database creation failed")
            return False
            
        # Database was successfully created
        debug.debug("Database created successfully")
        if parent_widget:
            from PyQt6.QtWidgets import QMessageBox
            # Ask user if they want sample data
            debug.debug("Asking user if they want sample data")
            reply = QMessageBox.question(
                parent_widget, 
                'Initialize Database',
                'Database created successfully. Would you like to add sample tasks?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    # Insert sample data
                    debug.debug("Inserting sample data")
                    from database.insert_test_data import insert_test_tasks
                    insert_test_tasks()
                    debug.debug("Sample tasks added to database")
                except Exception as e:
                    debug.error(f"Error adding sample data: {e}")
                    QMessageBox.warning(
                        parent_widget,
                        "Sample Data Error",
                        f"Could not add sample data: {e}\n\nThe database was created but will be empty."
                    )
    else:
        debug.debug("Database already exists")
    
    return True

if __name__ == "__main__":
    # When run directly, use settings manager
    debug.debug("db_setup.py running as main script")
    settings = SettingsManager()
    db_path = Path(settings.prompt_for_database_location())
    
    # Update the path in our central configuration
    debug.debug(f"Setting database path to: {db_path}")
    db_config.set_path(db_path)
    
    debug.debug("Initializing database...")
    init_database()
    debug.debug(f"Database initialization complete at: {db_path}")