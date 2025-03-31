# src/database/database_manager.py

from pathlib import Path
import sqlite3
import sys
import os

# Add parent directory to path so we can import app_settings
sys.path.append(str(Path(__file__).parent.parent))
from ui.app_settings import SettingsManager

class DatabaseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Initialize settings
        self.settings = SettingsManager()
        self._db_path = None
        self._connection = None  # Store a single connection
        self._initialized = True
    
    @property
    def db_path(self):
        """Get the current database path from settings"""
        if self._db_path is None:
            self._db_path = Path(self.settings.get_setting("database_path"))
        return self._db_path
    
    def set_db_path(self, path):
        """Set the database path explicitly"""
        self._db_path = Path(path)
        # Close any existing connection when path changes
        if self._connection is not None:
            self._connection.close()
            self._connection = None
    
    def get_connection(self):
        """Get a database connection"""
        # Create a new connection if none exists
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            # Set timeouts and journal mode for better performance
            self._connection.execute("PRAGMA busy_timeout = 5000")
            self._connection.execute("PRAGMA journal_mode = WAL")
            
        return self._connection
    
    def close_connection(self):
        """Close the database connection if open"""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
    
    def execute_query(self, query, params=None):
        """Execute a query and return the results"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        finally:
            cursor.close()
    
    def execute_update(self, query, params=None):
        """Execute an update query and return the number of rows affected"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.rowcount
        finally:
            cursor.close()
    
    def execute_many(self, query, params):
        """Execute a query with many parameter sets"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.executemany(query, params)
            conn.commit()
            return cursor.rowcount
        finally:
            cursor.close()
    
    def get_last_row_id(self):
        """Get the ID of the last inserted row"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT last_insert_rowid()")
            return cursor.fetchone()[0]
        finally:
            cursor.close()

# Return a singleton instance
def get_db_manager():
    return DatabaseManager()

# For backward compatibility with existing code
def get_db_path():
    return get_db_manager().db_path