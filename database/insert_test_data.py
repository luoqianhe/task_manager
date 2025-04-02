# src/database/insert_test_data.py

from pathlib import Path
import sqlite3
from datetime import date, timedelta

# Import centralized database configuration
from db_config import db_config, get_db_connection

def insert_test_tasks():
    print(f"Inserting test data into database at: {db_config.path}")
    
    try:
        # Get connection from central config
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # First verify that the tables exist
            tables_to_check = ['categories', 'priorities', 'tasks']
            for table in tables_to_check:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if not cursor.fetchone():
                    print(f"Table {table} doesn't exist. Creating tables first.")
                    # Create the database using the central configuration
                    db_config.create_database()
                    break
            
            # Get category IDs
            cursor.execute("SELECT id FROM categories WHERE name = 'Work'")
            result = cursor.fetchone()
            if not result:
                print("Work category not found. Creating it.")
                cursor.execute("INSERT INTO categories (name, color) VALUES (?, ?)", 
                            ('Work', '#F0F7FF'))
                work_id = cursor.lastrowid
            else:
                work_id = result[0]
            
            cursor.execute("SELECT id FROM categories WHERE name = 'Personal'")
            result = cursor.fetchone()
            if not result:
                print("Personal category not found. Creating it.")
                cursor.execute("INSERT INTO categories (name, color) VALUES (?, ?)", 
                            ('Personal', '#E8F5E9'))
                personal_id = cursor.lastrowid
            else:
                personal_id = result[0]
            
            cursor.execute("SELECT id FROM categories WHERE name = 'Learning'")
            result = cursor.fetchone()
            if not result:
                print("Learning category not found. Creating it.")
                cursor.execute("INSERT INTO categories (name, color) VALUES (?, ?)", 
                            ('Learning', '#F3E5F5'))
                learning_id = cursor.lastrowid
            else:
                learning_id = result[0]
            
            # Calculate some dates for test data
            today = date.today()
            tomorrow = today + timedelta(days=1)
            next_week = today + timedelta(days=7)
            
            # First check if tasks already exist
            cursor.execute("SELECT COUNT(*) FROM tasks")
            if cursor.fetchone()[0] > 0:
                print("Tasks already exist. Skipping task insertion.")
                return
            
            # Insert test data
            test_tasks = [
                # id, title, description, link, status, priority, due_date, category_id, parent_id, display_order, tree_level, is_compact
                (1, "Website Redesign", "Redesign the company website", "https://company.com", "In Progress", "High", next_week.isoformat(), work_id, None, 0, 0, 0),
                (2, "Design Homepage", "Create mockups for the homepage", None, "In Progress", "Medium", tomorrow.isoformat(), work_id, 1, 0, 1, 0),
                (3, "Contact Page", "Update contact information", None, "Not Started", "Low", next_week.isoformat(), work_id, 1, 1, 1, 0),
                
                (4, "Learn Python", "Complete Python course", "https://python.org", "In Progress", "Medium", None, learning_id, None, 1, 0, 0),
                (5, "Practice Exercises", "Complete chapter 5 exercises", None, "Not Started", "Medium", tomorrow.isoformat(), learning_id, 4, 0, 1, 0),
                
                (6, "Grocery Shopping", "Buy groceries for the week", None, "Not Started", "High", today.isoformat(), personal_id, None, 2, 0, 0),
                (7, "Exercise", "30 minutes of cardio", None, "Completed", "Medium", today.isoformat(), personal_id, None, 3, 0, 0)
            ]
            
            cursor.execute("DELETE FROM tasks")  # Clear existing data
            
            cursor.executemany("""
                INSERT INTO tasks (id, title, description, link, status, priority, 
                               due_date, category_id, parent_id, display_order, tree_level, is_compact)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, test_tasks)
            
            conn.commit()
            print("Test data inserted successfully!")
            
    except Exception as e:
        print(f"Error inserting test data: {e}")
        raise

if __name__ == "__main__":
    insert_test_tasks()