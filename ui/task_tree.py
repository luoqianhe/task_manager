# src/ui/task_tree.py

from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QHeaderView, QMessageBox, QDateEdit
from PyQt6.QtCore import Qt, QDate, QSize
from PyQt6.QtGui import QBrush, QColor
import sqlite3
from pathlib import Path
import webbrowser
import logging
from .task_pill_delegate import TaskPillDelegate
from datetime import datetime, date

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TaskTreeWidget(QTreeWidget):
    
    def __init__(self):
        super().__init__()
        self.setRootIsDecorated(False)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        
        # Change to just one column
        self.setColumnCount(1)
        self.setHeaderLabels(['Tasks'])
        
        # Hide the header
        self.setHeaderHidden(True)
        self.setIndentation(40)  # Increased indentation for better hierarchy view
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)  # IMPORTANT: Set on viewport too
        
        # Apply the custom delegate - ensure it's created after mouse tracking is enabled
        custom_delegate = TaskPillDelegate(self)
        self.setItemDelegate(custom_delegate)
        
        # Set a clean style
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
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Connect expansion/collapse signals
        self.itemExpanded.connect(self.onItemExpanded)
        self.itemCollapsed.connect(self.onItemCollapsed)

        # Connect double-click signal with our router method
        self.itemDoubleClicked.connect(self.onItemDoubleClicked)
        
        # Load tasks
        try:
            self.load_tasks()
        except Exception as e:
            print(f"Error loading tasks: {e}")
        
        # Debug delegate setup
        self.debug_delegate_setup()
    
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return:
            selected_items = self.selectedItems()
            if selected_items:
                self.edit_task(selected_items[0])
        elif event.key() == Qt.Key.Key_Delete:
            selected_items = self.selectedItems()
            if selected_items:
                self.delete_task(selected_items[0])
        else:
            super().keyPressEvent(event)

    def delete_task(self, item):
        reply = QMessageBox.question(
            self, 
            'Delete Task',
            'Are you sure you want to delete this task?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Import database manager
                from database.database_manager import get_db_manager
                db_manager = get_db_manager()
                
                # Delete the item and all its children
                def delete_item_and_children(task_id):
                    # First get all children
                    children = db_manager.execute_query(
                        "SELECT id FROM tasks WHERE parent_id = ?", 
                        (task_id,)
                    )
                    # Delete children recursively
                    for child in children:
                        delete_item_and_children(child[0])
                    # Delete this item
                    db_manager.execute_update(
                        "DELETE FROM tasks WHERE id = ?", 
                        (task_id,)
                    )
                
                delete_item_and_children(item.task_id)
                
                # Remove from tree
                parent = item.parent()
                if parent:
                    parent.removeChild(item)
                else:
                    index = self.indexOfTopLevelItem(item)
                    self.takeTopLevelItem(index)
            except Exception as e:
                print(f"Error deleting task: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete task: {str(e)}")

    def dropEvent(self, event):
        print("\n=== DRAG & DROP DEBUG ===")
        item = self.currentItem()
        print(f"Current item being dropped: {item.text(0) if item else 'None'}")
        
        if hasattr(item, 'task_id'):
            # Debug display_order BEFORE drop
            try:
                from database.database_manager import get_db_manager
                db_manager = get_db_manager()
                
                # Get current display_order and parent_id
                result = db_manager.execute_query(
                    "SELECT display_order, parent_id FROM tasks WHERE id = ?", 
                    (item.task_id,)
                )
                if result and len(result) > 0:
                    old_order, old_parent = result[0]
                    print(f"BEFORE DROP - Task ID: {item.task_id}, Display Order: {old_order}, Parent ID: {old_parent}")
                else:
                    print(f"Warning: Could not find task with ID {item.task_id} in database")
            except Exception as e:
                print(f"Error getting task info before drop: {e}")
        
        # Save the drop indicator position BEFORE calling super
        drop_pos = self.dropIndicatorPosition()
        print(f"Drop indicator position: {drop_pos}")
        
        # Call the parent implementation to handle the actual visual drop
        super().dropEvent(event)
        print("Parent dropEvent method completed")
        
        try:
            # Save new parent-child relationships to database
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            # Get the new parent and position in tree after super().dropEvent
            new_parent = item.parent()
            print(f"New parent after drop: {new_parent.text(0) if new_parent else 'None'}")
            
            # IMPORTANT: Handle priority header specially
            if new_parent and isinstance(new_parent.data(0, Qt.ItemDataRole.UserRole), dict) and new_parent.data(0, Qt.ItemDataRole.UserRole).get('is_priority_header', False):
                # This is a priority header - we need to update the task's priority
                priority_data = new_parent.data(0, Qt.ItemDataRole.UserRole)
                new_priority = priority_data.get('priority')
                print(f"Task was dropped into priority header: {new_priority}")
                
                # Update the task's priority in the database
                db_manager.execute_update(
                    "UPDATE tasks SET priority = ? WHERE id = ?",
                    (new_priority, item.task_id)
                )
                
                # Also update the item's data to reflect the new priority
                item_data = item.data(0, Qt.ItemDataRole.UserRole)
                item_data['priority'] = new_priority
                item.setData(0, Qt.ItemDataRole.UserRole, item_data)
                
                print(f"Updated task priority to: {new_priority}")
                
                # Skip the parent_id update since this is handled by the priority header
                return
            
            # The rest of your existing code for parent_id updates here...
            # Determine parent_id for database update
            if new_parent and hasattr(new_parent, 'task_id'):
                parent_id = new_parent.task_id
                print(f"Setting parent_id to: {parent_id}")
            else:
                # This is now a top-level item
                parent_id = None
                print(f"Setting parent_id to None (top-level item)")
            
            # Find the item's position among its siblings
            siblings_count = 0
            item_position = 0
            
            if new_parent:
                siblings_count = new_parent.childCount()
                for i in range(siblings_count):
                    if new_parent.child(i) == item:
                        item_position = i
                        break
            else:
                # Top-level item
                siblings_count = self.topLevelItemCount()
                for i in range(siblings_count):
                    if self.topLevelItem(i) == item:
                        item_position = i
                        break
                        
            print(f"Item position among siblings: {item_position} of {siblings_count}")
            
            # Get all sibling tasks in database to rearrange them
            try:
                # Get display_orders of all siblings
                if parent_id is not None:
                    result = db_manager.execute_query(
                        "SELECT id, display_order FROM tasks WHERE parent_id = ? ORDER BY display_order",
                        (parent_id,)
                    )
                else:
                    result = db_manager.execute_query(
                        "SELECT id, display_order FROM tasks WHERE parent_id IS NULL ORDER BY display_order"
                    )
                
                siblings = [(row[0], row[1]) for row in result]
                print(f"Siblings in DB (ID, order): {siblings}")
                
                # First, update the parent_id of the dragged item
                update_result = db_manager.execute_update(
                    "UPDATE tasks SET parent_id = ? WHERE id = ?", 
                    (parent_id, item.task_id)
                )
                print(f"Updated parent_id, rows affected: {update_result}")
                
                # Now recalculate all display_orders to match visual order
                # Start with display_order 1 for the first sibling
                new_orders = []
                current_order = 1
                
                # Add all siblings in order, inserting the dragged item at its new position
                for i in range(siblings_count):
                    sibling_item = new_parent.child(i) if new_parent else self.topLevelItem(i)
                    
                    if hasattr(sibling_item, 'task_id'):
                        # Add (id, new_order) pair to our list
                        new_orders.append((sibling_item.task_id, current_order))
                        current_order += 1
                
                print(f"New ordering to apply: {new_orders}")
                
                # Update all display_orders in one batch
                for task_id, order in new_orders:
                    db_manager.execute_update(
                        "UPDATE tasks SET display_order = ? WHERE id = ?",
                        (order, task_id)
                    )
                    print(f"Updated task ID {task_id} to display_order {order}")
                
                # Debug display_order AFTER drop
                result = db_manager.execute_query(
                    "SELECT display_order, parent_id FROM tasks WHERE id = ?", 
                    (item.task_id,)
                )
                if result and len(result) > 0:
                    new_order, new_parent_id = result[0]
                    print(f"AFTER DROP - Task ID: {item.task_id}, Display Order: {new_order}, Parent ID: {new_parent_id}")
                else:
                    print(f"Warning: Could not find task with ID {item.task_id} in database after update")
                
            except Exception as e:
                print(f"Error updating display_order: {e}")
                import traceback
                traceback.print_exc()
            
            # Recursively update all children
            print("Updating children hierarchy...")
            self._update_children_hierarchy(item)
            
            # Force refresh all tabs if in tabbed interface
            print("Attempting to refresh UI after drop...")
            parent = self.parent()
            while parent and not hasattr(parent, 'reload_all'):
                parent = parent.parent()
                
            if parent and hasattr(parent, 'reload_all'):
                print("Refreshing all tabs after drag and drop")
                # Use a short timer to let the current operation complete first
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(100, parent.reload_all)
            else:
                print("Tab refresh not available, refreshing current view")
                # Just refresh this tree
                self.load_tasks()
            
        except Exception as e:
            print(f"Error in dropEvent: {e}")
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to update task hierarchy: {str(e)}")
        
        print("=== END DRAG & DROP DEBUG ===\n")

    def _update_children_hierarchy(self, parent_item):
        """Update all children's hierarchy in the database"""
        try:
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                
                # Skip if not a task item
                if not hasattr(child, 'task_id'):
                    continue
                    
                # Import database manager
                from database.database_manager import get_db_manager
                db_manager = get_db_manager()
                
                # Update child's parent_id
                parent_id = parent_item.task_id if hasattr(parent_item, 'task_id') else None
                db_manager.execute_update(
                    """
                    UPDATE tasks 
                    SET parent_id = ?
                    WHERE id = ?
                    """, 
                    (parent_id, child.task_id)
                )
                
                # Recursively update all grandchildren
                self._update_children_hierarchy(child)
        except Exception as e:
            print(f"Error updating child hierarchy: {e}")

    def change_status(self, item, new_status):
        try:
            # Import database manager
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            # Check if this is a status change to or from "Completed"
            data = item.data(0, Qt.ItemDataRole.UserRole)
            old_status = data.get('status', '')
            
            # Get current timestamp formatted as ISO string if status is changing to Completed
            completed_at = None
            if new_status == "Completed" and old_status != "Completed":
                from datetime import datetime
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
            
            # Update item
            data = item.data(0, Qt.ItemDataRole.UserRole)
            data['status'] = new_status
            if completed_at:
                data['completed_at'] = completed_at
            elif 'completed_at' in data and new_status != "Completed":
                data.pop('completed_at', None)
                
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            
            # Force a repaint
            self.viewport().update()
            
            # Notify parent about status change if we're in a tabbed interface
            parent = self.parent()
            while parent and not hasattr(parent, 'reload_all'):
                parent = parent.parent()
                
            if parent and hasattr(parent, 'reload_all'):
                # This is a TabTaskTreeWidget within a TaskTabWidget
                # Reload all tabs to reflect the status change
                parent.reload_all()
                
        except Exception as e:
            print(f"Error changing task status: {e}")
            QMessageBox.critical(self, "Error", f"Failed to change task status: {str(e)}")

    def change_priority(self, item, new_priority):
        try:
            # Update database
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            db_manager.execute_update(
                "UPDATE tasks SET priority = ? WHERE id = ?", 
                (new_priority, item.task_id)
            )
            
            # Update item
            data = item.data(0, Qt.ItemDataRole.UserRole)
            data['priority'] = new_priority
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            
            # Force a repaint
            self.viewport().update()
        except Exception as e:
            print(f"Error changing task priority: {e}")
            QMessageBox.critical(self, "Error", f"Failed to change task priority: {str(e)}")

    def add_task_item(self, task_id, title, description, link, status, priority, due_date, category, is_compact=0):
        # Create a single-column item
        item = QTreeWidgetItem([title or ""])
        
        # Debug: Print the status to see if it's being passed in correctly
        print(f"Adding task: {title} with status: {status}")
        
        # Store all data as item data
        item.setData(0, Qt.ItemDataRole.UserRole, {
            'id': task_id,  # Store ID in user data too for easier access
            'title': title or "",
            'description': description or "",
            'link': link or "", 
            'status': status or "Not Started", 
            'priority': priority or "Medium",
            'due_date': due_date or "",
            'category': category or ""
        })
        
        item.task_id = task_id
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
        
        # Set item height based on compact state
        delegate = self.itemDelegate()
        if isinstance(delegate, TaskPillDelegate):
            # If this item is marked as compact in the database, add it to delegate's compact set
            if is_compact:
                delegate.compact_items.add(task_id)
            
            # Set appropriate height
            height = delegate.compact_height if is_compact else delegate.pill_height
            item.setSizeHint(0, QSize(100, height + delegate.item_margin * 2))
        
        # Apply background color based on category
        if category:
            try:
                from database.database_manager import get_db_manager
                db_manager = get_db_manager()
                
                result = db_manager.execute_query(
                    "SELECT color FROM categories WHERE name = ?", 
                    (category,)
                )
                if result and result[0]:
                    color = QColor(result[0][0])
                    item.setBackground(0, QBrush(color))
            except Exception as e:
                print(f"Error getting category color: {e}")
        
        return item

    def show_context_menu(self, position):
        item = self.itemAt(position)
        if not item:
            return
            
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
        
        # Add priority change submenu with priorities from database
        priority_menu = menu.addMenu("Change Priority")
        priority_actions = {}
        
        try:
            # Import database manager
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            # Get priorities from database
            results = db_manager.execute_query(
                "SELECT name FROM priorities ORDER BY display_order"
            )
            priorities = [row[0] for row in results]
            
            for priority in priorities:
                action = priority_menu.addAction(priority)
                priority_actions[action] = priority
        except Exception as e:
            print(f"Error loading priorities for context menu: {e}")
        
        action = menu.exec(self.mapToGlobal(position))
        
        if action == edit_action:
            self.edit_task(item)
        elif action == delete_action:
            self.delete_task(item)
        elif action in status_actions:
            self.change_status(item, status_actions[action])
        elif action in priority_actions:
            self.change_priority(item, priority_actions[action])

    def edit_task(self, item):
        from .task_dialogs import EditTaskDialog
        
        # Skip if not a task item
        if not hasattr(item, 'task_id'):
            return
            
        # Get current data from the item's user role data
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Get compact state from delegate
        delegate = self.itemDelegate()
        is_compact = False
        if isinstance(delegate, TaskPillDelegate):
            is_compact = item.task_id in delegate.compact_items
        
        # Determine the parent ID safely
        parent_id = None
        if item.parent():
            # Only use parent_id if the parent is a regular task item (not a priority header)
            if hasattr(item.parent(), 'task_id'):
                parent_id = item.parent().task_id
            # If parent is a priority header, leave parent_id as None
        
        task_data = {
            'id': item.task_id,
            'title': data['title'],
            'description': data['description'],
            'link': data['link'],
            'status': data['status'],
            'priority': data['priority'],
            'due_date': data['due_date'],
            'category': data['category'],
            'parent_id': parent_id,  # Safely determined parent_id
            'is_compact': is_compact  # Include compact state
        }
        
        # Open edit dialog
        dialog = EditTaskDialog(task_data, self)
        if dialog.exec():
            try:
                updated_data = dialog.get_data()
                
                # Import database manager
                from database.database_manager import get_db_manager
                db_manager = get_db_manager()
                
                # Get category ID
                category_name = updated_data['category']
                category_id = None
                
                if category_name:
                    result = db_manager.execute_query(
                        "SELECT id FROM categories WHERE name = ?", 
                        (category_name,)
                    )
                    if result and result[0]:
                        category_id = result[0][0]
                
                # Update database - is_compact state is preserved since we're not updating it here
                # The compact state is handled separately by the TaskPillDelegate
                db_manager.execute_update(
                    """
                    UPDATE tasks 
                    SET title = ?, description = ?, link = ?, status = ?, 
                        priority = ?, due_date = ?, category_id = ?, parent_id = ?
                    WHERE id = ?
                    """, 
                    (
                        updated_data['title'], 
                        updated_data['description'], 
                        updated_data['link'],
                        updated_data['status'], 
                        updated_data['priority'],
                        updated_data['due_date'],
                        category_id,
                        updated_data['parent_id'],
                        updated_data['id']
                    )
                )
                
                # Update item directly
                item.setText(0, updated_data['title'])
                item.setData(0, Qt.ItemDataRole.UserRole, {
                    'id': updated_data['id'],  # Include the ID in user data
                    'title': updated_data['title'],
                    'description': updated_data['description'],
                    'link': updated_data['link'],
                    'status': updated_data['status'],
                    'priority': updated_data['priority'],
                    'due_date': updated_data['due_date'],
                    'category': updated_data['category']
                })
                
                # Handle parent change if needed
                old_parent_id = task_data['parent_id']
                new_parent_id = updated_data['parent_id']
                
                if old_parent_id != new_parent_id:
                    # Remove from old parent
                    old_parent = item.parent()
                    if old_parent:
                        index = old_parent.indexOfChild(item)
                        old_parent.takeChild(index)
                    else:
                        index = self.indexOfTopLevelItem(item)
                        self.takeTopLevelItem(index)
                    
                    # Add to new parent
                    if new_parent_id:
                        # Find new parent and add as child
                        new_parent_found = False
                        for i in range(self.topLevelItemCount()):
                            top_item = self.topLevelItem(i)
                            if top_item.task_id == new_parent_id:
                                top_item.addChild(item)
                                new_parent_found = True
                                break
                            # Search in children
                            if not new_parent_found:
                                self._find_parent_and_add_child(top_item, new_parent_id, item)
                    else:
                        # Move to top level
                        self.addTopLevelItem(item)
                
                # If category changed, update background color
                if task_data['category'] != updated_data['category']:
                    if updated_data['category']:
                        result = db_manager.execute_query(
                            "SELECT color FROM categories WHERE name = ?", 
                            (updated_data['category'],)
                        )
                        if result and result[0]:
                            color = QColor(result[0][0])
                            item.setBackground(0, QBrush(color))
                    else:
                        # Remove background color
                        item.setBackground(0, QBrush())
                
                # Force a repaint
                self.viewport().update()
            
            except Exception as e:
                print(f"Error updating task: {e}")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"Failed to update task: {str(e)}")

    def add_new_task(self, data):
        try:
            # Import database manager
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            # Use a single connection for the entire operation
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get category ID
                category_name = data.get('category')
                category_id = None
                
                if category_name:
                    cursor.execute(
                        "SELECT id FROM categories WHERE name = ?", 
                        (category_name,)
                    )
                    result = cursor.fetchone()
                    if result:
                        category_id = result[0]
                
                # Get next display order
                parent_id = data.get('parent_id')
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
                
                # Check if is_compact column exists
                try:
                    cursor.execute("SELECT is_compact FROM tasks LIMIT 1")
                except sqlite3.OperationalError:
                    # Column doesn't exist, need to add it
                    cursor.execute("ALTER TABLE tasks ADD COLUMN is_compact INTEGER NOT NULL DEFAULT 0")
                    conn.commit()
                    print("Added is_compact column to tasks table")
                
                # Default is_compact value (new tasks are expanded by default)
                is_compact = 0
                
                # Insert new task
                cursor.execute(
                    """
                    INSERT INTO tasks (title, description, link, status, priority, 
                                    due_date, category_id, parent_id, display_order, is_compact)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, 
                    (
                        data.get('title', ''),
                        data.get('description', ''),
                        data.get('link', ''),
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
                
                # Commit changes
                conn.commit()
            
            # Add to tree UI
            new_item = self.add_task_item(
                new_id, 
                data.get('title', ''),
                data.get('description', ''),
                data.get('link', ''),
                data.get('status', 'Not Started'),
                data.get('priority', 'Medium'),
                data.get('due_date', ''),
                category_name,
                is_compact  # Pass the is_compact value
            )
            
            priority = data.get('priority', 'Medium')
            
            # If it has a parent, add it to that parent
            if parent_id:
                # Find parent item and add as child
                parent_item = self._find_item_by_id(parent_id)
                if parent_item:
                    parent_item.addChild(new_item)
            else:
                # Add to appropriate priority header
                for i in range(self.topLevelItemCount()):
                    top_item = self.topLevelItem(i)
                    top_data = top_item.data(0, Qt.ItemDataRole.UserRole)
                    if isinstance(top_data, dict) and top_data.get('is_priority_header', False):
                        if top_data.get('priority') == priority:
                            top_item.addChild(new_item)
                            break
            
            # Force a repaint
            self.viewport().update()
            
            return new_id
        except Exception as e:
            print(f"Error adding new task: {e}")
            # Show error message to user
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Error", f"Failed to add task: {str(e)}")
            return None

    def _find_item_by_id(self, item_id):
        """Find a task item by its ID"""
        # Check all priority headers
        for i in range(self.topLevelItemCount()):
            header_item = self.topLevelItem(i)
            
            # Check all tasks in this priority
            for j in range(header_item.childCount()):
                task_item = header_item.child(j)
                
                # Check if this is the item we want
                task_data = task_item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(task_data, dict) and task_data.get('id') == item_id:
                    return task_item
                
                # Recursively check children
                result = self._find_child_by_id(task_item, item_id)
                if result:
                    return result
        
        return None

    def _find_child_by_id(self, parent_item, item_id):
        """Recursively search for a child item by ID"""
        for i in range(parent_item.childCount()):
            child_item = parent_item.child(i)
            
            # Check if this is the item we want
            child_data = child_item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(child_data, dict) and child_data.get('id') == item_id:
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
            parent_item.addChild(new_item)
            return True
        
        # Check all children
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if self._find_parent_and_add_child(child, parent_id, new_item):
                return True
        
        return False
    
    def setItemHeight(self, item, size_hint):
        """Update the item's height based on the current view mode"""
        if item:
            # Update the item's size hint
            item.setSizeHint(0, size_hint)
            
            # Force a layout update
            self.viewport().update()
            
    def toggle_view_mode(self):
        """Toggle between compact and full view for all tasks"""
        delegate = self.itemDelegate()
        if hasattr(delegate, 'compact_items'):
            # Get all visible items
            items = []
            for i in range(self.topLevelItemCount()):
                items.append(self.topLevelItem(i))
                self._collect_child_items(self.topLevelItem(i), items)
            
            # If any items are in normal view, collapse all. Otherwise, expand all
            any_normal = False
            for item in items:
                user_data = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(user_data, dict) and 'id' in user_data:
                    if user_data['id'] not in delegate.compact_items:
                        any_normal = True
                        break
            
            # Toggle all items
            for item in items:
                user_data = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(user_data, dict) and 'id' in user_data:
                    item_id = user_data['id']
                    if any_normal:  # Make all compact
                        delegate.compact_items.add(item_id)
                    else:  # Make all normal
                        if item_id in delegate.compact_items:
                            delegate.compact_items.remove(item_id)
                    
                    # Update item size
                    height = delegate.compact_height if item_id in delegate.compact_items else delegate.pill_height
                    item.setSizeHint(0, QSize(self.viewport().width(), height + delegate.item_margin * 2))
            
            # Force layout update
            self.scheduleDelayedItemsLayout()
            self.viewport().update()
        
    def _collect_child_items(self, parent_item, items_list):
        """Helper to collect all child items recursively"""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            items_list.append(child)
            self._collect_child_items(child, items_list)
    
    def _collect_child_tasks(self, parent_item, tasks_list):
        """Helper to collect all child task IDs recursively"""
        # Create a temporary list to hold the items
        items = []
        # Use the existing method to collect all child items
        self._collect_child_items(parent_item, items)
        
        # Extract task_id from each item and add to the tasks_list
        for item in items:
            if hasattr(item, 'task_id'):
                tasks_list.append(item.task_id)
    
    def debug_delegate_setup(self):
        """Debug method to verify delegate installation and hover tracking"""
        print("\n===== DELEGATE SETUP DEBUG =====")
        
        # Check if delegate is set
        delegate = self.itemDelegate()
        if delegate is None:
            print("ERROR: No delegate installed")
            return
        
        print(f"Delegate class: {type(delegate).__name__}")
        
        # Check if it's the right type
        if not isinstance(delegate, TaskPillDelegate):
            print(f"ERROR: Wrong delegate type: {type(delegate).__name__}")
            return
        
        print("TaskPillDelegate is correctly installed")
        
        # Check mouse tracking
        print(f"TreeWidget mouse tracking: {self.hasMouseTracking()}")
        print(f"Viewport mouse tracking: {self.viewport().hasMouseTracking()}")
        
        # Check event filter installation - fixed to not use eventFilters()
        print("Event filters cannot be directly inspected, but should be installed")
        
        # Check if compact_items set exists and is loaded
        if hasattr(delegate, 'compact_items'):
            print(f"compact_items set exists with {len(delegate.compact_items)} items")
            print(f"Items in compact state: {delegate.compact_items}")
        else:
            print("ERROR: No compact_items set found in delegate")
        
        print("===== END DEBUG =====\n")
        
        # Force a viewport update to ensure proper redrawing
        self.viewport().update()
        
    def debug_toggle_buttons(self):
        """Debug method to force toggle buttons to appear on all items"""
        delegate = self.itemDelegate()
        if isinstance(delegate, TaskPillDelegate):
            print("Forcing toggle buttons to appear on all items")
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
                    print(f"Set toggle button for item at index {item_index.row()}")
                
                # Add the method to the delegate
                from types import MethodType
                delegate.show_toggle_button = MethodType(show_toggle_button, delegate)
            
            # Now show buttons for all top-level items
            for i in range(self.topLevelItemCount()):
                index = self.model().index(i, 0)
                delegate.show_toggle_button(self, index)
                
                # Also add for child items
                item = self.topLevelItem(i)
                self._debug_add_buttons_to_children(item, delegate)
        
        # Force repaint to show the buttons
        self.viewport().update()
        print("Forced viewport update to show toggle buttons")

    def _debug_add_buttons_to_children(self, parent_item, delegate):
        """Helper for debug_toggle_buttons to add buttons to child items"""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            index = self.indexFromItem(child)
            delegate.show_toggle_button(self, index)
            # Recursively add to this child's children
            self._debug_add_buttons_to_children(child, delegate)
            
    def get_settings_manager(self):
        """Get the settings manager instance"""
        try:
            # Try to get it from the tree widget's parent (MainWindow)
            if hasattr(self, 'parent') and callable(self.parent) and hasattr(self.parent(), 'settings'):
                return self.parent().settings
        except:
            pass
        
        # Fallback to creating a new instance
        from ui.app_settings import SettingsManager
        return SettingsManager()

    def debug_headers(self):
        """Debug the header items"""
        delegate = self.itemDelegate()
        if isinstance(delegate, TaskPillDelegate):
            delegate.debug_header_items(self)
        else:
            print("Delegate is not a TaskPillDelegate")

    def mousePressEvent(self, event):
        """Handle mouse press events including priority header toggle"""
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
                    self._header_toggle_item = item
                    event.accept()
                    return
                
                # For regular task items, don't interfere - let double-click work normally
        except Exception as e:
            print(f"Error in mousePressEvent: {e}")
        
        # Handle regular mouse press events
        super().mousePressEvent(event)

    def handle_double_click(self, item, column):
        """Handle double-click events with special case for priority headers"""
        # Get the item data
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Check if this is a priority header
        if isinstance(data, dict) and data.get('is_priority_header', False):
            # Toggle the header
            self.blockSignals(True)
            
            # Convert item to index for isExpanded method
            item_index = self.indexFromItem(item)
            
            # Check current expanded state
            if self.isExpanded(item_index):
                self.collapseItem(item)
                data['expanded'] = False
            else:
                self.expandItem(item)
                data['expanded'] = True
                
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            self.blockSignals(False)
            self._save_priority_expanded_states()
            return
        
        # Skip if not a task item
        if not hasattr(item, 'task_id'):
            return
        
        # Get the position of the double-click
        pos = self.mapFromGlobal(self.cursor().pos())
        rect = self.visualItemRect(item)
        
        # Calculate the right section boundary (where the link area begins)
        # This should match the width used in the delegate's _draw_right_panel method
        right_section_width = 100  # Same as in TaskPillDelegate
        right_section_boundary = rect.right() - right_section_width
        
        # Check if the click was in the right section (link area)
        if 'link' in data and data['link'] and pos.x() > right_section_boundary:
            # Handle link click
            link = data['link']
            if not link.startswith(('http://', 'https://')):
                link = 'https://' + link
            try:
                import webbrowser
                webbrowser.open(link)
            except Exception as e:
                print(f"Error opening link: {e}")
        else:
            # For clicks in the main content area, open edit dialog
            self.edit_task(item)

    def _save_priority_expanded_states(self):
        """Save the expanded state of priority headers to settings"""
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
            
            # Save to settings
            settings = self.get_settings_manager()
            settings.set_setting("expanded_priorities", expanded_priorities)
        except Exception as e:
            print(f"Error saving priority expanded states: {e}")

    def debug_priority_headers(self):
        """Debug method for priority headers specifically"""
        print("\n===== PRIORITY HEADERS DEBUG =====")
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            
            if isinstance(data, dict) and data.get('is_priority_header', False):
                priority = data.get('priority', 'Unknown')
                expanded = data.get('expanded', True)
                is_expanded = self.isItemExpanded(item)
                
                print(f"Header {i}: {priority}")
                print(f"  - Data expanded: {expanded}")
                print(f"  - Tree expanded: {is_expanded}")
                print(f"  - Child count: {item.childCount()}")
                print(f"  - Flags: {item.flags()}")
        
        # Get expanded states from settings
        settings = self.get_settings_manager()
        saved_expanded = settings.get_setting("expanded_priorities", [])
        print(f"Settings expanded priorities: {saved_expanded}")
        print("===== END DEBUG =====\n")
        
    def toggle_priority_header(self, header_item):
        """Directly toggle a priority header item with improved visual state control"""
        print(f"Toggling priority header: {header_item.text(0)}")
        
        # Get current data
        data = header_item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict):
            print("Warning: Priority header doesn't have proper data")
            return
        
        # Get current expanded state
        expanded = data.get('expanded', True)
        
        # Toggle state and update tree with a slight delay to ensure visual update
        if expanded:
            # Force a collapse
            self.collapseItem(header_item)
            # Update data
            data['expanded'] = False
            header_item.setData(0, Qt.ItemDataRole.UserRole, data)
            print(f"Collapsing priority header: {header_item.text(0)}")
        else:
            # Force an expand
            self.expandItem(header_item)
            # Update data
            data['expanded'] = True
            header_item.setData(0, Qt.ItemDataRole.UserRole, data)
            print(f"Expanding priority header: {header_item.text(0)}")
        
        # Save expanded states to settings
        self._save_priority_expanded_states()
        
        # Force a complete layout update
        self.scheduleDelayedItemsLayout()
        self.viewport().update()

    def synchronize_priority_headers(self):
        """Ensure all priority headers have visual states matching their logical states"""
        print("Synchronizing priority header states...")
        
        # Get expanded priorities from settings
        settings = self.get_settings_manager()
        expanded_priorities = settings.get_setting("expanded_priorities", [])
        print(f"Expanded priorities from settings: {expanded_priorities}")
        
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
                    print(f"Expanded header: {priority}")
                else:
                    self.collapseItem(item)
                    print(f"Collapsed header: {priority}")
        
        # Force layout update
        self.scheduleDelayedItemsLayout()
        self.viewport().update()

    def load_tasks(self):
        try:
            self.clear()
            
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
            for priority, color in priority_colors.items():
                header_item = PriorityHeaderItem(priority, color)
                self.addTopLevelItem(header_item)
                priority_headers[priority] = header_item
            
            # Check if is_compact column exists
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT is_compact FROM tasks LIMIT 1")
            except sqlite3.OperationalError:
                # Column doesn't exist, need to add it
                cursor.execute("ALTER TABLE tasks ADD COLUMN is_compact INTEGER NOT NULL DEFAULT 0")
                conn.commit()
                print("Added is_compact column to tasks table")
            
            # Get all tasks
            tasks = db_manager.execute_query(
                """
                SELECT t.id, t.title, t.description, t.link, t.status, t.priority, 
                    t.due_date, c.name, t.is_compact, t.parent_id
                FROM tasks t
                LEFT JOIN categories c ON t.category_id = c.id
                ORDER BY t.parent_id NULLS FIRST, t.display_order
                """
            )
            
            items = {}
            # First pass: create all items
            for row in tasks:
                task_id = row[0]
                priority = row[5] or "Medium"  # Default to Medium if None
                
                # Create the task item
                item = self.add_task_item(*row[:9])  # First 9 elements
                items[task_id] = item
                
                # Store parent info for second pass
                parent_id = row[9]  # Last element is parent_id
                if parent_id is None:
                    # This is a top-level task, add it to the priority header
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
            
            # Instead of just setting the expanded state in the data, make sure to
            # synchronize the visual state with the stored state
            self.synchronize_priority_headers()
            
        except Exception as e:
            print(f"Error loading tasks: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Error", f"Failed to load tasks: {str(e)}")

    def onItemExpanded(self, item):
        """Keep data in sync when item is expanded by the tree widget"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and data.get('is_priority_header', False):
            # Update data
            data['expanded'] = True
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            print(f"Header expanded by tree: {data.get('priority')}")
            
            # Save to settings
            self._save_priority_expanded_states()

    def onItemCollapsed(self, item):
        """Keep data in sync when item is collapsed by the tree widget"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and data.get('is_priority_header', False):
            # Update data
            data['expanded'] = False
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            print(f"Header collapsed by tree: {data.get('priority')}")
            
            # Save to settings
            self._save_priority_expanded_states()

    def mouseReleaseEvent(self, event):
        """Handle mouse release events, including delayed priority header toggle"""
        try:
            # Check if we have a stored header toggle item
            if hasattr(self, '_header_toggle_item') and self._header_toggle_item is not None:
                # Block signals to prevent unwanted events
                self.blockSignals(True)
                
                # Get item data
                item = self._header_toggle_item
                data = item.data(0, Qt.ItemDataRole.UserRole)
                
                # Convert item to index for isExpanded method
                item_index = self.indexFromItem(item)
                
                # Get current expanded state from visual state
                currently_expanded = self.isExpanded(item_index)
                
                # Toggle state
                if currently_expanded:
                    self.collapseItem(item)
                    # Update data
                    data['expanded'] = False
                else:
                    self.expandItem(item)
                    # Update data
                    data['expanded'] = True
                
                # Update item data
                item.setData(0, Qt.ItemDataRole.UserRole, data)
                
                # Save expanded states to settings
                self._save_priority_expanded_states()
                
                # Restore signals
                self.blockSignals(False)
                
                # Force update
                self.viewport().update()
                
                # Clear the stored item
                self._header_toggle_item = None
                
                event.accept()
                return
        except Exception as e:
            print(f"Error in mouseReleaseEvent: {e}")
        
        # Handle regular mouse release events
        super().mouseReleaseEvent(event)

    def onItemDoubleClicked(self, item, column):
        """Route double-clicks to appropriate handlers based on item type"""
        print(f"Double-click detected on item: {item.text(0)}")
        
        # Get the item data
        data = item.data(0, Qt.ItemDataRole.UserRole)
        print(f"Item data: {data}")
        
        # Check if this is a priority header
        if isinstance(data, dict) and data.get('is_priority_header', False):
            print("This is a priority header - routing to handleHeaderDoubleClick")
            self.handleHeaderDoubleClick(item)
        elif hasattr(item, 'task_id'):
            # This is a task item
            print(f"This is a task item (ID: {item.task_id}) - routing to handleTaskDoubleClick")
            self.handleTaskDoubleClick(item)
        else:
            print(f"Unknown item type - no handler available")

    def handleHeaderDoubleClick(self, item):
        """Handle double-click on priority headers"""
        # Get item data
        data = item.data(0, Qt.ItemDataRole.UserRole)
        priority = data.get('priority', 'Unknown')
        
        print(f"Double-clicked priority header: {priority}")
        
        # Disconnect the itemExpanded/itemCollapsed signals temporarily
        self.itemExpanded.disconnect(self.onItemExpanded)
        self.itemCollapsed.disconnect(self.onItemCollapsed)
        
        # Convert item to index for isExpanded method
        item_index = self.indexFromItem(item)
        
        # Check current expanded state
        currently_expanded = self.isExpanded(item_index)
        
        # Toggle state
        if currently_expanded:
            print(f"Collapsing header: {priority}")
            self.collapseItem(item)
            data['expanded'] = False
        else:
            print(f"Expanding header: {priority}")
            self.expandItem(item)
            data['expanded'] = True
        
        # Update item data
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        
        # Force update
        self.viewport().update()
        
        # Save expanded states
        self._save_priority_expanded_states()
        
        # Reconnect the signals after a short delay
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self.reconnectExpandCollapsedSignals)

    def handleTaskDoubleClick(self, item):
        """Handle double-click on task items"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        print(f"Double-clicked task: {data.get('title', 'Unknown')}")
        
        # Get the position of the double-click
        pos = self.mapFromGlobal(self.cursor().pos())
        rect = self.visualItemRect(item)
        
        # Calculate the right section boundary (where the link area begins)
        # This should match the width used in the delegate's _draw_right_panel method
        right_section_width = 100  # Same as in TaskPillDelegate
        right_section_boundary = rect.right() - right_section_width
        
        # Check if the click was in the right section (link area)
        if 'link' in data and data['link'] and pos.x() > right_section_boundary:
            # Handle link click
            link = data['link']
            if not link.startswith(('http://', 'https://')):
                link = 'https://' + link
            try:
                import webbrowser
                webbrowser.open(link)
            except Exception as e:
                print(f"Error opening link: {e}")
        else:
            # For clicks in the main content area, open edit dialog
            self.edit_task(item)
            
    def reconnectExpandCollapsedSignals(self):
        """Reconnect the expand/collapse signals"""
        try:
            self.itemExpanded.connect(self.onItemExpanded)
            self.itemCollapsed.connect(self.onItemCollapsed)
        except Exception as e:
            print(f"Error reconnecting signals: {e}")

class PriorityHeaderItem(QTreeWidgetItem):
    """Custom tree widget item for priority headers"""
    
    def __init__(self, priority_name, priority_color):
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
        
        # Use custom height
        self.setSizeHint(0, QSize(0, 25))