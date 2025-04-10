# src/ui/task_tabs.py

from PyQt6.QtWidgets import (QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QMessageBox, QMenu)
from PyQt6.QtCore import Qt, QSize, QTimer
from .task_tree import TaskTreeWidget, PriorityHeaderItem
from datetime import datetime

class TabTaskTreeWidget(TaskTreeWidget):
    """Specialized TaskTreeWidget that can be configured for specific views"""
    
    def __init__(self, filter_type=None):
        super().__init__()
        self.filter_type = filter_type
        self.use_priority_headers = filter_type == "current"
        
        # Ensure tree structure is visible for all tabs
        self.setRootIsDecorated(True)
        self.setIndentation(40)  # Ensure consistent indentation
        
    def load_tasks(self):
        """Override load_tasks to apply filters based on tab type"""
        try:
            self.clear()
            
            # Import database manager
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            # First check if completed_at column exists
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(tasks)")
                columns = [info[1] for info in cursor.fetchall()]
                has_completed_at = 'completed_at' in columns
            
            # Create query based on whether completed_at exists
            completed_at_field = ", t.completed_at" if has_completed_at else ""
            
            # Apply different loading logic based on filter type
            if self.filter_type == "current":
                # For current tab - filter tasks that are not Backlog or Completed
                query = f"""
                    SELECT t.id, t.title, t.description, t.link, t.status, t.priority, 
                        t.due_date, c.name, t.is_compact, t.parent_id{completed_at_field}
                    FROM tasks t
                    LEFT JOIN categories c ON t.category_id = c.id
                    WHERE t.status != 'Backlog' AND t.status != 'Completed'
                    ORDER BY t.parent_id NULLS FIRST, t.display_order
                    """
                tasks = db_manager.execute_query(query)
                
                # Format tasks with priority headers
                self._format_tasks_with_priority_headers(tasks)
                
            elif self.filter_type in ["backlog", "completed"]:
                # For backlog and completed tabs - simplified list without priority headers
                status_name = "Backlog" if self.filter_type == "backlog" else "Completed"
                
                # Get all tasks with the specific status
                order_by = "t.display_order"
                if has_completed_at and self.filter_type == "completed":
                    order_by = "t.completed_at DESC"
                    
                query = f"""
                    SELECT t.id, t.title, t.description, t.link, t.status, t.priority, 
                        t.due_date, c.name, t.is_compact, t.parent_id{completed_at_field}
                    FROM tasks t
                    LEFT JOIN categories c ON t.category_id = c.id
                    WHERE t.status = ?
                    ORDER BY t.parent_id NULLS FIRST, {order_by}
                    """
                tasks = db_manager.execute_query(query, (status_name,))
                
                # Format tasks as flat list without priority headers
                self._format_tasks_flat_list(tasks)
        
        except Exception as e:
            print(f"Error loading tasks for {self.filter_type} tab: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Error", f"Failed to load {self.filter_type} tasks: {str(e)}")

    def change_status_with_timestamp(self, item, new_status):
        """Change status with timestamp tracking for Completed tasks"""
        try:
            # Import database manager
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            # Check if completed_at column exists
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(tasks)")
                columns = [info[1] for info in cursor.fetchall()]
                has_completed_at = 'completed_at' in columns
            
            # Check if this is a status change to or from "Completed"
            data = item.data(0, Qt.ItemDataRole.UserRole)
            old_status = data.get('status', '')
            
            # Determine if this is a status change that would move the task between tabs
            is_tab_transition = False
            
            # Check for transitions between tabs
            if self.filter_type == "current":
                if new_status == "Backlog" or new_status == "Completed":
                    is_tab_transition = True
            elif self.filter_type == "backlog":
                if new_status != "Backlog":
                    is_tab_transition = True
            elif self.filter_type == "completed":
                if new_status != "Completed":
                    is_tab_transition = True
            
            # If we're changing task status, we need to collect all children
            # so we can also update their status to match
            child_tasks = []
            if is_tab_transition:
                self._collect_child_tasks(item, child_tasks)
            
            # Update main task status
            if has_completed_at:
                # Get current timestamp formatted as ISO string if status is changing to Completed
                completed_at = None
                if new_status == "Completed" and old_status != "Completed":
                    completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"Task completed at: {completed_at}")
                    
                    # Update database with completed_at timestamp
                    db_manager.execute_update(
                        "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?", 
                        (new_status, completed_at, item.task_id)
                    )
                elif old_status == "Completed" and new_status != "Completed":
                    # If changing from Completed to another status, clear the timestamp
                    db_manager.execute_update(
                        "UPDATE tasks SET status = ?, completed_at = NULL WHERE id = ?", 
                        (new_status, item.task_id)
                    )
                else:
                    # Normal status update without changing completion state
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
            else:
                # No completed_at column, just update status
                db_manager.execute_update(
                    "UPDATE tasks SET status = ? WHERE id = ?", 
                    (new_status, item.task_id)
                )
                # Update item data
                data['status'] = new_status
                
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            
            # Now update all child tasks with the same status
            if is_tab_transition and child_tasks:
                for child_id in child_tasks:
                    if has_completed_at:
                        if new_status == "Completed":
                            # All children of a completed task also get completed
                            child_completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            db_manager.execute_update(
                                "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?", 
                                (new_status, child_completed_at, child_id)
                            )
                        else:
                            # Children of non-completed tasks should also be non-completed
                            db_manager.execute_update(
                                "UPDATE tasks SET status = ?, completed_at = NULL WHERE id = ?", 
                                (new_status, child_id)
                            )
                    else:
                        # Just update status
                        db_manager.execute_update(
                            "UPDATE tasks SET status = ? WHERE id = ?", 
                            (new_status, child_id)
                        )
                        
                print(f"Updated status of {len(child_tasks)} child tasks to {new_status}")
            
            # Force a repaint
            self.viewport().update()
            
            # Notify parent about status change if we're in a tabbed interface
            # The task needs to move to another tab
            if is_tab_transition:
                parent = self.parent()
                while parent and not hasattr(parent, 'reload_all'):
                    parent = parent.parent()
                    
                if parent and hasattr(parent, 'reload_all'):
                    # Use a short timer to let the current operation complete first
                    QTimer.singleShot(100, parent.reload_all)
            
        except Exception as e:
            print(f"Error changing task status: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to change task status: {str(e)}")

    def _format_tasks_with_priority_headers(self, tasks):
        """Format tasks with priority headers (for Current Tasks tab)"""
        try:
            # Import database manager
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
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
            
            # Add all regular priorities
            for priority, color in priority_colors.items():
                header_item = PriorityHeaderItem(priority, color)
                self.addTopLevelItem(header_item)
                priority_headers[priority] = header_item
            
            # Ensure "Unprioritized" header exists, either from database or create it manually
            if "Unprioritized" not in priority_headers:
                unprioritized_color = "#AAAAAA"  # Medium gray
                unprioritized_header = PriorityHeaderItem("Unprioritized", unprioritized_color)
                self.addTopLevelItem(unprioritized_header)
                priority_headers["Unprioritized"] = unprioritized_header
            
            # First pass: create all items
            items = {}
            for row in tasks:
                task_id = row[0]
                priority = row[5] or "Unprioritized"  # Default to "Unprioritized" if None
                
                # Create the task item
                item = self.add_task_item(*row[:9])  # First 9 elements
                items[task_id] = item
                
                # Store parent info for second pass
                parent_id = row[9]  # Element at index 9 is parent_id
                if parent_id is None:
                    # This is a top-level task, add it to the appropriate priority header
                    if priority in priority_headers:
                        priority_headers[priority].addChild(item)
                    else:
                        # If priority doesn't match any header, use Unprioritized
                        priority_headers["Unprioritized"].addChild(item)
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
            settings = self.get_settings_manager()
            all_priorities = list(priority_headers.keys())
            expanded_priorities = settings.get_setting("expanded_priorities", all_priorities)
            
            for priority, header_item in priority_headers.items():
                # Get the color - either from priority_colors or default to gray for "Unprioritized"
                color = priority_colors.get(priority, "#AAAAAA")
                
                if priority in expanded_priorities:
                    self.expandItem(header_item)
                    header_item.setData(0, Qt.ItemDataRole.UserRole, {
                        'is_priority_header': True,
                        'priority': priority,
                        'color': color,
                        'expanded': True
                    })
                else:
                    self.collapseItem(header_item)
                    header_item.setData(0, Qt.ItemDataRole.UserRole, {
                        'is_priority_header': True,
                        'priority': priority,
                        'color': color,
                        'expanded': False
                    })
        except Exception as e:
            print(f"Error formatting tasks with priority headers: {e}")
            import traceback
            traceback.print_exc()
            
    def _format_tasks_flat_list(self, tasks):
        """Format tasks as a flat list with proper parent-child relationships"""
        try:
            items = {}
            
            # First pass: create all items
            for row in tasks:
                task_id = row[0]
                
                # Create the task item
                item = self.add_task_item(*row[:9])  # First 9 elements
                items[task_id] = item
                
                # Store parent info for second pass
                parent_id = row[9]  # Element at index 9 is parent_id
                if parent_id is None:
                    # This is a top-level task, add directly to the tree
                    self.addTopLevelItem(item)
                else:
                    # This is a child task, will be handled in second pass
                    item.setData(0, Qt.ItemDataRole.UserRole + 1, parent_id)
            
            # Second pass: handle parent-child relationships
            for task_id, item in items.items():
                parent_id = item.data(0, Qt.ItemDataRole.UserRole + 1)
                if parent_id is not None and parent_id in items:
                    parent_item = items[parent_id]
                    parent_item.addChild(item)
                elif parent_id is not None:
                    # Parent is not in this tab's filtered results
                    # This can happen when a child task has the correct status
                    # but its parent has a different status
                    
                    # Add directly to the tree as a top level item
                    if item.parent() is None:  # Only if not already added
                        self.addTopLevelItem(item)
            
            # Expand all items by default for better visibility
            for i in range(self.topLevelItemCount()):
                top_item = self.topLevelItem(i)
                self.expandItem(top_item)
                self._expand_all_children(top_item)
        
        except Exception as e:
            print(f"Error formatting tasks as flat list: {e}")
            import traceback
            traceback.print_exc()

    def _expand_all_children(self, item):
        """Recursively expand all child items"""
        for i in range(item.childCount()):
            child = item.child(i)
            self.expandItem(child)
            self._expand_all_children(child)

    def show_context_menu(self, position):
        """Override to customize the context menu based on tab type"""
        item = self.itemAt(position)
        if not item:
            return
            
        # Skip if this is a priority header
        user_data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(user_data, dict) and user_data.get('is_priority_header', False):
            return
            
        menu = QMenu(self)
        edit_action = menu.addAction("Edit Task")
        delete_action = menu.addAction("Delete Task")
        
        # Add a separator
        menu.addSeparator()
        
        # Add status change submenu
        status_menu = menu.addMenu("Change Status")
        statuses = []
        
        # Import database manager
        from database.database_manager import get_db_manager
        db_manager = get_db_manager()
        
        # Get statuses from database in display order
        result = db_manager.execute_query(
            "SELECT name FROM statuses ORDER BY display_order"
        )
        
        for row in result:
            statuses.append(row[0])
        
        status_actions = {}
        
        for status in statuses:
            action = status_menu.addAction(status)
            status_actions[action] = status
        
        # Add priority change submenu
        priority_menu = menu.addMenu("Change Priority")
        priority_actions = {}
        
        # Get priorities from database
        results = db_manager.execute_query(
            "SELECT name FROM priorities ORDER BY display_order"
        )
        priorities = [row[0] for row in results]
        
        for priority in priorities:
            action = priority_menu.addAction(priority)
            priority_actions[action] = priority
        
        # Execute menu and handle action
        action = menu.exec(self.mapToGlobal(position))
        
        if action == edit_action:
            self.edit_task(item)
        elif action == delete_action:
            self.delete_task(item)
        elif action in status_actions:
            self.change_status_with_timestamp(item, status_actions[action])
        elif action in priority_actions:
            self.change_priority(item, priority_actions[action])
    
    def change_status(self, item, new_status):
        """Override to use our timestamp-aware status change method"""
        return self.change_status_with_timestamp(item, new_status)

