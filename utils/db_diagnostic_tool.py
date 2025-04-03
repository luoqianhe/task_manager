# db_path_diagnostic.py
# Run this script to diagnose database path inconsistencies

import sys
from pathlib import Path
import importlib.util
import inspect

# Add the parent directory to the path to import app_settings
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

# Print current working directory and script location
print(f"Current working directory: {Path.cwd()}")
print(f"Script location: {Path(__file__).resolve()}")
print(f"Parent directory added to path: {parent_dir}")
print("-" * 60)

# Try to import the settings manager
try:
    from ui.app_settings import SettingsManager
    settings = SettingsManager()
    settings_path = Path(settings.settings_file)
    db_path_from_settings = Path(settings.get_setting("database_path"))
    
    print(f"Settings file: {settings_path}")
    print(f"Database path from settings: {db_path_from_settings}")
    print(f"Settings file exists: {settings_path.exists()}")
    print(f"Database file exists: {db_path_from_settings.exists()}")
except Exception as e:
    print(f"Error importing SettingsManager: {e}")

print("-" * 60)

# Try to import database modules
modules_to_check = [
    'database.db_setup',
    'database.database_manager',
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
            print(f"  DB_PATH: {db_path}")
            print(f"  Path exists: {Path(db_path).exists()}")
        else:
            print("  No DB_PATH attribute found")
        
        # Check for get_db_path function
        if hasattr(module, 'get_db_path'):
            try:
                db_path = module.get_db_path()
                print(f"  get_db_path(): {db_path}")
                print(f"  Path exists: {Path(db_path).exists()}")
            except Exception as e:
                print(f"  Error calling get_db_path(): {e}")
        
        # Check for DatabaseManager class
        if 'DatabaseManager' in dir(module):
            try:
                db_manager_class = getattr(module, 'DatabaseManager')
                # Try to create an instance
                db_manager = db_manager_class()
                if hasattr(db_manager, 'db_path'):
                    manager_path = db_manager.db_path
                    print(f"  DatabaseManager.db_path: {manager_path}")
                    print(f"  Path exists: {Path(manager_path).exists()}")
            except Exception as e:
                print(f"  Error creating DatabaseManager: {e}")
        
        # Look for any other path-related attributes or methods
        for name, member in inspect.getmembers(module):
            if 'path' in name.lower() or 'db' in name.lower():
                print(f"  Found path-related member: {name}")
                
    except Exception as e:
        print(f"  Error importing module: {e}")
    
    print()

print("-" * 60)
print("Path resolution recommendations:")
print("1. Make sure the app_settings.py is correctly loading the settings file")
print("2. Ensure all modules use the same mechanism to get the database path")
print("3. Consider adding a central database path configuration in a single location")
print("4. Update main.py to correctly set DB_PATH in all relevant modules")