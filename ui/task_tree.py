# src/ui/task_tree.py

from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QHeaderView, QMessageBox, QDateEdit
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

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent.parent))

# Now import directly from the database package
from database.memory_db_manager import get_memory_db_manager

# Import the debug logger
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
        self.setStyleSheet("""
            QTreeWidget {
                background-color: #f5f5f5;
                border: none;
                outline: none;
            }
            QTreeWidget::item {
                border: none;
                background-color: transparent;
            }
            QTreeWidget::item:selected {
                border: none;
                background-color: transparent;
            }
        """)
        
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
    
    def add_new_task(self, data):
        debug.debug(f"Adding new task: {data.get('title', 'No Title')}")
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

                # Verify links and files were saved
                cursor.execute("SELECT * FROM links WHERE task_id = ?", (new_id,))
                saved_links = cursor.fetchall()
                debug.debug(f"Verified {len(saved_links)} links were saved")
                
                cursor.execute("SELECT * FROM files WHERE task_id = ?", (new_id,))
                saved_files = cursor.fetchall()
                debug.debug(f"Verified {len(saved_files)} files were saved")
            
            # Add to tree UI
            debug.debug("Adding task to UI tree")
            new_item = self.add_task_item(
                new_id, 
                data.get('title', ''),
                data.get('description', ''),
                '',  # Empty legacy link placeholder
                data.get('status', 'Not Started'),
                data.get('priority', 'Medium'),
                data.get('due_date', ''),
                category_name,
                is_compact,  # Pass the is_compact value
                links=links,  # Pass links directly
                files=data.get('files', [])  # Pass files directly
            )
            
            priority = data.get('priority', 'Medium')
            
            # If it has a parent, add it to that parent
            if parent_id:
                debug.debug(f"Adding task to parent with ID: {parent_id}")
                # Find parent item and add as child
                parent_item = self._find_item_by_id(parent_id)
                if parent_item:
                    parent_item.addChild(new_item)
                    debug.debug("Added task to parent")
                else:
                    debug.error(f"Could not find parent with ID: {parent_id}")
            else:
                debug.debug(f"Adding top-level task with priority: {priority}")
                # Add to appropriate priority header
                for i in range(self.topLevelItemCount()):
                    top_item = self.topLevelItem(i)
                    top_data = top_item.data(0, Qt.ItemDataRole.UserRole)
                    if isinstance(top_data, dict) and top_data.get('is_priority_header', False):
                        if top_data.get('priority') == priority:
                            top_item.addChild(new_item)
                            debug.debug(f"Added task to priority header: {priority}")
                            break
            
            # Force a repaint
            debug.debug("Forcing viewport update")
            self.viewport().update()
            
            return new_id
        except Exception as e:
            debug.error(f"Error adding new task: {e}")
            import traceback
            traceback.print_exc()
            # Show error message to user
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Error", f"Failed to add task: {str(e)}")
            return None
        
    def change_status_with_timestamp(self, item, new_status):
        """Change status with timestamp tracking for Completed tasks"""
        debug.debug(f"Changing task status to: {new_status}")
        try:
            # Import database manager
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
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
            'files': files if files is not None else []
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

    def change_status(self, item, new_status):
        debug.debug(f"Changing status to: {new_status}")
        try:
            # Import database manager
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
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
                parent.reload_all()
                
        except Exception as e:
            debug.error(f"Error changing task status: {e}")
            QMessageBox.critical(self, "Error", f"Failed to change task status: {str(e)}")

    def change_priority(self, item, new_priority):
        debug.debug(f"Changing priority to: {new_priority}")
        try:
            # Update database
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
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
            parent = self.parent()
            while parent and not hasattr(parent, 'reload_all'):
                parent = parent.parent()
                
            if parent and hasattr(parent, 'reload_all'):
                # This is a TabTaskTreeWidget within a TaskTabWidget
                # Reload all tabs to reflect the priority change
                debug.debug("Requesting tab reload")
                parent.reload_all()
                
        except Exception as e:
            debug.error(f"Error changing task priority: {e}")
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
                from database.database_manager import get_db_manager
                db_manager = get_db_manager()
                
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
        else:
            debug.debug("User canceled task deletion")

    def dropEvent(self, event):
        """Handle drag and drop events for tasks and priority headers"""
        debug.debug("Processing drop event")
        item = self.currentItem()
        if not item:
            debug.debug("No current item, using standard drop handling")
            super().dropEvent(event)
            return
        
        debug.debug(f"Current item being dropped: {item.text(0)}")
        
        # Skip if item doesn't have a task ID (not a task)
        if not hasattr(item, 'task_id'):
            debug.debug("Item doesn't have task_id, using standard drop handling")
            super().dropEvent(event)
            return
        
        # Save the drop indicator position and prepare to determine drop target
        drop_indicator_pos = self.dropIndicatorPosition()
        drop_pos = event.position().toPoint()
        drop_index = self.indexAt(drop_pos)
        drop_target = self.itemFromIndex(drop_index) if drop_index.isValid() else None
        
        # Debug information
        debug.debug(f"Drop indicator position: {drop_indicator_pos}")
        debug.debug(f"Drop target: {drop_target.text(0) if drop_target else 'None'}")
        
        # Check if dropping on a priority header
        is_priority_header = False
        header_priority = None
        
        if drop_target:
            target_data = drop_target.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(target_data, dict) and target_data.get('is_priority_header', False):
                is_priority_header = True
                header_priority = target_data.get('priority')
                debug.debug(f"Drop target is a priority header with priority: {header_priority}")
        
        task_id = item.task_id
        old_priority = None
        old_parent_id = None
        
        # Get current data before any changes
        if hasattr(item, 'data'):
            user_data = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(user_data, dict):
                old_priority = user_data.get('priority')
                debug.debug(f"Task's current priority: {old_priority}")
        
        # Get original parent ID
        if item.parent() and hasattr(item.parent(), 'task_id'):
            old_parent_id = item.parent().task_id
            debug.debug(f"Task's current parent ID: {old_parent_id}")
        
        # Instead of letting Qt handle the visual drop, we'll update the database directly
        # and then reload the entire tree
        try:
            from database.memory_db_manager import get_memory_db_manager
            db_manager = get_memory_db_manager()
            
            if is_priority_header and header_priority:
                # Changing priority - dropped onto a priority header
                debug.debug(f"Changing task priority to: {header_priority}")
                
                # Update task priority in database
                db_manager.execute_update(
                    "UPDATE tasks SET priority = ?, parent_id = NULL WHERE id = ?",
                    (header_priority, task_id)
                )
                debug.debug(f"Task priority updated in database")
                
                # Update children's priorities as well
                child_task_ids = []
                self._collect_child_task_ids(item, child_task_ids)
                
                if child_task_ids:
                    debug.debug(f"Updating {len(child_task_ids)} children to priority: {header_priority}")
                    for child_id in child_task_ids:
                        db_manager.execute_update(
                            "UPDATE tasks SET priority = ? WHERE id = ?",
                            (header_priority, child_id)
                        )
                
                debug.debug(f"Updated priority for task and {len(child_task_ids)} children to: {header_priority}")
                
            else:
                # Standard parent-child handling
                debug.debug("Handling standard parent-child relationship")
                
                # Determine new parent from standard drop handling (simulate the drop)
                super().dropEvent(event)
                
                # Get the new parent after the standard drop
                new_parent = item.parent()
                
                # Determine parent_id for database update
                parent_id = None
                parent_priority = None
                
                if new_parent:
                    if hasattr(new_parent, 'task_id'):
                        parent_id = new_parent.task_id
                        
                        # Get parent's priority
                        parent_data = new_parent.data(0, Qt.ItemDataRole.UserRole)
                        if isinstance(parent_data, dict) and 'priority' in parent_data:
                            parent_priority = parent_data.get('priority')
                    
                    debug.debug(f"Setting parent_id to: {parent_id}, parent_priority: {parent_priority}")
                else:
                    debug.debug(f"Setting parent_id to None (top-level item)")
                
                # Update the database - reset parent_id
                db_manager.execute_update(
                    "UPDATE tasks SET parent_id = ? WHERE id = ?", 
                    (parent_id, task_id)
                )
                debug.debug(f"Updated task parent_id in database")
                
                # If parent has a different priority, update this task's priority
                if parent_priority and parent_priority != old_priority:
                    debug.debug(f"Parent has different priority, updating task priority to: {parent_priority}")
                    db_manager.execute_update(
                        "UPDATE tasks SET priority = ? WHERE id = ?",
                        (parent_priority, task_id)
                    )
                    
                    # Also update all children
                    child_task_ids = []
                    self._collect_child_task_ids(item, child_task_ids)
                    
                    if child_task_ids:
                        debug.debug(f"Updating {len(child_task_ids)} children to priority: {parent_priority}")
                        for child_id in child_task_ids:
                            db_manager.execute_update(
                                "UPDATE tasks SET priority = ? WHERE id = ?",
                                (parent_priority, child_id)
                            )
                    
                    debug.debug(f"Updated priority for task and {len(child_task_ids)} children to: {parent_priority}")
            
            # Reload the entire tree to ensure correct display
            debug.debug("Reloading tree...")
            self.load_tasks_tree()
            
            # Try to scroll to the task to make it visible
            self._scroll_to_task(task_id)
            
        except Exception as e:
            debug.error(f"Error in dropEvent: {e}")
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to update task: {str(e)}")

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
    
    def edit_task(self, item):
        debug.debug(f"Editing task: {item.text(0)}")
        from .task_dialogs import EditTaskDialog
        
        # Skip if not a task item
        if not hasattr(item, 'task_id'):
            debug.debug("Not a task item, skipping edit")
            return
            
        # Get current data from the item's user role data
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Get compact state from delegate
        delegate = self.itemDelegate()
        is_compact = False
        if isinstance(delegate, TaskPillDelegate):
            is_compact = item.task_id in delegate.compact_items
            debug.debug(f"Task compact state: {is_compact}")
        
        # Get links from the database
        debug.debug("Getting links from database")
        from database.memory_db_manager import get_memory_db_manager
        db_manager = get_memory_db_manager()
        links = db_manager.get_task_links(item.task_id)
        debug.debug(f"Found {len(links)} links")
        
        # Get files from the database
        debug.debug("Getting files from database")
        files = db_manager.get_task_files(item.task_id)
        debug.debug(f"Found {len(files)} files")
        
        # Determine the parent ID safely
        parent_id = None
        if item.parent():
            # Only use parent_id if the parent is a regular task item (not a priority header)
            if hasattr(item.parent(), 'task_id'):
                parent_id = item.parent().task_id
                debug.debug(f"Parent ID: {parent_id}")
            # If parent is a priority header, leave parent_id as None
            # BUT store the priority from the header
            elif isinstance(item.parent().data(0, Qt.ItemDataRole.UserRole), dict) and item.parent().data(0, Qt.ItemDataRole.UserRole).get('is_priority_header', False):
                header_data = item.parent().data(0, Qt.ItemDataRole.UserRole)
                # Make sure to use the priority from the header rather than the task's stored priority
                data['priority'] = header_data.get('priority', data['priority'])
                debug.debug(f"Parent is priority header: {data['priority']}")
        
        task_data = {
            'id': item.task_id,
            'title': data['title'],
            'description': data['description'],
            'links': links,       # Links structure
            'files': files,       # Files structure
            'status': data['status'],
            'priority': data['priority'],  # Now properly preserves the header's priority
            'due_date': data['due_date'],
            'category': data['category'],
            'parent_id': parent_id,
            'is_compact': is_compact
        }
        debug.debug(f"Created task data for edit dialog: {task_data}")
        
        # Open edit dialog
        debug.debug("Opening edit task dialog")
        dialog = EditTaskDialog(task_data, self)
        if dialog.exec():
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
                    if result and result[0]:
                        category_id = result[0][0]
                        debug.debug(f"Found category ID: {category_id}")
                
                # Update database
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
                
                # Update links
                # First, get existing links to identify which ones to remove
                debug.debug("Updating links")
                existing_links = db_manager.get_task_links(updated_data['id'])
                existing_ids = set(link_id for link_id, _, _ in existing_links if link_id is not None)
                
                # Get new links
                new_links = updated_data.get('links', [])
                new_link_ids = set(link_id for link_id, _, _ in new_links if link_id is not None)
                
                # Delete links that no longer exist
                links_to_delete = existing_ids - new_link_ids
                if links_to_delete:
                    debug.debug(f"Deleting {len(links_to_delete)} links that no longer exist")
                    for link_id in links_to_delete:
                        db_manager.delete_task_link(link_id)
                
                # Add or update links
                debug.debug(f"Adding or updating {len(new_links)} links")
                for i, (link_id, url, label) in enumerate(new_links):
                    if url and url.strip():
                        if link_id is None:
                            # New link - add it
                            debug.debug(f"Adding new link: {url}")
                            db_manager.add_task_link(updated_data['id'], url, label)
                        else:
                            # Existing link - update it
                            debug.debug(f"Updating existing link ID: {link_id}")
                            db_manager.update_task_link(link_id, url, label)
                            
                            # Also update its display order
                            db_manager.execute_update(
                                "UPDATE links SET display_order = ? WHERE id = ?",
                                (i, link_id)
                            )
                
                # Update files
                # First, get existing files to identify which ones to remove
                debug.debug("Updating files")
                existing_files = db_manager.get_task_files(updated_data['id'])
                existing_file_ids = set(file_id for file_id, _, _ in existing_files if file_id is not None)
                
                # Get new files
                new_files = updated_data.get('files', [])
                new_file_ids = set(file_id for file_id, _, _ in new_files if file_id is not None)
                
                # Delete files that no longer exist
                files_to_delete = existing_file_ids - new_file_ids
                if files_to_delete:
                    debug.debug(f"Deleting {len(files_to_delete)} files that no longer exist")
                    for file_id in files_to_delete:
                        db_manager.delete_task_file(file_id)
                
                # Add or update files
                debug.debug(f"Adding or updating {len(new_files)} files")
                for i, (file_id, file_path, file_name) in enumerate(new_files):
                    if file_path and file_path.strip():
                        if file_id is None:
                            # New file - add it
                            debug.debug(f"Adding new file: {file_path}")
                            db_manager.add_task_file(updated_data['id'], file_path, file_name)
                        else:
                            # Existing file - update it
                            debug.debug(f"Updating existing file ID: {file_id}")
                            db_manager.update_task_file(file_id, file_path, file_name)
                            
                            # Also update its display order
                            db_manager.execute_update(
                                "UPDATE files SET display_order = ? WHERE id = ?",
                                (i, file_id)
                            )
                
                # Check if status, category, or priority changed
                status_changed = task_data['status'] != updated_data['status']
                category_changed = task_data['category'] != updated_data['category']
                priority_changed = task_data['priority'] != updated_data['priority']
                debug.debug(f"Changes detected - status: {status_changed}, category: {category_changed}, priority: {priority_changed}")
                
                # Update item directly
                item.setText(0, updated_data['title'])
                
                # Update item data
                new_item_data = {
                    'id': updated_data['id'],
                    'title': updated_data['title'],
                    'description': updated_data['description'],
                    'links': new_links,  # Store new links structure
                    'files': new_files,  # Store new files structure
                    'status': updated_data['status'],
                    'priority': updated_data['priority'],
                    'due_date': updated_data['due_date'],
                    'category': updated_data['category']
                }
                item.setData(0, Qt.ItemDataRole.UserRole, new_item_data)
                debug.debug("Updated item data in UI")
                
                # Handle parent change if needed
                old_parent_id = task_data['parent_id']
                new_parent_id = updated_data['parent_id']
                
                if old_parent_id != new_parent_id:
                    debug.debug(f"Parent changed from {old_parent_id} to {new_parent_id}")
                    # Remove from old parent
                    old_parent = item.parent()
                    if old_parent:
                        debug.debug("Removing from old parent")
                        index = old_parent.indexOfChild(item)
                        old_parent.takeChild(index)
                    else:
                        debug.debug("Removing from top level")
                        index = self.indexOfTopLevelItem(item)
                        self.takeTopLevelItem(index)
                    
                    # Add to new parent
                    if new_parent_id:
                        debug.debug(f"Adding to new parent ID: {new_parent_id}")
                        # Find new parent and add as child
                        new_parent_found = False
                        for i in range(self.topLevelItemCount()):
                            top_item = self.topLevelItem(i)
                            if hasattr(top_item, 'task_id') and top_item.task_id == new_parent_id:
                                top_item.addChild(item)
                                new_parent_found = True
                                debug.debug("Added to new parent at top level")
                                break
                            # Search in children
                            if not new_parent_found:
                                self._find_parent_and_add_child(top_item, new_parent_id, item)
                    else:
                        # Move to top level
                        debug.debug("Adding as top-level item")
                        self.addTopLevelItem(item)
                
                # If category changed, update background color
                if task_data['category'] != updated_data['category']:
                    debug.debug("Category changed, updating background color")
                    if updated_data['category']:
                        result = db_manager.execute_query(
                            "SELECT color FROM categories WHERE name = ?", 
                            (updated_data['category'],)
                        )
                        if result and result[0]:
                            color = QColor(result[0][0])
                            item.setBackground(0, QBrush(color))
                            debug.debug(f"Set background color to: {result[0][0]}")
                    else:
                        # Remove background color
                        debug.debug("Removed background color")
                        item.setBackground(0, QBrush())
                
                # Force a repaint
                debug.debug("Forcing viewport update")
                self.viewport().update()
                
                # If status, category or priority changed, reload all tabs
                if status_changed or category_changed or priority_changed:
                    debug.debug("Status, category, or priority changed - reloading all tabs")
                    parent = self.parent()
                    while parent and not hasattr(parent, 'reload_all'):
                        parent = parent.parent()
                        
                    if parent and hasattr(parent, 'reload_all'):
                        # Use a short timer to let the current operation complete first
                        debug.debug("Scheduling reload of all tabs")
                        from PyQt6.QtCore import QTimer
                        QTimer.singleShot(100, parent.reload_all)
            
            except Exception as e:
                debug.error(f"Error updating task: {e}")
                import traceback
                traceback.print_exc()
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"Failed to update task: {str(e)}")
                                
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

    def load_tasks_tree(self):
        debug.debug("Loading tasks tree")
        try:
            self.clear()
            
            # Import database manager
            from database.memory_db_manager import get_memory_db_manager
            db_manager = get_memory_db_manager()
            
            # Debug check - verify links and files tables exist and have data
            try:
                debug.debug("Checking links table")
                all_links = db_manager.execute_query("SELECT * FROM links")
                debug.debug(f"Found {len(all_links)} links in database")
                
                debug.debug("Checking files table")
                all_files = db_manager.execute_query("SELECT * FROM files")
                debug.debug(f"Found {len(all_files)} files in database")
            except Exception as e:
                debug.error(f"Error checking links/files tables: {e}")
        
            # Get priority order map and colors
            debug.debug("Loading priorities")
            priority_order = {}
            priority_colors = {}
            result = db_manager.execute_query(
                "SELECT name, display_order, color FROM priorities ORDER BY display_order"
            )
            for name, order, color in result:
                priority_order[name] = order
                priority_colors[name] = color
            debug.debug(f"Loaded {len(priority_colors)} priorities")
            
            # Create headers for each priority
            debug.debug("Creating priority headers")
            priority_headers = {}
            for priority, color in priority_colors.items():
                header_item = PriorityHeaderItem(priority, color)
                self.addTopLevelItem(header_item)
                priority_headers[priority] = header_item
                debug.debug(f"Created header for priority: {priority}")
            
            # Check if is_compact column exists
            debug.debug("Checking is_compact column")
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT is_compact FROM tasks LIMIT 1")
                debug.debug("is_compact column exists")
            except sqlite3.OperationalError:
                # Column doesn't exist, need to add it
                debug.debug("is_compact column doesn't exist, adding it")
                cursor.execute("ALTER TABLE tasks ADD COLUMN is_compact INTEGER NOT NULL DEFAULT 0")
                conn.commit()
                debug.debug("Added is_compact column")
            
            # Get all tasks
            debug.debug("Querying all tasks")
            tasks = db_manager.execute_query(
                """
                SELECT t.id, t.title, t.description, '', t.status, t.priority, 
                    t.due_date, c.name, t.is_compact, t.parent_id
                FROM tasks t
                LEFT JOIN categories c ON t.category_id = c.id
                ORDER BY t.parent_id NULLS FIRST, t.display_order
                """
            )
            debug.debug(f"Found {len(tasks)} tasks")
            
            items = {}
            # First pass: create all items
            debug.debug("First pass: creating task items")
            for row in tasks:
                task_id = row[0]
                priority = row[5] or "Medium"  # Default to Medium if None
                
                # Load links for this task BEFORE creating the item
                debug.debug(f"Loading links for task {task_id}")
                task_links = []
                try:
                    task_links = db_manager.get_task_links(task_id)
                    debug.debug(f"Found {len(task_links)} links for task {task_id}")
                except Exception as e:
                    debug.error(f"Error loading links for task {task_id}: {e}")
                
                # Load files for this task BEFORE creating the item
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
                    row[0],  # task_id
                    row[1],  # title
                    row[2],  # description
                    row[3],  # link (legacy, empty)
                    row[4],  # status
                    row[5],  # priority
                    row[6],  # due_date
                    row[7],  # category
                    row[8],  # is_compact
                    links=task_links,  # Pass links as named parameter
                    files=task_files   # Pass files as named parameter
                )
                items[task_id] = item
                
                # Store parent info for second pass
                parent_id = row[9]  # Last element is parent_id
                if parent_id is None:
                    # This is a top-level task, add it to the priority header
                    debug.debug(f"Adding task {task_id} to priority header: {priority}")
                    priority_headers[priority].addChild(item)
                else:
                    # This is a child task, will be handled in second pass
                    debug.debug(f"Task {task_id} has parent_id {parent_id}, will be handled in second pass")
                    item.setData(0, Qt.ItemDataRole.UserRole + 1, parent_id)
            
            # Second pass: handle parent-child relationships for non-top-level tasks
            debug.debug("Second pass: handling parent-child relationships")
            for task_id, item in items.items():
                parent_id = item.data(0, Qt.ItemDataRole.UserRole + 1)
                if parent_id is not None and parent_id in items:
                    parent_item = items[parent_id]
                    parent_item.addChild(item)
                    debug.debug(f"Added task {task_id} as child of {parent_id}")
            
            # Instead of just setting the expanded state in the data, make sure to
            # synchronize the visual state with the stored state
            debug.debug("Synchronizing priority headers")
            self.synchronize_priority_headers()
            debug.debug("Tasks tree loaded successfully")
        
        except Exception as e:
            debug.error(f"Error loading tasks tree: {e}")
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Error", f"Failed to load tasks: {str(e)}")
            
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
            
    def show_context_menu(self, position):
        debug.debug("Showing context menu")
        item = self.itemAt(position)
        if not item:
            debug.debug("No item at position, skipping context menu")
            return
            
        debug.debug(f"Context menu for item: {item.text(0)}")
        menu = QMenu(self)
        edit_action = menu.addAction("Edit Task")
        delete_action = menu.addAction("Delete Task")
        
        # Add a separator
        menu.addSeparator()
        
        # Add status change submenu
        status_menu = menu.addMenu("Change Status")
        statuses = ['Not Started', 'In Progress', 'On Hold', 'Completed']
        status_actions = {}
        
        for status in statuses:
            action = status_menu.addAction(status)
            status_actions[action] = status
            debug.debug(f"Added status action: {status}")
        
        # Add priority change submenu with priorities from database
        priority_menu = menu.addMenu("Change Priority")
        priority_actions = {}
        
        try:
            # Import database manager
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            # Get priorities from database
            debug.debug("Getting priorities from database")
            results = db_manager.execute_query(
                "SELECT name FROM priorities ORDER BY display_order"
            )
            priorities = [row[0] for row in results]
            debug.debug(f"Found {len(priorities)} priorities")
            
            for priority in priorities:
                action = priority_menu.addAction(priority)
                priority_actions[action] = priority
                debug.debug(f"Added priority action: {priority}")
        except Exception as e:
            debug.error(f"Error loading priorities for context menu: {e}")
        
        debug.debug("Showing context menu")
        action = menu.exec(self.mapToGlobal(position))
        
        if action == edit_action:
            debug.debug("Edit action selected")
            self.edit_task(item)
        elif action == delete_action:
            debug.debug("Delete action selected")
            self.delete_task(item)
        elif action in status_actions:
            debug.debug(f"Status change selected: {status_actions[action]}")
            self.change_status(item, status_actions[action])
        elif action in priority_actions:
            debug.debug(f"Priority change selected: {priority_actions[action]}")
            self.change_priority(item, priority_actions[action])
        else:
            debug.debug("No action selected or menu canceled")

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
            
            # Update database records
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
            
            # Force a reload of all tabs to reflect the change
            debug.debug("Requesting reload of all tabs")
            self._reload_all_tabs()
            
        except Exception as e:
            debug.error(f"Error in _handle_drop_on_task: {e}")
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to update task hierarchy: {str(e)}")

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
                # Just refresh this tree
                debug.debug("Tab parent not found, refreshing current tree only")
                self.load_tasks_tree()
        except Exception as e:
            debug.error(f"Error reloading tabs: {e}")

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
        # Check if this is the parent
        if parent_item.task_id == parent_id:
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