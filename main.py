# src/main.py

from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QStackedWidget, QFileDialog, 
                           QMessageBox, QLabel, QTabWidget)
from ui.task_tree import TaskTreeWidget
from ui.task_pill_delegate import TaskPillDelegate
from ui.category_manager import CategoryManager
from ui.priority_manager import PriorityManager
from ui.status_manager import StatusManager
from ui.app_settings import AppSettingsWidget, SettingsManager
from PyQt6.QtGui import QKeySequence, QShortcut, QIcon, QFont
from PyQt6.QtCore import Qt, QSize
from pathlib import Path
from ui.status_manager import StatusManager, StatusItem
from ui.task_dialogs import EditStatusDialog
import csv
import sys
import sqlite3
import os

class MainWindow(QMainWindow):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task Organizer")
        self.setGeometry(100, 100, 900, 700)
        
        # Initialize settings manager
        self.settings = SettingsManager()
        
        # Get database path from settings
        self.db_path = self.settings.prompt_for_database_location(self)
        
        # Create stacked widget to hold both views
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # Initialize views
        self.init_task_view()
        self.init_settings_view()
        
        # Add widgets to the stack
        self.stacked_widget.addWidget(self.task_widget)
        self.stacked_widget.addWidget(self.settings_widget)
        
        # Show task view by default
        self.show_task_view()

        # Add shortcuts
        self.setup_shortcuts()
        
        # Set application style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QLabel {
                color: #333333;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: white;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover {
                background-color: #e0e0e0;
            }
        """)
    
    def setup_shortcuts(self):
        # New Task
        new_shortcut = QShortcut(QKeySequence.StandardKey.New, self)
        new_shortcut.activated.connect(self.show_add_dialog)
        
        # Edit (when task is selected)
        edit_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        edit_shortcut.activated.connect(self.edit_selected_task)
        
        # Settings
        settings_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        settings_shortcut.activated.connect(self.show_settings)
        
        # Import/Export
        import_shortcut = QShortcut(QKeySequence("Ctrl+I"), self)
        import_shortcut.activated.connect(self.import_from_csv)
        
        export_shortcut = QShortcut(QKeySequence("Ctrl+X"), self)
        export_shortcut.activated.connect(self.export_to_csv)
    
    def edit_selected_task(self):
        if self.stacked_widget.currentIndex() == 0:  # Only when in task view
            selected_items = self.tree.selectedItems()
            if selected_items:
                self.tree.edit_task(selected_items[0])
    
    def init_task_view(self):
        self.task_widget = QWidget()
        layout = QVBoxLayout(self.task_widget)
        
        # Add header
        header_layout = QHBoxLayout()
        title_label = QLabel("Task Organizer")
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #333333;
            margin-bottom: 10px;
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Add tree
        self.tree = TaskTreeWidget()
        layout.addWidget(self.tree)
        
        # Buttons container
        button_layout = QHBoxLayout()
        
        # Add Task button
        add_button = QPushButton("Add Task")
        add_button.setFixedHeight(40)
        add_button.clicked.connect(self.show_add_dialog)
        button_layout.addWidget(add_button)
        
        # Export button
        export_button = QPushButton("Export to CSV")
        export_button.setFixedHeight(40)
        export_button.setStyleSheet("""
            background-color: #2196F3;
        """)
        export_button.clicked.connect(self.export_to_csv)
        button_layout.addWidget(export_button)
        
        # Import button
        import_button = QPushButton("Import from CSV")
        import_button.setFixedHeight(40)
        import_button.setStyleSheet("""
            background-color: #2196F3;
        """)
        import_button.clicked.connect(self.import_from_csv)
        button_layout.addWidget(import_button)
        
        # Settings button
        settings_button = QPushButton("Settings")
        settings_button.setFixedHeight(40)
        settings_button.setStyleSheet("""
            background-color: #9C27B0;
        """)
        settings_button.clicked.connect(self.show_settings)
        button_layout.addWidget(settings_button)
        
        # Toggle View button
        toggle_view_button = QPushButton("Toggle View")
        toggle_view_button.setFixedHeight(40)
        toggle_view_button.setStyleSheet("""
            background-color: #607D8B;
        """)
        toggle_view_button.clicked.connect(self.toggle_task_view)
        toggle_view_button.setToolTip("Toggle between compact and full view")
        button_layout.addWidget(toggle_view_button)
        
        # Add buttons to main layout
        layout.addLayout(button_layout)

        # Add tooltips for keyboard shortcuts
        add_button.setToolTip("Add New Task (Ctrl+N)")
        export_button.setToolTip("Export to CSV (Ctrl+X)")
        import_button.setToolTip("Import from CSV (Ctrl+I)")
        settings_button.setToolTip("Settings (Ctrl+S)")
    
    def init_settings_view(self):
        self.settings_widget = QWidget()
        layout = QVBoxLayout(self.settings_widget)
        
        # Create tab widget for different settings sections
        self.settings_tabs = QTabWidget()
        
        # Create Category Manager tab
        self.category_manager = CategoryManager()
        self.settings_tabs.addTab(self.category_manager, "Categories")
        
        # Create Priority Manager tab
        self.priority_manager = PriorityManager()
        self.settings_tabs.addTab(self.priority_manager, "Priorities")
        
        # Create Status Manager tab
        self.status_manager = StatusManager()
        self.settings_tabs.addTab(self.status_manager, "Statuses")
        
        # Create App Settings tab
        self.app_settings = AppSettingsWidget(self)
        self.settings_tabs.addTab(self.app_settings, "App Settings")
        
        # Add tabs to layout
        layout.addWidget(self.settings_tabs)
        
        # Add Done button
        done_button = QPushButton("Back to Tasks")
        done_button.setFixedHeight(40)
        done_button.setStyleSheet("""
            background-color: #2196F3;
        """)
        done_button.clicked.connect(self.show_task_view)
        
        # Add button to layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(done_button)
        button_layout.addStretch()  # Push button to the left
        layout.addLayout(button_layout)

    def show_task_view(self):
        self.stacked_widget.setCurrentIndex(0)
        # Refresh tree when returning from settings
        self.tree.load_tasks()
    
    def show_settings(self):
        self.stacked_widget.setCurrentIndex(1)
    
    def show_add_dialog(self):
        from ui.task_dialogs import AddTaskDialog
        # Pass self (MainWindow) as the parent
        dialog = AddTaskDialog(self)
        if dialog.exec():
            # Pass the data to the tree for adding
            self.tree.add_new_task(dialog.get_data())
    
    def export_to_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", "", "CSV Files (*.csv)")
        
        if file_path:
            try:
                with open(file_path, 'w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(['Title', 'Description', 'Link', 'Status', 'Priority', 'Due Date', 'Category', 'Parent'])
                    
                    def write_items(parent_item=None):
                        items = []
                        if parent_item is None:
                            for i in range(self.tree.topLevelItemCount()):
                                items.append(self.tree.topLevelItem(i))
                        else:
                            for i in range(parent_item.childCount()):
                                items.append(parent_item.child(i))
                        
                        for item in items:
                            data = item.data(0, Qt.ItemDataRole.UserRole)
                            parent_title = ""
                            if item.parent():
                                parent_data = item.parent().data(0, Qt.ItemDataRole.UserRole)
                                parent_title = parent_data['title']
                            
                            writer.writerow([
                                data['title'],
                                data['description'],
                                data['link'],
                                data['status'],
                                data['priority'],
                                data['due_date'],
                                data['category'],
                                parent_title
                            ])
                            write_items(item)  # Write children
                    
                    write_items()
                QMessageBox.information(self, "Success", "Export completed successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error exporting data: {str(e)}")

    def import_from_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV", "", "CSV Files (*.csv)")
        
        if file_path:
            try:
                # First pass: create all items
                items_by_title = {}
                
                with open(file_path, 'r', newline='') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        data = {
                            'title': row['Title'],
                            'description': row.get('Description', ''),
                            'link': row.get('Link', ''),
                            'status': row.get('Status', 'Not Started'),
                            'priority': row.get('Priority', 'Medium'),
                            'due_date': row.get('Due Date', ''),
                            'category': row.get('Category', ''),
                            'parent_id': None  # Will be set in second pass
                        }
                        # Store the parent title for second pass
                        items_by_title[row['Title']] = {
                            'data': data,
                            'parent_title': row.get('Parent', '')
                        }
                
                # Second pass: set parent relationships
                for title, item_info in items_by_title.items():
                    parent_title = item_info['parent_title']
                    if parent_title and parent_title in items_by_title:
                        # Find parent's ID in database
                        with self.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("SELECT id FROM tasks WHERE title = ?", 
                                         (parent_title,))
                            result = cursor.fetchone()
                            if result:
                                item_info['data']['parent_id'] = result[0]
                
                # Add all items to database
                for item_info in items_by_title.values():
                    self.tree.add_new_task(item_info['data'])
                
                QMessageBox.information(self, "Success", "Import completed successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error importing data: {str(e)}")

    def save_template(self):
            """Save a template CSV file for data import."""
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Template CSV", "", "CSV Files (*.csv)")
            
            if file_path:
                try:
                    with open(file_path, 'w', newline='') as file:
                        writer = csv.writer(file)
                        # Write header row with column descriptions
                        writer.writerow(['Title', 'Description', 'Link', 'Status', 'Priority', 'Due Date', 'Category', 'Parent'])
                        # Add sample row
                        writer.writerow([
                            'Sample Task', 
                            'Description of the task', 
                            'https://example.com', 
                            'Not Started', 
                            'Medium', 
                            '2023-12-31', 
                            'Work', 
                            ''
                        ])
                        # Add instructions row
                        writer.writerow([
                            'Another Task',
                            'Another description',
                            '',
                            'Possible values: Not Started, In Progress, On Hold, Completed',
                            'Possible values: High, Medium, Low (or custom)',
                            'Format: YYYY-MM-DD',
                            'Must match existing category or be blank',
                            'Title of parent task or blank for top-level'
                        ])
                    
                    QMessageBox.information(self, "Success", "Template CSV created successfully!")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Error creating template: {str(e)}")

    def toggle_task_view(self):
        print("Toggle view button clicked")
        
        # Get the delegate
        delegate = self.tree.itemDelegate()
        
        # Make sure the delegate is the right type
        print(f"Delegate type: {type(delegate).__name__}")
        
        # Toggle the mode and update items
        if isinstance(delegate, TaskPillDelegate):
            # Explicitly set compact mode attribute
            if not hasattr(delegate, 'compact_mode'):
                delegate.compact_mode = False
            
            # Toggle and print the new state
            delegate.compact_mode = not delegate.compact_mode
            print(f"Compact mode: {delegate.compact_mode}")
            
            # Update button text
            sender = self.sender()
            if sender:
                sender.setText("Full View" if delegate.compact_mode else "Compact View")
            
            # Force a repaint
            self.tree.viewport().update()
            
            # Apply to all items
            for i in range(self.tree.topLevelItemCount()):
                self.toggle_item_view(self.tree.topLevelItem(i), delegate.compact_mode)
            
            # Force layout update
            self.tree.scheduleDelayedItemsLayout()
        else:
            print("Delegate is not a TaskPillDelegate instance")

    def toggle_item_view(self, item, compact_mode):
        # Set item size
        height = 40 if compact_mode else 80  # Compact or full height
        item.setSizeHint(0, QSize(self.tree.viewport().width(), height + 10))
        
        # Process children
        for i in range(item.childCount()):
            self.toggle_item_view(item.child(i), compact_mode)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    
    # Get the database path from settings
    db_path = Path(window.db_path)
    
    # Ensure database directory exists
    db_dir = db_path.parent
    if not db_dir.exists():
        db_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if database exists, if not initialize it
    if not db_path.exists():
        from database.db_setup import init_database
       
        # Update the DB_PATH to use our settings path
        import database.db_setup
        database.db_setup.DB_PATH = db_path
        init_database()
        
        # Insert test data
        from database.insert_test_data import insert_test_tasks
       
        # Update the DB_PATH in test data too
        import database.insert_test_data
        database.insert_test_data.DB_PATH = db_path
        insert_test_tasks()
    else:
        # Import and configure the database manager first
        from database.database_manager import get_db_manager
        db_manager = get_db_manager()
        
        # Update DB_PATH in the database manager
        if hasattr(db_manager, 'set_db_path'):
            db_manager.set_db_path(db_path)
        else:
            db_manager._db_path = db_path
        
        # Get connection from the database manager
        with db_manager.get_connection() as conn:
            # Set timeouts to avoid database locked errors
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute("PRAGMA journal_mode = WAL")
            
            cursor = conn.cursor()
            
            # Check if statuses table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='statuses'
            """)
            if not cursor.fetchone():
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
                
                print("Created statuses table with default values")
            
            # Check if priorities table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='priorities'
            """)
            if not cursor.fetchone():
                # Create priorities table
                cursor.execute("""
                    CREATE TABLE priorities (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        color TEXT NOT NULL,
                        display_order INTEGER NOT NULL
                    )
                """)
                
                # Insert default priorities
                default_priorities = [
                    ('High', '#F44336', 1),     # Red (highest priority)
                    ('Medium', '#FFC107', 2),   # Amber (medium priority)
                    ('Low', '#4CAF50', 3)       # Green (lowest priority)
                ]
                
                cursor.executemany("""
                    INSERT INTO priorities (name, color, display_order)
                    VALUES (?, ?, ?)
                """, default_priorities)
                
                print("Created priorities table with default values")
            else:
                # Check if display_order column exists
                try:
                    cursor.execute("SELECT display_order FROM priorities LIMIT 1")
                except sqlite3.OperationalError:
                    # Add display_order column
                    cursor.execute("ALTER TABLE priorities ADD COLUMN display_order INTEGER DEFAULT 0")
                    
                    # Set default display order values
                    priority_order = {
                        'High': 1,
                        'Medium': 2, 
                        'Low': 3
                    }
                    
                    # Get existing priorities
                    cursor.execute("SELECT id, name FROM priorities")
                    for priority_id, name in cursor.fetchall():
                        order = priority_order.get(name, 99)  # Default to end of list
                        cursor.execute(
                            "UPDATE priorities SET display_order = ? WHERE id = ?", 
                            (order, priority_id)
                        )
                    
                    print("Added display_order column to priorities table")
            
            conn.commit()
    
    # Import and configure the database manager
    from database.database_manager import get_db_manager
    db_manager = get_db_manager()
    
    # Make sure we close any existing connections before updating paths
    if hasattr(db_manager, '_connection') and db_manager._connection is not None:
        db_manager._connection.close()
        db_manager._connection = None
    
    # Update DB_PATH in the database manager
    if hasattr(db_manager, 'set_db_path'):
        db_manager.set_db_path(db_path)
    else:
        db_manager._db_path = db_path
    
    # Define a function for getting the connection
    def get_connection():
        return db_manager.get_connection()
    
    # Import all needed classes
    from ui.task_tree import TaskTreeWidget
    from ui.category_manager import CategoryManager, CategoryItem, EditCategoryDialog
    from ui.priority_manager import PriorityManager, PriorityItem, EditPriorityDialog
    from ui.status_manager import StatusManager, StatusItem, EditStatusDialog
    from ui.task_dialogs import AddTaskDialog, EditTaskDialog
    from ui.task_pill_delegate import TaskPillDelegate
    
    # Set the DB_PATH for backward compatibility
    TaskTreeWidget.DB_PATH = db_path
    CategoryManager.DB_PATH = db_path
    CategoryItem.DB_PATH = db_path
    EditCategoryDialog.DB_PATH = db_path
    PriorityManager.DB_PATH = db_path
    PriorityItem.DB_PATH = db_path
    EditPriorityDialog.DB_PATH = db_path
    StatusManager.DB_PATH = db_path
    StatusItem.DB_PATH = db_path
    EditStatusDialog.DB_PATH = db_path
    AddTaskDialog.DB_PATH = db_path
    EditTaskDialog.DB_PATH = db_path
    TaskPillDelegate.DB_PATH = db_path
    
    # Add get_connection method to all classes
    for cls in [TaskTreeWidget, CategoryManager, CategoryItem, EditCategoryDialog,
               PriorityManager, PriorityItem, EditPriorityDialog,
               StatusManager, StatusItem, EditStatusDialog,
               AddTaskDialog, EditTaskDialog, TaskPillDelegate]:
        setattr(cls, 'get_connection', staticmethod(get_connection))
    
    # Show the window and start the application
    window.show()
    sys.exit(app.exec())
    
if __name__ == "__main__":
    main()