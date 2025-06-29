# src/ui/task_tree.py

from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QHeaderView, QMessageBox, QDateEdit, QApplication
from PyQt6.QtCore import Qt, QDate, QSize, QTimer
from PyQt6.QtGui import QBrush, QColor
import sqlite3
from pathlib import Path
import webbrowser
import logging
from .task_pill_delegate import TaskPillDelegate
from datetime import datetime, date
import sys
from pathlib import Path
import time

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent.parent))

# Now import directly from the database package
from database.memory_db_manager import get_memory_db_manager

# Import the debug logger
from utils.debug_decorator import debug_method
from utils.debug_logger import get_debug_logger
debug = get_debug_logger()

# Existing logging setup - can be maintained for backward compatibility
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TaskTreeWidget(QTreeWidget):

    def __init__(self):
        debug.debug("Initializing TaskTreeWidget")
        super().__init__()
        self.setRootIsDecorated(False)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        
        # Change to just one column
        debug.debug("Setting up single column view")
        self.setColumnCount(1)
        self.setHeaderLabels(['Tasks'])
        
        # Hide the header
        self.setHeaderHidden(True)
        self.setIndentation(40)  # Increased indentation for better hierarchy view
        
        # Enable mouse tracking for hover effects
        debug.debug("Enabling mouse tracking")
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)  # IMPORTANT: Set on viewport too
        
        # Apply the custom delegate - ensure it's created after mouse tracking is enabled
        debug.debug("Creating and applying custom delegate")
        custom_delegate = TaskPillDelegate(self)
        self.setItemDelegate(custom_delegate)
        
        # Set a clean style
        debug.debug("Setting widget stylesheet")
        
        # Set alternating row colors to false to prevent default styling
        self.setAlternatingRowColors(False)
        
        # Set spacing between items
        self.setVerticalScrollMode(QTreeWidget.ScrollMode.ScrollPerPixel)
        self.setUniformRowHeights(False)
        
        # Set context menu
        debug.debug("Setting up context menu")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Connect expansion/collapse signals
        debug.debug("Connecting expansion/collapse signals")
        self.itemExpanded.connect(self.onItemExpanded)
        self.itemCollapsed.connect(self.onItemCollapsed)

        # Connect double-click signal with our router method
        self.itemDoubleClicked.connect(self.onItemDoubleClicked)
        
        # Defer loading tasks to avoid initialization order issues
        # This allows subclasses to fully initialize before loading tasks
        debug.debug("Scheduling deferred task loading")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._init_load_tasks_tree)
        
        # Debug delegate setup
        self.debug_delegate_setup()
        debug.debug("TaskTreeWidget initialization complete")

    def _init_load_tasks_tree(self):
        """Deferred task loading to handle initialization order"""
        debug.debug("Executing deferred task loading")
        try:
            self.load_tasks_tree()
        except Exception as e:
            debug.error(f"Error during deferred task loading: {e}")
            import traceback
            traceback.print_exc()

    @debug_method
    def add_new_task(self, data):
        """Add a new task with proper expanded state preservation"""
        debug.debug(f"Adding new task: {data.get('title', 'No Title')}")
        
        # Save expanded states before adding
        expanded_items = self._save_expanded_states()
        debug.debug(f"Saved {len(expanded_items)} expanded states before adding task")
        
        # Original task creation logic
        try:
            # Import database manager
            from database.memory_db_manager import get_memory_db_manager
            db_manager = get_memory_db_manager()
            
            # Use a single connection for the entire operation
            debug.debug("Opening database connection")
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get category ID
                category_name = data.get('category')
                category_id = None
                
                if category_name:
                    debug.debug(f"Looking up category ID for {category_name}")
                    cursor.execute(
                        "SELECT id FROM categories WHERE name = ?", 
                        (category_name,)
                    )
                    result = cursor.fetchone()
                    if result:
                        category_id = result[0]
                        debug.debug(f"Found category ID: {category_id}")
                
                # Get next display order
                parent_id = data.get('parent_id')
                debug.debug(f"Getting next display order for parent_id: {parent_id}")
                if parent_id:
                    cursor.execute(
                        "SELECT MAX(display_order) FROM tasks WHERE parent_id = ?",
                        (parent_id,)
                    )
                else:
                    cursor.execute(
                        "SELECT MAX(display_order) FROM tasks WHERE parent_id IS NULL"
                    )
                
                result = cursor.fetchone()
                max_order = result[0] if result and result[0] else 0
                display_order = max_order + 1
                debug.debug(f"Next display order will be: {display_order}")
                
                # Check if is_compact column exists
                debug.debug("Checking if is_compact column exists")
                try:
                    cursor.execute("SELECT is_compact FROM tasks LIMIT 1")
                    debug.debug("is_compact column exists")
                except sqlite3.OperationalError:
                    # Column doesn't exist, need to add it
                    debug.debug("is_compact column does not exist, adding it")
                    cursor.execute("ALTER TABLE tasks ADD COLUMN is_compact INTEGER NOT NULL DEFAULT 0")
                    conn.commit()
                
                # Default is_compact value (new tasks are expanded by default)
                is_compact = 0
                
                # Check if bee_item_id exists in the data
                bee_item_id = data.get('bee_item_id')
                
                # Insert new task including bee_item_id if present
                if bee_item_id:
                    debug.debug(f"Inserting new task with bee_item_id: {bee_item_id}")
                    cursor.execute(
                        """
                        INSERT INTO tasks (title, description, status, priority, 
                                        due_date, category_id, parent_id, display_order, is_compact, bee_item_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, 
                        (
                            data.get('title', ''),
                            data.get('description', ''),
                            data.get('status', 'Not Started'), 
                            data.get('priority', 'Medium'),
                            data.get('due_date', ''),
                            category_id,
                            parent_id,
                            display_order,
                            is_compact,
                            bee_item_id
                        )
                    )
                else:
                    debug.debug("Inserting new task without bee_item_id")
                    cursor.execute(
                        """
                        INSERT INTO tasks (title, description, status, priority, 
                                        due_date, category_id, parent_id, display_order, is_compact)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, 
                        (
                            data.get('title', ''),
                            data.get('description', ''),
                            data.get('status', 'Not Started'), 
                            data.get('priority', 'Medium'),
                            data.get('due_date', ''),
                            category_id,
                            parent_id,
                            display_order,
                            is_compact
                        )
                    )
                
                # Get the new task's ID
                cursor.execute("SELECT last_insert_rowid()")
                new_id = cursor.fetchone()[0]
                debug.debug(f"New task created with ID: {new_id}")
                
                # Add links if any
                links = data.get('links', [])
                if links:
                    debug.debug(f"Adding {len(links)} links to task")
                    for i, (link_id, url, label) in enumerate(links):
                        if url and url.strip():
                            debug.debug(f"Adding link: {url}, label: {label}")
                            cursor.execute(
                                """
                                INSERT INTO links (task_id, url, label, display_order)
                                VALUES (?, ?, ?, ?)
                                """,
                                (new_id, url, label, i)
                            )
                
                # Add files if any
                files = data.get('files', [])
                if files:
                    debug.debug(f"Adding {len(files)} files to task")
                    for i, (file_id, file_path, file_name) in enumerate(files):
                        if file_path and file_path.strip():
                            debug.debug(f"Adding file: {file_path}, name: {file_name}")
                            cursor.execute(
                                """
                                INSERT INTO files (task_id, file_path, file_name, display_order)
                                VALUES (?, ?, ?, ?)
                                """,
                                (new_id, file_path, file_name, i)
                            )

                # Commit changes
                debug.debug("Committing changes to database")
                conn.commit()

            # Now reload the tree and restore expanded states
            if hasattr(self, 'load_tasks_tab'):
                debug.debug("Reloading tasks with filtered method")
                self.load_tasks_tab()
            else:
                debug.debug("Reloading tasks with standard method")
                self.load_tasks_tree()
            
            # Restore expanded states
            self._restore_expanded_states(expanded_items)
            debug.debug(f"Restored {len(expanded_items)} expanded states")
            
            # Try to find and highlight the new task
            self._highlight_task(new_id)
            
            return new_id
        except Exception as e:
            debug.error(f"Error adding new task: {e}")
            import traceback
            traceback.print_exc()
            # Show error message to user
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Error", f"Failed to add task: {str(e)}")
            return None    

    def _highlight_task(self, task_id):
        """Find and highlight/select a task by its ID"""
        debug.debug(f"Attempting to highlight task: {task_id}")
        
        # Find the task item
        task_item = self._find_task_item_by_id(task_id)
        
        if task_item:
            # Select the item
            self.setCurrentItem(task_item)
            
            # Make sure it's visible
            self.scrollToItem(task_item)
            debug.debug(f"Successfully highlighted task {task_id}")
            return True
        
        debug.debug(f"Could not find task {task_id} to highlight")
        return False

    def change_status_with_timestamp(self, item, new_status):
        """Change status with timestamp tracking for Completed tasks"""
        debug.debug(f"Changing task status to: {new_status}")
        try:
            # Import database manager
            from database.memory_db_manager import get_memory_db_manager
            db_manager = get_memory_db_manager()
            
            # Check if completed_at column exists
            debug.debug("Checking if completed_at column exists")
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(tasks)")
                columns = [info[1] for info in cursor.fetchall()]
                has_completed_at = 'completed_at' in columns
                debug.debug(f"completed_at column exists: {has_completed_at}")
            
            # Check if this is a status change to or from "Completed"
            data = item.data(0, Qt.ItemDataRole.UserRole)
            old_status = data.get('status', '')
            debug.debug(f"Changing status from {old_status} to {new_status}")
            
            # Determine if this is a status change that would move the task between tabs
            is_tab_transition = False
            
            # Check for transitions between tabs
            if hasattr(self, 'filter_type'):
                debug.debug(f"Current filter type: {self.filter_type}")
                if self.filter_type == "current":
                    if new_status == "Backlog" or new_status == "Completed":
                        is_tab_transition = True
                elif self.filter_type == "backlog":
                    if new_status != "Backlog":
                        is_tab_transition = True
                elif self.filter_type == "completed":
                    if new_status != "Completed":
                        is_tab_transition = True
                debug.debug(f"Is tab transition: {is_tab_transition}")
            
            # If we're changing task status, we need to collect all children
            # so we can also update their status to match
            child_tasks = []
            if is_tab_transition:
                debug.debug("Collecting child tasks for status update")
                self._collect_child_tasks(item, child_tasks)
                debug.debug(f"Found {len(child_tasks)} child tasks to update")
            
            # Update main task status
            if has_completed_at:
                # Get current timestamp formatted as ISO string if status is changing to Completed
                completed_at = None
                if new_status == "Completed" and old_status != "Completed":
                    completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    debug.debug(f"Task completed at: {completed_at}")
                    
                    # Update database with completed_at timestamp
                    debug.debug("Updating task with completed timestamp")
                    db_manager.execute_update(
                        "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?", 
                        (new_status, completed_at, item.task_id)
                    )
                elif old_status == "Completed" and new_status != "Completed":
                    # If changing from Completed to another status, clear the timestamp
                    debug.debug("Clearing completed timestamp")
                    db_manager.execute_update(
                        "UPDATE tasks SET status = ?, completed_at = NULL WHERE id = ?", 
                        (new_status, item.task_id)
                    )
                else:
                    # Normal status update without changing completion state
                    debug.debug("Normal status update without completion state change")
                    db_manager.execute_update(
                        "UPDATE tasks SET status = ? WHERE id = ?", 
                        (new_status, item.task_id)
                    )
                
                # Update item data
                data['status'] = new_status
                if completed_at:
                    data['completed_at'] = completed_at
                    debug.debug("Added completed_at to item data")
                elif 'completed_at' in data and new_status != "Completed":
                    data.pop('completed_at', None)
                    debug.debug("Removed completed_at from item data")
            else:
                # No completed_at column, just update status
                debug.debug("No completed_at column, updating status only")
                db_manager.execute_update(
                    "UPDATE tasks SET status = ? WHERE id = ?", 
                    (new_status, item.task_id)
                )
                # Update item data
                data['status'] = new_status
                
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            debug.debug("Updated item data")
            
            # Now update all child tasks with the same status
            if is_tab_transition and child_tasks:
                debug.debug(f"Updating {len(child_tasks)} child tasks to status: {new_status}")
                for child_id in child_tasks:
                    if has_completed_at:
                        if new_status == "Completed":
                            # All children of a completed task also get completed
                            child_completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            debug.debug(f"Completing child task {child_id} at {child_completed_at}")
                            db_manager.execute_update(
                                "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?", 
                                (new_status, child_completed_at, child_id)
                            )
                        else:
                            # Children of non-completed tasks should also be non-completed
                            debug.debug(f"Updating child task {child_id} status and clearing completed_at")
                            db_manager.execute_update(
                                "UPDATE tasks SET status = ?, completed_at = NULL WHERE id = ?", 
                                (new_status, child_id)
                            )
                    else:
                        # Just update status
                        debug.debug(f"Updating child task {child_id} status only")
                        db_manager.execute_update(
                            "UPDATE tasks SET status = ? WHERE id = ?", 
                            (new_status, child_id)
                        )
                        
                debug.debug(f"Updated status of {len(child_tasks)} child tasks to {new_status}")
            
            # Force a repaint
            debug.debug("Forcing viewport update")
            self.viewport().update()
            
            # Notify parent about status change if we're in a tabbed interface
            # The task needs to move to another tab
            if is_tab_transition:
                debug.debug("Requesting tab reload due to status transition")
                parent = self.parent()
                while parent and not hasattr(parent, 'reload_all'):
                    parent = parent.parent()
                    
                if parent and hasattr(parent, 'reload_all'):
                    # Use a short timer to let the current operation complete first
                    debug.debug("Scheduling reload of all tabs")
                    QTimer.singleShot(100, parent.reload_all)
            
            return True
            
        except Exception as e:
            debug.error(f"Error changing task status: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to change task status: {str(e)}")
            return False

    def _handle_tab_transition_with_expanded_states(self, parent, expanded_items):
        """Handle a tab transition while preserving expanded states"""
        debug.debug("Handling tab transition with expanded states preservation")
        # Store the expanded states in a way that will survive across tabs
        # We can use main_window's settings for temporary storage
        if hasattr(parent, 'main_window') and hasattr(parent.main_window, 'settings'):
            parent.main_window.settings.set_setting("temp_expanded_states", expanded_items)
            debug.debug(f"Stored {len(expanded_items)} expanded states in settings")
        
        # Trigger the reload_all method
        parent.reload_all()
        
        # After reloading, restore the expanded states
        QTimer.singleShot(300, self._restore_expanded_states_after_tab_transition)

    def _restore_expanded_states_after_tab_transition(self):
        """Restore expanded states after a tab transition"""
        debug.debug("Restoring expanded states after tab transition")
        # Try to get the stored expanded states from main_window's settings
        parent = self.parent()
        while parent and not hasattr(parent, 'main_window'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'main_window') and hasattr(parent.main_window, 'settings'):
            expanded_items = parent.main_window.settings.get_setting("temp_expanded_states", [])
            debug.debug(f"Retrieved {len(expanded_items)} expanded states from settings")
            
            # Restore the expanded states
            self._restore_expanded_states(expanded_items)
            
            # Clear the temporary storage
            parent.main_window.settings.set_setting("temp_expanded_states", [])
            
    def add_task_item(self, task_id, title, description, link, status, priority, due_date, category, is_compact=0, links=None, files=None):
        debug.debug(f"Adding task item: ID={task_id}, title={title}")
        # Create a single-column item
        item = QTreeWidgetItem([title or ""])
        
        # Debug prints
        debug.debug(f"Links parameter: {links}")
        debug.debug(f"Files parameter: {files}")
        
        # Store all data as item data
        user_data = {
            'id': task_id,
            'title': title or "",
            'description': description or "",
            'status': status or "Not Started", 
            'priority': priority or "Medium",
            'due_date': due_date or "",
            'category': category or "",
            'links': links if links is not None else [],
            'files': files if files is not None else [],
            'expanded': False
        }
        
        debug.debug(f"Setting user data with links: {user_data.get('links', [])}")
        debug.debug(f"Setting user data with files: {user_data.get('files', [])}")
        item.setData(0, Qt.ItemDataRole.UserRole, user_data)
        
        # Verify the data was set correctly
        verify_data = item.data(0, Qt.ItemDataRole.UserRole)
        debug.debug(f"Verified user data links: {verify_data.get('links', [])}")
        debug.debug(f"Verified user data files: {verify_data.get('files', [])}")
        
        
        item.task_id = task_id
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
        
        # Set item height based on compact state
        delegate = self.itemDelegate()
        if isinstance(delegate, TaskPillDelegate):
            # If this item is marked as compact in the database, add it to delegate's compact set
            if is_compact:
                debug.debug(f"Task {task_id} is compact, adding to delegate compact set")
                delegate.compact_items.add(task_id)
            
            # Set appropriate height
            height = delegate.compact_height if is_compact else delegate.pill_height
            item.setSizeHint(0, QSize(100, height + delegate.item_margin * 2))
            debug.debug(f"Set item size hint to height: {height + delegate.item_margin * 2}")
        
        # Apply background color based on category
        if category:
            try:
                debug.debug(f"Setting background color for category: {category}")
                from database.database_manager import get_db_manager
                db_manager = get_db_manager()
                
                result = db_manager.execute_query(
                    "SELECT color FROM categories WHERE name = ?", 
                    (category,)
                )
                if result and result[0]:
                    color = QColor(result[0][0])
                    item.setBackground(0, QBrush(color))
                    debug.debug(f"Background color set to: {result[0][0]}")
            except Exception as e:
                debug.error(f"Error setting category color: {e}")
        
        return item

    @debug_method
    def change_status(self, item, new_status):
        debug.debug(f"Changing status to: {new_status}")
        
        # If this instance has the change_status_with_timestamp method, use it instead
        if hasattr(self, 'change_status_with_timestamp'):
            debug.debug(f"Delegating to change_status_with_timestamp: {new_status}")
            return self.change_status_with_timestamp(item, new_status)
            
        try:
            # Import database manager
            from database.memory_db_manager import get_memory_db_manager
            db_manager = get_memory_db_manager()
            
            # Check if this is a status change to or from "Completed"
            data = item.data(0, Qt.ItemDataRole.UserRole)
            old_status = data.get('status', '')
            debug.debug(f"Changing from status: {old_status}")
            
            # Get current timestamp formatted as ISO string if status is changing to Completed
            completed_at = None
            if new_status == "Completed" and old_status != "Completed":
                from datetime import datetime
                completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                debug.debug(f"Task completed at: {completed_at}")
                
                # Update database with completed_at timestamp
                db_manager.execute_update(
                    "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?", 
                    (new_status, completed_at, item.task_id)
                )
            elif old_status == "Completed" and new_status != "Completed":
                # If changing from Completed to another status, clear the timestamp
                debug.debug("Clearing completed_at timestamp")
                db_manager.execute_update(
                    "UPDATE tasks SET status = ?, completed_at = NULL WHERE id = ?", 
                    (new_status, item.task_id)
                )
            else:
                # Normal status update without changing completion state
                debug.debug("Standard status update")
                db_manager.execute_update(
                    "UPDATE tasks SET status = ? WHERE id = ?", 
                    (new_status, item.task_id)
                )
            
            # Update item
            data = item.data(0, Qt.ItemDataRole.UserRole)
            data['status'] = new_status
            if completed_at:
                data['completed_at'] = completed_at
                debug.debug("Added completed_at to item data")
            elif 'completed_at' in data and new_status != "Completed":
                data.pop('completed_at', None)
                debug.debug("Removed completed_at from item data")
                
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            
            # Force a repaint
            debug.debug("Forcing viewport update")
            self.viewport().update()
            
            # Notify parent about status change if we're in a tabbed interface
            parent = self.parent()
            while parent and not hasattr(parent, 'reload_all'):
                parent = parent.parent()
                
            if parent and hasattr(parent, 'reload_all'):
                # This is a TabTaskTreeWidget within a TaskTabWidget
                # Reload all tabs to reflect the status change
                debug.debug("Requesting tab reload")
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(100, parent.reload_all)
                
        except Exception as e:
            debug.error(f"Error changing task status: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to change task status: {str(e)}")
            
    def change_priority(self, item, new_priority):
        debug.debug(f"Changing priority to: {new_priority}")
        try:
            # Update database
            from database.memory_db_manager import get_memory_db_manager
            db_manager = get_memory_db_manager()
            
            db_manager.execute_update(
                "UPDATE tasks SET priority = ? WHERE id = ?", 
                (new_priority, item.task_id)
            )
            debug.debug("Updated priority in database")
            
            # Update item
            data = item.data(0, Qt.ItemDataRole.UserRole)
            data['priority'] = new_priority
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            debug.debug("Updated priority in item data")
            
            # Force a repaint
            debug.debug("Forcing viewport update")
            self.viewport().update()
            
            # Notify parent about priority change if we're in a tabbed interface
            # and force a reload of all tabs
            parent = self.parent()
            while parent and not hasattr(parent, 'reload_all'):
                parent = parent.parent()
                
            if parent and hasattr(parent, 'reload_all'):
                # This is a TabTaskTreeWidget within a TaskTabWidget
                # Use a short timer to let the current operation complete first
                debug.debug("Scheduling reload of all tabs")
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(100, parent.reload_all)
                
        except Exception as e:
            debug.error(f"Error changing task priority: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to change task priority: {str(e)}")

    def debug_delegate_setup(self):
        """Debug method to verify delegate installation and hover tracking"""
        debug.debug("Checking delegate setup")
        
        # Check if delegate is set
        delegate = self.itemDelegate()
        if delegate is None:
            debug.error("No delegate installed")
            return
        
        debug.debug(f"Delegate class: {type(delegate).__name__}")
        
        # Check if it's the right type
        if not isinstance(delegate, TaskPillDelegate):
            debug.error(f"Wrong delegate type: {type(delegate).__name__}")
            return
        
        debug.debug("TaskPillDelegate is correctly installed")
        
        # Check mouse tracking
        debug.debug(f"TreeWidget mouse tracking: {self.hasMouseTracking()}")
        debug.debug(f"Viewport mouse tracking: {self.viewport().hasMouseTracking()}")
        
        # Check event filter installation - fixed to not use eventFilters()
        debug.debug("Event filters cannot be directly inspected, but should be installed")
        
        # Check if compact_items set exists and is loaded
        if hasattr(delegate, 'compact_items'):
            debug.debug(f"compact_items set exists with {len(delegate.compact_items)} items")
            debug.debug(f"Items in compact state: {delegate.compact_items}")
        else:
            debug.error("No compact_items set found in delegate")
        
        # Force a viewport update to ensure proper redrawing
        self.viewport().update()
        debug.debug("Forced viewport update")
        
    def debug_headers(self):
        """Debug the header items"""
        debug.debug("Debugging headers")
        delegate = self.itemDelegate()
        if isinstance(delegate, TaskPillDelegate):
            delegate.debug_header_items(self)
        else:
            debug.error("Delegate is not a TaskPillDelegate")

    def debug_priority_headers(self):
        """Debug method for priority headers specifically"""
        debug.debug("Debugging priority headers")
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            
            if isinstance(data, dict) and data.get('is_priority_header', False):
                priority = data.get('priority', 'Unknown')
                expanded = data.get('expanded', True)
                item_index = self.indexFromItem(item)
                is_expanded = self.isExpanded(item_index)
                debug.debug(f"Priority header: {priority}, expanded in data: {expanded}, visually expanded: {is_expanded}")
        
        # Get expanded states from settings
        settings = self.get_settings_manager()
        saved_expanded = settings.get_setting("expanded_priorities", [])
        debug.debug(f"Settings expanded priorities: {saved_expanded}")

    def debug_toggle_buttons(self):
        """Debug method to force toggle buttons to appear on all items"""
        debug.debug("Forcing toggle buttons to appear on all items")
        delegate = self.itemDelegate()
        if isinstance(delegate, TaskPillDelegate):
            # First we need to add the show_toggle_button method to the delegate
            if not hasattr(delegate, 'show_toggle_button'):
                def show_toggle_button(tree_widget, item_index):
                    """Force show the toggle button for a specific item"""
                    delegate.hover_item = item_index
                    rect = tree_widget.visualRect(item_index)
                    delegate.toggle_button_rect = QRectF(
                        rect.center().x() - 12,
                        rect.top() - 12,
                        24, 24
                    )
                    debug.debug(f"Set toggle button for item at index {item_index.row()}")
                
                # Add the method to the delegate
                from types import MethodType
                delegate.show_toggle_button = MethodType(show_toggle_button, delegate)
                debug.debug("Added show_toggle_button method to delegate")
            
            # Now show buttons for all top-level items
            debug.debug("Adding toggle buttons to all top-level items")
            for i in range(self.topLevelItemCount()):
                index = self.model().index(i, 0)
                delegate.show_toggle_button(self, index)
                
                # Also add for child items
                item = self.topLevelItem(i)
                self._debug_add_buttons_to_children(item, delegate)
        
        # Force repaint to show the buttons
        self.viewport().update()
        debug.debug("Forced viewport update to show toggle buttons")

    @debug_method
    def delete_task(self, item):
        debug.debug(f"Deleting task with ID: {item.task_id}")
        reply = QMessageBox.question(
            self, 
            'Delete Task',
            'Are you sure you want to delete this task?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            debug.debug("User confirmed task deletion")
            try:
                # Import database manager
                from database.memory_db_manager import get_memory_db_manager
                db_manager = get_memory_db_manager()
                
                # Delete the item and all its children
                def delete_item_and_children(task_id):
                    # First get all children
                    debug.debug(f"Getting children of task {task_id}")
                    children = db_manager.execute_query(
                        "SELECT id FROM tasks WHERE parent_id = ?", 
                        (task_id,)
                    )
                    # Delete children recursively
                    for child in children:
                        debug.debug(f"Recursively deleting child task {child[0]}")
                        delete_item_and_children(child[0])
                    # Delete this item
                    debug.debug(f"Deleting task {task_id}")
                    db_manager.execute_update(
                        "DELETE FROM tasks WHERE id = ?", 
                        (task_id,)
                    )
                
                delete_item_and_children(item.task_id)
                debug.debug("Task and all children deleted from database")
                
                # THIS IS THE CRITICAL PART - Explicitly save changes to file
                debug.debug("Explicitly saving memory database to file")
                db_manager.save_to_file()
                debug.debug("Database saved to file after deletion")
                
                # Remove from tree
                parent = item.parent()
                if parent:
                    debug.debug("Removing task from parent")
                    parent.removeChild(item)
                else:
                    debug.debug("Removing top-level task")
                    index = self.indexOfTopLevelItem(item)
                    self.takeTopLevelItem(index)
                debug.debug("Task removed from UI")
                
            except Exception as e:
                debug.error(f"Error deleting task: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete task: {str(e)}")
                        
    def _scroll_to_task(self, task_id):
        """Find a task by ID and scroll to it"""
        debug.debug(f"Attempting to scroll to task: {task_id}")
        try:
            # Try to find the task in the tree
            for i in range(self.topLevelItemCount()):
                top_item = self.topLevelItem(i)
                
                # Check if this is a priority header
                top_data = top_item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(top_data, dict) and top_data.get('is_priority_header', False):
                    # Search in children of this header
                    debug.debug(f"Searching in priority header: {top_data.get('priority', 'Unknown')}")
                    for j in range(top_item.childCount()):
                        child_item = top_item.child(j)
                        if hasattr(child_item, 'task_id') and child_item.task_id == task_id:
                            # Found it! Scroll to it
                            debug.debug(f"Found task in priority header, scrolling to it")
                            self.scrollToItem(child_item)
                            self.setCurrentItem(child_item)
                            return True
                        
                        # Check for grandchildren
                        if self._find_and_scroll_to_child(child_item, task_id):
                            return True
                
                # Could also be a direct top-level task
                elif hasattr(top_item, 'task_id') and top_item.task_id == task_id:
                    # Found it! Scroll to it
                    debug.debug(f"Found task as top-level item, scrolling to it")
                    self.scrollToItem(top_item)
                    self.setCurrentItem(top_item)
                    return True
                    
            debug.debug(f"Task {task_id} not found for scrolling")
            return False
        except Exception as e:
            debug.error(f"Error scrolling to task: {e}")
            return False

    @debug_method
    def _update_children_priorities(self, parent_id, new_priority, db_manager):
        """Recursively update priorities of all children to match parent's priority"""
        debug.debug(f"Updating priorities for children of task {parent_id}")
        
        try:
            # Get all direct children
            children = db_manager.execute_query(
                "SELECT id, title FROM tasks WHERE parent_id = ?",
                (parent_id,)
            )
            
            for child_row in children:
                child_id = child_row[0]
                child_title = child_row[1]
                debug.debug(f"Updating child task {child_id} '{child_title}' to priority: {new_priority}")
                print('Updaging child task', child_id, child_title, 'to priority:', new_priority)
                # Update this child's priority
                db_manager.execute_update(
                    "UPDATE tasks SET priority = ? WHERE id = ?",
                    (new_priority, child_id)
                )
                
                # Recursively update this child's children
                self._update_children_priorities(child_id, new_priority, db_manager)
            
            debug.debug(f"Updated priorities for {len(children)} children of task {parent_id}")
            print('Updated priorities for', len(children), 'children of task', parent_id)
        except Exception as e:
            debug.error(f"Error updating children priorities: {e}")
            import traceback
            traceback.print_exc()

    @debug_method
    def dropEvent(self, event):
        """Handle drag and drop events for tasks with improved database consistency"""
        debug.debug("=== DRAG & DROP EVENT START ===")
        debug.debug(f"Drop position: {event.position().x()}, {event.position().y()}")

        # Save the dragged item BEFORE calling super().dropEvent()
        dragged_item = self.currentItem()
        if not dragged_item or not hasattr(dragged_item, 'task_id'):
            debug.debug("No valid dragged item with task_id, canceling drop")
            event.ignore()
            return

        dragged_id = dragged_item.task_id
        dragged_title = dragged_item.text(0)
        debug.debug(f"Dragged item: ID={dragged_id}, Title='{dragged_title}'")

        # Get the drop target information
        drop_pos = event.position().toPoint()
        drop_index = self.indexAt(drop_pos)
        drop_item = self.itemAt(drop_pos) if drop_index.isValid() else None
        
        # Log drop target information
        drop_is_header = False
        drop_target_id = None
        if drop_item:
            drop_data = drop_item.data(0, Qt.ItemDataRole.UserRole)
            
            if isinstance(drop_data, dict) and drop_data.get('is_priority_header', False):
                drop_is_header = True
                priority = drop_data.get('priority', 'Unknown')
                debug.debug(f"Drop target is priority header: '{priority}'")
            elif hasattr(drop_item, 'task_id'):
                drop_target_id = drop_item.task_id
                drop_title = drop_item.text(0)
                debug.debug(f"Drop target task: ID={drop_target_id}, Title='{drop_title}'")
            else:
                debug.debug(f"Drop target is unknown type: {drop_item}")
        else:
            debug.debug("Drop target is empty space (no item)")
        
        # Save expanded states before the drop
        expanded_items = self._save_expanded_states()
        debug.debug(f"Saved expanded states for {len(expanded_items)} items")
        
        # Log tree structure before drop
        debug.debug("--- Tree structure before drop ---")
        self._debug_tree_structure()
        
        # First, let Qt handle the visual drop
        debug.debug("Letting Qt handle the visual drop")
        super().dropEvent(event)
        
        # Log tree structure after Qt's handling
        debug.debug("--- Tree structure after Qt handling ---")
        self._debug_tree_structure()
        
        # IMPORTANT: We need to find the dragged item again after Qt's handling
        # since currentItem() might have changed
        dragged_item = self._find_task_item_by_id(dragged_id)
        
        if not dragged_item:
            debug.debug(f"ERROR: Could not find dragged item with ID {dragged_id} after drop")
            return
        
        debug.debug(f"Found dragged item after drop: {dragged_item.text(0)}")
        
        # Now update database to match the visual state
        try:
            # Get database manager
            from database.memory_db_manager import get_memory_db_manager
            db_manager = get_memory_db_manager()
            
            # Get the new parent after the drop
            new_parent = dragged_item.parent()
            
            # Determine parent_id for database update
            parent_id = None
            if new_parent:
                if hasattr(new_parent, 'task_id'):
                    parent_id = new_parent.task_id
                    debug.debug(f"New parent has task_id: {parent_id}")
                else:
                    # Check if this is a priority header
                    new_parent_data = new_parent.data(0, Qt.ItemDataRole.UserRole)
                    if isinstance(new_parent_data, dict) and new_parent_data.get('is_priority_header', False):
                        priority = new_parent_data.get('priority', 'Unknown')
                        debug.debug(f"New parent is priority header: '{priority}'")
                    else:
                        debug.debug(f"New parent has no task_id and is not a priority header: {new_parent.text(0)}")
            else:
                debug.debug("Task is now a top-level item (no parent)")
            
            # If we dropped on a specific task but Qt didn't make it a child, fix it
            if drop_target_id and not drop_is_header and (not parent_id or parent_id != drop_target_id):
                debug.debug(f"Qt didn't establish correct parent-child relationship, fixing manually")
                
                # Remove the item from its current parent
                if new_parent:
                    idx = new_parent.indexOfChild(dragged_item)
                    if idx >= 0:
                        new_parent.takeChild(idx)
                else:
                    idx = self.indexOfTopLevelItem(dragged_item)
                    if idx >= 0:
                        self.takeTopLevelItem(idx)
                
                # Find the target item again and add as a child
                target_item = self._find_task_item_by_id(drop_target_id)
                if target_item:
                    target_item.addChild(dragged_item)
                    parent_id = drop_target_id  # Update parent_id for database
                    debug.debug(f"Manually added item as child of {drop_target_id}")
                else:
                    debug.debug(f"ERROR: Could not find target item with ID {drop_target_id}")
            
            # Update the database to reflect the new parent-child relationship
            debug.debug(f"Updating database: task {dragged_id} → parent {parent_id}")
            db_manager.execute_update(
                "UPDATE tasks SET parent_id = ? WHERE id = ?", 
                (parent_id, dragged_id)
            )
            
            # If parent has a priority, update this task's priority to match
            if parent_id is not None:
                # Get parent priority from database
                result = db_manager.execute_query(
                    "SELECT priority FROM tasks WHERE id = ?", 
                    (parent_id,)
                )
                if result and len(result) > 0 and result[0][0]:
                    parent_priority = result[0][0]
                    debug.debug(f"Updating task priority to match parent: {parent_priority}")
                    db_manager.execute_update(
                        "UPDATE tasks SET priority = ? WHERE id = ?",
                        (parent_priority, dragged_id)
                    )
                    
                    # Also update all children recursively
                    self._update_children_priorities(dragged_id, parent_priority, db_manager)
            
            # If we're dropping to a priority header (top level), update the priority too
            elif new_parent and not hasattr(new_parent, 'task_id'):
                new_parent_data = new_parent.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(new_parent_data, dict) and new_parent_data.get('is_priority_header', False):
                    new_priority = new_parent_data.get('priority', '')
                    if new_priority:
                        debug.debug(f"Setting task priority to match header: {new_priority}")
                        db_manager.execute_update(
                            "UPDATE tasks SET priority = ? WHERE id = ?",
                            (new_priority, dragged_id)
                        )
                        
                        # Also update all children recursively
                        self._update_children_priorities(dragged_id, new_priority, db_manager)
            
            # Force a save to the database file after drag and drop operations
            debug.debug("Saving memory database to file after drag and drop")
            db_manager.save_to_file()
            
            # Update the display orders in the database
            if new_parent:
                debug.debug(f"Updating display orders for parent")
                self._update_display_orders(new_parent)
            
            # Reload all tabs to ensure consistency
            debug.debug("Scheduling reload of all tabs")
            parent = self.parent()
            while parent and not hasattr(parent, 'reload_all'):
                parent = parent.parent()
                
            if parent and hasattr(parent, 'reload_all'):
                # Use a short timer to let the current operation complete first
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(100, parent.reload_all)
            
        except Exception as e:
            debug.error(f"Error updating database after drop: {e}")
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to update task hierarchy: {str(e)}")
        
        debug.debug("=== DRAG & DROP EVENT END ===")

    # Add a method to find a task by its ID
    @debug_method
    def _find_task_item_by_id(self, task_id):
        """Find a task item by its ID anywhere in the tree"""
        debug.debug(f"Searching for task with ID: {task_id}")
        
        # Search in all top-level items
        for i in range(self.topLevelItemCount()):
            top_item = self.topLevelItem(i)
            
            # Check if this is a priority header (search its children)
            top_data = top_item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(top_data, dict) and top_data.get('is_priority_header', False):
                # Search all children of this header
                for j in range(top_item.childCount()):
                    child = top_item.child(j)
                    
                    # Check if this is the item we're looking for
                    if hasattr(child, 'task_id') and child.task_id == task_id:
                        debug.debug(f"Found task {task_id} under priority header")
                        return child
                    
                    # Check children of this task recursively
                    found = self._find_child_task_by_id(child, task_id)
                    if found:
                        return found
                        
            # Check if this is a top-level task
            elif hasattr(top_item, 'task_id') and top_item.task_id == task_id:
                debug.debug(f"Found task {task_id} as top-level item")
                return top_item
        
        debug.debug(f"Task {task_id} not found in tree")
        return None

    @debug_method
    def _find_child_task_by_id(self, parent_item, task_id):
        """Recursively search for a child task with the given ID"""
        # Go through all children
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            
            # Check if this is the task we're looking for
            if hasattr(child, 'task_id') and child.task_id == task_id:
                debug.debug(f"Found task {task_id} as child")
                return child
            
            # Recursively check this child's children
            found = self._find_child_task_by_id(child, task_id)
            if found:
                return found
        
        return None

    @debug_method
    def _debug_tree_structure(self):
        """Debug print the entire tree structure"""
        debug.debug("Current tree structure:")
        print('Current tree structure:')
        
        # Process each top-level item
        for i in range(self.topLevelItemCount()):
            top_item = self.topLevelItem(i)
            top_data = top_item.data(0, Qt.ItemDataRole.UserRole)
            
            # Check if it's a priority header
            if isinstance(top_data, dict) and top_data.get('is_priority_header', False):
                priority = top_data.get('priority', 'Unknown')
                debug.debug(f"Priority Header: '{priority}' ({top_item.childCount()} children)")
                print('Priority Header:', priority, '(', top_item.childCount(), 'children)')
                
                # Show children
                self._debug_item_children(top_item, 1)
            elif hasattr(top_item, 'task_id'):
                # It's a regular top-level task
                task_id = top_item.task_id
                task_title = top_item.text(0)
                debug.debug(f"Top-level Task: [ID: {task_id}] '{task_title}' ({top_item.childCount()} children)")
                print('Top-level Task:', '[ID:', task_id, ']', task_title, '(', top_item.childCount(), 'children)')
                
                # Show children
                self._debug_item_children(top_item, 1)
            else:
                debug.debug(f"Unknown top-level item: {top_item.text(0)}")
                print('Unknown top-level item:', top_item.text(0))

    @debug_method
    def _debug_item_children(self, parent_item, level):
        """Recursively debug print children with indentation"""
        indent = "  " * level
        
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            
            if hasattr(child, 'task_id'):
                task_id = child.task_id
                task_title = child.text(0)
                task_data = child.data(0, Qt.ItemDataRole.UserRole)
                priority = task_data.get('priority', 'Unknown') if isinstance(task_data, dict) else 'Unknown'
                
                debug.debug(f"{indent}Child Task: [ID: {task_id}] '{task_title}' (Priority: {priority}, {child.childCount()} children)")
                print('' + indent + 'Child Task:', '[ID:', task_id, ']', task_title, '(Priority:', priority, ',', child.childCount(), 'children)')
                
                # Recursively process grandchildren
                if child.childCount() > 0:
                    self._debug_item_children(child, level + 1)
            else:
                debug.debug(f"{indent}Unknown child item: {child.text(0)}")  
                print('' + indent + 'Unknown child item:', child.text(0))          

    def _reload_with_expanded_states(self, expanded_items):
        """Reload the tree while preserving expanded states"""
        debug.debug("Reloading tree with preserved expanded states")
        # Determine which load method to use
        if hasattr(self, 'filter_type'):
            self.load_tasks_tab()  # Use the filtered loading method
        else:
            self.load_tasks_tree()  # Use the standard loading method
        
        # Restore expanded states after a short delay to ensure UI is updated
        QTimer.singleShot(100, lambda saved_states=expanded_items: self._restore_expanded_states(saved_states))
        
        # Try to scroll to the task that was moved to make it visible
        if hasattr(self, 'currentItem') and self.currentItem() and hasattr(self.currentItem(), 'task_id'):
            task_id = self.currentItem().task_id
            QTimer.singleShot(150, lambda tid=task_id: self._scroll_to_task(tid))

    def _find_and_scroll_to_child(self, parent_item, task_id):
        """Recursively search for a child and scroll to it if found"""
        try:
            for i in range(parent_item.childCount()):
                child_item = parent_item.child(i)
                
                if hasattr(child_item, 'task_id') and child_item.task_id == task_id:
                    # Found it! Scroll to it
                    debug.debug(f"Found task in children, scrolling to it")
                    self.scrollToItem(child_item)
                    self.setCurrentItem(child_item)
                    return True
                    
                # Check grandchildren
                if self._find_and_scroll_to_child(child_item, task_id):
                    return True
                    
            return False
        except Exception as e:
            debug.error(f"Error in _find_and_scroll_to_child: {e}")
            return False

    def _update_children_priority(self, parent_item, new_priority):
        """Update all children with the parent's priority"""
        debug.debug(f"Updating children to priority: {new_priority}")
        try:
            # Get database manager
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            # First, collect all child task IDs to update
            child_task_ids = []
            self._collect_child_task_ids(parent_item, child_task_ids)
            
            # If no children, just return
            if not child_task_ids:
                debug.debug("No children found to update")
                return
                
            # Update all children in one database operation
            debug.debug(f"Updating {len(child_task_ids)} children")
            for task_id in child_task_ids:
                # Update child priority in database
                db_manager.execute_update(
                    """
                    UPDATE tasks 
                    SET priority = ?
                    WHERE id = ?
                    """, 
                    (new_priority, task_id)
                )
            
            debug.debug(f"Updated priority for {len(child_task_ids)} children to: {new_priority}")
            
            # Force a tree reload instead of trying to update UI directly
            debug.debug("Reloading tree to reflect changes")
            self.load_tasks_tree()
            
        except Exception as e:
            debug.error(f"Error updating children priorities: {e}")
      
    def _collect_child_task_ids(self, parent_item, task_ids_list):
        """Helper to collect all child task IDs recursively without UI dependencies"""
        # Skip if parent item is invalid
        if parent_item is None:
            debug.debug("Invalid parent item (None)")
            return
            
        # Loop through children
        try:
            debug.debug(f"Collecting child tasks from parent item (has {parent_item.childCount()} children)")
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                
                # Skip if not a task item
                if not hasattr(child, 'task_id'):
                    debug.debug("Child is not a task item, skipping")
                    continue
                    
                # Add this child's ID to the list
                task_ids_list.append(child.task_id)
                debug.debug(f"Added child task ID: {child.task_id}")
                
                # Recursively process this child's children
                self._collect_child_task_ids(child, task_ids_list)
        except RuntimeError:
            # Skip if the item was deleted during iteration
            debug.warning("RuntimeError during child collection - item may have been deleted")
            pass
            
    def force_reload_tabs(self):
        """Force reload of all tabs"""
        debug.debug("Forcing reload of all tabs")
        try:
            parent = self.parent()
            while parent and not hasattr(parent, 'reload_all'):
                parent = parent.parent()
                
            if parent and hasattr(parent, 'reload_all'):
                # Use a short timer to let the current operation complete first
                debug.debug("Found parent with reload_all method, scheduling reload")
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(100, parent.reload_all)
            else:
                # Just refresh this tree
                debug.debug("Tab parent not found, refreshing current tree only")
                self.load_tasks_tree()
        except Exception as e:
            debug.error(f"Error reloading tabs: {e}")
            import traceback
            traceback.print_exc()

    @debug_method
    def edit_task(self, item):
        """Edit a task while preserving expanded states"""
        debug.debug(f"Editing task: {item.text(0)}")
        
        # Save expanded states before editing
        expanded_items = self._save_expanded_states()
        debug.debug(f"Saved {len(expanded_items)} expanded states before editing")
        
        # Rest of your original edit_task method...
        from .task_dialogs import EditTaskDialog
        
        # Skip if not a task item
        if not hasattr(item, 'task_id'):
            debug.debug("Not a task item, skipping edit")
            return
            
        # Get the task ID from the item
        task_id = item.task_id
        debug.debug(f"Task ID: {task_id}")
        
        # Get the memory database manager
        from database.memory_db_manager import get_memory_db_manager
        db_manager = get_memory_db_manager()
        
        try:
            # Get the complete task data directly from the database
            debug.debug("Querying database for complete task data")
            
            # Use the execute_query method from memory_db_manager
            result = db_manager.execute_query("""
                SELECT 
                    t.id, t.title, t.description, t.status, t.priority, 
                    t.due_date, c.name AS category_name, t.parent_id, t.is_compact,
                    p.title AS parent_title, p.priority AS parent_priority
                FROM tasks t
                LEFT JOIN categories c ON t.category_id = c.id
                LEFT JOIN tasks p ON t.parent_id = p.id
                WHERE t.id = ?
            """, (task_id,))
            
            if not result or len(result) == 0:
                debug.error(f"Task with ID {task_id} not found in database")
                return
                
            # First row of results
            row = result[0]
                
            # Create structured task data with debug info
            db_task_data = {
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'status': row[3],
                'priority': row[4],
                'due_date': row[5],
                'category': row[6],
                'parent_id': row[7],
                'is_compact': bool(row[8]),
                'parent_title': row[9],  # For debugging
                'parent_priority': row[10]  # For debugging
            }
            
            debug.debug(f"Retrieved task data from database: {db_task_data}")
            debug.debug(f"Parent information - ID: {db_task_data['parent_id']}, " 
                    f"Title: {db_task_data['parent_title']}, "
                    f"Priority: {db_task_data['parent_priority']}")
            
            # Get links using the specialized method from memory_db_manager
            debug.debug("Getting links from database")
            links = db_manager.get_task_links(task_id)
            debug.debug(f"Found {len(links)} links")
            
            # Get files using the specialized method from memory_db_manager
            debug.debug("Getting files from database")
            files = db_manager.get_task_files(task_id)
            debug.debug(f"Found {len(files)} files")
            
            # Get compact state from delegate
            delegate = self.itemDelegate()
            is_compact = False
            if isinstance(delegate, TaskPillDelegate):
                is_compact = task_id in delegate.compact_items
                debug.debug(f"Task compact state: {is_compact}")
                
                # Override the is_compact from the database with the delegate's state
                # since that's what's currently displayed
                db_task_data['is_compact'] = is_compact
            
            # Create the final task data structure for the dialog
            task_data = {
                'id': db_task_data['id'],
                'title': db_task_data['title'],
                'description': db_task_data['description'],
                'links': links,
                'files': files,
                'status': db_task_data['status'],
                'priority': db_task_data['priority'],
                'due_date': db_task_data['due_date'],
                'category': db_task_data['category'],
                'parent_id': db_task_data['parent_id'],
                'is_compact': db_task_data['is_compact']
            }
            
            debug.debug(f"Created task data for edit dialog: {task_data}")
            
            # Open edit dialog
            debug.debug("Opening edit task dialog")
            dialog = EditTaskDialog(task_data, self)
            
            if dialog.exec():
                # Process dialog results and save changes
                try:
                    debug.debug("Edit dialog accepted, saving changes")
                    updated_data = dialog.get_data()
                    
                    # Get category ID
                    category_name = updated_data['category']
                    category_id = None
                    
                    if category_name:
                        debug.debug(f"Looking up category ID for: {category_name}")
                        result = db_manager.execute_query(
                            "SELECT id FROM categories WHERE name = ?", 
                            (category_name,)
                        )
                        if result and len(result) > 0:
                            category_id = result[0][0]
                            debug.debug(f"Found category ID: {category_id}")
                    
                    # Update database using execute_update from memory_db_manager
                    debug.debug("Updating task in database")
                    db_manager.execute_update(
                        """
                        UPDATE tasks 
                        SET title = ?, description = ?, status = ?, 
                            priority = ?, due_date = ?, category_id = ?, parent_id = ?
                        WHERE id = ?
                        """, 
                        (
                            updated_data['title'], 
                            updated_data['description'], 
                            updated_data['status'], 
                            updated_data['priority'],
                            updated_data['due_date'],
                            category_id,
                            updated_data['parent_id'],
                            updated_data['id']
                        )
                    )
                    
                    # Update links - use specialized methods from memory_db_manager
                    debug.debug("Updating links")
                    new_links = updated_data.get('links', [])
                    existing_links = db_manager.get_task_links(updated_data['id'])
                    
                    # Track existing link IDs for deletion
                    existing_ids = set(link_id for link_id, _, _ in existing_links if link_id is not None)
                    new_link_ids = set(link_id for link_id, _, _ in new_links if link_id is not None)
                    
                    # Delete links that no longer exist
                    links_to_delete = existing_ids - new_link_ids
                    if links_to_delete:
                        debug.debug(f"Deleting {len(links_to_delete)} links")
                        for link_id in links_to_delete:
                            db_manager.delete_task_link(link_id)
                    
                    # Add or update links
                    debug.debug(f"Adding/updating {len(new_links)} links")
                    for i, (link_id, url, label) in enumerate(new_links):
                        if url and url.strip():
                            if link_id is None:
                                # New link - add it
                                debug.debug(f"Adding new link: {url}")
                                db_manager.add_task_link(updated_data['id'], url, label)
                            else:
                                # Existing link - update it
                                debug.debug(f"Updating existing link: {link_id}")
                                db_manager.update_task_link(link_id, url, label)
                    
                    # Update files - use specialized methods from memory_db_manager
                    debug.debug("Updating files")
                    new_files = updated_data.get('files', [])
                    existing_files = db_manager.get_task_files(updated_data['id'])
                    
                    # Track existing file IDs for deletion
                    existing_file_ids = set(file_id for file_id, _, _ in existing_files if file_id is not None)
                    new_file_ids = set(file_id for file_id, _, _ in new_files if file_id is not None)
                    
                    # Delete files that no longer exist
                    files_to_delete = existing_file_ids - new_file_ids
                    if files_to_delete:
                        debug.debug(f"Deleting {len(files_to_delete)} files")
                        for file_id in files_to_delete:
                            db_manager.delete_task_file(file_id)
                    
                    # Add or update files
                    debug.debug(f"Adding/updating {len(new_files)} files")
                    for i, (file_id, file_path, file_name) in enumerate(new_files):
                        if file_path and file_path.strip():
                            if file_id is None:
                                # New file - add it
                                debug.debug(f"Adding new file: {file_path}")
                                db_manager.add_task_file(updated_data['id'], file_path, file_name)
                            else:
                                # Existing file - update it
                                debug.debug(f"Updating existing file: {file_id}")
                                db_manager.update_task_file(file_id, file_path, file_name)
                    
                    # Explicitly save to file after editing task
                    debug.debug("Saving memory database to file after task edit")
                    db_manager.save_to_file()
                    
                    # Reload the tree and restore expanded states
                    if hasattr(self, 'load_tasks_tab'):
                        debug.debug("Reloading tasks with filtered method")
                        self.load_tasks_tab()
                    else:
                        debug.debug("Reloading tasks with standard method")
                        self.load_tasks_tree()
                    
                    # Restore expanded states
                    self._restore_expanded_states(expanded_items)
                    debug.debug(f"Restored {len(expanded_items)} expanded states")
                    
                    # Highlight the edited task
                    self._highlight_task(task_id)
                    
                except Exception as e:
                    debug.error(f"Error updating task: {e}")
                    import traceback
                    traceback.print_exc()
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.critical(self, "Error", f"Failed to update task: {str(e)}")
                    
        except Exception as e:
            debug.error(f"Error preparing task data for editing: {e}")
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to load task data: {str(e)}")    
    
    def get_settings_manager(self):
        """Get the settings manager instance"""
        debug.debug("Getting settings manager")
        try:
            # Try to get it from the tree widget's parent (MainWindow)
            if hasattr(self, 'parent') and callable(self.parent) and hasattr(self.parent(), 'settings'):
                debug.debug("Found settings manager in parent")
                return self.parent().settings
        except Exception as e:
            debug.error(f"Error getting settings manager from parent: {e}")
        
        # Fallback to creating a new instance
        debug.debug("Creating new SettingsManager instance")
        from ui.app_settings import SettingsManager
        return SettingsManager()

    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        debug.debug("Getting database connection")
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()

    def handle_links_click(self, item, point_in_task_pill):
        """Handle clicks on the links section of a task pill"""
        debug.debug("Handling links click")
        # Get item data
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Check if we have any links
        links = data.get('links', [])
        debug.debug(f"Found {len(links)} links in task data")
        
        # Also check legacy link
        legacy_link = data.get('link')
        if not links and legacy_link and legacy_link.strip():
            debug.debug(f"Using legacy link: {legacy_link}")
            links = [(None, legacy_link, None)]
        
        # If no links, return
        if not links:
            debug.debug("No links found, nothing to do")
            return
        
        # Create links menu
        debug.debug("Creating links context menu")
        menu = QMenu(self)
        
        # Add individual links with labels if available
        for link_id, url, label in links:
            action_text = label if label else url
            action = menu.addAction(action_text)
            action.setData(url)
            debug.debug(f"Added menu item: {action_text}")
        
        # Add separator if we have more than one link
        if len(links) > 1:
            menu.addSeparator()
            debug.debug("Added separator")
            # Add "Open All" actions
            open_all_action = menu.addAction("Open All Links")
            open_all_action.setData("open_all")
            debug.debug("Added 'Open All Links' action")
            
            open_all_new_window_action = menu.addAction("Open All in New Window")
            open_all_new_window_action.setData("open_all_new_window")
            debug.debug("Added 'Open All in New Window' action")
        
        # Execute menu
        debug.debug("Showing links menu")
        action = menu.exec(self.mapToGlobal(point_in_task_pill))
        
        if action:
            action_data = action.data()
            debug.debug(f"User selected action with data: {action_data}")
            
            if action_data == "open_all":
                # Open all links in current window
                debug.debug("Opening all links in current window")
                for _, url, _ in links:
                    if url:
                        self.open_link(url)
            elif action_data == "open_all_new_window":
                # Open all links in new window
                debug.debug("Opening all links in new window")
                self.open_links_in_new_window(links)
            else:
                # Open individual link
                debug.debug(f"Opening individual link: {action_data}")
                self.open_link(action_data)

    def open_link(self, url):
        """Open a single link in the default browser"""
        debug.debug(f"Opening link: {url}")
        try:
            import webbrowser
            # Make sure URL has a protocol
            if not (url.startswith("http://") or url.startswith("https://") or url.startswith("ftp://")):
                url = "https://" + url
                debug.debug(f"Added protocol to URL: {url}")
                
            webbrowser.open(url)
            debug.debug("Link opened successfully")
        except Exception as e:
            debug.error(f"Error opening link: {e}")
            QMessageBox.warning(self, "Error", f"Could not open link: {e}")

    def open_links_in_new_window(self, links):
        """Open all links in a new browser window"""
        debug.debug(f"Opening {len(links)} links in new window")
        try:
            import webbrowser
            import time
            
            # Filter out empty URLs
            valid_links = [(link_id, url, label) for link_id, url, label in links if url]
            
            if not valid_links:
                debug.debug("No valid links to open")
                return
                
            # Open the first link in a new window
            first_link_id, first_url, _ = valid_links[0]
            
            # Make sure URL has a protocol
            if not (first_url.startswith("http://") or first_url.startswith("https://") or first_url.startswith("ftp://")):
                first_url = "https://" + first_url
                debug.debug(f"Added protocol to first URL: {first_url}")
                
            # Open first link in a new window
            debug.debug(f"Opening first link in new window: {first_url}")
            webbrowser.open_new(first_url)
            
            # Wait a bit for the window to open
            debug.debug("Waiting for window to open")
            time.sleep(0.5)
            
            # Open the rest of the links in new tabs in the same window
            for link_id, url, _ in valid_links[1:]:
                # Make sure URL has a protocol
                if not (url.startswith("http://") or url.startswith("https://") or url.startswith("ftp://")):
                    url = "https://" + url
                    debug.debug(f"Added protocol to URL: {url}")
                    
                debug.debug(f"Opening additional link in new tab: {url}")
                webbrowser.open_new_tab(url)
                # Small delay to prevent overwhelming the browser
                time.sleep(0.1)
                
            debug.debug("All links opened successfully")
                
        except Exception as e:
            debug.error(f"Error opening links in new window: {e}")
            QMessageBox.warning(self, "Error", f"Could not open links in new window: {e}")
            
    def handle_double_click(self, item, column):
        """Handle double-click events with special case for priority headers"""
        debug.debug("Processing double-click event")
        # Get the item data
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Check if this is a priority header
        if isinstance(data, dict) and data.get('is_priority_header', False):
            debug.debug("Double-clicked on priority header")
            # Toggle the header
            self.blockSignals(True)
            
            # Convert item to index for isExpanded method
            item_index = self.indexFromItem(item)
            
            # Check current expanded state
            if self.isExpanded(item_index):
                debug.debug("Collapsing priority header")
                self.collapseItem(item)
                data['expanded'] = False
            else:
                debug.debug("Expanding priority header")
                self.expandItem(item)
                data['expanded'] = True
                
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            self.blockSignals(False)
            self._save_priority_expanded_states()
            return
        
        # Skip if not a task item
        if not hasattr(item, 'task_id'):
            debug.debug("Not a task item, ignoring double-click")
            return
        
        # Get the position of the double-click
        pos = self.mapFromGlobal(self.cursor().pos())
        rect = self.visualItemRect(item)
        debug.debug(f"Double-click position: {pos.x()}, {pos.y()}")
        
        # Calculate the right section boundary (where the link area begins)
        # This should match the width used in the delegate's _draw_right_panel method
        right_section_width = 100  # Same as in TaskPillDelegate
        right_section_boundary = rect.right() - right_section_width
        debug.debug(f"Right section boundary: {right_section_boundary}")
        
        # Check if the click was in the right section (link area)
        if 'link' in data and data['link'] and pos.x() > right_section_boundary:
            # Handle link click
            link = data['link']
            debug.debug(f"Click was in link area, opening link: {link}")
            if not link.startswith(('http://', 'https://')):
                link = 'https://' + link
                debug.debug(f"Added protocol to link: {link}")
            try:
                import webbrowser
                webbrowser.open(link)
                debug.debug("Link opened successfully")
            except Exception as e:
                debug.error(f"Error opening link: {e}")
        else:
            # For clicks in the main content area, open edit dialog
            debug.debug("Click was in main content area, opening edit dialog")
            self.edit_task(item)

    def handle_files_click(self, item, point_in_task_pill):
        """Handle clicks on the files section of a task pill"""
        debug.debug("Handling files click")
        # Get item data
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Check if we have any files
        files = data.get('files', [])
        debug.debug(f"Found {len(files)} files in task data")
        
        # If no files, return
        if not files:
            debug.debug("No files found, nothing to do")
            return
        
        # Create files menu
        debug.debug("Creating files context menu")
        menu = QMenu(self)
        
        # Add individual files with names if available
        for file_id, file_path, file_name in files:
            display_name = file_name if file_name else file_path
            action = menu.addAction(display_name)
            action.setData(file_path)
            debug.debug(f"Added menu item: {display_name}")
        
        # Add separator if we have files
        if files:
            menu.addSeparator()
            debug.debug("Added separator")
            
            # Add "Open All" action
            open_all_action = menu.addAction("Open All Files")
            open_all_action.setData("open_all")
            debug.debug("Added 'Open All Files' action")
            
            # Add "Open All Locations" action
            open_locations_action = menu.addAction("Open All File Locations")
            open_locations_action.setData("open_locations")
            debug.debug("Added 'Open All File Locations' action")
        
        # Execute menu
        debug.debug("Showing files menu")
        action = menu.exec(self.mapToGlobal(point_in_task_pill))
        
        if action:
            action_data = action.data()
            debug.debug(f"User selected action with data: {action_data}")
            
            if action_data == "open_all":
                # Open all files
                debug.debug("Opening all files")
                self.open_all_files(files)
            elif action_data == "open_locations":
                # Open all file locations
                debug.debug("Opening all file locations")
                self.open_all_file_locations(files)
            else:
                # Open individual file
                debug.debug(f"Opening individual file: {action_data}")
                self.open_file(item, action_data)

    def open_all_files(self, files):
        """Open all files with their default applications"""
        debug.debug(f"Opening {len(files)} files")
        for _, file_path, _ in files:
            if file_path:
                try:
                    debug.debug(f"Attempting to open file: {file_path}")
                    self.open_file(None, file_path)
                    debug.debug(f"Opened file: {file_path}")
                except Exception as e:
                    debug.error(f"Error opening file {file_path}: {e}")
                    # Continue with the next file even if one fails

    def open_all_file_locations(self, files):
        """Open file explorer windows showing the location of each file"""
        debug.debug(f"Opening locations for {len(files)} files")
        import os
        import platform
        import subprocess
        
        for _, file_path, _ in files:
            if not file_path or not os.path.exists(file_path):
                debug.debug(f"File does not exist: {file_path}")
                continue
                
            try:
                # Get the directory containing the file
                file_dir = os.path.dirname(file_path)
                debug.debug(f"Opening directory: {file_dir}")
                
                # Open the directory based on platform
                system = platform.system()
                debug.debug(f"Current platform: {system}")
                
                if system == 'Windows':
                    # On Windows, use Explorer to open the directory and select the file
                    debug.debug("Using Explorer to select file")
                    subprocess.run(['explorer', '/select,', os.path.normpath(file_path)])
                elif system == 'Darwin':  # macOS
                    # On macOS, use Finder to open and select the file
                    debug.debug("Using Finder to reveal file")
                    subprocess.run(['open', '-R', file_path])
                else:  # Linux and others
                    # On Linux, just open the directory
                    debug.debug("Using xdg-open to open directory")
                    subprocess.run(['xdg-open', file_dir])
                    
                debug.debug(f"Opened location for: {file_path}")
            except Exception as e:
                debug.error(f"Error opening location for {file_path}: {e}")
                # Continue with the next file even if one fails

    def open_file(self, item, file_path):
        """Open a file with the default application"""
        debug.debug(f"Opening file: {file_path}")
        if not file_path:
            debug.debug("No file path provided")
            return
            
        try:
            import os
            import platform
            
            # Check if file exists
            if not os.path.exists(file_path):
                debug.debug(f"File not found: {file_path}")
                # Handle file not found
                if item is not None:  # Only show dialog if we have an item reference
                    from PyQt6.QtWidgets import QMessageBox
                    
                    debug.debug("Showing file not found dialog")
                    reply = QMessageBox.question(
                        self,
                        "File Not Found",
                        f"The file '{file_path}' could not be found. Would you like to update the file path?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | 
                        QMessageBox.StandardButton.Discard
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        # Let the user select a new file
                        from PyQt6.QtWidgets import QFileDialog
                        
                        debug.debug("User chose to update file path")
                        new_path, _ = QFileDialog.getOpenFileName(
                            self, "Update File Path", "", "All Files (*.*)"
                        )
                        
                        if new_path:
                            debug.debug(f"User selected new path: {new_path}")
                            # Update the file path in the database
                            self.update_file_path(item, file_path, new_path)
                            
                            # Try opening the new file
                            self.open_file(item, new_path)
                            
                    elif reply == QMessageBox.StandardButton.Discard:
                        # Remove the file from the task
                        debug.debug("User chose to remove file")
                        self.remove_file_from_task(item, file_path)
                else:
                    debug.debug(f"File not found and no item reference: {file_path}")
                return
                
            # Open file with default application based on platform
            system = platform.system()
            debug.debug(f"Opening file on platform: {system}")
            
            if system == 'Windows':
                os.startfile(file_path)
                debug.debug("Opened file with startfile")
            elif system == 'Darwin':  # macOS
                import subprocess
                subprocess.call(('open', file_path))
                debug.debug("Opened file with 'open' command")
            else:  # Linux and others
                import subprocess
                subprocess.call(('xdg-open', file_path))
                debug.debug("Opened file with 'xdg-open' command")
                
        except Exception as e:
            debug.error(f"Error opening file: {e}")
            
            # Handle other errors if we have an item reference
            if item is not None:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Error", f"Could not open file: {str(e)}")
                
    def handleHeaderDoubleClick(self, item):
        """Handle double-click on priority headers"""
        # Get item data
        data = item.data(0, Qt.ItemDataRole.UserRole)
        priority = data.get('priority', 'Unknown')
        
        debug.debug(f"Double-clicked priority header: {priority}")
        
        # Disconnect the itemExpanded/itemCollapsed signals temporarily
        debug.debug("Disconnecting expansion signals")
        self.itemExpanded.disconnect(self.onItemExpanded)
        self.itemCollapsed.disconnect(self.onItemCollapsed)
        
        # Convert item to index for isExpanded method
        item_index = self.indexFromItem(item)
        
        # Check current expanded state
        currently_expanded = self.isExpanded(item_index)
        debug.debug(f"Current expanded state: {currently_expanded}")
        
        # Toggle state
        if currently_expanded:
            debug.debug(f"Collapsing header: {priority}")
            self.collapseItem(item)
            data['expanded'] = False
        else:
            debug.debug(f"Expanding header: {priority}")
            self.expandItem(item)
            data['expanded'] = True
        
        # Update item data
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        
        # Force update
        debug.debug("Forcing viewport update")
        self.viewport().update()
        
        # Save expanded states
        debug.debug("Saving priority expanded states")
        self._save_priority_expanded_states()
        
        # Reconnect the signals after a short delay
        debug.debug("Scheduling reconnection of signals")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self.reconnectExpandCollapsedSignals)

    def handleTaskDoubleClick(self, item):
        """Handle double-click on task items with updated link handling"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        debug.debug(f"Double-clicked task: {data.get('title', 'Unknown')}")
        
        # Get the position of the double-click
        pos = self.mapFromGlobal(self.cursor().pos())
        rect = self.visualItemRect(item)
        debug.debug(f"Double-click position: {pos.x()}, {pos.y()}")
        
        # Calculate the right section boundary using settings
        settings = self.get_settings_manager()
        right_section_width = settings.get_setting("right_panel_width", 100)
        right_section_boundary = rect.right() - right_section_width
        debug.debug(f"Right section boundary: {right_section_boundary}")
        
        # Check if the click was in the right section
        if pos.x() > right_section_boundary:
            # Find out what's in the right panel
            debug.debug("Click was in right panel")
            right_panel_contents = settings.get_setting("right_panel_contents", ["Link", "Due Date"])
            debug.debug(f"Right panel contents: {right_panel_contents}")
            
            # If "Link" is in the right panel, handle the click
            if "Link" in right_panel_contents:
                # Check for links
                links = data.get('links', [])
                legacy_link = data.get('link', '')
                
                if (links and isinstance(links, list) and len(links) > 0) or legacy_link:
                    # Handle link section click
                    debug.debug("Handling link section click")
                    self.handle_links_click(item, pos)
                    return
        
        # For clicks in the main content area, open edit dialog
        debug.debug("Opening edit dialog")
        self.edit_task(item)
     
    def keyPressEvent(self, event):
        debug.debug(f"Key press event: {event.key()}")
        if event.key() == Qt.Key.Key_Return:
            selected_items = self.selectedItems()
            if selected_items:
                debug.debug(f"Editing task via Enter key: {selected_items[0].text(0)}")
                self.edit_task(selected_items[0])
        elif event.key() == Qt.Key.Key_Delete:
            selected_items = self.selectedItems()
            if selected_items:
                debug.debug(f"Deleting task via Delete key: {selected_items[0].text(0)}")
                self.delete_task(selected_items[0])
        else:
            debug.debug("Passing key event to parent")
            super().keyPressEvent(event)

    @debug_method
    def load_tasks_tree(self):
        """Load all tasks without filtering (base implementation)"""
        debug.debug("Loading all tasks (base implementation)")
        start_time = time.time()
        
        try:
            # Save the expanded states before clearing
            expanded_items = self._save_expanded_states()
            debug.debug(f"Saved expanded states for {len(expanded_items)} items")
            
            self.clear()
            
            # Import database manager
            from database.memory_db_manager import get_memory_db_manager
            db_manager = get_memory_db_manager()
            
            # Check if completed_at column exists
            debug.debug("Checking database schema for completed_at column")
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(tasks)")
                columns = [info[1] for info in cursor.fetchall()]
                has_completed_at = 'completed_at' in columns
                debug.debug(f"Has completed_at column: {has_completed_at}")
            
            # Create query to load ALL tasks (no filtering)
            completed_at_field = ", t.completed_at" if has_completed_at else ""
            debug.debug(f"Completed_at field in query: {completed_at_field}")
            
            query = f"""
                SELECT t.id, t.title, t.description, '', t.status, t.priority, 
                    t.due_date, c.name, t.is_compact, t.parent_id{completed_at_field}
                FROM tasks t
                LEFT JOIN categories c ON t.category_id = c.id
                ORDER BY t.parent_id NULLS FIRST, t.display_order
                """
            debug.debug("Executing query to load all tasks")
            tasks = db_manager.execute_query(query)
            debug.debug(f"Query returned {len(tasks)} total tasks")
            
            # Process tasks with priority headers (like Current Tasks tab)
            debug.debug("Processing all tasks with priority headers")
            self._process_all_tasks_with_priority_headers(tasks)
            
            # Restore expanded states
            self._restore_expanded_states(expanded_items)
            debug.debug(f"Restored expanded states for {len(expanded_items)} items")
            
            end_time = time.time()
            debug.debug(f"Load tasks tree completed in {end_time - start_time:.3f} seconds")
            
        except Exception as e:
            debug.error(f"Error loading tasks tree: {e}")
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Error", f"Failed to load tasks: {str(e)}")

    @debug_method
    def _process_all_tasks_with_priority_headers(self, tasks):
        """Process all tasks and organize them under priority headers"""
        start_time = time.time()
        try:
            debug.debug(f"Processing {len(tasks)} tasks with priority headers")
            
            # Import database manager
            from database.memory_db_manager import get_memory_db_manager
            db_manager = get_memory_db_manager()
            
            # Get priority order map and colors
            debug.debug("Getting priority order map and colors")
            priority_order = {}
            priority_colors = {}
            result = db_manager.execute_query(
                "SELECT name, display_order, color FROM priorities ORDER BY display_order"
            )
            for name, order, color in result:
                priority_order[name] = order
                priority_colors[name] = color
            debug.debug(f"Found {len(priority_colors)} priorities")
            
            # Create headers for each priority
            debug.debug("Creating priority headers")
            priority_headers = {}
            for priority, color in priority_colors.items():
                debug.debug(f"Creating header for priority: {priority}, color: {color}")
                header_item = PriorityHeaderItem(priority, color)
                self.addTopLevelItem(header_item)
                priority_headers[priority] = header_item
            
            # Ensure "Unprioritized" header exists if not in database
            if "Unprioritized" not in priority_headers:
                debug.debug("Creating Unprioritized header (not found in database)")
                unprioritized_color = "#AAAAAA"  # Medium gray
                unprioritized_header = PriorityHeaderItem("Unprioritized", unprioritized_color)
                self.addTopLevelItem(unprioritized_header)
                priority_headers["Unprioritized"] = unprioritized_header
            
            # Restore expanded state from settings
            debug.debug("Restoring expanded states from settings")
            settings = self.get_settings_manager()
            all_priorities = list(priority_headers.keys())
            expanded_priorities = settings.get_setting("expanded_priorities", all_priorities)
            debug.debug(f"Expanded priorities from settings: {expanded_priorities}")
            
            for priority, header_item in priority_headers.items():
                # Get the color - either from priority_colors or default to gray for "Unprioritized"
                color = priority_colors.get(priority, "#AAAAAA")
                
                if priority in expanded_priorities:
                    debug.debug(f"Expanding header for priority: {priority}")
                    self.expandItem(header_item)
                    header_item.setData(0, Qt.ItemDataRole.UserRole, {
                        'is_priority_header': True,
                        'priority': priority,
                        'color': color,
                        'expanded': True
                    })
                else:
                    debug.debug(f"Collapsing header for priority: {priority}")
                    self.collapseItem(header_item)
                    header_item.setData(0, Qt.ItemDataRole.UserRole, {
                        'is_priority_header': True,
                        'priority': priority,
                        'color': color,
                        'expanded': False
                    })
            
            items = {}
            
            # First pass: create all items with proper links and files
            debug.debug("First pass: creating all items with links and files")
            for i, row in enumerate(tasks):
                if i % 20 == 0:  # Log progress every 20 items
                    debug.debug(f"Processing task {i+1}/{len(tasks)}")
                
                task_id = row[0]
                
                # Load links for this task
                debug.debug(f"Loading links for task {task_id}")
                task_links = []
                try:
                    task_links = db_manager.get_task_links(task_id)
                    debug.debug(f"Found {len(task_links)} links for task {task_id}")
                except Exception as e:
                    debug.error(f"Error loading links for task {task_id}: {e}")
                
                # Load files for this task
                debug.debug(f"Loading files for task {task_id}")
                task_files = []
                try:
                    task_files = db_manager.get_task_files(task_id)
                    debug.debug(f"Found {len(task_files)} files for task {task_id}")
                except Exception as e:
                    debug.error(f"Error loading files for task {task_id}: {e}")
                
                # Create the task item WITH links and files
                debug.debug(f"Creating task item for ID: {task_id}")
                item = self.add_task_item(
                    row[0],      # task_id
                    row[1],      # title
                    row[2],      # description
                    '',          # link (empty legacy field)
                    row[4],      # status
                    row[5],      # priority
                    row[6],      # due_date
                    row[7],      # category
                    row[8],      # is_compact
                    links=task_links,  # Pass links as named parameter
                    files=task_files   # Pass files as named parameter
                )
                items[task_id] = item
                
                # Store parent info for second pass
                parent_id = row[9]  # parent_id
                debug.debug(f"Task {task_id} has parent_id: {parent_id}")
                
                # Process using priority headers logic
                priority = row[5] or "Unprioritized"  # Default to Unprioritized if None
                debug.debug(f"Task {task_id} has priority: {priority}")
                
                if parent_id is None:
                    # This is a top-level task, add it to the priority header
                    if priority in priority_headers:
                        debug.debug(f"Adding task {task_id} to priority header: {priority}")
                        priority_headers[priority].addChild(item)
                    else:
                        # If no matching header, use Unprioritized
                        debug.debug(f"No header found for priority '{priority}', using Unprioritized for task {task_id}")
                        priority_headers["Unprioritized"].addChild(item)
                else:
                    # This is a child task, will be handled in second pass
                    debug.debug(f"Task {task_id} is a child task, will be handled in second pass")
                    item.setData(0, Qt.ItemDataRole.UserRole + 1, parent_id)
                            
            # Second pass: handle parent-child relationships for non-top-level tasks
            debug.debug("Second pass: handling parent-child relationships")
            parent_child_count = 0
            for task_id, item in items.items():
                parent_id = item.data(0, Qt.ItemDataRole.UserRole + 1)
                if parent_id is not None and parent_id in items:
                    parent_item = items[parent_id]
                    parent_item.addChild(item)
                    parent_child_count += 1
                    debug.debug(f"Added task {task_id} as child of {parent_id}")
            
            debug.debug(f"Processed {parent_child_count} parent-child relationships")
            end_time = time.time()
            debug.debug(f"Task processing completed in {end_time - start_time:.3f} seconds")
        
        except Exception as e:
            debug.error(f"Error processing tasks with priority headers: {e}")
            debug.error(traceback.format_exc())
            
    def dragMoveEvent(self, event):
        """Handle drag move events and implement autoscroll"""
        debug.debug("Drag move event")
        # Call the parent implementation first
        super().dragMoveEvent(event)
        
        # Get the viewport rectangle
        viewport_rect = self.viewport().rect()
        
        # Define the scroll margins (how close to the edge before scrolling begins)
        margin = 50
        
        # Get the current position
        pos = event.position().toPoint()
        
        # Get the current vertical scroll position
        v_scroll_bar = self.verticalScrollBar()
        current_scroll = v_scroll_bar.value()
        
        # Check if we're near the top edge
        if pos.y() < margin:
            # Calculate how much to scroll (closer to edge = faster scroll)
            scroll_amount = max(1, (margin - pos.y()) // 5)
            # Scroll up
            debug.debug(f"Auto-scrolling up by {scroll_amount}")
            v_scroll_bar.setValue(current_scroll - scroll_amount)
        
        # Check if we're near the bottom edge
        elif pos.y() > viewport_rect.height() - margin:
            # Calculate how much to scroll (closer to edge = faster scroll)
            scroll_amount = max(1, (pos.y() - (viewport_rect.height() - margin)) // 5)
            # Scroll down
            debug.debug(f"Auto-scrolling down by {scroll_amount}")
            v_scroll_bar.setValue(current_scroll + scroll_amount)
        
    def mousePressEvent(self, event):
        """Handle mouse press events including priority header toggle"""
        debug.debug("Mouse press event")
        try:
            pos = event.position().toPoint()
            index = self.indexAt(pos)
            
            if index.isValid():
                item = self.itemFromIndex(index)
                
                # Get item data
                data = item.data(0, Qt.ItemDataRole.UserRole)
                
                # Check if this is a priority header and click is in toggle area (left 40 pixels)
                if isinstance(data, dict) and data.get('is_priority_header', False) and pos.x() < 40:
                    # Store this item temporarily to handle in mouseReleaseEvent
                    debug.debug(f"Clicked on priority header toggle area: {data.get('priority', 'Unknown')}")
                    self._header_toggle_item = item
                    event.accept()
                    return
                
                # For regular task items, don't interfere - let double-click work normally
                debug.debug("Regular mouse press on task item")
        except Exception as e:
            debug.error(f"Error in mousePressEvent: {e}")
        
        # Handle regular mouse press events
        debug.debug("Passing mouse press to parent")
        super().mousePressEvent(event)
       
    def mouseReleaseEvent(self, event):
        """Handle mouse release events, including delayed priority header toggle"""
        debug.debug("Mouse release event")
        try:
            # Check if we have a stored header toggle item
            if hasattr(self, '_header_toggle_item') and self._header_toggle_item is not None:
                # Block signals to prevent unwanted events
                debug.debug("Processing header toggle")
                self.blockSignals(True)
                
                # Get item data
                item = self._header_toggle_item
                data = item.data(0, Qt.ItemDataRole.UserRole)
                priority = data.get('priority', 'Unknown')
                
                # Convert item to index for isExpanded method
                item_index = self.indexFromItem(item)
                
                # Get current expanded state from visual state
                currently_expanded = self.isExpanded(item_index)
                debug.debug(f"Priority header '{priority}' current expanded state: {currently_expanded}")
                
                # Toggle state
                if currently_expanded:
                    debug.debug(f"Collapsing priority header: {priority}")
                    self.collapseItem(item)
                    # Update data
                    data['expanded'] = False
                else:
                    debug.debug(f"Expanding priority header: {priority}")
                    self.expandItem(item)
                    # Update data
                    data['expanded'] = True
                
                # Update item data
                item.setData(0, Qt.ItemDataRole.UserRole, data)
                
                # Save expanded states to settings
                debug.debug("Saving expanded states to settings")
                self._save_priority_expanded_states()
                
                # Restore signals
                self.blockSignals(False)
                
                # Force update
                debug.debug("Forcing viewport update")
                self.viewport().update()
                
                # Clear the stored item
                self._header_toggle_item = None
                
                event.accept()
                return
        except Exception as e:
            debug.error(f"Error in mouseReleaseEvent: {e}")
        
        # Handle regular mouse release events
        debug.debug("Passing mouse release to parent")
        super().mouseReleaseEvent(event)

    def onItemCollapsed(self, item):
        """Keep data in sync when item is collapsed by the tree widget"""
        debug.debug("Item collapsed event")
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and data.get('is_priority_header', False):
            # Update data
            priority = data.get('priority', 'Unknown')
            debug.debug(f"Priority header collapsed: {priority}")
            data['expanded'] = False
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            
            # Save to settings
            debug.debug("Saving to settings")
            self._save_priority_expanded_states()
        
        # Handle regular task items with children
        elif isinstance(data, dict) and 'id' in data and hasattr(item, 'task_id') and item.childCount() > 0:
            # Update data
            task_id = data['id']
            debug.debug(f"Task item expanded: {task_id}")
            data['expanded'] = False
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            
            # Save to settings
            self._save_expanded_states()

    def onItemExpanded(self, item):
        """Keep data in sync when item is expanded by the tree widget"""
        debug.debug("Item expanded event")
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and data.get('is_priority_header', False):
            # Update data
            priority = data.get('priority', 'Unknown')
            debug.debug(f"Priority header expanded: {priority}")
            data['expanded'] = True
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            
            # Save to settings
            debug.debug("Saving expanded states to settings")
            self._save_priority_expanded_states()
        
        # Handle regular task items with children
        elif isinstance(data, dict) and 'id' in data and hasattr(item, 'task_id') and item.childCount() > 0:
            # Update data
            task_id = data['id']
            debug.debug(f"Task item expanded: {task_id}")
            data['expanded'] = True
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            
            # Save to settings
            self._save_expanded_states()

    def onItemDoubleClicked(self, item, column):
        """Route double-clicks to appropriate handlers based on item type"""
        debug.debug(f"Double-click on item: {item.text(0)}")
        
        # Get the item data
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Check if this is a priority header
        if isinstance(data, dict) and data.get('is_priority_header', False):
            debug.debug("Routing to handleHeaderDoubleClick")
            self.handleHeaderDoubleClick(item)
        elif hasattr(item, 'task_id'):
            # This is a task item
            debug.debug("Routing to handleTaskDoubleClick")
            self.handleTaskDoubleClick(item)
        else:
            debug.debug(f"Unknown item type - no handler available")

    def reconnectExpandCollapsedSignals(self):
        """Reconnect the expand/collapse signals"""
        debug.debug("Reconnecting expand/collapse signals")
        try:
            self.itemExpanded.connect(self.onItemExpanded)
            self.itemCollapsed.connect(self.onItemCollapsed)
            debug.debug("Signals reconnected successfully")
        except Exception as e:
            debug.error(f"Error reconnecting signals: {e}")

    def setItemHeight(self, item, size_hint):
        """Update the item's height based on the current view mode"""
        debug.debug(f"Setting item height for: {item.text(0)}")
        if item:
            # Update the item's size hint
            item.setSizeHint(0, size_hint)
            debug.debug(f"Set size hint: {size_hint.width()}x{size_hint.height()}")
            
            # Force a layout update
            debug.debug("Forcing viewport update")
            self.viewport().update()

    @debug_method
    def show_context_menu(self, position):
        debug.debug("Showing context menu")
        item = self.itemAt(position)
        if not item:
            debug.debug("No item at position, skipping context menu")
            return
            
        # Skip if this is a priority header
        user_data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(user_data, dict) and user_data.get('is_priority_header', False):
            debug.debug("Item is a priority header, skipping context menu")
            return
            
        debug.debug(f"Creating context menu for item: {item.text(0)}")
        
        # Get OS style from application
        app = QApplication.instance()
        os_style = "Default"
        if app.property("style_manager"):
            os_style = app.property("style_manager").current_style
            debug.debug(f"Detected OS style: {os_style}")
        
        # Create menu
        menu = QMenu(self)
        
        # Apply OS-specific styles (existing code)
        if os_style == "macOS":
            menu.setStyleSheet("""
                QMenu {
                    font-family: -apple-system, '.AppleSystemUIFont', 'SF Pro Text';
                    background-color: #FFFFFF;
                    border: 1px solid #D2D2D7;
                    border-radius: 10px;
                    padding: 5px;
                }
                QMenu::item {
                    padding: 5px 30px 5px 20px;
                    border-radius: 6px;
                }
                QMenu::item:selected {
                    background-color: #0071E3;
                    color: white;
                }
                QMenu::item:disabled {
                    color: #8E8E93;
                }
                QMenu::separator {
                    height: 1px;
                    background-color: #D2D2D7;
                    margin: 5px 0px 5px 0px;
                }
            """)
        elif os_style == "Windows":
            menu.setStyleSheet("""
                QMenu {
                    font-family: 'Segoe UI', sans-serif;
                    background-color: #FFFFFF;
                    border: 1px solid #CCCCCC;
                    padding: 2px;
                }
                QMenu::item {
                    padding: 6px 30px 6px 20px;
                }
                QMenu::item:selected {
                    background-color: #0078D7;
                    color: white;
                }
                QMenu::item:disabled {
                    color: #999999;
                }
                QMenu::separator {
                    height: 1px;
                    background-color: #CCCCCC;
                    margin: 4px 0px 4px 0px;
                }
            """)
        else:  # Linux
            menu.setStyleSheet("""
                QMenu {
                    font-family: 'Ubuntu', 'Noto Sans', sans-serif;
                    background-color: #FFFFFF;
                    border: 1px solid #C6C6C6;
                    border-radius: 4px;
                    padding: 2px;
                }
                QMenu::item {
                    padding: 6px 30px 6px 20px;
                    border-radius: 3px;
                }
                QMenu::item:selected {
                    background-color: #3584E4;
                    color: white;
                }
                QMenu::item:disabled {
                    color: #999999;
                }
                QMenu::separator {
                    height: 1px;
                    background-color: #C6C6C6;
                    margin: 4px 0px 4px 0px;
                }
            """)
        
        # Create actions
        edit_action = menu.addAction("Edit Task")
        delete_action = menu.addAction("Delete Task")
        
        # Add separator
        menu.addSeparator()
        
        # NEW: Add Task Creation submenu
        new_task_menu = QMenu("New Task", menu)
        new_task_menu.setStyleSheet(menu.styleSheet())
        
        new_child_action = new_task_menu.addAction("New Task under this task")
        new_sibling_action = new_task_menu.addAction("New Task under this header")
        
        menu.addMenu(new_task_menu)
        
        # Add separator
        menu.addSeparator()
        
        # Check if task has links or files
        task_data = item.data(0, Qt.ItemDataRole.UserRole)
        has_links = False
        has_files = False

        if isinstance(task_data, dict):
            links = task_data.get('links', [])
            files = task_data.get('files', [])
            legacy_link = task_data.get('link', '')
            
            # Ensure we're working with proper data types
            if links and isinstance(links, list) and len(links) > 0:
                has_links = True
                debug.debug(f"Task has {len(links)} modern links")
            elif legacy_link and isinstance(legacy_link, str) and legacy_link.strip():
                has_links = True
                debug.debug(f"Task has legacy link: {legacy_link}")
            
            if files and isinstance(files, list) and len(files) > 0:
                has_files = True
                debug.debug(f"Task has {len(files)} files")

        debug.debug(f"has_links={has_links} (type: {type(has_links)}), has_files={has_files} (type: {type(has_files)})")
        
        # Add link action (enabled/disabled based on availability)
        open_links_action = menu.addAction("Open all links in new browser window")
        open_links_action.setEnabled(has_links)
        
        # Add file location action (enabled/disabled based on availability)
        open_file_locations_action = menu.addAction("Open all file locations")
        open_file_locations_action.setEnabled(has_files)
        
        # Add separator
        menu.addSeparator()
        
        # NEW: Add quick complete action
        mark_complete_action = menu.addAction("Mark task as complete")
        # Disable if already completed
        current_status = task_data.get('status', '') if isinstance(task_data, dict) else ''
        mark_complete_action.setEnabled(current_status != "Completed")
        
        # Add separator
        menu.addSeparator()
        
        # Import database manager
        from database.memory_db_manager import get_memory_db_manager
        db_manager = get_memory_db_manager()
        
        # Existing status change submenu
        status_menu = QMenu("Change Status", menu)
        status_menu.setStyleSheet(menu.styleSheet())
        menu.addMenu(status_menu)
        
        # Get statuses from database in display order
        debug.debug("Getting statuses from database")
        result = db_manager.execute_query(
            "SELECT name FROM statuses ORDER BY display_order"
        )
        
        statuses = [row[0] for row in result]
        debug.debug(f"Adding {len(statuses)} status options to menu")
        status_actions = {}
        
        for status in statuses:
            action = status_menu.addAction(status)
            status_actions[action] = status
        
        # Existing priority change submenu
        priority_menu = QMenu("Change Priority", menu)
        priority_menu.setStyleSheet(menu.styleSheet())
        menu.addMenu(priority_menu)
        
        # Get priorities from database
        debug.debug("Getting priorities from database")
        results = db_manager.execute_query(
            "SELECT name FROM priorities ORDER BY display_order"
        )
        priorities = [row[0] for row in results]
        debug.debug(f"Adding {len(priorities)} priority options to menu")
        priority_actions = {}
        
        for priority in priorities:
            action = priority_menu.addAction(priority)
            priority_actions[action] = priority
        
        # NEW: Add category change submenu
        category_menu = QMenu("Change Category", menu)
        category_menu.setStyleSheet(menu.styleSheet())
        menu.addMenu(category_menu)
        
        # Get categories from database
        debug.debug("Getting categories from database")
        category_results = db_manager.execute_query(
            "SELECT name FROM categories ORDER BY name"
        )
        categories = [row[0] for row in category_results]
        debug.debug(f"Adding {len(categories)} category options to menu")
        category_actions = {}
        
        # Add "None" option first
        none_category_action = category_menu.addAction("None")
        category_actions[none_category_action] = None
        
        # Add separator if there are categories
        if categories:
            category_menu.addSeparator()
        
        # Add all categories
        for category in categories:
            action = category_menu.addAction(category)
            category_actions[action] = category
        
        # NEW: Add separator before expand/collapse options
        menu.addSeparator()
        
        # NEW: Add Expand All and Collapse All options
        expand_all_action = menu.addAction("Expand All")
        collapse_all_action = menu.addAction("Collapse All")
        
        # Execute menu and handle action
        debug.debug("Showing context menu")
        action = menu.exec(self.mapToGlobal(position))
        
        # Handle actions
        if action == edit_action:
            debug.debug(f"Edit action selected for item: {item.text(0)}")
            self.edit_task(item)
        elif action == delete_action:
            debug.debug(f"Delete action selected for item: {item.text(0)}")
            self.delete_task(item)
        elif action == new_child_action:
            debug.debug(f"New child task action selected for item: {item.text(0)}")
            self.create_child_task(item)
        elif action == new_sibling_action:
            debug.debug(f"New sibling task action selected for item: {item.text(0)}")
            self.create_sibling_task(item)
        elif action == open_links_action:
            debug.debug(f"Open all links action selected for item: {item.text(0)}")
            self.open_all_task_links(item)
        elif action == open_file_locations_action:
            debug.debug(f"Open all file locations action selected for item: {item.text(0)}")
            self.open_all_task_file_locations(item)
        elif action == mark_complete_action:
            debug.debug(f"Mark complete action selected for item: {item.text(0)}")
            if hasattr(self, 'change_status_with_timestamp'):
                self.change_status_with_timestamp(item, "Completed")
            else:
                self.change_status(item, "Completed")
        elif action == expand_all_action:
            debug.debug("Expand all action selected")
            self.expand_all_items()
        elif action == collapse_all_action:
            debug.debug("Collapse all action selected")
            self.collapse_all_items()
        elif action in status_actions:
            new_status = status_actions[action]
            debug.debug(f"Status change selected: {new_status} for item: {item.text(0)}")
            if hasattr(self, 'change_status_with_timestamp'):
                self.change_status_with_timestamp(item, new_status)
            else:
                self.change_status(item, new_status)
        elif action in priority_actions:
            new_priority = priority_actions[action]
            debug.debug(f"Priority change selected: {new_priority} for item: {item.text(0)}")
            self.change_priority(item, new_priority)
        elif action in category_actions:
            new_category = category_actions[action]
            debug.debug(f"Category change selected: {new_category} for item: {item.text(0)}")
            self.change_category(item, new_category)
        else:
            debug.debug("No action selected or menu canceled")

    @debug_method
    def create_child_task(self, parent_item):
        """Create a new task as a child of the selected task"""
        debug.debug(f"Creating child task for parent: {parent_item.text(0)}")
        
        # Get parent task data
        parent_data = parent_item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(parent_data, dict) or 'id' not in parent_data:
            debug.error("Parent item doesn't have valid task data")
            return
        
        parent_id = parent_data['id']
        parent_priority = parent_data.get('priority', 'Medium')
        parent_category = parent_data.get('category', '')
        
        debug.debug(f"Parent task ID: {parent_id}, priority: {parent_priority}")
        
        # Open add task dialog
        from ui.task_dialogs import AddTaskDialog
        dialog = AddTaskDialog(self)
        
        # Set the parent
        for i in range(dialog.parent_combo.count()):
            if dialog.parent_combo.itemData(i) == parent_id:
                dialog.parent_combo.setCurrentIndex(i)
                debug.debug(f"Set parent combo to index {i}")
                break
        
        # Set priority to match parent
        priority_index = dialog.priority_combo.findText(parent_priority)
        if priority_index >= 0:
            dialog.priority_combo.setCurrentIndex(priority_index)
            debug.debug(f"Set priority to match parent: {parent_priority}")
        
        # Set category to match parent if available
        if parent_category:
            category_index = dialog.category_combo.findText(parent_category)
            if category_index >= 0:
                dialog.category_combo.setCurrentIndex(category_index)
                debug.debug(f"Set category to match parent: {parent_category}")
        
        if dialog.exec():
            debug.debug("Child task dialog accepted")
            data = dialog.get_data()
            
            # Ensure parent_id is set correctly
            data['parent_id'] = parent_id
            
            # Add the task
            task_id = self.add_new_task(data)
            if task_id:
                debug.debug(f"Added child task with ID: {task_id}")
                # Reload to reflect changes
                self._reload_all_tabs()

    @debug_method
    def create_sibling_task(self, sibling_item):
        """Create a new task under the same priority header as the selected task"""
        debug.debug(f"Creating sibling task for: {sibling_item.text(0)}")
        
        # Get sibling task data
        sibling_data = sibling_item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(sibling_data, dict):
            debug.error("Sibling item doesn't have valid task data")
            return
        
        sibling_priority = sibling_data.get('priority', 'Medium')
        debug.debug(f"Sibling priority: {sibling_priority}")
        
        # Open add task dialog
        from ui.task_dialogs import AddTaskDialog
        dialog = AddTaskDialog(self)
        
        # Set priority to match sibling (this determines which header it goes under)
        priority_index = dialog.priority_combo.findText(sibling_priority)
        if priority_index >= 0:
            dialog.priority_combo.setCurrentIndex(priority_index)
            debug.debug(f"Set priority to match sibling: {sibling_priority}")
        
        # Leave parent as "None" so it's a root-level task under the header
        dialog.parent_combo.setCurrentIndex(0)  # "None" is always first
        
        if dialog.exec():
            debug.debug("Sibling task dialog accepted")
            data = dialog.get_data()
            
            # Ensure it's a root-level task with the correct priority
            data['parent_id'] = None
            data['priority'] = sibling_priority
            
            # Add the task
            task_id = self.add_new_task(data)
            if task_id:
                debug.debug(f"Added sibling task with ID: {task_id}")
                # Reload to reflect changes
                self._reload_all_tabs()

    @debug_method
    def open_all_task_links(self, item):
        """Open all links for a task in new browser window"""
        debug.debug(f"Opening all links for task: {item.text(0)}")
        
        # Get task data
        task_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(task_data, dict):
            debug.error("Task item doesn't have valid data")
            return
        
        # Get links
        links = task_data.get('links', [])
        legacy_link = task_data.get('link', '')
        
        # Convert legacy link if it exists and no modern links
        if not links and legacy_link and legacy_link.strip():
            links = [(None, legacy_link, None)]
            debug.debug(f"Using legacy link: {legacy_link}")
        
        if not links:
            debug.debug("No links found to open")
            return
        
        # Use existing method from task tree
        self.open_links_in_new_window(links)

    @debug_method
    def open_all_task_file_locations(self, item):
        """Open file explorer windows for all files attached to a task"""
        debug.debug(f"Opening all file locations for task: {item.text(0)}")
        
        # Get task data
        task_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(task_data, dict):
            debug.error("Task item doesn't have valid data")
            return
        
        # Get files
        files = task_data.get('files', [])
        
        if not files:
            debug.debug("No files found to open locations for")
            return
        
        # Use existing method from task tree
        self.open_all_file_locations(files)

    @debug_method
    def change_category(self, item, new_category):
        """Change the category of a task"""
        debug.debug(f"Changing category to: {new_category}")
        try:
            # Import database manager
            from database.memory_db_manager import get_memory_db_manager
            db_manager = get_memory_db_manager()
            
            # Get category ID if not None
            category_id = None
            if new_category:
                debug.debug(f"Looking up category ID for: {new_category}")
                result = db_manager.execute_query(
                    "SELECT id FROM categories WHERE name = ?", 
                    (new_category,)
                )
                if result and len(result) > 0:
                    category_id = result[0][0]
                    debug.debug(f"Found category ID: {category_id}")
            
            # Update database
            debug.debug(f"Updating task {item.task_id} with category_id: {category_id}")
            db_manager.execute_update(
                "UPDATE tasks SET category_id = ? WHERE id = ?", 
                (category_id, item.task_id)
            )
            
            # Update item data
            data = item.data(0, Qt.ItemDataRole.UserRole)
            data['category'] = new_category
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            debug.debug("Updated category in item data")
            
            # Force a repaint
            debug.debug("Forcing viewport update")
            self.viewport().update()
            
            # Reload tabs to reflect changes
            debug.debug("Scheduling reload of all tabs")
            self._reload_all_tabs()
            
        except Exception as e:
            debug.error(f"Error changing task category: {e}")
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to change task category: {str(e)}")
    
    def synchronize_priority_headers(self):
        """Ensure all priority headers have visual states matching their logical states"""
        debug.debug("Synchronizing priority headers")
        
        # Get expanded priorities from settings
        settings = self.get_settings_manager()
        expanded_priorities = settings.get_setting("expanded_priorities", [])
        debug.debug(f"Expanded priorities from settings: {expanded_priorities}")
        
        # Go through all top-level items
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            
            if isinstance(data, dict) and data.get('is_priority_header', False):
                priority = data.get('priority')
                should_be_expanded = priority in expanded_priorities
                
                # Update data to match setting
                data['expanded'] = should_be_expanded
                item.setData(0, Qt.ItemDataRole.UserRole, data)
                
                # Directly set visual state
                if should_be_expanded:
                    self.expandItem(item)
                    debug.debug(f"Expanded header: {priority}")
                else:
                    self.collapseItem(item)
                    debug.debug(f"Collapsed header: {priority}")
        
        # Force layout update
        debug.debug("Scheduling delayed layout")
        self.scheduleDelayedItemsLayout()
        debug.debug("Forcing viewport update")
        self.viewport().update()

    def toggle_priority_header(self, header_item):
        """Directly toggle a priority header item with improved visual state control"""
        debug.debug(f"Toggling priority header: {header_item.text(0)}")
        
        # Get current data
        data = header_item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict):
            debug.warning("Priority header doesn't have proper data")
            return
        
        # Get current expanded state
        expanded = data.get('expanded', True)
        debug.debug(f"Current expanded state: {expanded}")
        
        # Toggle state and update tree with a slight delay to ensure visual update
        if expanded:
            # Force a collapse
            debug.debug(f"Collapsing priority header: {header_item.text(0)}")
            self.collapseItem(header_item)
            # Update data
            data['expanded'] = False
            header_item.setData(0, Qt.ItemDataRole.UserRole, data)
        else:
            # Force an expand
            debug.debug(f"Expanding priority header: {header_item.text(0)}")
            self.expandItem(header_item)
            # Update data
            data['expanded'] = True
            header_item.setData(0, Qt.ItemDataRole.UserRole, data)
        
        # Save expanded states to settings
        debug.debug("Saving expanded states to settings")
        self._save_priority_expanded_states()
        
        # Force a complete layout update
        debug.debug("Scheduling delayed layout")
        self.scheduleDelayedItemsLayout()
        debug.debug("Forcing viewport update")
        self.viewport().update()

    def toggle_view_mode(self):
        """Toggle between compact and full view for all tasks"""
        debug.debug("Toggling view mode for all visible tasks")
        delegate = self.itemDelegate()
        if hasattr(delegate, 'compact_items'):
            # Get all visible items
            items = []
            for i in range(self.topLevelItemCount()):
                items.append(self.topLevelItem(i))
                self._collect_child_items(self.topLevelItem(i), items)
            debug.debug(f"Found {len(items)} items to process")
            
            # If any items are in normal view, collapse all. Otherwise, expand all
            any_normal = False
            for item in items:
                user_data = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(user_data, dict) and 'id' in user_data:
                    if user_data['id'] not in delegate.compact_items:
                        any_normal = True
                        debug.debug(f"Found normal (non-compact) item: {user_data.get('id')}")
                        break
            
            # Toggle all items
            debug.debug(f"Any normal items found: {any_normal}, toggling accordingly")
            changes_count = 0
            for item in items:
                user_data = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(user_data, dict) and 'id' in user_data:
                    item_id = user_data['id']
                    if any_normal:  # Make all compact
                        delegate.compact_items.add(item_id)
                        debug.debug(f"Setting item {item_id} to compact")
                    else:  # Make all normal
                        if item_id in delegate.compact_items:
                            delegate.compact_items.remove(item_id)
                            debug.debug(f"Setting item {item_id} to normal")
                    
                    # Update item size
                    height = delegate.compact_height if item_id in delegate.compact_items else delegate.pill_height
                    item.setSizeHint(0, QSize(self.viewport().width(), height + delegate.item_margin * 2))
                    changes_count += 1
            
            debug.debug(f"Changed {changes_count} items")
            
            # Force layout update
            debug.debug("Scheduling delayed layout")
            self.scheduleDelayedItemsLayout()
            debug.debug("Forcing viewport update")
            self.viewport().update()   

    def _handle_drop_on_header(self, item, header):
        """Handle dropping a task onto a priority header"""
        debug.debug(f"Handling drop of task onto priority header")
        try:
            from database.memory_db_manager import get_memory_db_manager
            db_manager = get_memory_db_manager()
            
            # Get the priority from the header
            header_data = header.data(0, Qt.ItemDataRole.UserRole)
            priority = header_data.get('priority')
            
            if not priority:
                debug.error("Priority header has no priority value")
                return
                
            debug.debug(f"Moving task to priority: {priority}")
            
            # Get the current task status to preserve it
            task_data = item.data(0, Qt.ItemDataRole.UserRole)
            current_status = task_data.get('status', 'Not Started')
            
            # Remove the item from its current parent
            old_parent = item.parent()
            if old_parent:
                debug.debug("Removing item from old parent")
                index = old_parent.indexOfChild(item)
                old_parent.removeChild(item)
            else:
                debug.debug("Removing item from top level")
                index = self.indexOfTopLevelItem(item)
                if index >= 0:
                    self.takeTopLevelItem(index)
            
            # Add the item to the priority header
            debug.debug(f"Adding item to priority header: {priority}")
            header.addChild(item)
            
            # Update item data
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            item_data['priority'] = priority
            item.setData(0, Qt.ItemDataRole.UserRole, item_data)
            
            # Update database records - ensure status is preserved
            debug.debug(f"Updating database for task {item.task_id}")
            db_manager.execute_update(
                "UPDATE tasks SET priority = ?, parent_id = NULL WHERE id = ?",
                (priority, item.task_id)
            )
            
            debug.debug(f"Task moved to priority header: {priority}")
            
            # Update display orders
            debug.debug("Updating display orders")
            self._update_display_orders(header)
            
            # Force a reload of all tabs to reflect the change
            debug.debug("Requesting reload of all tabs")
            self._reload_all_tabs()
            
        except Exception as e:
            debug.error(f"Error in _handle_drop_on_header: {e}")
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to update task: {str(e)}")
                
    def _handle_drop_on_task(self, event, item, target_task):
        """Handle dropping a task onto another task or empty area"""
        debug.debug(f"Handling drop of task onto another task")
        try:
            # Save the expanded state of all items before the drop
            expanded_items = self._save_expanded_states()
            debug.debug(f"Saved expanded states for {len(expanded_items)} items")
            
            # Let the standard QTreeWidget implementation handle the visual aspects
            debug.debug("Using standard drop handling first")
            super().dropEvent(event)
            
            from database.memory_db_manager import get_memory_db_manager
            db_manager = get_memory_db_manager()
            
            # Get the new parent after the standard drop
            new_parent = item.parent()
            
            # Determine parent_id for database update
            parent_id = None
            if new_parent and hasattr(new_parent, 'task_id'):
                parent_id = new_parent.task_id
                debug.debug(f"Setting parent_id to: {parent_id}")
            else:
                debug.debug(f"Setting parent_id to None (top-level item)")
            
            # Update the database
            debug.debug(f"Updating database for task {item.task_id}")
            db_manager.execute_update(
                "UPDATE tasks SET parent_id = ? WHERE id = ?", 
                (parent_id, item.task_id)
            )
            
            # If the item was added to a parent, update display orders
            if new_parent:
                debug.debug(f"Updating display orders for new parent")
                self._update_display_orders(new_parent)
            
            # Recursively update all children
            debug.debug("Updating children hierarchy")
            self._update_children_hierarchy(item)
            self._restore_expanded_states(expanded_items)
            debug.debug(f"Restored expanded states for {len(expanded_items)} items")
            
            # Force a reload of all tabs to reflect the change
            debug.debug("Requesting reload of all tabs")
            self._reload_all_tabs()
            
        except Exception as e:
            debug.error(f"Error in _handle_drop_on_task: {e}")
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to update task hierarchy: {str(e)}")

    @debug_method
    def _save_expanded_states(self):
        """Save expanded states of all items with improved task hierarchy tracking"""
        debug.debug("Saving expanded states of all items")
        expanded_items = []
        
        # First collect all items
        all_items = []
        for i in range(self.topLevelItemCount()):
            top_item = self.topLevelItem(i)
            all_items.append(top_item)
            self._collect_child_items(top_item, all_items)
            
        debug.debug(f"Collected {len(all_items)} total items")
        print(f"Collected {len(all_items)} total items")
        
        # Count items with children
        items_with_children = [item for item in all_items if item.childCount() > 0]
        debug.debug(f"Found {len(items_with_children)} items with children")
        print(f"Found {len(items_with_children)} items with children")
        
        # Now check expanded state for each item
        for item in all_items:
            index = self.indexFromItem(item)
            
            # Skip invalid items
            if not index.isValid():
                continue
                
            if self.isExpanded(index):
                # Get the item's data dictionary
                data = item.data(0, Qt.ItemDataRole.UserRole)
                
                # For priority headers
                if isinstance(data, dict) and data.get('is_priority_header', False):
                    priority = data.get('priority', 'Unknown')
                    expanded_items.append(f"priority:{priority}")
                    debug.debug(f"Saved expanded state for priority header: {priority}")
                    print(f"Saved expanded state for priority header: {priority}")
                
                # For regular task items with children
                elif hasattr(item, 'task_id') and item.childCount() > 0:
                    # Only save items that actually have children
                    expanded_items.append(f"task:{item.task_id}")
                    debug.debug(f"Saved expanded state for task: {item.task_id} '{item.text(0)}'")
                    print(f"Saved expanded state for task: {item.task_id} '{item.text(0)}'")
        
        # Store in settings
        settings = self.get_settings_manager()
        settings.set_setting("expanded_task_states", expanded_items)
        debug.debug(f"Saved {len(expanded_items)} expanded states to settings")
        print(f"Saved {len(expanded_items)} expanded states to settings")
                
        # Also store in tab-specific setting
        parent = self.parent()
        while parent and not hasattr(parent, 'main_window'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'main_window'):
            
            # Get the tab widget
            tabs = parent.main_window.tabs
            for i in range(tabs.count()):
                tab = tabs.widget(i)
                if hasattr(tab, 'task_tree') and tab.task_tree == self:
                    tab_key = f"expanded_states_tab_{i}"
                    settings.set_setting(tab_key, expanded_items)
                    debug.debug(f"Saved expanded states to tab-specific key: {tab_key}")
                    break
        
        return expanded_items

    @debug_method
    def _restore_expanded_states(self, expanded_items=None):
        """Restore expanded states with improved persistence"""
        debug.debug("Restoring expanded states")
        
        # If expanded_items not provided, get from settings
        if expanded_items is None:
            settings = self.get_settings_manager()
            expanded_items = settings.get_setting("expanded_task_states", [])
            print('EXPANDED ITEMS:', expanded_items)
        
        # If no items to restore, just return
        if not expanded_items:
            debug.debug("No expanded states to restore")
            return 0
        
        debug.debug(f"Restoring {len(expanded_items)} expanded states")
        
        # Temporarily block signals to prevent interference
        original_state = self.signalsBlocked()
        self.blockSignals(True)
        
        try:
            # FIRST STEP: Collapse everything first
            debug.debug("First collapsing all items")
            for i in range(self.topLevelItemCount()):
                item = self.topLevelItem(i)
                self.collapseItem(item)
                
                # Recursively collapse all children
                self._collapse_children_recursive(item)
            
            # SECOND STEP: Now expand only specified items
            # Collect all items for restoration
            all_items = []
            for i in range(self.topLevelItemCount()):
                top_item = self.topLevelItem(i)
                all_items.append(top_item)
                self._collect_child_items(top_item, all_items)
            
            # First expand priority headers
            priority_headers_expanded = 0
            for item in all_items:
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(data, dict) and data.get('is_priority_header', False):
                    priority = data.get('priority', 'Unknown')
                    if f"priority:{priority}" in expanded_items:
                        debug.debug(f"Expanding priority header: {priority}")
                        self.expandItem(item)
                        # Also update the data state
                        data['expanded'] = True
                        item.setData(0, Qt.ItemDataRole.UserRole, data)
                        priority_headers_expanded += 1
            
            # Then expand task items
            task_items_expanded = 0
            for item in all_items:
                if hasattr(item, 'task_id') and item.childCount() > 0:
                    if f"task:{item.task_id}" in expanded_items:
                        debug.debug(f"Expanding task item: {item.task_id}")
                        self.expandItem(item)
                        task_items_expanded += 1
                        # Update the data state if possible
                        data = item.data(0, Qt.ItemDataRole.UserRole)
                        if isinstance(data, dict):
                            data['expanded'] = True
                            item.setData(0, Qt.ItemDataRole.UserRole, data)
            
            debug.debug(f"Successfully expanded {priority_headers_expanded} priority headers and {task_items_expanded} task items")
            return priority_headers_expanded + task_items_expanded
        finally:
            # Restore original signal blocking state
            self.blockSignals(original_state)
  
    @debug_method
    def _collapse_children_recursive(self, parent_item):
        """Helper method to collapse all children of an item recursively"""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            self.collapseItem(child)
            
            # Update the expanded state in the data if possible
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, dict):
                data['expanded'] = False
                child.setData(0, Qt.ItemDataRole.UserRole, data)
            
            # Process this child's children recursively
            if child.childCount() > 0:
                self._collapse_children_recursive(child)
                      
    @debug_method
    def _collapse_all_children(self, parent_item):
        """Recursively collapse all children and update their data state"""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            
            # Collapse the child
            self.collapseItem(child)
            
            # Update data state
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, dict) and 'id' in data:
                data['expanded'] = False
                child.setData(0, Qt.ItemDataRole.UserRole, data)
            
            # Recursively process grandchildren
            if child.childCount() > 0:
                self._collapse_all_children(child)
    
    def _reload_all_tabs(self):
        """Find the TaskTabWidget and reload all tabs"""
        debug.debug("Attempting to reload all tabs")
        try:
            parent = self.parent()
            while parent and not hasattr(parent, 'reload_all'):
                parent = parent.parent()
                
            if parent and hasattr(parent, 'reload_all'):
                # Use a short timer to let the current operation complete first
                debug.debug("Found parent with reload_all method, scheduling reload")
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(100, parent.reload_all)
            else:
                # Just refresh this tree using the proper load method
                debug.debug("Tab parent not found, refreshing current tree only")
                if hasattr(self, 'load_tasks_tab'):
                    # Use the specialized method with proper filtering if available
                    debug.debug("Using load_tasks_tab with filtering")
                    self.load_tasks_tab()
                else:
                    # Fall back to the base method which doesn't filter
                    print('DEBUG: Using load_tasks_tree without filtering, ', hasattr(self, 'load_tasks_tab'))
                    debug.debug("Using load_tasks_tree without filtering")
                    self.load_tasks_tree()
        except Exception as e:
            debug.error(f"Error reloading tabs: {e}")
            import traceback
            traceback.print_exc()

    def _update_children_hierarchy(self, parent_item):
        """Update all children's hierarchy in the database"""
        debug.debug(f"Updating hierarchy for children of: {parent_item.text(0)}")
        try:
            debug.debug(f"Parent has {parent_item.childCount()} children")
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                
                # Skip if not a task item
                if not hasattr(child, 'task_id'):
                    debug.debug("Child is not a task item, skipping")
                    continue
                    
                # Import database manager
                from database.database_manager import get_db_manager
                db_manager = get_db_manager()
                
                # Update child's parent_id
                parent_id = parent_item.task_id if hasattr(parent_item, 'task_id') else None
                debug.debug(f"Updating child task {child.task_id} with parent_id: {parent_id}")
                db_manager.execute_update(
                    """
                    UPDATE tasks 
                    SET parent_id = ?
                    WHERE id = ?
                    """, 
                    (parent_id, child.task_id)
                )
                
                # Recursively update all grandchildren
                debug.debug(f"Recursing for grandchildren of task {child.task_id}")
                self._update_children_hierarchy(child)
        except Exception as e:
            debug.error(f"Error updating child hierarchy: {e}")

    def _update_display_orders(self, parent_item):
        """Update display orders for all children of the parent item"""
        debug.debug(f"Updating display orders for children of: {parent_item.text(0)}")
        try:
            from database.memory_db_manager import get_memory_db_manager
            db_manager = get_memory_db_manager()
            
            # Determine parent_id for database query
            parent_id = None
            if hasattr(parent_item, 'task_id'):
                parent_id = parent_item.task_id
                debug.debug(f"Parent ID: {parent_id}")
            
            # Get all child items
            child_count = parent_item.childCount()
            debug.debug(f"Parent has {child_count} children")
            new_orders = []
            
            # Assign new display orders based on visual position
            for i in range(child_count):
                child = parent_item.child(i)
                if hasattr(child, 'task_id'):
                    new_orders.append((child.task_id, i+1))  # Display orders start at 1
                    debug.debug(f"Assigning order {i+1} to task {child.task_id}")
            
            # Update all display orders in one batch
            debug.debug(f"Updating {len(new_orders)} display orders in database")
            for task_id, order in new_orders:
                db_manager.execute_update(
                    "UPDATE tasks SET display_order = ? WHERE id = ?",
                    (order, task_id)
                )
                
            debug.debug(f"Updated display orders for {len(new_orders)} items")
            
        except Exception as e:
            debug.error(f"Error updating display orders: {e}")
            import traceback
            traceback.print_exc()

    def _find_item_by_id(self, item_id):
        """Find a task item by its ID"""
        debug.debug(f"Searching for item with ID: {item_id}")
        # Check all priority headers
        for i in range(self.topLevelItemCount()):
            header_item = self.topLevelItem(i)
            
            # Check all tasks in this priority
            for j in range(header_item.childCount()):
                task_item = header_item.child(j)
                
                # Check if this is the item we want
                task_data = task_item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(task_data, dict) and task_data.get('id') == item_id:
                    debug.debug(f"Found item in priority header")
                    return task_item
                
                # Recursively check children
                result = self._find_child_by_id(task_item, item_id)
                if result:
                    return result
        
        debug.debug(f"Item with ID {item_id} not found")
        return None

    def _find_child_by_id(self, parent_item, item_id):
        """Recursively search for a child item by ID"""
        for i in range(parent_item.childCount()):
            child_item = parent_item.child(i)
            
            # Check if this is the item we want
            child_data = child_item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(child_data, dict) and child_data.get('id') == item_id:
                debug.debug(f"Found child item with ID {item_id}")
                return child_item
            
            # Recursively check children
            result = self._find_child_by_id(child_item, item_id)
            if result:
                return result
        
        return None
    
    def _find_parent_and_add_child(self, parent_item, parent_id, new_item):
        """Helper method to recursively find a parent item and add a child to it"""
        # Check if this is the parent and has the task_id attribute
        if hasattr(parent_item, 'task_id') and parent_item.task_id == parent_id:
            debug.debug(f"Found parent item, adding child")
            parent_item.addChild(new_item)
            return True
        
        # Check all children
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if self._find_parent_and_add_child(child, parent_id, new_item):
                return True
        
        return False
    
    def _collect_child_items(self, parent_item, items_list):
        """Helper to collect all child items recursively"""
        debug.debug(f"Collecting child items from parent: {parent_item.text(0)}")
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            items_list.append(child)
            debug.debug(f"Added child: {child.text(0)}")
            self._collect_child_items(child, items_list)
    
    def _collect_child_tasks(self, parent_item, tasks_list):
        """Helper to collect all child task IDs recursively"""
        debug.debug(f"Collecting child task IDs from parent: {parent_item.text(0)}")
        # Create a temporary list to hold the items
        items = []
        # Use the existing method to collect all child items
        self._collect_child_items(parent_item, items)
        
        # Extract task_id from each item and add to the tasks_list
        for item in items:
            if hasattr(item, 'task_id'):
                tasks_list.append(item.task_id)
                debug.debug(f"Added task ID: {item.task_id}")

    def _debug_add_buttons_to_children(self, parent_item, delegate):
        """Helper for debug_toggle_buttons to add buttons to child items"""
        debug.debug(f"Adding toggle buttons to children of: {parent_item.text(0)}")
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            index = self.indexFromItem(child)
            delegate.show_toggle_button(self, index)
            debug.debug(f"Added toggle button to child: {child.text(0)}")
            # Recursively add to this child's children
            self._debug_add_buttons_to_children(child, delegate)
 
    def _save_priority_expanded_states(self):
        """Save the expanded state of priority headers to settings"""
        debug.debug("Saving priority expanded states to settings")
        try:
            expanded_priorities = []
            for i in range(self.topLevelItemCount()):
                top_item = self.topLevelItem(i)
                
                # Check if this is a priority header
                data = top_item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(data, dict) and data.get('is_priority_header', False):
                    # Convert item to index
                    top_item_index = self.indexFromItem(top_item)
                    
                    # Use the visual state to determine if expanded
                    if self.isExpanded(top_item_index):
                        priority = data.get('priority')
                        expanded_priorities.append(priority)
                        debug.debug(f"Priority header expanded: {priority}")
            
            # Save to settings
            settings = self.get_settings_manager()
            settings.set_setting("expanded_priorities", expanded_priorities)
            debug.debug(f"Saved expanded priorities: {expanded_priorities}")
        except Exception as e:
            debug.error(f"Error saving priority expanded states: {e}")

    @debug_method
    def expand_all_items(self):
        """Expand all items in the tree (priority headers and tasks with children)"""
        debug.debug("Expanding all items")
        try:
            # Block signals to prevent multiple save operations
            self.blockSignals(True)
            
            # Expand all top-level items and their children
            expanded_count = 0
            for i in range(self.topLevelItemCount()):
                item = self.topLevelItem(i)
                expanded_count += self._expand_item_recursively(item)
            
            # Save the expanded states
            self._save_expanded_states()
            
            # Also save priority expanded states if applicable
            if hasattr(self, '_save_priority_expanded_states'):
                self._save_priority_expanded_states()
            
            # Restore signals
            self.blockSignals(False)
            
            # Force viewport update
            self.viewport().update()
            
            debug.debug(f"Expanded {expanded_count} items successfully")
            
        except Exception as e:
            debug.error(f"Error expanding all items: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Ensure signals are restored even if there's an error
            self.blockSignals(False)

    @debug_method  
    def collapse_all_items(self):
        """Collapse all items in the tree (priority headers and tasks with children)"""
        debug.debug("Collapsing all items")
        try:
            # Block signals to prevent multiple save operations
            self.blockSignals(True)
            
            # Collapse all top-level items and their children
            collapsed_count = 0
            for i in range(self.topLevelItemCount()):
                item = self.topLevelItem(i)
                collapsed_count += self._collapse_item_recursively(item)
            
            # Save the expanded states (which should now be mostly empty)
            self._save_expanded_states()
            
            # Also save priority expanded states if applicable
            if hasattr(self, '_save_priority_expanded_states'):
                self._save_priority_expanded_states()
            
            # Restore signals
            self.blockSignals(False)
            
            # Force viewport update
            self.viewport().update()
            
            debug.debug(f"Collapsed {collapsed_count} items successfully")
            
        except Exception as e:
            debug.error(f"Error collapsing all items: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Ensure signals are restored even if there's an error
            self.blockSignals(False)

    @debug_method
    def _expand_item_recursively(self, item):
        """Recursively expand an item and all its children"""
        expanded_count = 0
        
        if item.childCount() > 0:
            # Expand this item
            self.expandItem(item)
            expanded_count += 1
            
            # Update the item's data to reflect expanded state
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, dict):
                data['expanded'] = True
                item.setData(0, Qt.ItemDataRole.UserRole, data)
            
            # Recursively expand all children
            for i in range(item.childCount()):
                child = item.child(i)
                expanded_count += self._expand_item_recursively(child)
        
        return expanded_count

    @debug_method
    def _collapse_item_recursively(self, item):
        """Recursively collapse an item and all its children"""
        collapsed_count = 0
        
        if item.childCount() > 0:
            # First collapse all children recursively
            for i in range(item.childCount()):
                child = item.child(i)
                collapsed_count += self._collapse_item_recursively(child)
            
            # Then collapse this item
            self.collapseItem(item)
            collapsed_count += 1
            
            # Update the item's data to reflect collapsed state
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, dict):
                data['expanded'] = False
                item.setData(0, Qt.ItemDataRole.UserRole, data)
        
        return collapsed_count  
class PriorityHeaderItem(QTreeWidgetItem):
    """Custom tree widget item for priority headers"""
    
    def __init__(self, priority_name, priority_color):
        debug.debug(f"Creating priority header item: {priority_name}")
        super().__init__()
        self.priority_name = priority_name
        self.priority_color = priority_color
        self.setText(0, priority_name.upper())
        
        # Add a flag to identify this as a priority header
        self.setData(0, Qt.ItemDataRole.UserRole, {
            'is_priority_header': True,
            'priority': priority_name,
            'color': priority_color,
            'expanded': True,  # Track expanded state
        })
        
        # Make it selectable to improve click behavior
        self.setFlags(self.flags() | Qt.ItemFlag.ItemIsSelectable)
        
        # Set the background color
        self.setBackground(0, QBrush(QColor(priority_color)))
        debug.debug(f"Set background color to: {priority_color}")
        
        # Use custom height
        self.setSizeHint(0, QSize(0, 25))
        debug.debug("Priority header item created")