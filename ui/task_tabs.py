# src/ui/task_tabs.py

# Import the debug utilities
from utils.debug_logger import get_debug_logger
from utils.debug_decorator import debug_method

# Initialize the debugger
debug = get_debug_logger()
debug.debug("Loading task_tabs.py module")

from PyQt6.QtWidgets import (QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QMessageBox, QMenu)
from PyQt6.QtCore import Qt, QSize, QTimer
from .task_tree import TaskTreeWidget, PriorityHeaderItem
from datetime import datetime
import sys
from pathlib import Path
import time
import traceback

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent.parent))

# Now import directly from the database package
from database.memory_db_manager import get_memory_db_manager
from ui.bee_todos import BeeToDoWidget

class TabTaskTreeWidget(TaskTreeWidget):
    """Specialized TaskTreeWidget that can be configured for specific views"""
    
    @debug_method
    def __init__(self, filter_type="current"):
        debug.debug(f"Initializing TabTaskTreeWidget with filter_type={filter_type}")
        super().__init__()
        self.filter_type = filter_type
        self.use_priority_headers = filter_type == "current"
        debug.debug(f"Priority headers enabled: {self.use_priority_headers}")
        
        # Ensure tree structure is visible for all tabs
        self.setRootIsDecorated(True)
        self.setIndentation(40)  # Ensure consistent indentation
        debug.debug(f"Set root decoration: True, indentation: 40")
        
        # Defer loading tasks to avoid initialization order issues
        # This allows subclasses to fully initialize before loading tasks
        from PyQt6.QtCore import QTimer
        debug.debug(f"Scheduling deferred load for {filter_type} tab")
        QTimer.singleShot(0, self._init_load_tasks_tab)
        
        # Debug delegate setup
        debug.debug("Calling debug_delegate_setup")
        self.debug_delegate_setup()
        debug.debug("TabTaskTreeWidget initialization complete")
        
    @debug_method
    def _init_load_tasks_tab(self):
        """Deferred task loading to handle initialization order"""
        try:
            debug.debug("Executing deferred load_tasks_tab")
            self.load_tasks_tab()
            
            # After loading, restore expanded states
            debug.debug("Restoring expanded states after initial load")
            self._restore_expanded_states()
        except Exception as e:
            debug.error(f"Error during deferred task loading: {e}")
            debug.error(traceback.format_exc())
    
    @debug_method
    def load_tasks_tab(self):
        """Load tasks with tab-specific filtering and fetch links from database"""
        start_time = time.time()
        try:
            debug.debug(f"Loading tasks for tab type: {self.filter_type}")
            self.clear()
            
            # Import database manager
            from database.memory_db_manager import get_memory_db_manager
            db_manager = get_memory_db_manager()
            
            # First check if completed_at column exists
            debug.debug("Checking database schema for completed_at column")
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(tasks)")
                columns = [info[1] for info in cursor.fetchall()]
                has_completed_at = 'completed_at' in columns
                debug.debug(f"Has completed_at column: {has_completed_at}")
            
            # Create query based on whether completed_at exists
            completed_at_field = ", t.completed_at" if has_completed_at else ""
            debug.debug(f"Completed_at field in query: {completed_at_field}")
            
            # Apply different loading logic based on filter type
            if self.filter_type == "current":
                debug.debug("Building query for CURRENT tasks")
                # For current tab - filter tasks that are not Backlog or Completed
                query = f"""
                    SELECT t.id, t.title, t.description, '', t.status, t.priority, 
                        t.due_date, c.name, t.is_compact, t.parent_id{completed_at_field}
                    FROM tasks t
                    LEFT JOIN categories c ON t.category_id = c.id
                    WHERE t.status != 'Backlog' AND t.status != 'Completed'
                    ORDER BY t.parent_id NULLS FIRST, t.display_order
                    """
                debug.debug(f"Executing current tasks query: {query.strip()}")
                tasks = db_manager.execute_query(query)
                debug.debug(f"Query returned {len(tasks)} current tasks")
                
                # Process tasks with proper link loading
                debug.debug("Processing current tasks with priority headers")
                self._process_tasks_with_links(tasks, use_priority_headers=True)
                
            elif self.filter_type in ["backlog", "completed"]:
                debug.debug(f"Building query for {self.filter_type.upper()} tasks")
                # For backlog and completed tabs - simplified list without priority headers
                status_name = "Backlog" if self.filter_type == "backlog" else "Completed"
                debug.debug(f"Status name filter: {status_name}")
                
                # Get all tasks with the specific status
                order_by = "t.display_order"
                if has_completed_at and self.filter_type == "completed":
                    order_by = "t.completed_at DESC"
                debug.debug(f"Order by clause: {order_by}")
                    
                query = f"""
                    SELECT t.id, t.title, t.description, '', t.status, t.priority, 
                        t.due_date, c.name, t.is_compact, t.parent_id{completed_at_field}
                    FROM tasks t
                    LEFT JOIN categories c ON t.category_id = c.id
                    WHERE t.status = ?
                    ORDER BY t.parent_id NULLS FIRST, {order_by}
                    """
                debug.debug(f"Executing {self.filter_type} query with param: {status_name}")
                tasks = db_manager.execute_query(query, (status_name,))
                debug.debug(f"Query returned {len(tasks)} {self.filter_type} tasks")
                
                # Process tasks with proper link loading
                debug.debug(f"Processing {self.filter_type} tasks without priority headers")
                self._process_tasks_with_links(tasks, use_priority_headers=False)
            
            end_time = time.time()
            debug.debug(f"Load tasks tab completed in {end_time - start_time:.3f} seconds")
        
        except Exception as e:
            debug.error(f"Error loading tasks for {self.filter_type} tab: {e}")
            debug.error(traceback.format_exc())
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Error", f"Failed to load {self.filter_type} tasks: {str(e)}")

    @debug_method
    def _process_tasks_with_links(self, tasks, use_priority_headers=True):
        """Process tasks and load links and files for each task"""
        start_time = time.time()
        try:
            debug.debug(f"Processing {len(tasks)} tasks with links, use_priority_headers={use_priority_headers}")
            
            # Import database manager
            from database.memory_db_manager import get_memory_db_manager
            db_manager = get_memory_db_manager()
            
            if use_priority_headers:
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
                
                # Restore expanded state from settings
                debug.debug("Restoring expanded states from settings")
                settings = self.get_settings_manager()
                all_priorities = list(priority_colors.keys())
                expanded_priorities = settings.get_setting("expanded_priorities", all_priorities)
                debug.debug(f"Expanded priorities from settings: {expanded_priorities}")
                
                for priority, header_item in priority_headers.items():
                    if priority in expanded_priorities:
                        debug.debug(f"Expanding header for priority: {priority}")
                        self.expandItem(header_item)
                        header_item.setData(0, Qt.ItemDataRole.UserRole, {
                            'is_priority_header': True,
                            'priority': priority,
                            'color': priority_colors[priority],
                            'expanded': True
                        })
                    else:
                        debug.debug(f"Collapsing header for priority: {priority}")
                        self.collapseItem(header_item)
                        header_item.setData(0, Qt.ItemDataRole.UserRole, {
                            'is_priority_header': True,
                            'priority': priority,
                            'color': priority_colors[priority],
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
                load_links_start = time.time()
                debug.debug(f"Loading links for task {task_id}")
                task_links = []
                try:
                    task_links = db_manager.get_task_links(task_id)
                    debug.debug(f"Found {len(task_links)} links for task {task_id}")
                except Exception as e:
                    debug.error(f"Error loading links for task {task_id}: {e}")
                load_links_end = time.time()
                if load_links_end - load_links_start > 0.05:  # Log slow operations
                    debug.debug(f"Link loading took {load_links_end - load_links_start:.3f} seconds for task {task_id}")
                
                # Load files for this task
                load_files_start = time.time()
                debug.debug(f"Loading files for task {task_id}")
                task_files = []
                try:
                    task_files = db_manager.get_task_files(task_id)
                    debug.debug(f"Found {len(task_files)} files for task {task_id}")
                except Exception as e:
                    debug.error(f"Error loading files for task {task_id}: {e}")
                load_files_end = time.time()
                if load_files_end - load_files_start > 0.05:  # Log slow operations
                    debug.debug(f"File loading took {load_files_end - load_files_start:.3f} seconds for task {task_id}")
                
                # Create the task item WITH links and files
                item_create_start = time.time()
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
                item_create_end = time.time()
                if item_create_end - item_create_start > 0.05:  # Log slow operations
                    debug.debug(f"Item creation took {item_create_end - item_create_start:.3f} seconds for task {task_id}")
                
                # Store parent info for second pass
                parent_id = row[9]  # parent_id
                debug.debug(f"Task {task_id} has parent_id: {parent_id}")
                
                if use_priority_headers:
                    # Process using priority headers logic
                    priority = row[5] or "Medium"  # Default to Medium if None
                    debug.debug(f"Task {task_id} has priority: {priority}")
                    
                    if parent_id is None:
                        # This is a top-level task, add it to the priority header
                        if priority in priority_headers:
                            debug.debug(f"Adding task {task_id} to priority header: {priority}")
                            priority_headers[priority].addChild(item)
                        else:
                            # If no matching header (should not happen), use Medium
                            debug.debug(f"No header found for priority '{priority}', using Medium for task {task_id}")
                            priority_headers["Medium"].addChild(item)
                    else:
                        # This is a child task, will be handled in second pass
                        debug.debug(f"Task {task_id} is a child task, will be handled in second pass")
                        item.setData(0, Qt.ItemDataRole.UserRole + 1, parent_id)
                else:
                    # Simple flat list processing
                    if parent_id is None:
                        # This is a top-level task, add directly to the tree
                        debug.debug(f"Adding task {task_id} as top-level item")
                        self.addTopLevelItem(item)
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
            debug.error(f"Error processing tasks with links and files: {e}")
            debug.error(traceback.format_exc())
        
    @debug_method
    def _format_tasks_with_priority_headers(self, tasks):
        """Format tasks with priority headers (for Current Tasks tab)"""
        start_time = time.time()
        try:
            debug.debug(f"Formatting {len(tasks)} tasks with priority headers")
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
            
            # Add all regular priorities
            for priority, color in priority_colors.items():
                debug.debug(f"Creating header for priority: {priority}")
                header_item = PriorityHeaderItem(priority, color)
                self.addTopLevelItem(header_item)
                priority_headers[priority] = header_item
            
            # Ensure "Unprioritized" header exists, either from database or create it manually
            if "Unprioritized" not in priority_headers:
                debug.debug("Creating Unprioritized header (not found in database)")
                unprioritized_color = "#AAAAAA"  # Medium gray
                unprioritized_header = PriorityHeaderItem("Unprioritized", unprioritized_color)
                self.addTopLevelItem(unprioritized_header)
                priority_headers["Unprioritized"] = unprioritized_header
            
            # First pass: create all items
            debug.debug("First pass: creating task items")
            items = {}
            for i, row in enumerate(tasks):
                if i % 20 == 0:  # Log progress every 20 items
                    debug.debug(f"Processing task {i+1}/{len(tasks)}")
                
                task_id = row[0]
                priority = row[5] or "Unprioritized"  # Default to "Unprioritized" if None
                debug.debug(f"Task {task_id} has priority: {priority}")
                
                # Create the task item
                item = self.add_task_item(*row[:9])  # First 9 elements
                items[task_id] = item
                
                # Store parent info for second pass
                parent_id = row[9]  # Element at index 9 is parent_id
                debug.debug(f"Task {task_id} has parent_id: {parent_id}")
                
                # Check if this task has a parent_id
                if parent_id is None:
                    # This is a top-level task, add it to the appropriate priority header
                    if priority in priority_headers:
                        debug.debug(f"Adding task {task_id} to priority header: {priority}")
                        priority_headers[priority].addChild(item)
                    else:
                        # Fallback to Unprioritized if unknown priority
                        debug.debug(f"Unknown priority '{priority}', adding task {task_id} to Unprioritized")
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
                    
            # Restore expanded state of priority headers from settings
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
                    
            end_time = time.time()
            debug.debug(f"Formatting with priority headers completed in {end_time - start_time:.3f} seconds")
        except Exception as e:
            debug.error(f"Error formatting tasks with priority headers: {e}")
            debug.error(traceback.format_exc())

    @debug_method
    def _format_tasks_flat_list(self, tasks):
        """Format tasks as a flat list with proper parent-child relationships"""
        start_time = time.time()
        try:
            debug.debug(f"Formatting {len(tasks)} tasks as flat list")
            items = {}
            
            # First pass: create all items
            debug.debug("First pass: creating task items")
            for i, row in enumerate(tasks):
                if i % 20 == 0:  # Log progress every 20 items
                    debug.debug(f"Processing task {i+1}/{len(tasks)}")
                
                task_id = row[0]
                debug.debug(f"Creating task item for ID: {task_id}")
                
                # Create the task item
                item = self.add_task_item(*row[:9])  # First 9 elements
                items[task_id] = item
                
                # Store parent info for second pass
                parent_id = row[9]  # Element at index 9 is parent_id
                debug.debug(f"Task {task_id} has parent_id: {parent_id}")
                
                if parent_id is None:
                    # This is a top-level task, add directly to the tree
                    debug.debug(f"Adding task {task_id} as top-level item")
                    self.addTopLevelItem(item)
                else:
                    # This is a child task, will be handled in second pass
                    debug.debug(f"Task {task_id} is a child task, will be handled in second pass")
                    item.setData(0, Qt.ItemDataRole.UserRole + 1, parent_id)
            
            # Second pass: handle parent-child relationships
            debug.debug("Second pass: handling parent-child relationships")
            parent_child_count = 0
            orphan_count = 0
            
            for task_id, item in items.items():
                parent_id = item.data(0, Qt.ItemDataRole.UserRole + 1)
                if parent_id is not None and parent_id in items:
                    parent_item = items[parent_id]
                    parent_item.addChild(item)
                    parent_child_count += 1
                    debug.debug(f"Added task {task_id} as child of {parent_id}")
                elif parent_id is not None:
                    # Parent is not in this tab's filtered results
                    # This can happen when a child task has the correct status
                    # but its parent has a different status
                    debug.debug(f"Task {task_id} has parent {parent_id} not in current filter")
                    
                    # Add directly to the tree as a top level item
                    if item.parent() is None:  # Only if not already added
                        debug.debug(f"Adding task {task_id} as orphaned top-level item")
                        self.addTopLevelItem(item)
                        orphan_count += 1
            
            debug.debug(f"Processed {parent_child_count} parent-child relationships, {orphan_count} orphaned tasks")
            
            # Expand all items by default for better visibility
            debug.debug("Expanding all top-level items")
            expand_count = 0
            for i in range(self.topLevelItemCount()):
                top_item = self.topLevelItem(i)
                self.expandItem(top_item)
                expand_count += 1
                self._expand_all_children(top_item)
            
            debug.debug(f"Expanded {expand_count} top-level items")
            end_time = time.time()
            debug.debug(f"Formatting flat list completed in {end_time - start_time:.3f} seconds")
        
        except Exception as e:
            debug.error(f"Error formatting tasks as flat list: {e}")
            debug.error(traceback.format_exc())

    @debug_method
    def _expand_all_children(self, item):
        """Recursively expand all child items"""
        child_count = item.childCount()
        debug.debug(f"Expanding {child_count} children")
        expanded_count = 0
        
        for i in range(item.childCount()):
            child = item.child(i)
            self.expandItem(child)
            expanded_count += 1
            
            # Recursively expand grandchildren
            grandchild_count = self._expand_all_children(child)
            expanded_count += grandchild_count
            
        return expanded_count

    # @debug_method
    # def show_context_menu(self, position):
    #     """Override to customize the context menu based on tab type"""
    #     debug.debug(f"Showing context menu at position {position.x()}, {position.y()}")
    #     item = self.itemAt(position)
    #     if not item:
    #         debug.debug("No item at position, skipping context menu")
    #         return
            
    #     # Skip if this is a priority header
    #     user_data = item.data(0, Qt.ItemDataRole.UserRole)
    #     if isinstance(user_data, dict) and user_data.get('is_priority_header', False):
    #         debug.debug("Item is a priority header, skipping context menu")
    #         return
                
    #     debug.debug(f"Creating context menu for item: {item.text(0)}")
    #     menu = QMenu(self)
        
    #     # Force hover highlighting with strong styling
    #     menu.setStyleSheet("""
    #         QMenu {
    #             background-color: #FFFFFF;
    #             border: 1px solid #D0D0D0;
    #             padding: 2px;
    #         }
    #         QMenu::item {
    #             padding: 6px 28px 6px 15px;
    #             margin: 2px;
    #             min-width: 150px;
    #         }
    #         QMenu::item:selected, QMenu::item:hover {
    #             background-color: #0071E3 !important;
    #             color: white !important;
    #         }
    #         QMenu::separator {
    #             height: 1px;
    #             background-color: #D0D0D0;
    #             margin: 4px 0px;
    #         }
    #     """)
        
    #     edit_action = menu.addAction("Edit Task")
    #     delete_action = menu.addAction("Delete Task")
        
    #     # Add a separator
    #     menu.addSeparator()
        
    #     # Add status change submenu
    #     status_menu = QMenu("Change Status", self)
    #     status_menu.setStyleSheet(menu.styleSheet())  # Apply same styling to submenu
        
    #     statuses = []
        
    #     # Import database manager
    #     from database.memory_db_manager import get_memory_db_manager
    #     db_manager = get_memory_db_manager()
        
    #     # Get statuses from database in display order
    #     debug.debug("Getting statuses from database")
    #     result = db_manager.execute_query(
    #         "SELECT name FROM statuses ORDER BY display_order"
    #     )
        
    #     for row in result:
    #         statuses.append(row[0])
        
    #     debug.debug(f"Adding {len(statuses)} status options to menu")
    #     status_actions = {}
        
    #     for status in statuses:
    #         action = status_menu.addAction(status)
    #         status_actions[action] = status
        
    #     menu.addMenu(status_menu)
        
    #     # Add priority change submenu
    #     priority_menu = QMenu("Change Priority", self)
    #     priority_menu.setStyleSheet(menu.styleSheet())  # Apply same styling to submenu
    #     priority_actions = {}
        
    #     # Get priorities from database
    #     debug.debug("Getting priorities from database")
    #     results = db_manager.execute_query(
    #         "SELECT name FROM priorities ORDER BY display_order"
    #     )
    #     priorities = [row[0] for row in results]
    #     debug.debug(f"Adding {len(priorities)} priority options to menu")
        
    #     for priority in priorities:
    #         action = priority_menu.addAction(priority)
    #         priority_actions[action] = priority
        
    #     menu.addMenu(priority_menu)
        
    #     # Execute menu and handle action
    #     debug.debug("Showing context menu")
    #     action = menu.exec(self.mapToGlobal(position))
        
    #     if action == edit_action:
    #         debug.debug(f"Edit action selected for item: {item.text(0)}")
    #         self.edit_task(item)
    #     elif action == delete_action:
    #         debug.debug(f"Delete action selected for item: {item.text(0)}")
    #         self.delete_task(item)
    #     elif action in status_actions:
    #         new_status = status_actions[action]
    #         debug.debug(f"Status change selected: {new_status} for item: {item.text(0)}")
    #         self.change_status_with_timestamp(item, new_status)
    #     elif action in priority_actions:
    #         new_priority = priority_actions[action]
    #         debug.debug(f"Priority change selected: {new_priority} for item: {item.text(0)}")
    #         self.change_priority(item, new_priority)
    #     else:
    #         debug.debug("No action selected or menu canceled")
    
    @debug_method
    def change_status(self, item, new_status):
        """Override to use our timestamp-aware status change method"""
        debug.debug(f"Delegating to change_status_with_timestamp: {new_status}")
        return self.change_status_with_timestamp(item, new_status)

class TaskTabWidget(QTabWidget):
    """Widget that contains the tabbed task interface"""
    
    @debug_method
    def __init__(self, main_window):
        debug.debug("Initializing TaskTabWidget")
        super().__init__()
        self.main_window = main_window
        self.setup_tabs()
        
        # Connect tab change signal
        debug.debug("Connecting tab change signal")
        self.currentChanged.connect(self.handle_tab_changed)
        debug.debug("TaskTabWidget initialization complete")
    
    @debug_method
    def setup_tabs(self):
        """Set up the four tabs"""
        debug.debug("Setting up tabs")
        # Create the four tab widgets
        debug.debug("Creating 'current' tab")
        self.current_tasks_tab = self.create_tab("current")
        
        debug.debug("Creating 'backlog' tab")
        self.backlog_tab = self.create_tab("backlog")
        
        # Create Bee To Dos tab
        debug.debug("Creating 'bee_todos' tab")
        self.bee_todos_tab = self.create_bee_todos_tab()
        
        debug.debug("Creating 'completed' tab")
        self.completed_tab = self.create_tab("completed")
        
        # Add them to the tab widget in the new order
        debug.debug("Adding tabs to widget")
        self.addTab(self.current_tasks_tab, "Current Tasks")
        self.addTab(self.backlog_tab, "Backlog")
        self.addTab(self.bee_todos_tab, "Bee To Dos")  # New tab
        self.addTab(self.completed_tab, "Completed Tasks")
        
        # Force load the current tasks tab data
        debug.debug("Loading current tasks tab data")
        self.current_tasks_tab.task_tree.load_tasks_tab()
        
        # Set tab tool tips for better UX
        debug.debug("Setting tab tooltips")
        self.setTabToolTip(0, "View and manage current active tasks")
        self.setTabToolTip(1, "View and manage tasks in your backlog")
        self.setTabToolTip(2, "View and manage To-Dos from your Bee device")
        self.setTabToolTip(3, "View completed tasks")   
        debug.debug("Tab setup complete")
        
    @debug_method
    def create_tab(self, filter_type):
        """Create a tab widget with a task tree for the given filter type"""
        debug.debug(f"Creating tab for filter type: {filter_type}")
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        
        # Create specialized task tree for this tab
        debug.debug(f"Creating TabTaskTreeWidget for filter type: {filter_type}")
        task_tree = TabTaskTreeWidget(filter_type)
        layout.addWidget(task_tree)
        
        # Store the task tree as an attribute on the widget for easy access
        tab_widget.task_tree = task_tree
        debug.debug(f"Tab creation for {filter_type} completed")
        
        return tab_widget
    
    @debug_method
    def get_current_tree(self):
        """Get the task tree for the currently active tab"""
        debug.debug("Getting task tree for current tab")
        current_tab = self.currentWidget()
        if hasattr(current_tab, 'task_tree'):
            debug.debug(f"Found task tree for tab index: {self.currentIndex()}")
            return current_tab.task_tree
        
        debug.debug("No task tree found for current tab")
        return None
    
    @debug_method
    def reload_all(self):
        """Reload all task trees while preserving expanded states"""
        debug.debug("Reloading all task trees with expanded state preservation")
        
        # Get the current tab's tree and save its expanded states
        current_tab = self.currentWidget()
        expanded_items = None
        if hasattr(current_tab, 'task_tree'):
            expanded_items = current_tab.task_tree._save_expanded_states()
            debug.debug(f"Saved {len(expanded_items)} expanded states from current tab")
        
        # Reload all tabs
        for i in range(self.count()):
            tab = self.widget(i)
            if hasattr(tab, 'task_tree'):
                tab.task_tree.load_tasks_tab()
        
        # Restore expanded states to the current tab
        if expanded_items and self.currentWidget() == current_tab:
            current_tab.task_tree._restore_expanded_states(expanded_items)
            debug.debug(f"Restored {len(expanded_items)} expanded states to current tab")
    
    @debug_method
    def create_bee_todos_tab(self):
        """Create the Bee To Dos tab"""
        debug.debug("Creating Bee To Dos tab")
        
        # Create tab widget
        debug.debug("Creating tab widget for Bee To Dos")
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        
        # Create Bee To Dos widget
        debug.debug("Creating BeeToDoWidget instance")
        from ui.bee_todos import BeeToDoWidget
        bee_todos_widget = BeeToDoWidget(self.main_window)
        layout.addWidget(bee_todos_widget)
        
        # Store the widget for easy access
        tab_widget.bee_todos_widget = bee_todos_widget
        debug.debug("Bee To Dos tab creation complete")
        
        return tab_widget
    
    @debug_method
    def handle_tab_changed(self, index):
        """Handle tab changed event"""
        debug.debug(f"Tab changed to index: {index}")
        
        # Save expanded states of previous tab
        if hasattr(self, 'previous_tab_index'):
            previous_tab = self.widget(self.previous_tab_index)
            if previous_tab and hasattr(previous_tab, 'task_tree'):
                debug.debug(f"Saving expanded states for tab: {self.tabText(self.previous_tab_index)}")
                # Save expanded states with a unique key for this tab
                tab_key = f"expanded_states_tab_{self.previous_tab_index}"
                expanded_items = previous_tab.task_tree._save_expanded_states()
                # Store in settings with tab-specific key
                self.main_window.settings.set_setting(tab_key, expanded_items)
                debug.debug(f"Saved {len(expanded_items) if expanded_items else 0} expanded states with key: {tab_key}")
        
        # Store current tab index for next time
        self.previous_tab_index = index
        
        # Get the newly selected tab
        tab = self.widget(index)
        tab_name = self.tabText(index)
        debug.debug(f"Selected tab: {tab_name}")
        
        # Special handling for Bee To Dos tab
        if index == 2:  # Bee To Dos tab
            debug.debug("Bee To Dos tab selected, checking API key")
            # [existing Bee To Dos code]
            
        elif hasattr(tab, 'task_tree'):
            # Regular task tab - load tasks first
            debug.debug(f"Regular task tab selected, loading tasks for tab: {tab_name}")
            load_start = time.time()
            tab.task_tree.load_tasks_tab()
            load_end = time.time()
            debug.debug(f"Tab load completed in {load_end - load_start:.3f} seconds")
            
            # After loading tasks, restore expanded states specific to this tab
            tab_key = f"expanded_states_tab_{index}"
            expanded_items = self.main_window.settings.get_setting(tab_key, [])
            debug.debug(f"Restoring {len(expanded_items)} expanded states for key: {tab_key}")
            
            # Use a short delay to ensure the tree is fully loaded
            QTimer.singleShot(50, lambda: self._restore_tab_expanded_states(tab.task_tree, expanded_items))
        
        else:
            debug.debug(f"Tab has no recognized content to load: {tab_name}")

    @debug_method
    def _restore_tab_expanded_states(self, tree, expanded_items):
        """Helper to restore expanded states with a delay"""
        debug.debug(f"Restoring {len(expanded_items)} expanded states to tree")
        tree._restore_expanded_states(expanded_items)