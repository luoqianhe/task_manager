# src/main.py - updated with debugging
from utils.debug_logger import get_debug_logger
from utils.debug_init import init_debugger
from utils.debug_decorator import debug_method
from ui.app_settings import SettingsManager
from ui.os_style_manager import OSStyleManager
import argparse

# Create argument parser
parser = argparse.ArgumentParser(description='Task Organizer')
parser.add_argument('--debug', action='store_true', help='Enable debugging')
parser.add_argument('--debug-file', action='store_true', help='Log to file')
parser.add_argument('--debug-console', action='store_true', help='Log to console')
parser.add_argument('--debug-file-path', type=str, help='Path to log file')
args = parser.parse_args()

# Initialize settings manager first
settings = SettingsManager()

# Set arguments based on saved settings
debug_enabled = settings.get_setting("debug_enabled", False)
args.debug = debug_enabled
args.debug_file = debug_enabled  # Enable file logging if debug is enabled
args.debug_console = debug_enabled  # Enable console logging if debug is enabled

# Initialize debugger with settings from config
debug = init_debugger(args)
debug._enabled = debug_enabled
debug._log_to_file = debug_enabled
debug._log_to_console = debug_enabled

debug.debug("Starting Task Organizer application")

# Existing imports
from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QStackedWidget, QFileDialog, 
                           QMessageBox, QLabel, QTabWidget)
from ui.task_tree import TaskTreeWidget
from ui.task_tabs import TaskTabWidget
from ui.task_pill_delegate import TaskPillDelegate
from ui.combined_settings import CombinedSettingsManager
from ui.app_settings import AppSettingsWidget, SettingsManager
from PyQt6.QtGui import QKeySequence, QShortcut, QIcon, QFont
from PyQt6.QtCore import Qt, QSize, QTimer
from pathlib import Path
from ui.task_dialogs import AddTaskDialog
import csv
import sys
import sqlite3
from datetime import datetime
import traceback
import os
from ui.combined_display_settings import CombinedDisplaySettingsWidget

# Import database modules
from database.memory_db_manager import get_memory_db_manager
from database.db_config import db_config, ensure_db_exists

# Global function for database connection used by all classes
def get_global_connection():
    debug.debug("Getting global database connection")
    return get_memory_db_manager().get_connection()

