# src/ui/task_display_helper.py

from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt, QTimer
from datetime import datetime

# Import the debug logger and decorator
from utils.debug_logger import get_debug_logger
from utils.debug_decorator import debug_method

# Get debug logger instance
debug = get_debug_logger()

class TaskDisplayHelper:
    """
    Helper class to manage task display logic for the tabbed interface.
    This separates the display logic from the widget implementation.
    """
    
    @staticmethod
    @debug_method
    def should_display_in_tab(task_data, tab_type):
        """Determine if a task should be displayed in a specific tab"""
        debug.debug(f"Checking if task should display in tab: {tab_type}")
        if not task_data or not isinstance(task_data, dict):
            debug.debug("Invalid task data, not displaying")
            return False
            
        status = task_data.get('status', '')
        debug.debug(f"Task status: {status}")
        
        if tab_type == "current":
            # Current tab shows tasks that are not Backlog or Completed
            result = status != "Backlog" and status != "Completed"
            debug.debug(f"Display in Current tab: {result}")
            return result
        elif tab_type == "backlog":
            # Backlog tab shows only Backlog tasks
            result = status == "Backlog"
            debug.debug(f"Display in Backlog tab: {result}")
            return result
        elif tab_type == "completed":
            # Completed tab shows only Completed tasks
            result = status == "Completed"
            debug.debug(f"Display in Completed tab: {result}")
            return result
        
        # Default case - unknown tab type
        debug.debug(f"Unknown tab type: {tab_type}, not displaying")
        return False
    
    @staticmethod
    @debug_method
    def process_status_change(task_tree, item, new_status):
        """Process a status change including tab transitions"""
        debug.debug(f"Processing status change to: {new_status}")
        try:
            # Get the data from the item
            data = item.data(0, Qt.ItemDataRole.UserRole)
            old_status = data.get('status', '')
            debug.debug(f"Old status: {old_status}")
            
            # Skip if status isn't actually changing
            if old_status == new_status:
                debug.debug("Status not changing, skipping update")
                return
                
            # Import database manager
            debug.debug("Getting database manager")
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            # Special handling for Completed status
            completed_at = None
            if new_status == "Completed" and old_status != "Completed":
                # Task is being completed - record timestamp
                completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                debug.debug(f"Task completed at: {completed_at}")
                
                # Update database
                debug.debug("Updating database with completed status and timestamp")
                db_manager.execute_update(
                    "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?", 
                    (new_status, completed_at, item.task_id)
                )
            elif old_status == "Completed" and new_status != "Completed":
                # Uncompleting a task - clear timestamp
                debug.debug("Clearing completed timestamp")
                db_manager.execute_update(
                    "UPDATE tasks SET status = ?, completed_at = NULL WHERE id = ?", 
                    (new_status, item.task_id)
                )
            else:
                # Regular status update
                debug.debug("Regular status update")
                db_manager.execute_update(
                    "UPDATE tasks SET status = ? WHERE id = ?", 
                    (new_status, item.task_id)
                )
            
            # Update item data
            debug.debug("Updating item data")
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
            task_tree.viewport().update()
            
            # Determine if this task needs to move to another tab
            current_tab = None
            if hasattr(task_tree, 'filter_type'):
                current_tab = task_tree.filter_type
                debug.debug(f"Current tab type: {current_tab}")
            
            # If task needs to move to another tab, schedule reload of all tabs
            is_tab_transition = False
            
            if current_tab == "current" and (new_status == "Backlog" or new_status == "Completed"):
                is_tab_transition = True
                debug.debug("Task will transition from Current tab")
            elif current_tab == "backlog" and new_status != "Backlog":
                is_tab_transition = True
                debug.debug("Task will transition from Backlog tab")
            elif current_tab == "completed" and new_status != "Completed":
                is_tab_transition = True
                debug.debug("Task will transition from Completed tab")
            
            if is_tab_transition:
                debug.debug("Tab transition required, looking for parent with reload_all method")
                # Notify parent about status change if we're in a tabbed interface
                # The task needs to move to another tab
                parent = task_tree.parent()
                while parent and not hasattr(parent, 'reload_all'):
                    parent = parent.parent()
                    
                if parent and hasattr(parent, 'reload_all'):
                    # Use a short timer to let the current operation complete first
                    debug.debug("Found parent with reload_all, scheduling reload after delay")
                    QTimer.singleShot(100, parent.reload_all)
                else:
                    debug.debug("Could not find parent with reload_all method")
            
            debug.debug("Status change processed successfully")
            return True
            
        except Exception as e:
            debug.error(f"Error processing status change: {e}")
            QMessageBox.critical(task_tree, "Error", f"Failed to change task status: {str(e)}")
            return False
    
    @staticmethod
    @debug_method
    def format_tasks_for_display(task_tree, tasks, use_priority_headers=True):
        """Format tasks for display in a tree widget with optional priority grouping"""
        debug.debug(f"Formatting {len(tasks)} tasks for display with priority headers: {use_priority_headers}")
        try:
            task_tree.clear()
            debug.debug("Tree cleared")
            
            # Import database manager
            debug.debug("Getting database manager")
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            if use_priority_headers:
                debug.debug("Using priority headers formatting")
                # Get priority order map and colors
                debug.debug("Getting priorities from database")
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
                    from ui.task_tree import PriorityHeaderItem
                    header_item = PriorityHeaderItem(priority, color)
                    task_tree.addTopLevelItem(header_item)
                    priority_headers[priority] = header_item
                    debug.debug(f"Created header for priority: {priority}")
                
                # First pass: create all items
                debug.debug("First pass: creating task items")
                items = {}
                for row in tasks:
                    task_id = row[0]
                    priority = row[5] or "Medium"  # Default to Medium if None
                    debug.debug(f"Processing task {task_id} with priority {priority}")
                    
                    # Create the task item
                    item = task_tree.add_task_item(*row[:9])  # First 9 elements
                    items[task_id] = item
                    
                    # Store parent info for second pass
                    parent_id = row[9]  # Last element is parent_id
                    if parent_id is None:
                        # This is a top-level task, add it to the priority header
                        debug.debug(f"Task {task_id} is top-level, adding to priority header {priority}")
                        if priority in priority_headers:
                            priority_headers[priority].addChild(item)
                        else:
                            debug.warning(f"Priority header not found for: {priority}")
                    else:
                        # This is a child task, will be handled in second pass
                        debug.debug(f"Task {task_id} has parent {parent_id}, will be processed in second pass")
                        item.setData(0, Qt.ItemDataRole.UserRole + 1, parent_id)
                
                # Second pass: handle parent-child relationships for non-top-level tasks
                debug.debug("Second pass: handling parent-child relationships")
                for task_id, item in items.items():
                    parent_id = item.data(0, Qt.ItemDataRole.UserRole + 1)
                    if parent_id is not None and parent_id in items:
                        parent_item = items[parent_id]
                        parent_item.addChild(item)
                        debug.debug(f"Added task {task_id} as child of {parent_id}")
                
                # Restore expanded state of priority headers from settings
                debug.debug("Restoring expanded state of priority headers")
                settings = task_tree.get_settings_manager()
                all_priorities = list(priority_colors.keys())
                expanded_priorities = settings.get_setting("expanded_priorities", all_priorities)
                debug.debug(f"Expanded priorities from settings: {expanded_priorities}")
                
                for priority, header_item in priority_headers.items():
                    if priority in expanded_priorities:
                        task_tree.expandItem(header_item)
                        header_item.setData(0, Qt.ItemDataRole.UserRole, {
                            'is_priority_header': True,
                            'priority': priority,
                            'color': priority_colors[priority],
                            'expanded': True
                        })
                        debug.debug(f"Expanded header: {priority}")
                    else:
                        task_tree.collapseItem(header_item)
                        header_item.setData(0, Qt.ItemDataRole.UserRole, {
                            'is_priority_header': True,
                            'priority': priority,
                            'color': priority_colors[priority],
                            'expanded': False
                        })
                        debug.debug(f"Collapsed header: {priority}")
            else:
                # For Backlog and Completed tabs - simplified list without priority headers
                debug.debug("Using simplified list formatting without priority headers")
                items = {}
                # First pass: create all items
                debug.debug("First pass: creating task items")
                for row in tasks:
                    task_id = row[0]
                    debug.debug(f"Processing task {task_id}")
                    
                    # Create the task item
                    item = task_tree.add_task_item(*row[:9])  # First 9 elements
                    items[task_id] = item
                    
                    # Store parent info for second pass
                    parent_id = row[9]  # Element at index 9 is parent_id
                    if parent_id is None:
                        # This is a top-level task, add directly to the tree
                        debug.debug(f"Task {task_id} is top-level, adding to tree root")
                        task_tree.addTopLevelItem(item)
                    else:
                        # This is a child task, will be handled in second pass
                        debug.debug(f"Task {task_id} has parent {parent_id}, will be processed in second pass")
                        item.setData(0, Qt.ItemDataRole.UserRole + 1, parent_id)
                
                # Second pass: handle parent-child relationships
                debug.debug("Second pass: handling parent-child relationships")
                for task_id, item in items.items():
                    parent_id = item.data(0, Qt.ItemDataRole.UserRole + 1)
                    if parent_id is not None and parent_id in items:
                        parent_item = items[parent_id]
                        parent_item.addChild(item)
                        debug.debug(f"Added task {task_id} as child of {parent_id}")
            
            debug.debug("Task formatting completed successfully")
            return True
        
        except Exception as e:
            debug.error(f"Error formatting tasks: {e}")
            import traceback
            traceback.print_exc()
            return False