class TaskTabWidget(QTabWidget):
    """Widget that contains the tabbed task interface"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setup_tabs()
        
        # Connect tab change signal
        self.currentChanged.connect(self.handle_tab_changed)
    
    def setup_tabs(self):
        """Set up the three tabs"""
        # Create the three tab widgets
        self.current_tasks_tab = self.create_tab("current")
        self.backlog_tab = self.create_tab("backlog")
        self.completed_tab = self.create_tab("completed")
        
        # Add them to the tab widget
        self.addTab(self.current_tasks_tab, "Current Tasks")
        self.addTab(self.backlog_tab, "Backlog")
        self.addTab(self.completed_tab, "Completed Tasks")
        
        # Set tab tool tips for better UX
        self.setTabToolTip(0, "View and manage current active tasks")
        self.setTabToolTip(1, "View and manage tasks in your backlog")
        self.setTabToolTip(2, "View completed tasks")
    
    def create_tab(self, filter_type):
        """Create a tab widget with a task tree for the given filter type"""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        
        # Create specialized task tree for this tab
        task_tree = TabTaskTreeWidget(filter_type)
        layout.addWidget(task_tree)
        
        # Store the task tree as an attribute on the widget for easy access
        tab_widget.task_tree = task_tree
        
        return tab_widget
    
    def get_current_tree(self):
        """Get the task tree for the currently active tab"""
        current_tab = self.currentWidget()
        if hasattr(current_tab, 'task_tree'):
            return current_tab.task_tree
        return None
    
    def reload_all(self):
        """Reload all task trees"""
        for i in range(self.count()):
            tab = self.widget(i)
            if hasattr(tab, 'task_tree'):
                tab.task_tree.load_tasks()
    
    def handle_tab_changed(self, index):
        """Handle tab changed event"""
        # Refresh the newly selected tab's content
        tab = self.widget(index)
        if hasattr(tab, 'task_tree'):
            tab.task_tree.load_tasks()