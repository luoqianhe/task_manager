# src/database/insert_test_data.py

from pathlib import Path
import sqlite3
from datetime import date, timedelta

# Default DB path (will be overridden)
DB_PATH = Path(__file__).parent / "task_manager.db"

def insert_test_tasks():
    print(f"Inserting test data into database at: {DB_PATH}")
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Get category IDs
        cursor.execute("SELECT id FROM categories WHERE name = 'Work'")
        work_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT id FROM categories WHERE name = 'Personal'")
        personal_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT id FROM categories WHERE name = 'Learning'")
        learning_id = cursor.fetchone()[0]
        
        # Calculate some dates for test data
        today = date.today()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)
        
        # Insert test data
        test_tasks = [
            # id, title, description, link, status, priority, due_date, category_id, parent_id, display_order, tree_level
            (1, "Website Redesign", "Redesign the company website", "https://company.com", "In Progress", "High", next_week.isoformat(), work_id, None, 0, 0),
            (2, "Design Homepage", "Create mockups for the homepage", None, "In Progress", "Medium", tomorrow.isoformat(), work_id, 1, 0, 1),
            (3, "Contact Page", "Update contact information", None, "Not Started", "Low", next_week.isoformat(), work_id, 1, 1, 1),
            
            (4, "Learn Python", "Complete Python course", "https://python.org", "In Progress", "Medium", None, learning_id, None, 1, 0),
            (5, "Practice Exercises", "Complete chapter 5 exercises", None, "Not Started", "Medium", tomorrow.isoformat(), learning_id, 4, 0, 1),
            
            (6, "Grocery Shopping", "Buy groceries for the week", None, "Not Started", "High", today.isoformat(), personal_id, None, 2, 0),
            (7, "Exercise", "30 minutes of cardio", None, "Completed", "Medium", today.isoformat(), personal_id, None, 3, 0)
        ]
        
        cursor.execute("DELETE FROM tasks")  # Clear existing data
        
        cursor.executemany("""
            INSERT INTO tasks (id, title, description, link, status, priority, 
                               due_date, category_id, parent_id, display_order, tree_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, test_tasks)
        
        conn.commit()
        print("Test data inserted successfully!")

if __name__ == "__main__":
    insert_test_tasks()