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
        self.itemDoubleClicked.connect(self.handle_double_click)
        
        # Load tasks
        try:
            self.load_tasks()
        except Exception as e:
            print(f"Error loading tasks: {e}")
        
        # Debug delegate setup
        self.debug_delegate_setup()
    
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

    def mousePressEvent(self, event):
        """Handle mouse press events including priority header toggle"""
        index = self.indexAt(event.position().toPoint())
        if index.isValid():
            item = self.itemFromIndex(index)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            
            # Check if this is a priority header
            if isinstance(data, dict) and data.get('is_priority_header', False):
                # Check if click is in the arrow area (left 40 pixels)
                if event.position().x() < 40:
                    # Toggle expanded state
                    expanded = data.get('expanded', True)
                    
                    # Toggle the state
                    if expanded:
                        self.collapseItem(item)
                        data['expanded'] = False
                    else:
                        self.expandItem(item)
                        data['expanded'] = True
                    
                    # Update the item data
                    item.setData(0, Qt.ItemDataRole.UserRole, data)
                    
                    # Save expanded state to settings
                    expanded_priorities = []
                    for i in range(self.topLevelItemCount()):
                        top_item = self.topLevelItem(i)
                        top_data = top_item.data(0, Qt.ItemDataRole.UserRole)
                        if isinstance(top_data, dict) and top_data.get('is_priority_header', False):
                            # Check if the item is expanded
                            if not top_data.get('expanded', True):
                                continue
                            expanded_priorities.append(top_data.get('priority'))
                    
                    settings = self.get_settings_manager()
                    settings.set_setting("expanded_priorities", expanded_priorities)
                    
                    # Force update
                    self.viewport().update()
                    event.accept()  # Mark the event as handled
                    return  # Return without a value instead of returning True
        
        # Handle regular mouse press events
        super().mousePressEvent(event)

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

    def handle_double_click(self, item, column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Check if this is a priority header
        if isinstance(data, dict) and data.get('is_priority_header', False):
            # Toggle expanded state for priority headers on double-click
            expanded = data.get('expanded', True)
            data['expanded'] = not expanded
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            
            if expanded:
                self.collapseItem(item)
            else:
                self.expandItem(item)
            
            return  # Exit early for priority headers
        
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
                webbrowser.open(link)
            except Exception as e:
                print(f"Error opening link: {e}")
        else:
            # For clicks in the main content area, open edit dialog
            self.edit_task(item)

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
            
            # Restore expanded state of priority headers from settings
            settings = self.get_settings_manager()
            all_priorities = list(priority_colors.keys())
            expanded_priorities = settings.get_setting("expanded_priorities", all_priorities)
            
            for priority, header_item in priority_headers.items():
                if priority in expanded_priorities:
                    self.expandItem(header_item)
                    header_item.setData(0, Qt.ItemDataRole.UserRole, {
                        'is_priority_header': True,
                        'priority': priority,
                        'color': priority_colors[priority],
                        'expanded': True
                    })
                else:
                    self.collapseItem(header_item)
                    header_item.setData(0, Qt.ItemDataRole.UserRole, {
                        'is_priority_header': True,
                        'priority': priority,
                        'color': priority_colors[priority],
                        'expanded': False
                    })
        
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
        
        # Make it not selectable, but still draggable for reordering
        self.setFlags(self.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        
        # Set the background color
        self.setBackground(0, QBrush(QColor(priority_color)))
        
        # Use custom height
        self.setSizeHint(0, QSize(0, 25))