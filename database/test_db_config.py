# src/tests/test_db_config.py

import sys
from pathlib import Path
import unittest
import tempfile
import sqlite3
import shutil

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import the database configuration
from database.db_config import db_config

class TestDatabaseConfig(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.test_db_path = Path(self.test_dir) / "test_db.sqlite"
        
        # Store the original path
        self.original_path = db_config.path
        
        # Set the test path
        db_config.set_path(self.test_db_path)
    
    def tearDown(self):
        # Restore the original path
        db_config.set_path(self.original_path)
        
        # Remove temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_path_setting(self):
        """Test that the path setting works correctly"""
        self.assertEqual(db_config.path, self.test_db_path)
        
        # Test setting a new path
        new_path = Path(self.test_dir) / "another_test.db"
        db_config.set_path(new_path)
        self.assertEqual(db_config.path, new_path)
    
    def test_directory_creation(self):
        """Test that directory creation works"""
        # Remove the test directory
        shutil.rmtree(self.test_dir)
        
        # Test that the method creates the directory
        db_config.ensure_directory_exists()
        
        # Check that the directory exists
        self.assertTrue(self.test_db_path.parent.exists())
    
    def test_database_creation(self):
        """Test that database creation works"""
        # Create the database
        result = db_config.create_database()
        
        # Check the result
        self.assertTrue(result)
        
        # Check that the database file exists
        self.assertTrue(self.test_db_path.exists())
        
        # Check that the tables were created
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Check that required tables exist
        required_tables = ['categories', 'priorities', 'statuses', 'tasks']
        for table in required_tables:
            self.assertIn(table, tables)
        
        # Check that defaults were inserted
        cursor.execute("SELECT COUNT(*) FROM categories")
        self.assertGreater(cursor.fetchone()[0], 0)
        
        cursor.execute("SELECT COUNT(*) FROM priorities")
        self.assertGreater(cursor.fetchone()[0], 0)
        
        cursor.execute("SELECT COUNT(*) FROM statuses")
        self.assertGreater(cursor.fetchone()[0], 0)
        
        conn.close()
    
    def test_connection(self):
        """Test that we can get a database connection"""
        # Create the database first
        db_config.create_database()
        
        # Get a connection
        conn = db_config.connection()
        
        # Check that it's a valid connection
        self.assertIsInstance(conn, sqlite3.Connection)
        
        # Test that we can execute a query
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM categories")
        count = cursor.fetchone()[0]
        self.assertGreater(count, 0)
        
        # Close the connection
        conn.close()
    
    def test_database_existence_check(self):
        """Test that we can check if the database exists"""
        # Initially the database doesn't exist
        self.assertFalse(db_config.database_exists())
        
        # Create it
        db_config.create_database()
        
        # Now it should exist
        self.assertTrue(db_config.database_exists())

if __name__ == '__main__':
    unittest.main()