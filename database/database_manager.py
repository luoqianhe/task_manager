# src/database/database_manager.py

from pathlib import Path
import sqlite3
import sys
import os

# Import our centralized database configuration
from database.db_config import db_config, get_db_path, get_db_connection

# Import debug logger
from utils.debug_logger import get_debug_logger
debug = get_debug_logger()

class DatabaseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            debug.debug("Creating new DatabaseManager instance")
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        debug.debug("Initializing DatabaseManager")
        # Store connection
        self._connection = None  # Store a single connection
        self._initialized = True
    
    def get_task_links(self, task_id):
        """Get all links for a specific task"""
        debug.debug(f"Getting links for task ID: {task_id}")
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT id, url, label, display_order
                FROM links
                WHERE task_id = ?
                ORDER BY display_order
            """, (task_id,))
            
            # Convert to proper three-element tuples (id, url, label)
            results = cursor.fetchall()
            debug.debug(f"Found {len(results)} links for task {task_id}")
            return [(row[0], row[1], row[2]) for row in results]
        finally:
            cursor.close()
            
    @property
    def db_path(self):
        """Get the current database path from the central configuration"""
        path = get_db_path()
        debug.debug(f"Getting database path: {path}")
        return path
    
    def set_db_path(self, path):
        """Set the database path explicitly through the central configuration"""
        debug.debug(f"Setting database path: {path}")
        db_config.set_path(path)
        
        # Close any existing connection when path changes
        if self._connection is not None:
            debug.debug("Closing existing connection due to path change")
            self._connection.close()
            self._connection = None
    
    def get_connection(self):
        """Get a database connection"""
        # Create a new connection if none exists
        if self._connection is None:
            debug.debug("No existing connection, creating new one")
            # Ensure the database exists
            if not db_config.database_exists():
                debug.debug("Database doesn't exist, creating it")
                db_config.create_database()
                
            # Get a connection from the central configuration
            debug.debug("Getting connection from central configuration")
            self._connection = get_db_connection()
            
        return self._connection
    
    def close_connection(self):
        """Close the database connection if open"""
        if self._connection is not None:
            debug.debug("Closing database connection")
            self._connection.close()
            self._connection = None
    
    def execute_query(self, query, params=None):
        """Execute a query and return the results"""
        debug.debug(f"Executing query: {query}")
        if params:
            debug.debug(f"Parameters: {params}")
            
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results = cursor.fetchall()
            debug.debug(f"Query returned {len(results)} rows")
            return results
        finally:
            cursor.close()
    
    def execute_update(self, query, params=None):
        """Execute an update query and return the number of rows affected"""
        debug.debug(f"Executing update: {query}")
        if params:
            debug.debug(f"Parameters: {params}")
            
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            affected_rows = cursor.rowcount
            debug.debug(f"Update affected {affected_rows} rows")
            return affected_rows
        finally:
            cursor.close()
    
    def execute_many(self, query, params):
        """Execute a query with many parameter sets"""
        debug.debug(f"Executing many: {query}")
        debug.debug(f"Number of parameter sets: {len(params)}")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.executemany(query, params)
            conn.commit()
            affected_rows = cursor.rowcount
            debug.debug(f"Execute many affected {affected_rows} rows")
            return affected_rows
        finally:
            cursor.close()
    
    def get_last_row_id(self):
        """Get the ID of the last inserted row"""
        debug.debug("Getting last row ID")
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT last_insert_rowid()")
            last_id = cursor.fetchone()[0]
            debug.debug(f"Last row ID: {last_id}")
            return last_id
        finally:
            cursor.close()

# Return a singleton instance
def get_db_manager():
    debug.debug("get_db_manager called")
    return DatabaseManager()

# For backward compatibility with existing code
def get_db_path():
    debug.debug("get_db_path called (compatibility function)")
    return get_db_manager().db_path