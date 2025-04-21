# src/main.py - updated with proper database initialization

from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QStackedWidget, QFileDialog, 
                           QMessageBox, QLabel, QTabWidget)
from ui.task_tree import TaskTreeWidget
from ui.task_tabs import TaskTabWidget
from ui.task_pill_delegate import TaskPillDelegate
from ui.combined_settings import CombinedSettingsManager
from ui.app_settings import AppSettingsWidget, SettingsManager
from PyQt6.QtGui import QKeySequence, QShortcut, QIcon, QFont
from PyQt6.QtCore import Qt, QSize
from pathlib import Path
import csv
import sys
import sqlite3
from datetime import datetime
import os

# Import database modules
from database.memory_db_manager import get_memory_db_manager
from database.db_config import db_config, ensure_db_exists

# Global function for database connection used by all classes
def get_global_connection():
    return get_memory_db_manager().get_connection()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task Organizer")
        self.setGeometry(100, 100, 900, 600)  # Slightly wider window
        
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
        
        # Tab navigation
        tab1_shortcut = QShortcut(QKeySequence("Ctrl+1"), self)
        tab1_shortcut.activated.connect(lambda: self.tabs.setCurrentIndex(0))
        
        tab2_shortcut = QShortcut(QKeySequence("Ctrl+2"), self)
        tab2_shortcut.activated.connect(lambda: self.tabs.setCurrentIndex(1))
        
        tab3_shortcut = QShortcut(QKeySequence("Ctrl+3"), self)
        tab3_shortcut.activated.connect(lambda: self.tabs.setCurrentIndex(2))
        
    def edit_selected_task(self):
        if self.stacked_widget.currentIndex() == 0:  # Only when in task view
            current_tree = self.tabs.get_current_tree()
            if current_tree:
                selected_items = current_tree.selectedItems()
                if selected_items:
                    current_tree.edit_task(selected_items[0])
    
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
        
        # Create and add tabbed widget
        self.tabs = TaskTabWidget(self)
        layout.addWidget(self.tabs)
        
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
        
        # Add buttons to main layout
        layout.addLayout(button_layout)

        # Add tooltips for keyboard shortcuts
        add_button.setToolTip("Add New Task (Ctrl+N)")
        export_button.setToolTip("Export to CSV (Ctrl+X)")
        import_button.setToolTip("Import from CSV (Ctrl+I)")
        settings_button.setToolTip("Settings (Ctrl+S)")
        
        # Tab shortcuts
        self.tabs.setTabToolTip(0, "Current Tasks (Ctrl+1)")
        self.tabs.setTabToolTip(1, "Backlog (Ctrl+2)")
        self.tabs.setTabToolTip(2, "Completed Tasks (Ctrl+3)")
    
        # Debug priority headers
        self.tabs.current_tasks_tab.task_tree.debug_priority_headers()
        
    def init_settings_view(self):
        self.settings_widget = QWidget()
        layout = QVBoxLayout(self.settings_widget)
        
        # Create tab widget for different settings sections
        self.settings_tabs = QTabWidget()
        
        # Create Combined Settings Manager tab
        self.combined_settings = CombinedSettingsManager()
        self.settings_tabs.addTab(self.combined_settings, "Task Organization")
        
        # Create Font Settings tab
        from ui.font_settings import FontSettingsWidget  
        self.font_settings = FontSettingsWidget(self)
        self.settings_tabs.addTab(self.font_settings, "Font Settings")
        
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
        # Refresh all tabs when returning from settings
        self.tabs.reload_all()
    
    def show_settings(self):
        self.stacked_widget.setCurrentIndex(1)
    
    def show_add_dialog(self):
        from ui.task_dialogs import AddTaskDialog
        from PyQt6.QtWidgets import QMessageBox
        from datetime import datetime
        
        # Get the current tab index
        current_tab_index = self.tabs.currentIndex()
        
        if current_tab_index == 2:  # Completed tab
            # Ask for confirmation when creating a completed task
            reply = QMessageBox.question(
                self,
                "Create Completed Task",
                "Are you sure you want to create a task that's already completed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return  # User canceled, exit the function
            
            # User confirmed, proceed with creating a completed task
            dialog = AddTaskDialog(self)
            
            # Set status to Completed
            dialog.status_combo.setCurrentText("Completed")
            
            # Make this field read-only to prevent changes
            dialog.status_combo.setEnabled(False)
            
            # Set current date/time as completion time
            # We'll store this in the data when task is created
            completion_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if dialog.exec():
                data = dialog.get_data()
                
                # Add the completion timestamp
                data['completed_at'] = completion_time
                
                # Get the current tree and add the task
                current_tree = self.tabs.get_current_tree()
                if current_tree:
                    current_tree.add_new_task(data)
                    
                    # Refresh all tabs
                    self.tabs.reload_all()
                    
        elif current_tab_index == 1:  # Backlog tab
            # Creating a task in the Backlog tab
            dialog = AddTaskDialog(self)
            
            # Set default status to Backlog
            dialog.status_combo.setCurrentText("Backlog")
            
            # Set priority to Unprioritized by default
            unprioritized_index = dialog.priority_combo.findText("Unprioritized") 
            if unprioritized_index >= 0:
                dialog.priority_combo.setCurrentIndex(unprioritized_index)
            
            if dialog.exec():
                # Ensure status is Backlog (in case user changed it)
                data = dialog.get_data()
                data['status'] = "Backlog"
                
                # Get the current tree and add the task
                current_tree = self.tabs.get_current_tree()
                if current_tree:
                    current_tree.add_new_task(data)
                    
                    # Refresh all tabs
                    self.tabs.reload_all()
                
        else:  # Current Tasks tab (or any other future tab)
            # Standard task creation process
            dialog = AddTaskDialog(self)
            
            # Set priority to Unprioritized by default
            unprioritized_index = dialog.priority_combo.findText("Unprioritized")
            if unprioritized_index >= 0:
                dialog.priority_combo.setCurrentIndex(unprioritized_index)
            
            if dialog.exec():
                # Get the current tree and add the task
                current_tree = self.tabs.get_current_tree()
                if current_tree:
                    current_tree.add_new_task(dialog.get_data())
                    
                    # Refresh all tabs
                    self.tabs.reload_all()
    
    def export_to_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", "", "CSV Files (*.csv)")
        
        if file_path:
            try:
                with open(file_path, 'w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        'Title', 'Description', 'Link', 'Status', 'Priority', 
                        'Due Date', 'Category', 'Parent', 'Completed At'
                    ])
                    
                    # Use the memory database manager
                    memory_db = get_memory_db_manager()
                    
                    # Query all tasks with their parent titles
                    tasks = memory_db.execute_query("""
                        SELECT t.title, t.description, t.link, t.status, t.priority, 
                               t.due_date, c.name, p.title as parent_title, t.completed_at
                        FROM tasks t
                        LEFT JOIN categories c ON t.category_id = c.id
                        LEFT JOIN tasks p ON t.parent_id = p.id
                        ORDER BY t.id
                    """)
                    
                    # Write all tasks to CSV
                    for task in tasks:
                        writer.writerow(task)
                
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
                            'parent_id': None,  # Will be set in second pass
                            'completed_at': row.get('Completed At', '')
                        }
                        # Store the parent title for second pass
                        items_by_title[row['Title']] = {
                            'data': data,
                            'parent_title': row.get('Parent', '')
                        }
                
                # Second pass: set parent relationships
                memory_db = get_memory_db_manager()
                conn = memory_db.get_connection()
                cursor = conn.cursor()
                
                for title, item_info in items_by_title.items():
                    parent_title = item_info['parent_title']
                    if parent_title and parent_title in items_by_title:
                        # Find parent's ID in database
                        cursor.execute("SELECT id FROM tasks WHERE title = ?", 
                                     (parent_title,))
                        result = cursor.fetchone()
                        if result:
                            item_info['data']['parent_id'] = result[0]
                
                # Add all items to database
                current_tree = self.tabs.get_current_tree()
                if current_tree:
                    for item_info in items_by_title.values():
                        current_tree.add_new_task(item_info['data'])
                    
                    # Refresh all tabs
                    self.tabs.reload_all()
                
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
                    writer.writerow([
                        'Title', 'Description', 'Link', 'Status', 'Priority', 
                        'Due Date', 'Category', 'Parent', 'Completed At'
                    ])
                    # Add sample row
                    writer.writerow([
                        'Sample Task', 
                        'Description of the task', 
                        'https://example.com', 
                        'Not Started', 
                        'Medium', 
                        '2023-12-31', 
                        'Work', 
                        '',
                        ''
                    ])
                    # Add instructions row
                    writer.writerow([
                        'Another Task',
                        'Another description',
                        '',
                        'Possible values: Not Started, In Progress, On Hold, Completed, Backlog',
                        'Possible values: High, Medium, Low (or custom)',
                        'Format: YYYY-MM-DD',
                        'Must match existing category or be blank',
                        'Title of parent task or blank for top-level',
                        'Format: YYYY-MM-DD HH:MM:SS (auto-filled when status becomes Completed)'
                    ])
                    
                QMessageBox.information(self, "Success", "Template CSV created successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error creating template: {str(e)}")

