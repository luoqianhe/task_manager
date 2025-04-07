# src/main.py - with integrated settings changes

from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QStackedWidget, QFileDialog, 
                           QMessageBox, QLabel, QTabWidget)
from ui.task_tree import TaskTreeWidget
from ui.task_pill_delegate import TaskPillDelegate
from ui.combined_settings import CombinedSettingsManager  # Updated import
from ui.app_settings import AppSettingsWidget, SettingsManager
from PyQt6.QtGui import QKeySequence, QShortcut, QIcon, QFont
from PyQt6.QtCore import Qt, QSize
from pathlib import Path
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
        self.setGeometry(100, 100, 800, 600)
        
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
        
        # Debug: Force show all toggle buttons
        self.tree.debug_toggle_buttons() 
        
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

def main():
    app = QApplication(sys.argv)
    
    # Create main window (this initializes settings)
    window = MainWindow()
    
    # Import and configure the database path
    from database.db_config import db_config, ensure_db_exists
    
    # Set the database path from the settings
    db_config.set_path(window.db_path)
    print(f"Main using database path: {db_config.path}")
    
    # Ensure the database exists and is initialized
    if not ensure_db_exists():
        # Database creation failed
        QMessageBox.critical(
            window,
            "Database Error",
            "Failed to create the database. Please check permissions and try again."
        )
        return 1
    
    # If database was just created, ask about sample data
    if not db_config.path.exists():
        reply = QMessageBox.question(
            window, 
            'Initialize Database',
            'Would you like to add sample tasks to the new database?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from database.insert_test_data import insert_test_tasks
                insert_test_tasks()
                print("Sample tasks added to database")
            except Exception as e:
                QMessageBox.warning(
                    window,
                    "Sample Data Error",
                    f"Could not add sample data: {e}\n\nThe database was created but will be empty."
                )
    
    # Import database manager 
    from database.database_manager import get_db_manager
    db_manager = get_db_manager()
    
    # Define a function for getting the connection
    def get_connection():
        return db_manager.get_connection()
    
    # Import all needed classes
    from ui.task_tree import TaskTreeWidget
    from ui.combined_settings import CombinedSettingsManager, SettingPillItem, EditItemDialog
    from ui.task_dialogs import AddTaskDialog, EditTaskDialog
    from ui.task_pill_delegate import TaskPillDelegate
    
    # Add get_connection method to all classes
    for cls in [TaskTreeWidget, CombinedSettingsManager, SettingPillItem, EditItemDialog,
               AddTaskDialog, EditTaskDialog, TaskPillDelegate]:
        setattr(cls, 'get_connection', staticmethod(get_connection))
    
    # Show the window and start the application
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()