# src/database/check_db.py

from pathlib import Path
import sqlite3

# Import central database configuration
from database.db_config import db_config, get_db_connection

def check_db():
    print(f"Checking database at: {db_config.path}")
    
    # Ensure the database exists
    if not db_config.database_exists():
        print("Database does not exist. Creating it now.")
        db_config.create_database()
    
    # Get connection from central configuration
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check for ai_models table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ai_models'")
        if cursor.fetchone():
            print("\nAI Models:")
            cursor.execute("SELECT * FROM ai_models")
            models = cursor.fetchall()
            for model in models:
                print(f"ID: {model[0]}, Name: {model[1]}, Pattern: {model[2]}, Color: {model[3]}")
        else:
            print("\nAI Models table not found")
        
        # Check for chats table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chats'")
        if cursor.fetchone():
            print("\nChats:")
            cursor.execute("SELECT * FROM chats")
            chats = cursor.fetchall()
            for chat in chats:
                print(f"ID: {chat[0]}, Title: {chat[1]}, Link: {chat[2]}, Status: {chat[3]}, AI: {chat[4]}")
        else:
            print("\nChats table not found")
        
        # Check for tasks table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
        if cursor.fetchone():
            print("\nTasks:")
            cursor.execute("SELECT COUNT(*) FROM tasks")
            task_count = cursor.fetchone()[0]
            print(f"Total tasks: {task_count}")
            
            if task_count > 0:
                print("\nSample tasks:")
                cursor.execute("SELECT id, title, status FROM tasks LIMIT 5")
                tasks = cursor.fetchall()
                for task in tasks:
                    print(f"ID: {task[0]}, Title: {task[1]}, Status: {task[2]}")
        else:
            print("\nTasks table not found")
        
        # List all tables
        print("\nAll tables in database:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for table in tables:
            print(f"- {table[0]}")

if __name__ == "__main__":
    check_db()