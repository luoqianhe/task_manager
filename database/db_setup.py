# src/database/db_setup.py

from pathlib import Path
import sqlite3
import sys
import os

# Import settings manager
sys.path.append(str(Path(__file__).parent.parent))
from ui.app_settings import SettingsManager

# Default DB path (will be overridden)
DB_PATH = Path(__file__).parent / "task_manager.db"

def init_database():
    global DB_PATH
    
    # Use the global DB_PATH that can be overridden by main.py
    db_path = DB_PATH
    print(f"Initializing database at: {db_path}")
    
    # Create parent directory if it doesn't exist
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Try to use database manager if it's available
    try:
        from database.database_manager import get_db_manager
        db_manager = get_db_manager()
        # Ensure it uses our path
        db_manager.set_db_path(db_path)
        conn = db_manager.get_connection()
        print("Using database manager connection")
    except Exception as e:
        # Fallback to direct connection if needed
        print(f"Using direct connection: {e}")
        conn = sqlite3.connect(db_path)
    
    cursor = conn.cursor()
    
    # Drop existing tables
    cursor.execute("DROP TABLE IF EXISTS tasks")
    cursor.execute("DROP TABLE IF EXISTS categories")
    cursor.execute("DROP TABLE IF EXISTS priorities")
    
    # Create categories table
    cursor.execute("""
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            color TEXT NOT NULL
        )
    """)
    
    # Insert default categories
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
    
    # Create priorities table
    cursor.execute("""
        CREATE TABLE priorities (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            color TEXT NOT NULL,
            display_order INTEGER NOT NULL
        )
    """)
    
    # Insert default priorities (ordered by importance - 1 is highest)
    default_priorities = [
        ('High', '#F44336', 1),     # Red (highest priority)
        ('Medium', '#FFC107', 2),   # Amber (medium priority)
        ('Low', '#4CAF50', 3)       # Green (lowest priority)
    ]
    
    cursor.executemany("""
        INSERT INTO priorities (name, color, display_order)
        VALUES (?, ?, ?)
    """, default_priorities)
    
    # Create tasks table
    cursor.execute("""
        CREATE TABLE tasks (
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
            FOREIGN KEY (category_id) REFERENCES categories (id),
            FOREIGN KEY (parent_id) REFERENCES tasks (id)
        )
    """)

    # Create statuses table
    cursor.execute("DROP TABLE IF EXISTS statuses")
    cursor.execute("""
        CREATE TABLE statuses (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            color TEXT NOT NULL,
            display_order INTEGER NOT NULL
        )
    """)

    # Insert default statuses
    default_statuses = [
        ('Not Started', '#F44336', 1),  # Red
        ('In Progress', '#FFC107', 2),  # Amber
        ('On Hold', '#9E9E9E', 3),      # Gray
        ('Completed', '#4CAF50', 4)     # Green
    ]

    cursor.executemany("""
        INSERT INTO statuses (name, color, display_order)
        VALUES (?, ?, ?)
    """, default_statuses)

    print("Database tables created successfully")

if __name__ == "__main__":
    # When run directly, use settings manager
    settings = SettingsManager()
    DB_PATH = Path(settings.prompt_for_database_location())
    
    print("Initializing database...")
    init_database()
    print(f"Database initialized at: {DB_PATH}")