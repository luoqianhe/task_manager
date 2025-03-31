# create_status_table.py
import sqlite3
from pathlib import Path

# Get the database path from your settings file (you'll need to adjust this)
from ui.app_settings import SettingsManager
settings = SettingsManager()
db_path = Path(settings.get_setting("database_path"))

print(f"Creating statuses table in database at: {db_path}")

with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    
    # First check if the table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='statuses'
    """)
    exists = cursor.fetchone()
    print(f"Table exists: {exists is not None}")
    
    if not exists:
        # Create statuses table
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
        
        # Make sure to commit
        conn.commit()
        print("Created statuses table with default values")
    else:
        print("Statuses table already exists")
        
    # Verify the table exists and has data
    cursor.execute("SELECT COUNT(*) FROM statuses")
    count = cursor.fetchone()[0]
    print(f"Number of status records: {count}")