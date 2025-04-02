# src/utils/verify_db_path.py
"""
This script verifies that all parts of the application are using
the same database path from the centralized configuration.
"""

import sys
from pathlib import Path
import importlib

# Add parent directory to path
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

print("Database Path Verification Tool")
print("===============================")
print(f"Working directory: {Path.cwd()}")
print(f"Script location: {current_dir}")
print()

# First, check settings
try:
    from ui.app_settings import SettingsManager
    settings = SettingsManager()
    db_path_from_settings = Path(settings.get_setting("database_path"))
    print(f"Database path from settings: {db_path_from_settings}")
    print(f"Path exists: {db_path_from_settings.exists()}")
except Exception as e:
    print(f"Error getting path from settings: {e}")

print()

# Check central configuration
try:
    from database.db_config import db_config
    central_path = db_config.path
    print(f"Database path from central config: {central_path}")
    print(f"Path exists: {central_path.exists()}")
except Exception as e:
    print(f"Error getting path from central config: {e}")

print()

# Check database manager
try:
    from database.database_manager import get_db_manager
    db_manager = get_db_manager()
    manager_path = db_manager.db_path
    print(f"Database path from DatabaseManager: {manager_path}")
    print(f"Path exists: {manager_path.exists()}")
except Exception as e:
    print(f"Error getting path from DatabaseManager: {e}")

print()

# Check modules that used to have hard-coded paths
modules_to_check = [
    'database.db_setup',
    'database.insert_test_data',
    'database.check_db'
]

for module_name in modules_to_check:
    print(f"Checking module: {module_name}")
    try:
        # Import the module
        module = importlib.import_module(module_name)
        
        # Check for DB_PATH attribute
        if hasattr(module, 'DB_PATH'):
            db_path = getattr(module, 'DB_PATH')
            print(f"  [WARNING] Module has DB_PATH attribute: {db_path}")
            print(f"  This should be removed in favor of the central config.")
        else:
            print("  No DB_PATH attribute found - good!")
        
    except Exception as e:
        print(f"  Error importing module: {e}")
    
    print()

print("Testing Database Creation")
print("========================")
try:
    # Try creating the database
    print(f"Creating database at: {central_path}")
    result = db_config.create_database()
    print(f"Creation result: {result}")
    
    # Try getting a connection
    conn = db_config.connection()
    print("Successfully got a database connection")
    
    # Check tables
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tables in database: {', '.join(tables)}")
    
    # Close connection
    conn.close()
    
except Exception as e:
    print(f"Error testing database creation: {e}")

print()
print("Verification complete!")