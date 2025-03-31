# src/database/check_db.py

from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).parent / "project_manager.db"

def check_db():
    print(f"Checking database at: {DB_PATH}")
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        print("\nAI Models:")
        cursor.execute("SELECT * FROM ai_models")
        models = cursor.fetchall()
        for model in models:
            print(f"ID: {model[0]}, Name: {model[1]}, Pattern: {model[2]}, Color: {model[3]}")
        
        print("\nChats:")
        cursor.execute("SELECT * FROM chats")
        chats = cursor.fetchall()
        for chat in chats:
            print(f"ID: {chat[0]}, Title: {chat[1]}, Link: {chat[2]}, Status: {chat[3]}, AI: {chat[4]}")

if __name__ == "__main__":
    check_db()