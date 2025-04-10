# src/database/db_config.py
"""
Central database configuration module.
This is the single source of truth for database location in the application.
"""

from pathlib import Path
import sys
import os
import sqlite3

# Add parent directory to path to find the ui package
sys.path.append(str(Path(__file__).parent.parent))

class DatabaseConfig:
    # Singleton instance
    _instance = None
    
    # Class attribute to hold the path
    _db_path = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConfig, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if self._initialized:
            return
            
        self._initialized = True
        self._load_path_from_settings()
    
    def _load_path_from_settings(self):
        """Load the database path from settings"""
        try:
            # Import the settings manager
            from ui.app_settings import SettingsManager
            settings = SettingsManager()
            
            # Get path from settings
            self._db_path = Path(settings.get_setting("database_path"))
            print(f"Loaded database path from settings: {self._db_path}")
        except Exception as e:
            # Fallback to default if settings can't be loaded
            self._db_path = Path.home() / "Documents" / "TaskOrganizer" / "task_manager.db"
            print(f"Error loading path from settings: {e}")
            print(f"Using default path: {self._db_path}")
    
    @property
    def path(self):
        """Get the current database path"""
        if self._db_path is None:
            self._load_path_from_settings()
        return self._db_path
    
    def set_path(self, new_path):
        """Set the database path and update settings"""
        # Convert to Path object if string
        if isinstance(new_path, str):
            new_path = Path(new_path)
        
        # Update the stored path
        old_path = self._db_path
        self._db_path = new_path
        
        print(f"Database path changed from {old_path} to {new_path}")
        
        # Update settings if possible
        try:
            from ui.app_settings import SettingsManager
            settings = SettingsManager()
            settings.set_setting("database_path", str(new_path))
        except Exception as e:
            print(f"Error updating path in settings: {e}")
    
    def ensure_directory_exists(self):
        """Create the database directory if it doesn't exist"""
        directory = self.path.parent
        if not directory.exists():
            print(f"Creating database directory: {directory}")
            directory.mkdir(parents=True, exist_ok=True)
    
    def connection(self):
        """Get a new database connection"""
        # Ensure directory exists
        self.ensure_directory_exists()
        
        # Create connection
        conn = sqlite3.connect(self.path)
        
        # Set pragmas for better performance
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
        
        return conn
    
    def database_exists(self):
        """Check if the database file exists"""
        return self.path.exists()
    
    def create_database(self):
        """Create a new database with all required tables"""
        if self.database_exists():
            print(f"Database already exists at {self.path}")
            return True
            
        print(f"Creating new database at {self.path}")
        self.ensure_directory_exists()
        
        try:
            # Create connection
            conn = self.connection()
            cursor = conn.cursor()
            
            # Create tables
            self._create_tables(cursor)
            
            # Commit changes
            conn.commit()
            conn.close()
            
            print("Database created successfully")
            return True
        except Exception as e:
            print(f"Error creating database: {e}")
            return False

    def _create_tables(self, cursor):
        """Create all database tables"""
        # Create categories table
        print("Creating categories table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                color TEXT NOT NULL
            )
        """)
        
        # Insert default categories if table is empty
        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] == 0:
            default_categories = [
                ('Work', '#F0F7FF'),        # Light blue
                ('Personal', '#E8F5E9'),    # Light green
                ('Shopping', '#FFF8E1'),    # Light yellow
                ('Health', '#FFEBEE'),      # Light red
                ('Learning', '#F3E5F5')     # Light purple
            ]
            
            cursor.executemany("""
                INSERT INTO categories (name, color)
                VALUES (?, ?)
            """, default_categories)
            print("Inserted default categories")
        
        # Create priorities table
        print("Creating priorities table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS priorities (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                color TEXT NOT NULL,
                display_order INTEGER NOT NULL
            )
        """)
        
        # Insert default priorities if table is empty
        cursor.execute("SELECT COUNT(*) FROM priorities")
        if cursor.fetchone()[0] == 0:
            default_priorities = [
                ('High', '#F44336', 1),     # Red (highest priority)
                ('Medium', '#FFC107', 2),   # Amber (medium priority)
                ('Low', '#4CAF50', 3),       # Green (lowest priority)
                ('Unprioritized', '#AAAAAA', 4)  # Gray (no priority)
            ]
            
            cursor.executemany("""
                INSERT INTO priorities (name, color, display_order)
                VALUES (?, ?, ?)
            """, default_priorities)
            print("Inserted default priorities")
        
        # Create statuses table
        print("Creating statuses table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS statuses (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                color TEXT NOT NULL,
                display_order INTEGER NOT NULL
            )
        """)
        
        # Insert default statuses if table is empty
        cursor.execute("SELECT COUNT(*) FROM statuses")
        if cursor.fetchone()[0] == 0:
            default_statuses = [
                ('Not Started', '#F44336', 1),  # Red
                ('In Progress', '#FFC107', 2),  # Amber
                ('On Hold', '#9E9E9E', 3),      # Gray
                ('Backlog', '#9C27B0', 4),      # Purple
                ('Completed', '#4CAF50', 5)     # Green
            ]
            
            cursor.executemany("""
                INSERT INTO statuses (name, color, display_order)
                VALUES (?, ?, ?)
            """, default_statuses)
            print("Inserted default statuses")
        
        # Create tasks table
        print("Creating tasks table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                link TEXT,
                status TEXT NOT NULL DEFAULT 'Not Started',
                priority TEXT NOT NULL DEFAULT 'Medium',
                due_date TEXT,
                category_id INTEGER,
                parent_id INTEGER DEFAULT NULL,
                display_order INTEGER NOT NULL DEFAULT 0,
                tree_level INTEGER NOT NULL DEFAULT 0,
                is_compact INTEGER NOT NULL DEFAULT 0,
                completed_at TEXT DEFAULT NULL,
                FOREIGN KEY (category_id) REFERENCES categories (id),
                FOREIGN KEY (parent_id) REFERENCES tasks (id)
            )
        """)
        print("All tables created successfully")    

# Create a global instance to be imported by other modules
db_config = DatabaseConfig()

# Simple wrapper functions for easy access
def get_db_path():
    """Get the database path"""
    return db_config.path

def set_db_path(path):
    """Set the database path"""
    db_config.set_path(path)
    return db_config.path

def get_db_connection():
    """Get a database connection"""
    return db_config.connection()

def ensure_db_exists():
    """Ensure the database exists and is initialized"""
    if not db_config.database_exists():
        return db_config.create_database()
    return True