class MainWindow(QMainWindow):
    
    @debug_method
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 900, 600)
        
        # Initialize settings manager
        self.settings = SettingsManager()
        
        # Get OS style information
        app = QApplication.instance()
        self.os_style = "Default"
        if app.property("style_manager"):
            self.os_style = app.property("style_manager").current_style
            debug.debug(f"MainWindow using OS style: {self.os_style}")
            
        # Apply OS-specific window settings
        self.apply_os_window_settings()
        
        # Initialize settings manager
        debug.debug("Creating SettingsManager")
        self.settings = SettingsManager()
        
        # Set default display settings if not already set
        if not self.settings.get_setting("right_panel_contents"):
            debug.debug("Setting default right_panel_contents")
            self.settings.set_setting("right_panel_contents", ["Link", "Due Date"])
        if not self.settings.get_setting("left_panel_contents"):
            debug.debug("Setting default left_panel_contents")
            self.settings.set_setting("left_panel_contents", ["Category", "Status"])
        
        # Get database path from settings
        debug.debug("Getting database path from settings")
        self.db_path = self.settings.prompt_for_database_location(self)
        debug.debug(f"Database path: {self.db_path}")
        
        # Create stacked widget to hold both views
        debug.debug("Creating stacked widget")
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # Initialize views
        debug.debug("Initializing task view")
        self.init_task_view()
        debug.debug("Initializing settings view")
        self.init_settings_view()
        
        # Add widgets to the stack
        debug.debug("Adding widgets to stack")
        self.stacked_widget.addWidget(self.task_widget)
        self.stacked_widget.addWidget(self.settings_widget)
        
        # Show task view by default
        debug.debug("Showing task view")
        self.show_task_view()
        
        debug.debug("Scheduling expanded state restoration")
        QTimer.singleShot(300, self._restore_initial_expanded_states)
    
        debug.debug(f"MainWindow initialization complete. Settings: left_panel_contents={self.settings.get_setting('left_panel_contents')}, right_panel_contents={self.settings.get_setting('right_panel_contents')}")

    @debug_method
    def _restore_initial_expanded_states(self):
        """Restore expanded states when application first starts"""
        debug.debug("Restoring initial expanded states")
        
        # Restore for each tab with progressively increasing delays
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, 'task_tree'):
                # Get tab-specific expanded states from settings
                tab_key = f"expanded_states_tab_{i}"
                expanded_items = self.settings.get_setting(tab_key, [])
                
                if expanded_items:
                    debug.debug(f"Scheduling restoration of {len(expanded_items)} expanded states for tab {i}")
                    # Use a longer delay for later tabs
                    delay = 800 + (i * 200)  # Increasing delay for each tab
                    QTimer.singleShot(delay, lambda t=tab.task_tree, items=expanded_items: 
                        self._delayed_restore_states(t, items))
                else:
                    debug.debug(f"No saved expanded states for tab {i}, skipping")
                    
    @debug_method
    def _delayed_restore_states(self, tree, expanded_items):
        """Helper method for delayed state restoration with better error handling"""
        debug.debug(f"Executing delayed state restoration with {len(expanded_items)} items")
        try:
            tree._restore_expanded_states(expanded_items)
            debug.debug("Delayed state restoration completed successfully")
        except Exception as e:
            debug.error(f"Error during delayed state restoration: {e}")
            debug.error(traceback.format_exc())
    
    @debug_method
    def init_settings_view(self):
        debug.debug('Creating settings view')
        self.settings_widget = QWidget()
        layout = QVBoxLayout(self.settings_widget)
        
        # Create tab widget for different settings sections
        debug.debug('Creating settings tabs')
        self.settings_tabs = QTabWidget()
        
        # Create Combined Settings Manager tab
        debug.debug('Creating Combined Settings tab')
        self.combined_settings = CombinedSettingsManager(main_window=self)
        self.settings_tabs.addTab(self.combined_settings, "Task Attributes")
        
        # Create Combined Display Settings tab
        try:
            debug.debug('Creating Display Settings tab')
            from ui.combined_display_settings import CombinedDisplaySettingsWidget
            self.display_settings = CombinedDisplaySettingsWidget(self)
            self.settings_tabs.addTab(self.display_settings, "Display Settings")
        except Exception as e:
            debug.error(f"Error creating display settings widget: {e}")
        
        # Create App Settings tab (Bee API key management is still here)
        debug.debug('Creating App Settings tab')
        self.app_settings = AppSettingsWidget(self)
        self.settings_tabs.addTab(self.app_settings, "App Settings")
        
        # Add tabs to layout
        layout.addWidget(self.settings_tabs)
        debug.debug('Settings view initialized')
      
    @debug_method
    def setup_shortcuts(self):
        debug.debug("Setting up keyboard shortcuts")
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
        debug.debug("Shortcuts setup complete")
    
    @debug_method
    def edit_selected_task(self):
        debug.debug("Edit selected task invoked")
        if self.stacked_widget.currentIndex() == 0:  # Only when in task view
            current_tree = self.tabs.get_current_tree()
            if current_tree:
                selected_items = current_tree.selectedItems()
                if selected_items:
                    debug.debug(f"Editing task: {selected_items[0].text(0)}")
                    current_tree.edit_task(selected_items[0])
                else:
                    debug.debug("No task selected to edit")
            else:
                debug.debug("No current tree available")

    @debug_method
    def init_task_view(self):
        debug.debug("Initializing task view")
        self.task_widget = QWidget()
        layout = QVBoxLayout(self.task_widget)
        
        # Add header
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Create and add tabbed widget
        debug.debug("Creating task tab widget")
        self.tabs = TaskTabWidget(self)
        layout.addWidget(self.tabs)
        
        # Buttons container
        button_layout = QHBoxLayout()
        
        # Add Task button
        add_button = QPushButton("Add Task")
        add_button.setFixedHeight(40)
        add_button.clicked.connect(self.show_add_dialog)
        button_layout.addWidget(add_button)
        
        # Donate button
        donate_button = QPushButton("Donate")
        donate_button.setFixedHeight(40)
        donate_button.clicked.connect(self.show_donate_dialog)
        # Make the donate button green
        donate_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        button_layout.addWidget(donate_button)
        
        # Settings button
        settings_button = QPushButton("Settings")
        settings_button.setFixedHeight(40)
        settings_button.clicked.connect(self.show_settings)
        button_layout.addWidget(settings_button)
        
        # Add buttons to main layout
        layout.addLayout(button_layout)

        # Add tooltips for keyboard shortcuts
        add_button.setToolTip("Add New Task (Ctrl+N)")
        donate_button.setToolTip("Support the development")
        settings_button.setToolTip("Settings (Ctrl+S)")
        
        # Tab shortcuts
        self.tabs.setTabToolTip(0, "Current Tasks (Ctrl+1)")
        self.tabs.setTabToolTip(1, "Backlog (Ctrl+2)")
        self.tabs.setTabToolTip(2, "Completed Tasks (Ctrl+3)")
        
        # Debug priority headers
        debug.debug("Debugging priority headers")
        self.tabs.current_tasks_tab.task_tree.debug_priority_headers()
        debug.debug("Task view initialization complete")

    @debug_method
    def show_donate_dialog(self, checked=False):
        debug.debug("Opening donate dialog")
        try:
            message = QMessageBox(self)
            message.setWindowTitle("Support Development")
            message.setText("Thank you for considering supporting the development of this application!")
            message.setInformativeText("Click 'Visit Website' to visit Paypal\n"
                                "and make a donation.\n"
                                "Click 'Copy URL' to copy my Paypal donation URL.")
           #  QMessageBox.information(self, "Copied", "blarp")
            message.setIcon(QMessageBox.Icon.Information)
            message.addButton(QMessageBox.StandardButton.Ok)
            
            # Add a button to copy information
            copy_button = message.addButton("Copy Info", QMessageBox.ButtonRole.ActionRole)
            
            # Add a button to visit website
            website_button = message.addButton("Visit Website", QMessageBox.ButtonRole.ActionRole)
            
            result = message.exec()
            
            if message.clickedButton() == copy_button:
                # Copy donation info to clipboard
                clipboard = QApplication.clipboard()
                clipboard.setText("https://www.paypal.com/donate/?business=YYKCLVPVTKSP6&no_recurring=0&item_name=I+make+software+that%27s+useful+for+myself.+Maybe+it%27s+useful+for+you%2C+too.&currency_code=USD")
                QMessageBox.information(self, "Copied", "Donation information copied to clipboard!")
            elif message.clickedButton() == website_button:
                # Open donation website
                import webbrowser
                webbrowser.open("https://www.paypal.com/donate/?business=YYKCLVPVTKSP6&no_recurring=0&item_name=I+make+software+that%27s+useful+for+myself.+Maybe+it%27s+useful+for+you%2C+too.&currency_code=USD")
        except Exception as e:
            debug.error(f"Error showing donate dialog: {e}")
            QMessageBox.critical(self, "Error", f"Error showing donate dialog: {str(e)}")    

    @debug_method
    def show_task_view(self, checked=False):
        debug.debug("Showing task view")
        # If coming from settings view, restore expanded states
        if self.stacked_widget.currentIndex() == 1:  # settings view
            debug.debug("Switching from settings to task view")
            
        self.stacked_widget.setCurrentIndex(0)
        # Refresh all tabs when returning from settings
        debug.debug("Reloading all tabs")
        self.tabs.reload_all()
        
        # Restore expanded states after reload
        current_tab = self.tabs.currentWidget()
        if hasattr(current_tab, 'task_tree'):
            debug.debug("Restoring expanded states after returning to task view")
            QTimer.singleShot(100, lambda: current_tab.task_tree._restore_expanded_states())

    @debug_method
    def show_settings(self, checked=False):
        debug.debug("Showing settings view")
        # Save expanded states before switching to settings
        current_tab = self.tabs.currentWidget()
        if hasattr(current_tab, 'task_tree'):
            debug.debug("Saving expanded states before switching to settings")
            print('show_settings save_expanded_states called')
            current_tab.task_tree._save_expanded_states()
            
        self.stacked_widget.setCurrentIndex(1)
    
    @debug_method
    def show_add_dialog(self, checked=False):
        debug.debug("Opening Add Task dialog")
        # from ui.task_dialogs import AddTaskDialog
        # from PyQt6.QtWidgets import QMessageBox
        # from datetime import datetime
        
        # Get the current tab index
        current_tab_index = self.tabs.currentIndex()
        debug.debug(f"Current tab index: {current_tab_index}")
        
        if current_tab_index == 2:  # Completed tab
            debug.debug("Creating task in Completed tab")
            # Ask for confirmation when creating a completed task
            reply = QMessageBox.question(
                self,
                "Create Completed Task",
                "Are you sure you want to create a task that's already completed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                debug.debug("User canceled creating completed task")
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
            debug.debug(f"Setting completion time: {completion_time}")
            
            if dialog.exec():
                debug.debug("Completed task dialog accepted")
                data = dialog.get_data()
                
                # Add the completion timestamp
                data['completed_at'] = completion_time
                
                # Get the current tree and add the task
                current_tree = self.tabs.get_current_tree()
                if current_tree:
                    task_id = current_tree.add_new_task(data)
                    debug.debug(f"Added completed task with ID: {task_id}")
                    
                    # Refresh all tabs
                    self.tabs.reload_all()
                    
        elif current_tab_index == 1:  # Backlog tab
            debug.debug("Creating task in Backlog tab")
            # Creating a task in the Backlog tab
            dialog = AddTaskDialog(self)
            
            # Set default status to Backlog
            dialog.status_combo.setCurrentText("Backlog")
            
            # Set priority to Unprioritized by default
            unprioritized_index = dialog.priority_combo.findText("Unprioritized") 
            if unprioritized_index >= 0:
                dialog.priority_combo.setCurrentIndex(unprioritized_index)
            
            if dialog.exec():
                debug.debug("Backlog task dialog accepted")
                # Ensure status is Backlog (in case user changed it)
                data = dialog.get_data()
                data['status'] = "Backlog"
                
                # Get the current tree and add the task
                current_tree = self.tabs.get_current_tree()
                if current_tree:
                    task_id = current_tree.add_new_task(data)
                    debug.debug(f"Added backlog task with ID: {task_id}")
                    
                    # Refresh all tabs
                    self.tabs.reload_all()
                
        else:  # Current Tasks tab (or any other future tab)
            debug.debug("Creating task in Current Tasks tab")
            # Standard task creation process
            dialog = AddTaskDialog(self)
            
            # Set priority to Unprioritized by default
            unprioritized_index = dialog.priority_combo.findText("Unprioritized")
            if unprioritized_index >= 0:
                dialog.priority_combo.setCurrentIndex(unprioritized_index)
            
            if dialog.exec():
                debug.debug("Current task dialog accepted")
                # Get the current tree and add the task
                current_tree = self.tabs.get_current_tree()
                if current_tree:
                    task_id = current_tree.add_new_task(dialog.get_data())
                    debug.debug(f"Added current task with ID: {task_id}")
                    
                    # Refresh all tabs
                    self.tabs.reload_all()
    
    @debug_method
    def export_to_csv(self, checked=False):
        debug.debug("Opening export to CSV dialog")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", "", "CSV Files (*.csv)")
        
        if file_path:
            debug.debug(f"Exporting to CSV file: {file_path}")
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
                    debug.debug("Querying tasks for export")
                    tasks = memory_db.execute_query("""
                        SELECT t.title, t.description, t.link, t.status, t.priority, 
                               t.due_date, c.name, p.title as parent_title, t.completed_at
                        FROM tasks t
                        LEFT JOIN categories c ON t.category_id = c.id
                        LEFT JOIN tasks p ON t.parent_id = p.id
                        ORDER BY t.id
                    """)
                    
                    # Write all tasks to CSV
                    debug.debug(f"Writing {len(tasks)} tasks to CSV")
                    for task in tasks:
                        writer.writerow(task)
                
                debug.debug("Export completed successfully")
                QMessageBox.information(self, "Success", "Export completed successfully!")
            except Exception as e:
                debug.error(f"Error exporting data: {e}")
                QMessageBox.critical(self, "Error", f"Error exporting data: {str(e)}")
        else:
            debug.debug("Export canceled by user")

    @debug_method
    def import_from_csv(self, checked=False):
        debug.debug("Opening import from CSV dialog")
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV", "", "CSV Files (*.csv)")
        
        if file_path:
            debug.debug(f"Importing from CSV file: {file_path}")
            try:
                # First pass: create all items
                items_by_title = {}
                
                with open(file_path, 'r', newline='') as file:
                    reader = csv.DictReader(file)
                    row_count = 0
                    for row in reader:
                        row_count += 1
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
                    debug.debug(f"Read {row_count} rows from CSV")
                
                # Second pass: set parent relationships
                debug.debug("Processing parent relationships")
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
                            debug.debug(f"Set parent ID {result[0]} for task '{title}'")
                
                # Add all items to database
                current_tree = self.tabs.get_current_tree()
                if current_tree:
                    debug.debug("Adding tasks to database")
                    added_count = 0
                    for title, item_info in items_by_title.items():
                        task_id = current_tree.add_new_task(item_info['data'])
                        if task_id:
                            added_count += 1
                    
                    debug.debug(f"Added {added_count} tasks from CSV")
                    
                    # Refresh all tabs
                    self.tabs.reload_all()
                
                debug.debug("Import completed successfully")
                QMessageBox.information(self, "Success", "Import completed successfully!")
            except Exception as e:
                debug.error(f"Error importing data: {e}")
                QMessageBox.critical(self, "Error", f"Error importing data: {str(e)}")
        else:
            debug.debug("Import canceled by user")

    @debug_method
    def save_template(self, checked=False):
        debug.debug("Saving template CSV")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Template CSV", "", "CSV Files (*.csv)")
        
        if file_path:
            debug.debug(f"Creating template CSV file: {file_path}")
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
                
                debug.debug("Template CSV created successfully")
                QMessageBox.information(self, "Success", "Template CSV created successfully!")
            except Exception as e:
                debug.error(f"Error creating template: {e}")
                QMessageBox.critical(self, "Error", f"Error creating template: {str(e)}")
        else:
            debug.debug("Template creation canceled by user")

    @debug_method
    def closeEvent(self, event):
        """Handle application shutdown"""
        debug.debug("Application closing - handling closeEvent")
        try:
            # Save expanded states for tabs with either expanded priority headers or tasks
            debug.debug("Saving expanded states for all relevant tabs")
            
            # Loop through tabs and check for any expanded items
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if hasattr(tab, 'task_tree'):
                    debug.debug(f"Checking tab {i} for expanded items")
                    
                    # Count expanded items (both priority headers and tasks)
                    tree = tab.task_tree
                    all_items = []
                    for j in range(tree.topLevelItemCount()):
                        top_item = tree.topLevelItem(j)
                        all_items.append(top_item)
                        if hasattr(tree, '_collect_child_items'):
                            tree._collect_child_items(top_item, all_items)
                    
                    # Check for any expanded items (priority headers or tasks)
                    expanded_items = []
                    for item in all_items:
                        index = tree.indexFromItem(item)
                        if index.isValid() and tree.isExpanded(index):
                            # Check if it's a priority header
                            data = item.data(0, Qt.ItemDataRole.UserRole)
                            if isinstance(data, dict) and data.get('is_priority_header', False):
                                priority = data.get('priority', 'Unknown')
                                expanded_items.append(f"priority:{priority}")
                                debug.debug(f"Found expanded priority header: {priority}")
                            # Check if it's a task with children
                            elif hasattr(item, 'task_id') and item.childCount() > 0:
                                expanded_items.append(f"task:{item.task_id}")
                                debug.debug(f"Found expanded task: {item.task_id}")
                    
                    # Save if we have any expanded items (priority headers or tasks)
                    if expanded_items:
                        tab_key = f"expanded_states_tab_{i}"
                        self.settings.set_setting(tab_key, expanded_items)
                        debug.debug(f"Saved {len(expanded_items)} expanded states for tab {i}")
                        
                        # Also save to the common key if it's the current tab
                        if i == self.tabs.currentIndex():
                            self.settings.set_setting("expanded_task_states", expanded_items)
                            debug.debug("Saved to common expanded_task_states key (current tab)")
                    else:
                        debug.debug(f"No expanded items in tab {i}, not saving")
            
            # Save the in-memory database back to file
            debug.debug("Saving in-memory database to file")
            from database.memory_db_manager import get_memory_db_manager
            db_manager = get_memory_db_manager()
            db_manager.save_to_file()
            debug.debug("Database saved successfully before exit")
            
            # Explicitly save settings before exit
            debug.debug("Saving application settings")
            self.settings.save_settings(self.settings.settings)
            debug.debug(f"Settings saved successfully.")

        except Exception as e:
            debug.error(f"Error saving data on exit: {e}")
            reply = QMessageBox.question(
                self, "Database Save Error",
                f"Failed to save database: {e}\n\nDo you still want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                debug.debug("User canceled application exit")
                event.ignore()
                return
        
        # Accept the close event
        debug.debug("Application shutdown complete")
        event.accept()
       
    @debug_method
    def on_settings_tab_changed(self, index):
        debug.debug(f"Settings tab changed to index {index}")
        # If switching to Bee To Dos tab
        if index == 3:  # Adjust index as needed based on tab position
            debug.debug("Switched to Bee To Dos settings tab")
            # Check if we have an API key
            api_key = self.settings.get_setting("bee_api_key", "")
            if not api_key:
                debug.debug("No Bee API key found, showing API key dialog")
                # No API key, show dialog
                from ui.bee_api_dialog import BeeApiKeyDialog
                dialog = BeeApiKeyDialog(self)
                
                if dialog.exec():
                    debug.debug("User provided API key")
                    # User provided an API key
                    api_key = dialog.get_api_key()
                    key_label = dialog.get_key_label()
                    
                    if api_key:
                        debug.debug("Saving API key to settings")
                        # Save to settings
                        self.settings.set_setting("bee_api_key", api_key)
                        if key_label:
                            self.settings.set_setting("bee_api_key_label", key_label)
                        
                        # Initialize Bee To Dos with new key
                        debug.debug("Initializing Bee To Dos with new API key")
                        self.bee_todos.initialize_with_api_key(api_key)
                    else:
                        debug.debug("No API key provided, switching back to previous tab")
                        # No API key provided, switch back to previous tab
                        self.settings_tabs.setCurrentIndex(self.previous_tab_index)
                else:
                    debug.debug("User canceled API key dialog, switching back to previous tab")
                    # User cancelled, switch back to previous tab
                    self.settings_tabs.setCurrentIndex(self.previous_tab_index)
            else:
                debug.debug("Using existing Bee API key")
                # API key exists, make sure Bee To Dos widget is initialized
                self.bee_todos.initialize_with_api_key(api_key)
        
        # Store the current tab index for reference
        self.previous_tab_index = index

    @debug_method
    def apply_os_window_settings(self):
        """Apply OS-specific settings to the main window"""
        if self.os_style == "macOS":
            # macOS styling
            self.setWindowTitle("Task Organizer")
            # macOS has its own window controls, so minimal adjustments needed
            
        elif self.os_style == "Windows":
            # Windows styling
            self.setWindowTitle("Task Organizer")
            # Optional: Use Windows-specific icon
            if Path("resources/icons/windows_app_icon.ico").exists():
                self.setWindowIcon(QIcon("resources/icons/windows_app_icon.ico"))
                
        else:  # Linux
            # Linux styling
            self.setWindowTitle("Task Organizer")
            # Optional: Use Linux-specific icon
            if Path("resources/icons/linux_app_icon.png").exists():
                self.setWindowIcon(QIcon("resources/icons/linux_app_icon.png"))
                
def apply_connection_method():
    """Apply the global connection method to all classes that need it"""
    debug.debug("Applying global connection method to classes")
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
    debug.debug("Global connection method applied to classes")


def main():
    debug.debug("Starting main() function")
    app = QApplication(sys.argv)
    
    # Initialize settings manager first
    debug.debug("Initializing SettingsManager")
    settings = SettingsManager()
    
    # Create OS Style Manager
    debug.debug("Creating OS Style Manager")
    style_manager = OSStyleManager(settings)
    
    # Apply OS-specific styling with user customizations
    os_style = style_manager.apply_os_styles(app)
    debug.debug(f"Applied {os_style} styling to application")
    
    # Store the style manager in the app properties for later reference
    app.setProperty("style_manager", style_manager)
    
    debug.debug(f"Initial settings: left_panel_contents={settings.get_setting('left_panel_contents')}, right_panel_contents={settings.get_setting('right_panel_contents')}")
    
    # Get database path from settings
    debug.debug("Getting database path from settings")
    db_path = settings.prompt_for_database_location()
    debug.debug(f"Database path: {db_path}")
    
    # Set the database path in the central configuration
    debug.debug("Setting database path in central configuration")
    db_config.set_path(db_path)
    
    # Initialize the memory database first - IMPORTANT!
    debug.debug("Initializing memory database")
    memory_db_manager = get_memory_db_manager()
    
    # Ensure directory exists
    debug.debug("Ensuring database directory exists")
    db_config.ensure_directory_exists()
    
    # Create database if it doesn't exist
    if not db_config.database_exists():
        debug.debug("Database doesn't exist. Creating a new one...")
        db_config.create_database()
    
    # Load the database into memory
    debug.debug(f"Loading database into memory from {db_path}")
    memory_db_manager.load_from_file(db_path)
    
    # Test connection before proceeding
    try:
        debug.debug("Testing database connection")
        test_result = memory_db_manager.execute_query("SELECT 1")
        debug.debug(f"Database connection test successful: {test_result}")
    except Exception as e:
        debug.error(f"Database connection test failed: {e}")
        QMessageBox.critical(None, "Database Error", 
                           f"Failed to initialize database: {str(e)}\n\nThe application will now exit.")
        sys.exit(1)
    
    # Apply the global connection method to all classes
    debug.debug("Applying global connection method")
    apply_connection_method()
    
    # Create main window
    debug.debug("Creating MainWindow")
    window = MainWindow()
    
    # Show the window and start the application
    debug.debug("Showing main window and starting application")
    window.show()
    
    debug.debug("Entering Qt event loop")
    sys.exit(app.exec())
         
if __name__ == "__main__":
    main()