def apply_connection_method():
    """Apply the global connection method to all classes that need it"""
    # Import all needed classes
    from ui.task_tree import TaskTreeWidget
    from ui.task_tabs import TabTaskTreeWidget, TaskTabWidget  
    from ui.combined_settings import CombinedSettingsManager, SettingPillItem, EditItemDialog
    from ui.task_dialogs import AddTaskDialog, EditTaskDialog
    from ui.task_pill_delegate import TaskPillDelegate
    
    # Add get_connection method to all classes
    for cls in [TaskTreeWidget, TabTaskTreeWidget, TaskTabWidget, CombinedSettingsManager, 
               SettingPillItem, EditItemDialog, AddTaskDialog, EditTaskDialog, TaskPillDelegate]:
        setattr(cls, 'get_connection', staticmethod(get_global_connection))

def main():
    app = QApplication(sys.argv)
    
    # Initialize settings manager first
    settings = SettingsManager()
    
    # Get database path from settings
    db_path = settings.prompt_for_database_location()
    
    # Set the database path in the central configuration
    db_config.set_path(db_path)
    
    # Print initialization information
    print(f"Initializing application with database path: {db_path}")
    
    # Initialize the memory database first - IMPORTANT!
    memory_db_manager = get_memory_db_manager()
    
    # Ensure directory exists
    db_config.ensure_directory_exists()
    
    # Create database if it doesn't exist
    if not db_config.database_exists():
        print("Database doesn't exist. Creating a new one...")
        db_config.create_database()
    
    # Load the database into memory
    print(f"Loading database into memory from {db_path}")
    memory_db_manager.load_from_file(db_path)
    
    # Test connection before proceeding
    try:
        test_result = memory_db_manager.execute_query("SELECT 1")
        print(f"Database connection test successful: {test_result}")
    except Exception as e:
        print(f"ERROR: Database connection test failed: {e}")
        QMessageBox.critical(None, "Database Error", 
                           f"Failed to initialize database: {str(e)}\n\nThe application will now exit.")
        sys.exit(1)
    
    # Apply the global connection method to all classes
    apply_connection_method()
    
    # Create main window
    window = MainWindow()
    
    # Show the window and start the application
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()