# src/ui/bee_todos.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                           QHBoxLayout, QListWidget, QListWidgetItem, QCheckBox, 
                           QGroupBox, QMessageBox, QProgressBar, QDialog, QRadioButton, QComboBox)
from PyQt6.QtCore import Qt, QThreadPool, QRunnable, pyqtSignal, QObject
from PyQt6.QtGui import QFont

import asyncio
import threading
import sys
import json

# Import the Bee To-Do Manager
from beeai import Bee

# Signal manager for async operations
class WorkerSignals(QObject):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

# Worker class for async operations
class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        
    def run(self):
        try:
            # Run async function in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.fn(*self.args, **self.kwargs))
            loop.close()
            self.signals.finished.emit(result)
        except Exception as e:
            print(f"Worker error: {e}")
            self.signals.error.emit(str(e))
            
class BeeToDoWidget(QWidget):
    """Widget for the Bee To Dos tab"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.settings = main_window.settings
        self.bee_manager = None
        self.api_key = None
        self.todos = []
        self.thread_pool = QThreadPool()
        
        # Set up the basic UI structure
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the initial UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Bee To Dos")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header_label)
        
        # Description
        desc_label = QLabel("Manage and import To-Do items from your Bee wearable device")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Content area - we'll populate this when initialized with API key
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        
        # Empty state message
        self.empty_label = QLabel("Initializing Bee To Dos...")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.empty_label)
        
        layout.addWidget(self.content_area)
    
    def initialize_with_api_key(self, api_key):
        """Initialize with the provided API key"""
        if api_key == self.api_key and self.bee_manager:
            # Already initialized with this key
            return
            
        self.api_key = api_key
        
        # Clear content area
        self.clear_content_area()
        self.empty_label.setText("Loading Bee To Dos...")
        self.empty_label.setVisible(True)
        
        # Create Bee manager
        self.create_bee_manager()
        
        # Initialize UI with the API key
        self.initialize_ui()
        
        # Load To Dos
        self.load_todos()
    
    def clear_content_area(self):
        """Clear the content area to prepare for new content"""
        # Hide all widgets except empty label
        for i in range(self.content_layout.count()):
            widget = self.content_layout.itemAt(i).widget()
            if widget and widget != self.empty_label:
                widget.setVisible(False)
    
    def create_bee_manager(self):
        """Create the Bee manager for API access"""
        try:
            # Create Bee manager with the API key
            self.bee_manager = BeeToDoManager(self.api_key)
            print("Bee manager created successfully")
        except Exception as e:
            print(f"Error creating Bee manager: {e}")
            self.empty_label.setText(f"Error initializing Bee: {str(e)}")
            self.bee_manager = None
        
    def initialize_ui(self):
        """Initialize the UI with API key"""
        if not hasattr(self, 'todos_group'):
            # Create UI components if they don't exist yet
            self.create_todos_ui()
        else:
            # Show existing UI components
            self.todos_group.setVisible(True)
            self.actions_group.setVisible(True)
    
    def create_todos_ui(self):
        """Create the UI components for To-Dos"""
        # To-Do Items group
        self.todos_group = QGroupBox("To-Do Items")
        todos_layout = QVBoxLayout()
        
        # Top actions - Refresh and Select All
        top_actions = QHBoxLayout()
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_todos)
        top_actions.addWidget(self.refresh_btn)
        
        top_actions.addStretch()
        
        # Select All checkbox
        self.select_all_cb = QCheckBox("Select All")
        self.select_all_cb.stateChanged.connect(self.toggle_select_all)
        top_actions.addWidget(self.select_all_cb)
        
        todos_layout.addLayout(top_actions)
        
        # To-Do list
        self.todos_list = QListWidget()
        self.todos_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        todos_layout.addWidget(self.todos_list)
        
        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        todos_layout.addWidget(self.progress_bar)
        
        # Status label - shows count or loading state
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        todos_layout.addWidget(self.status_label)
        
        self.todos_group.setLayout(todos_layout)
        self.content_layout.addWidget(self.todos_group)
        
        # Actions group
        self.actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout()
        
        # Batch Edit button
        self.batch_edit_btn = QPushButton("Batch Edit")
        self.batch_edit_btn.clicked.connect(self.batch_edit)
        actions_layout.addWidget(self.batch_edit_btn)
        
        # Delete button
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected)
        actions_layout.addWidget(self.delete_btn)
        
        self.actions_group.setLayout(actions_layout)
        self.content_layout.addWidget(self.actions_group)
        
        # Initially hide the UI until we have to-dos loaded
        self.todos_group.setVisible(False)
        self.actions_group.setVisible(False)
    
    def load_todos(self):
        """Load To Dos from the Bee API"""
        if not self.bee_manager:
            self.empty_label.setText("Error: Bee manager not initialized")
            return
        
        # Show loading state
        self.empty_label.setText("Loading To-Dos from Bee...")
        self.empty_label.setVisible(True)
        
        if hasattr(self, 'todos_group'):
            self.todos_group.setVisible(False)
            self.actions_group.setVisible(False)
        
        # Show progress bar
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
        
        # Create worker to fetch todos in background
        worker = Worker(self.bee_manager.get_all_todos)
        worker.signals.finished.connect(self.on_todos_loaded)
        worker.signals.error.connect(self.on_load_error)
        worker.signals.progress.connect(self.update_progress)
        
        # Execute the worker
        self.thread_pool.start(worker)
    
    def on_todos_loaded(self, todos):
        """Handle loaded to-dos"""
        self.todos = todos
        print(f"Loaded {len(todos)} to-dos")
        
        # Hide loading indicator
        self.empty_label.setVisible(False)
        
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(False)
        
        # Show UI groups
        if hasattr(self, 'todos_group'):
            self.todos_group.setVisible(True)
            self.actions_group.setVisible(True)
        
        # Populate to-dos list
        self.populate_todos_list()
        
        # Update status with count
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"{len(todos)} items total")
    
    def on_load_error(self, error_msg):
        """Handle error when loading to-dos"""
        print(f"Error loading to-dos: {error_msg}")
        
        # Show error message
        self.empty_label.setText(f"Error loading To-Dos: {error_msg}")
        self.empty_label.setVisible(True)
        
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(False)
        
        # Hide UI groups
        if hasattr(self, 'todos_group'):
            self.todos_group.setVisible(False)
            self.actions_group.setVisible(False)
    
    def update_progress(self, value):
        """Update progress bar"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(value)
    
    def populate_todos_list(self):
        """Populate the to-dos list widget"""
        if not hasattr(self, 'todos_list'):
            return
            
        # Clear existing items
        self.todos_list.clear()
        
        # Add to-dos with checkboxes
        for todo in self.todos:
            # Create custom widget item with checkbox
            item_widget = self.create_todo_item_widget(todo)
            
            # Create list item
            item = QListWidgetItem()
            item.setSizeHint(item_widget.sizeHint())
            
            # Add to list
            self.todos_list.addItem(item)
            self.todos_list.setItemWidget(item, item_widget)
    
    def create_todo_item_widget(self, todo):
        """Create a widget for a to-do item with checkbox"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)
        
        # Checkbox for selection
        checkbox = QCheckBox()
        checkbox.setChecked(False)  # Initially unchecked
        layout.addWidget(checkbox)
        
        # To-do text
        todo_text = todo.get('text', 'Untitled To-Do')
        text_label = QLabel(todo_text)
        
        # Apply styling based on completion state
        if todo.get('completed', False):
            # Style for completed to-dos
            text_label.setStyleSheet("color: gray;")
            # Use strikethrough font
            font = text_label.font()
            font.setStrikeOut(True)
            text_label.setFont(font)
        
        layout.addWidget(text_label, 1)  # 1 = stretch factor
        
        # Add due date if available
        if todo.get('due_date'):
            date_label = QLabel(todo.get('due_date'))
            date_label.setStyleSheet("color: gray; font-style: italic;")
            layout.addWidget(date_label)
        
        # Store todo data in widget for later reference
        widget.setProperty("todo_id", todo.get('id'))
        widget.setProperty("text", todo_text)
        widget.setProperty("completed", todo.get('completed', False))
        widget.checkbox = checkbox  # Store reference to checkbox
        
        return widget
    
    def toggle_select_all(self, state):
        """Toggle selection of all to-dos"""
        if not hasattr(self, 'todos_list'):
            return
            
        is_checked = state == Qt.CheckState.Checked
        
        # Update all checkboxes
        for i in range(self.todos_list.count()):
            item = self.todos_list.item(i)
            item_widget = self.todos_list.itemWidget(item)
            if hasattr(item_widget, 'checkbox'):
                item_widget.checkbox.setChecked(is_checked)
    
    def get_selected_todos(self):
        """Get list of selected to-dos"""
        selected_todos = []
        
        if not hasattr(self, 'todos_list'):
            return selected_todos
            
        for i in range(self.todos_list.count()):
            item = self.todos_list.item(i)
            item_widget = self.todos_list.itemWidget(item)
            
            if hasattr(item_widget, 'checkbox') and item_widget.checkbox.isChecked():
                # Find todo data by ID
                todo_id = item_widget.property("todo_id")
                todo = next((t for t in self.todos if t.get('id') == todo_id), None)
                
                if todo:
                    selected_todos.append(todo)
        
        return selected_todos
    
    def batch_edit(self):
        """Show batch edit dialog for selected to-dos"""
        selected_todos = self.get_selected_todos()
        
        if not selected_todos:
            QMessageBox.information(self, "No Selection", "Please select one or more To-Do items first.")
            return
        
        # We'll implement the batch edit dialog later
        QMessageBox.information(self, "Batch Edit", f"Selected {len(selected_todos)} To-Do items for batch editing.\nThis feature is coming soon!")
    
    def delete_selected(self):
        """Delete selected to-dos"""
        selected_todos = self.get_selected_todos()
        
        if not selected_todos:
            QMessageBox.information(self, "No Selection", "Please select one or more To-Do items first.")
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Delete {len(selected_todos)} selected Bee to-do items?\n\n" +
            "This action will permanently remove these items from your Bee device and cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Get the IDs of selected to-dos
            todo_ids = [todo.get('id') for todo in selected_todos]
            
            # Show progress dialog
            progress_dialog = QMessageBox(self)
            progress_dialog.setWindowTitle("Deleting To-Dos")
            progress_dialog.setText(f"Deleting {len(todo_ids)} to-do items...")
            progress_dialog.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress_dialog.show()
            
            # Create worker to delete todos in background
            worker = Worker(self.bee_manager.delete_multiple_todos, todo_ids)
            worker.signals.finished.connect(lambda results: self.on_delete_completed(results, progress_dialog))
            worker.signals.error.connect(lambda error: self.on_delete_error(error, progress_dialog))
            
            # Execute the worker
            self.thread_pool.start(worker)

    def on_delete_completed(self, results, progress_dialog):
        """Handle completion of to-do deletion"""
        # Close progress dialog
        progress_dialog.close()
        
        # Count successes and failures
        successes = sum(1 for _, success in results if success)
        failures = len(results) - successes
        
        # Show result message
        if failures == 0:
            QMessageBox.information(
                self,
                "Deletion Complete",
                f"Successfully deleted {successes} to-do items."
            )
        else:
            QMessageBox.warning(
                self,
                "Deletion Partially Complete",
                f"Successfully deleted {successes} to-do items.\n"
                f"Failed to delete {failures} to-do items."
            )
        
        # Refresh to-dos list
        self.load_todos()

    def on_delete_error(self, error, progress_dialog):
        """Handle error during to-do deletion"""
        # Close progress dialog
        progress_dialog.close()
        
        # Show error message
        QMessageBox.critical(
            self,
            "Deletion Error",
            f"An error occurred while deleting to-do items: {error}"
        )

    def get_categories(self):
        """Get list of categories from database"""
        categories = []
        try:
            # Get database manager
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            # Query categories
            results = db_manager.execute_query("SELECT name FROM categories ORDER BY name")
            categories = [row[0] for row in results]
        except Exception as e:
            print(f"Error getting categories: {e}")
        
        return categories

    def get_priorities(self):
        """Get list of priorities from database"""
        priorities = []
        try:
            # Get database manager
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            # Query priorities
            results = db_manager.execute_query("SELECT name FROM priorities ORDER BY display_order")
            priorities = [row[0] for row in results]
        except Exception as e:
            print(f"Error getting priorities: {e}")
            # Default priorities if query fails
            priorities = ["High", "Medium", "Low", "Unprioritized"]
        
        return priorities

    def batch_edit(self):
        """Show batch edit dialog for selected to-dos"""
        selected_todos = self.get_selected_todos()
        
        if not selected_todos:
            QMessageBox.information(self, "No Selection", "Please select one or more To-Do items first.")
            return
        
        # Create batch edit dialog
        dialog = BatchEditDialog(self, len(selected_todos))
        
        # Load categories and priorities
        dialog.load_categories(self.get_categories())
        dialog.load_priorities(self.get_priorities())
        
        if dialog.exec():
            # Get batch edit options
            import_location = dialog.get_import_location()
            priority = dialog.get_priority()
            category = dialog.get_category()
            
            # Process imports
            self.import_selected_todos(selected_todos, import_location, priority, category)

    def import_selected_todos(self, todos, destination, priority=None, category=None):
        """Import selected to-dos to the app"""
        if not todos:
            return
        
        # Show progress dialog
        progress_dialog = QMessageBox(self)
        progress_dialog.setWindowTitle("Importing To-Dos")
        progress_dialog.setText(f"Importing {len(todos)} to-do items...")
        progress_dialog.setStandardButtons(QMessageBox.StandardButton.NoButton)
        progress_dialog.show()
        
        try:
            # Format todos for import
            formatted_todos = []
            for todo in todos:
                # Create task data structure matching app's format
                task_data = {
                    'title': todo.get('text', 'Untitled To-Do'),
                    'description': '',  # Bee API doesn't have descriptions
                    'status': 'Completed' if todo.get('completed') else 
                            ('Backlog' if destination == 'Backlog' else 'Not Started'),
                    'priority': priority if priority else 'Medium',
                    'due_date': todo.get('due_date') if 'due_date' in todo else '',
                    'category': category,
                    'parent_id': None,  # No parent information from Bee
                    'bee_item_id': todo.get('id')  # Save the Bee item ID
                }
                formatted_todos.append(task_data)
            
            # Use the app's main window to add tasks
            tasks_added = 0
            
            # Get the appropriate task tree
            if destination == "Backlog":
                current_tree = self.main_window.tabs.backlog_tab.task_tree
            else:
                current_tree = self.main_window.tabs.current_tasks_tab.task_tree
            
            # Add all tasks to the tree
            for task_data in formatted_todos:
                try:
                    # Add the task
                    task_id = current_tree.add_new_task(task_data)
                    if task_id:
                        tasks_added += 1
                except Exception as e:
                    print(f"Error adding task: {e}")
            
            # Close progress dialog
            progress_dialog.close()
            
            # Reload all tabs to reflect changes
            self.main_window.tabs.reload_all()
            
            # Show success message
            QMessageBox.information(
                self, 
                "Import Complete", 
                f"Successfully imported {tasks_added} To-Do items from Bee"
            )
            
        except Exception as e:
            # Close progress dialog
            progress_dialog.close()
            
            # Show error message
            QMessageBox.critical(
                self,
                "Import Error",
                f"An error occurred while importing to-do items: {str(e)}"
            )
            
class BeeToDoManager:
    def __init__(self, api_key):
        self.api_key = api_key
        self.bee = Bee(api_key)

    async def delete_todo(self, todo_id):
        """Delete a to-do item"""
        try:
            await self.bee.delete_todo("me", todo_id)
            return True
        except Exception as e:
            print(f"Error deleting todo: {e}")
            return False

    async def delete_multiple_todos(self, todo_ids):
        """Delete multiple to-do items"""
        results = []
        for todo_id in todo_ids:
            try:
                # Delete the todo
                success = await self.bee.delete_todo("me", todo_id)
                results.append((todo_id, True))
            except Exception as e:
                print(f"Error deleting todo {todo_id}: {e}")
                results.append((todo_id, False))
        
        return results

    async def get_all_todos(self):
        """Fetch all to-do items from the Bee API using SDK with pagination"""
        try:
            all_todos = []
            page = 1
            has_more = True
            
            print("Fetching todos using SDK with pagination...")
            
            while has_more:
                print(f"Fetching page {page}...")
                
                # Try to use SDK with page parameter
                try:
                    # The SDK might support the page parameter
                    todos_response = await self.bee.get_todos("me", page=page)
                except TypeError:
                    # If page parameter doesn't work, we'll need to use the default call
                    todos_response = await self.bee.get_todos("me")
                
                # Get the current page of todos
                current_todos = todos_response.get("todos", [])
                
                if not current_todos:
                    print(f"No todos on page {page}")
                    break
                
                print(f"Fetched {len(current_todos)} todos on page {page}")
                all_todos.extend(current_todos)
                
                # If we got exactly 10 items, there might be more pages
                has_more = len(current_todos) == 10
                
                # Move to next page
                page += 1
            
            print(f"Total todos fetched: {len(all_todos)}")
            return all_todos
            
        except Exception as e:
            print(f"Error fetching todos: {e}")
            raise

class BatchEditDialog(QDialog):
    """Dialog for batch editing to-do items"""
    
    def __init__(self, parent=None, selected_count=0):
        super().__init__(parent)
        self.selected_count = selected_count
        self.setWindowTitle("Batch Edit Selected Items")
        self.setMinimumWidth(400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header with count of selected items
        header_label = QLabel(f"{self.selected_count} items selected")
        header_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(header_label)
        
        # Import location (Current Tasks or Backlog)
        location_group = QGroupBox("Import Location")
        location_layout = QVBoxLayout()
        
        self.current_radio = QRadioButton("Current Tasks")
        self.backlog_radio = QRadioButton("Backlog")
        
        # Default to Current Tasks
        self.current_radio.setChecked(True)
        
        location_layout.addWidget(self.current_radio)
        location_layout.addWidget(self.backlog_radio)
        location_group.setLayout(location_layout)
        layout.addWidget(location_group)
        
        # Priority selection
        priority_group = QGroupBox("Set Priority")
        priority_layout = QVBoxLayout()
        
        self.priority_combo = QComboBox()
        # Will be populated with priorities from database
        self.priority_combo.addItems(["Medium", "High", "Low", "Unprioritized"])
        self.priority_combo.setCurrentText("Medium")
        
        self.apply_priority_check = QCheckBox("Apply to selected items")
        self.apply_priority_check.setChecked(False)
        
        priority_layout.addWidget(self.priority_combo)
        priority_layout.addWidget(self.apply_priority_check)
        priority_group.setLayout(priority_layout)
        layout.addWidget(priority_group)
        
        # Category selection
        category_group = QGroupBox("Set Category")
        category_layout = QVBoxLayout()
        
        self.category_combo = QComboBox()
        # Will be populated with categories from database
        self.category_combo.addItem("None")
        
        self.apply_category_check = QCheckBox("Apply to selected items")
        self.apply_category_check.setChecked(False)
        
        category_layout.addWidget(self.category_combo)
        category_layout.addWidget(self.apply_category_check)
        category_group.setLayout(category_layout)
        layout.addWidget(category_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        apply_btn = QPushButton("Apply Changes")
        apply_btn.clicked.connect(self.accept)
        apply_btn.setDefault(True)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(apply_btn)
        
        layout.addLayout(button_layout)
    
    def get_import_location(self):
        """Get selected import location"""
        return "Backlog" if self.backlog_radio.isChecked() else "Current Tasks"
    
    def get_priority(self):
        """Get selected priority if checked"""
        if self.apply_priority_check.isChecked():
            return self.priority_combo.currentText()
        return None
    
    def get_category(self):
        """Get selected category if checked"""
        if self.apply_category_check.isChecked():
            category = self.category_combo.currentText()
            return None if category == "None" else category
        return None
    
    def load_categories(self, categories):
        """Load categories into the combo box"""
        self.category_combo.clear()
        self.category_combo.addItem("None")
        for category in categories:
            self.category_combo.addItem(category)
    
    def load_priorities(self, priorities):
        """Load priorities into the combo box"""
        self.priority_combo.clear()
        for priority in priorities:
            self.priority_combo.addItem(priority)
        # Default to Medium
        index = self.priority_combo.findText("Medium")
        if index >= 0:
            self.priority_combo.setCurrentIndex(index)