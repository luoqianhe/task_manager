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
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        
        # Change to just one column
        self.setColumnCount(1)
        self.setHeaderLabels(['Tasks'])
        
        # Hide the header
        self.setHeaderHidden(True)
        self.setIndentation(40)  # Increased indentation for better hierarchy view
        
        # Apply the custom delegate
        self.setItemDelegate(TaskPillDelegate(self))
        
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
        self.itemDoubleClicked.connect(self.handle_double_click)
        
        # Load tasks
        try:
            self.load_tasks()
        except Exception as e:
            print(f"Error loading tasks: {e}")

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
        item = self.currentItem()
        super().dropEvent(event)
        
        try:
            # Save new parent-child relationships to database
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            def update_item_parent(item):
                parent_id = item.parent().task_id if item.parent() else None
                db_manager.execute_update(
                    """
                    UPDATE tasks 
                    SET parent_id = ?
                    WHERE id = ?
                    """, 
                    (parent_id, item.task_id)
                )
                
                # Update all children too
                for i in range(item.childCount()):
                    update_item_parent(item.child(i))
            
            update_item_parent(item)
        except Exception as e:
            print(f"Error updating task parent: {e}")
            QMessageBox.critical(self, "Error", f"Failed to update task hierarchy: {str(e)}")

    def change_status(self, item, new_status):
        try:
            # Update database
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            db_manager.execute_update(
                "UPDATE tasks SET status = ? WHERE id = ?", 
                (new_status, item.task_id)
            )
            
            # Update item
            data = item.data(0, Qt.ItemDataRole.UserRole)
            data['status'] = new_status
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            
            # Force a repaint
            self.viewport().update()
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

    def add_task_item(self, task_id, title, description, link, status, priority, due_date, category):
        # Create a single-column item
        item = QTreeWidgetItem([title or ""])
        
        # Debug: Print the status to see if it's being passed in correctly
        print(f"Adding task: {title} with status: {status}")
        
        # Store all data as item data
        item.setData(0, Qt.ItemDataRole.UserRole, {
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
        
        # Set item height
        delegate = self.itemDelegate()
        if isinstance(delegate, TaskPillDelegate):
            item.setSizeHint(0, QSize(100, delegate.pill_height + delegate.item_margin * 2))
        
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
        
        # Get current data from the item's user role data
        data = item.data(0, Qt.ItemDataRole.UserRole)
        task_data = {
            'id': item.task_id,
            'title': data['title'],
            'description': data['description'],
            'link': data['link'],
            'status': data['status'],
            'priority': data['priority'],
            'due_date': data['due_date'],
            'category': data['category'],
            'parent_id': item.parent().task_id if item.parent() else None
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
                
                # Update database
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

    def handle_double_click(self, item, column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data['link']:  # Link column
            link = data['link']
            if not link.startswith(('http://', 'https://')):
                link = 'https://' + link
            try:
                webbrowser.open(link)
            except Exception as e:
                print(f"Error opening link: {e}")
        else:
            # For other columns, open edit dialog
            self.edit_task(item)

    def load_tasks(self):
        try:
            self.clear()
            
            # Import database manager
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            # Get priority order map
            priority_order = {}
            result = db_manager.execute_query(
                "SELECT name, display_order FROM priorities ORDER BY display_order"
            )
            for name, order in result:
                priority_order[name] = order
            
            # Select top-level tasks and join with priorities to sort by priority order
            top_level_tasks = db_manager.execute_query(
                """
                SELECT t.id, t.title, t.description, t.link, t.status, t.priority, 
                    t.due_date, c.name 
                FROM tasks t
                LEFT JOIN categories c ON t.category_id = c.id
                LEFT JOIN priorities p ON t.priority = p.name
                WHERE t.parent_id IS NULL 
                ORDER BY p.display_order, t.display_order
                """
            )
            
            items = {}
            for row in top_level_tasks:
                item = self.add_task_item(*row)
                items[row[0]] = item
                self.addTopLevelItem(item)
            
            # Select child tasks
            child_tasks = db_manager.execute_query(
                """
                SELECT t.id, t.title, t.description, t.link, t.status, t.priority, 
                    t.due_date, c.name, t.parent_id
                FROM tasks t
                LEFT JOIN categories c ON t.category_id = c.id
                LEFT JOIN priorities p ON t.priority = p.name
                WHERE t.parent_id IS NOT NULL 
                ORDER BY t.parent_id, p.display_order, t.display_order
                """
            )
            
            for row in child_tasks:
                item = self.add_task_item(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7])
                parent_id = row[8]
                if parent_id in items:
                    items[parent_id].addChild(item)
                    items[row[0]] = item  # Add this child to the items dict too
        
        except Exception as e:
            print(f"Error loading tasks: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Error", f"Failed to load tasks: {str(e)}")

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
                
                # Insert new task
                cursor.execute(
                    """
                    INSERT INTO tasks (title, description, link, status, priority, 
                                    due_date, category_id, parent_id, display_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        display_order
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
                category_name
            )
            
            # Add to appropriate parent
            if parent_id:
                # Find parent item and add as child
                for i in range(self.topLevelItemCount()):
                    item = self.topLevelItem(i)
                    if item.task_id == parent_id:
                        item.addChild(new_item)
                        break
                    # Check children recursively
                    if item.childCount() > 0:
                        self._find_parent_and_add_child(item, parent_id, new_item)
            else:
                self.addTopLevelItem(new_item)
            
            # Force a repaint
            self.viewport().update()
            
            return new_id
        except Exception as e:
            print(f"Error adding new task: {e}")
            # Show error message to user
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Error", f"Failed to add task: {str(e)}")
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