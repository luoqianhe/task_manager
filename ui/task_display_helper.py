# src/ui/task_display_helper.py

from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt, QTimer
from datetime import datetime

class TaskDisplayHelper:
    """
    Helper class to manage task display logic for the tabbed interface.
    This separates the display logic from the widget implementation.
    """
    
    @staticmethod
    def should_display_in_tab(task_data, tab_type):
        """Determine if a task should be displayed in a specific tab"""
        if not task_data or not isinstance(task_data, dict):
            return False
            
        status = task_data.get('status', '')
        
        if tab_type == "current":
            # Current tab shows tasks that are not Backlog or Completed
            return status != "Backlog" and status != "Completed"
        elif tab_type == "backlog":
            # Backlog tab shows only Backlog tasks
            return status == "Backlog"
        elif tab_type == "completed":
            # Completed tab shows only Completed tasks
            return status == "Completed"
        
        # Default case - unknown tab type
        return False
    
    @staticmethod
    def process_status_change(task_tree, item, new_status):
        """Process a status change including tab transitions"""
        try:
            # Get the data from the item
            data = item.data(0, Qt.ItemDataRole.UserRole)
            old_status = data.get('status', '')
            
            # Skip if status isn't actually changing
            if old_status == new_status:
                return
                
            # Import database manager
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            # Special handling for Completed status
            completed_at = None
            if new_status == "Completed" and old_status != "Completed":
                # Task is being completed - record timestamp
                completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Update database
                db_manager.execute_update(
                    "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?", 
                    (new_status, completed_at, item.task_id)
                )
            elif old_status == "Completed" and new_status != "Completed":
                # Uncompleting a task - clear timestamp
                db_manager.execute_update(
                    "UPDATE tasks SET status = ?, completed_at = NULL WHERE id = ?", 
                    (new_status, item.task_id)
                )
            else:
                # Regular status update
                db_manager.execute_update(
                    "UPDATE tasks SET status = ? WHERE id = ?", 
                    (new_status, item.task_id)
                )
            
            # Update item data
            data['status'] = new_status
            if completed_at:
                data['completed_at'] = completed_at
            elif 'completed_at' in data and new_status != "Completed":
                data.pop('completed_at', None)
                
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            
            # Force a repaint
            task_tree.viewport().update()
            
            # Determine if this task needs to move to another tab
            current_tab = None
            if hasattr(task_tree, 'filter_type'):
                current_tab = task_tree.filter_type
            
            # If task needs to move to another tab, schedule reload of all tabs
            is_tab_transition = False
            
            if current_tab == "current" and (new_status == "Backlog" or new_status == "Completed"):
                is_tab_transition = True
            elif current_tab == "backlog" and new_status != "Backlog":
                is_tab_transition = True
            elif current_tab == "completed" and new_status != "Completed":
                is_tab_transition = True
            
            if is_tab_transition:
                # Notify parent about status change if we're in a tabbed interface
                # The task needs to move to another tab
                parent = task_tree.parent()
                while parent and not hasattr(parent, 'reload_all'):
                    parent = parent.parent()
                    
                if parent and hasattr(parent, 'reload_all'):
                    # Use a short timer to let the current operation complete first
                    QTimer.singleShot(100, parent.reload_all)
            
            return True
            
        except Exception as e:
            print(f"Error processing status change: {e}")
            QMessageBox.critical(task_tree, "Error", f"Failed to change task status: {str(e)}")
            return False
    
    @staticmethod
    def format_tasks_for_display(task_tree, tasks, use_priority_headers=True):
        """Format tasks for display in a tree widget with optional priority grouping"""
        try:
            task_tree.clear()
            
            # Import database manager
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            if use_priority_headers:
                # Get priority order map and colors
                priority_order = {}
                priority_colors = {}
                result = db_manager.execute_query(
                    "SELECT name, display_order, color FROM priorities ORDER BY display_order"
                )
                for name, order, color in result:
                    priority_order[name] = order
                    priority_colors[name] = color
                
                # Create headers for each priority
                priority_headers = {}
                for priority, color in priority_colors.items():
                    from ui.task_tree import PriorityHeaderItem
                    header_item = PriorityHeaderItem(priority, color)
                    task_tree.addTopLevelItem(header_item)
                    priority_headers[priority] = header_item
                
                # First pass: create all items
                items = {}
                for row in tasks:
                    task_id = row[0]
                    priority = row[5] or "Medium"  # Default to Medium if None
                    
                    # Create the task item
                    item = task_tree.add_task_item(*row[:9])  # First 9 elements
                    items[task_id] = item
                    
                    # Store parent info for second pass
                    parent_id = row[9]  # Last element is parent_id
                    if parent_id is None:
                        # This is a top-level task, add it to the priority header
                        if priority in priority_headers:
                            priority_headers[priority].addChild(item)
                    else:
                        # This is a child task, will be handled in second pass
                        item.setData(0, Qt.ItemDataRole.UserRole + 1, parent_id)
                
                # Second pass: handle parent-child relationships for non-top-level tasks
                for task_id, item in items.items():
                    parent_id = item.data(0, Qt.ItemDataRole.UserRole + 1)
                    if parent_id is not None and parent_id in items:
                        parent_item = items[parent_id]
                        parent_item.addChild(item)
                
                # Restore expanded state of priority headers from settings
                settings = task_tree.get_settings_manager()
                all_priorities = list(priority_colors.keys())
                expanded_priorities = settings.get_setting("expanded_priorities", all_priorities)
                
                for priority, header_item in priority_headers.items():
                    if priority in expanded_priorities:
                        task_tree.expandItem(header_item)
                        header_item.setData(0, Qt.ItemDataRole.UserRole, {
                            'is_priority_header': True,
                            'priority': priority,
                            'color': priority_colors[priority],
                            'expanded': True
                        })
                    else:
                        task_tree.collapseItem(header_item)
                        header_item.setData(0, Qt.ItemDataRole.UserRole, {
                            'is_priority_header': True,
                            'priority': priority,
                            'color': priority_colors[priority],
                            'expanded': False
                        })
            else:
                # For Backlog and Completed tabs - simplified list without priority headers
                items = {}
                # First pass: create all items
                for row in tasks:
                    task_id = row[0]
                    
                    # Create the task item
                    item = task_tree.add_task_item(*row[:9])  # First 9 elements
                    items[task_id] = item
                    
                    # Store parent info for second pass
                    parent_id = row[9]  # Element at index 9 is parent_id
                    if parent_id is None:
                        # This is a top-level task, add directly to the tree
                        task_tree.addTopLevelItem(item)
                    else:
                        # This is a child task, will be handled in second pass
                        item.setData(0, Qt.ItemDataRole.UserRole + 1, parent_id)
                
                # Second pass: handle parent-child relationships
                for task_id, item in items.items():
                    parent_id = item.data(0, Qt.ItemDataRole.UserRole + 1)
                    if parent_id is not None and parent_id in items:
                        parent_item = items[parent_id]
                        parent_item.addChild(item)
            
            return True
        
        except Exception as e:
            print(f"Error formatting tasks: {e}")
            return False