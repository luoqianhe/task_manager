# src/ui/combined_settings.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QListWidget, QListWidgetItem,
                             QColorDialog, QMessageBox, QDialog, QScrollArea,
                             QComboBox, QFrame, QSizePolicy, QApplication)
from PyQt6.QtGui import QColor, QBrush, QDrag
from PyQt6.QtCore import Qt, QSize, QMimeData, QPoint
from pathlib import Path
import sqlite3
import json

# Base class for setting items with consistent pill style
class SettingPillItem(QWidget):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    def __init__(self, item_id, name, color, display_order=None, item_type="category"):
        super().__init__()
        self.item_id = item_id
        self.display_order = display_order
        self.item_type = item_type  # "category", "priority", or "status"
        self.name = name  # Store the name for drag-drop identification
        self.color = color  # Store the color for reference
        self.setAcceptDrops(True)  # Enable drops
        
        # Create a frame to serve as the colored background
        self.frame = QFrame(self)
        self.frame.setObjectName("coloredFrame")
        self.frame.setStyleSheet(f"#coloredFrame {{ background-color: {color}; border-radius: 5px; }}")
        
        # Create a consistent layout for all pill types
        layout = QHBoxLayout(self.frame)
        layout.setContentsMargins(15, 17, 15, 17)  # Consistent padding
        layout.setSpacing(10)  # Space between controls
        
        # Item name with larger font - white text
        name_label = QLabel(name)
        name_label.setStyleSheet("font-weight: bold; font-size: 14px; color: white;")
        layout.addWidget(name_label)
        
        # Add stretch to push buttons to the right
        layout.addStretch()
        
        # Add grip handle icon to indicate draggable - white color
        drag_icon = QLabel("☰")  # Unicode hamburger/grip icon
        drag_icon.setStyleSheet("font-size: 16px; color: white;")
        drag_icon.setToolTip("Drag to reorder")
        layout.addWidget(drag_icon)
        
        # Color indicator and edit button - white circle with text
        color_btn = QPushButton("Edit Color")
        color_btn.setFixedSize(80, 30)
        color_btn.setStyleSheet("background-color: white; color: #333; border-radius: 5px; border: none;")
        color_btn.clicked.connect(self.change_color)
        layout.addWidget(color_btn)
        
        # Edit button - white background
        edit_btn = QPushButton("Edit Name")
        edit_btn.setFixedSize(80, 30)
        edit_btn.setStyleSheet("background-color: white; color: #333; border-radius: 5px; border: none;")
        edit_btn.clicked.connect(self.edit_item)
        layout.addWidget(edit_btn)
        
        # Delete button - white background - disabled for Completed status
        delete_btn = QPushButton("Delete")
        delete_btn.setFixedSize(80, 30)
        delete_btn.clicked.connect(self.delete_item)
        
        # Disable deletion of "Completed" status
        if item_type == "status" and name == "Completed":
            delete_btn.setEnabled(False)
            delete_btn.setToolTip("The Completed status cannot be deleted")
            delete_btn.setStyleSheet("background-color: #e0e0e0; color: #888; border-radius: 5px; border: none;")
        else:
            delete_btn.setStyleSheet("background-color: white; color: #333; border-radius: 5px; border: none;")
        
        layout.addWidget(delete_btn)
        
        # Main layout for this widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.frame)
        
        self.setFixedHeight(60)  # Consistent height for all items


    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.display_order is not None:
            # Start drag if this is a priority or status (has display_order)
            self.drag_start_position = event.position().toPoint()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton) or self.display_order is None:
            # Only allow drag for items with display_order (priorities and statuses)
            super().mouseMoveEvent(event)
            return
            
        # Calculate distance to see if we should start a drag
        if (event.position().toPoint() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return
            
        # Start drag operation
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Store item data in mime data for drop handling
        data = {
            'item_id': self.item_id,
            'item_type': self.item_type,
            'display_order': self.display_order,
            'name': self.name
        }
        mime_data.setText(json.dumps(data))
        drag.setMimeData(mime_data)
        
        # Create a pixmap of this widget as drag visual
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.position().toPoint())
        
        # Execute drag
        drag.exec(Qt.DropAction.MoveAction)
    
    def dragEnterEvent(self, event):
        # Only accept drags from same type of items
        if event.mimeData().hasText():
            try:
                data = json.loads(event.mimeData().text())
                if data['item_type'] == self.item_type and data['item_id'] != self.item_id:
                    event.acceptProposedAction()
                    return
            except (json.JSONDecodeError, KeyError):
                pass
        event.ignore()
    
    def dropEvent(self, event):
        # Handle item reordering
        if event.mimeData().hasText():
            try:
                data = json.loads(event.mimeData().text())
                
                # Find parent CombinedSettingsManager
                parent = self
                while parent and not isinstance(parent, CombinedSettingsManager):
                    parent = parent.parent()
                
                if parent:
                    # Call reorder method with source and target ids
                    parent.reorder_items(
                        self.item_type,
                        data['item_id'],  # Source item
                        self.item_id      # Target item (where to drop)
                    )
                    event.acceptProposedAction()
            except (json.JSONDecodeError, KeyError):
                event.ignore()
        else:
            event.ignore()
    
    def change_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            new_color = color.name()
            self.update_color_in_db(new_color)
            self.setStyleSheet(f"background-color: {new_color}; border-radius: 5px;")
            
            # Update color button
            for child in self.findChildren(QPushButton):
                if child.width() == 30 and child.height() == 30:
                    child.setStyleSheet(f"background-color: {new_color}; border-radius: 15px;")
                    break
    
    def change_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            new_color = color.name()
            self.update_color_in_db(new_color)
            
            # Update the stored color
            self.color = new_color
            
            # Update the frame background
            self.frame.setStyleSheet(f"#coloredFrame {{ background-color: {new_color}; border-radius: 5px; }}")
    
    def update_color_in_db(self, color):
        # Get correct table name (handle special plurals)
        if self.item_type == "status":
            table_name = "statuses"
        elif self.item_type == "priority":
            table_name = "priorities"
        else:
            table_name = f"{self.item_type}s"  # categories
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE {table_name} SET color = ? WHERE id = ?",
                         (color, self.item_id))
            conn.commit()
    
    def edit_item(self):
        # Find the CombinedSettingsManager instance
        parent = self
        while parent and not isinstance(parent, CombinedSettingsManager):
            parent = parent.parent()
        
        if parent:
            parent.edit_item(self.item_type, self.item_id)

    def delete_item(self):
        # Don't allow deletion of Completed status
        if self.item_type == "status" and self.name == "Completed":
            QMessageBox.information(self, "Cannot Delete", 
                                   "The Completed status cannot be deleted as it's required by the system.")
            return
            
        reply = QMessageBox.question(self, f'Delete {self.item_type.title()}', 
                                f'Are you sure you want to delete this {self.item_type}?',
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # Find the CombinedSettingsManager instance
            parent = self
            while parent and not isinstance(parent, CombinedSettingsManager):
                parent = parent.parent()
            
            if parent:
                parent.delete_item(self.item_type, self.item_id)

# Main class for combined settings management
class CombinedSettingsManager(QWidget):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_all_items()
        self.setStyleSheet("""
            QPushButton { 
                background-color: #f0f0f0;
                color: black;
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:disabled {
                background-color: #e0e0e0;
                color: #888888;
            }
            QLineEdit {
                max-height: 25px;
                padding: 2px 5px;
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
                color: black;
            }
            QListWidget {
                border: 1px solid #cccccc;
                background-color: white;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 1px;
                margin: 1px;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 5px;
                background-color: white;
            }
        """)
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header_label = QLabel("Task Organization Settings")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(header_label)
        
        # Description
        desc_label = QLabel("Manage categories, priorities, and statuses for your tasks.")
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)
        
        # Setting type selector
        selector_layout = QHBoxLayout()
        selector_layout.setContentsMargins(0, 10, 0, 10)
        
        self.setting_type_label = QLabel("Setting Type:")
        self.setting_type_label.setStyleSheet("font-weight: bold;")
        
        self.setting_type_combo = QComboBox()
        self.setting_type_combo.addItems(["Categories", "Priorities", "Statuses"])
        self.setting_type_combo.currentTextChanged.connect(self.change_setting_view)
        self.setting_type_combo.setFixedHeight(30)
        self.setting_type_combo.setMinimumWidth(150)
        
        selector_layout.addWidget(self.setting_type_label)
        selector_layout.addWidget(self.setting_type_combo)
        selector_layout.addStretch()
        
        main_layout.addLayout(selector_layout)
        
        # Create a scroll area for the list widgets
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Container for list widgets
        self.lists_container = QWidget()
        self.lists_layout = QVBoxLayout(self.lists_container)
        self.lists_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create list widgets for each setting type
        self.categories_list = QListWidget()
        self.categories_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.categories_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #cccccc;
                background-color: white;
                border-radius: 5px;
                spacing: 0px;
            }
            QListWidget::item {
                padding: 0px;
                margin: 0px;
            }
        """)
        self.categories_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        
        self.priorities_list = QListWidget()
        self.priorities_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.priorities_list.setStyleSheet(self.categories_list.styleSheet())
        self.priorities_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        
        self.statuses_list = QListWidget()
        self.statuses_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.statuses_list.setStyleSheet(self.categories_list.styleSheet())
        self.statuses_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        
        # Add all lists to the container but only show one
        self.lists_layout.addWidget(self.categories_list)
        self.lists_layout.addWidget(self.priorities_list)
        self.lists_layout.addWidget(self.statuses_list)
        
        # Only show the first list initially
        self.priorities_list.hide()
        self.statuses_list.hide()
        
        # Set the scroll area widget
        scroll_area.setWidget(self.lists_container)
        main_layout.addWidget(scroll_area, 1)  # 1 = stretch factor
        
        # Add new item form
        form_layout = QHBoxLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name")
        self.name_input.setFixedHeight(30)
        
        self.color_btn = QPushButton("Pick Color")
        self.color_btn.setFixedHeight(30)
        self.color_btn.clicked.connect(self.pick_color)
        
        self.add_btn = QPushButton("Add Item")
        self.add_btn.setFixedHeight(30)
        self.add_btn.clicked.connect(self.add_item)
        
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(self.color_btn)
        form_layout.addWidget(self.add_btn)
        
        main_layout.addLayout(form_layout)
        self.setLayout(main_layout)
    
    def pick_color(self):
        self.selected_color = QColorDialog.getColor().name()
        self.color_btn.setStyleSheet(f"background-color: {self.selected_color}; border-radius: 5px;")
    
    def change_setting_view(self, setting_type):
        """Switch between different setting views"""
        # Hide all lists
        self.categories_list.hide()
        self.priorities_list.hide()
        self.statuses_list.hide()
        
        # Show the selected list
        if setting_type == "Categories":
            self.categories_list.show()
            self.add_btn.setText("Add Category")
            self.name_input.setPlaceholderText("Category Name")
        elif setting_type == "Priorities":
            self.priorities_list.show()
            self.add_btn.setText("Add Priority")
            self.name_input.setPlaceholderText("Priority Name")
        else:  # Statuses
            self.statuses_list.show()
            self.add_btn.setText("Add Status")
            self.name_input.setPlaceholderText("Status Name")
    
    def load_all_items(self):
        """Load all categories, priorities, and statuses"""
        self.load_categories()
        self.load_priorities()
        self.load_statuses()
    
    def load_categories(self):
        """Load categories from the database"""
        self.categories_list.clear()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categories ORDER BY name")
            categories = cursor.fetchall()
            
            for category in categories:
                # Create a pill item for each category
                category_widget = SettingPillItem(
                    category[0],  # id
                    category[1],  # name
                    category[2],  # color
                    None,         # no display_order for categories
                    "category"    # item type
                )
                
                # Create a list item and set its size
                item = QListWidgetItem(self.categories_list)
                item.setSizeHint(QSize(category_widget.sizeHint().width(), 60))
                
                # Add the widget to the list item
                self.categories_list.setItemWidget(item, category_widget)
    
    def load_priorities(self):
        """Load priorities from the database"""
        self.priorities_list.clear()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, color, display_order FROM priorities ORDER BY display_order")
            priorities = cursor.fetchall()
            
            for priority in priorities:
                # Create a pill item for each priority
                priority_widget = SettingPillItem(
                    priority[0],  # id
                    priority[1],  # name
                    priority[2],  # color
                    priority[3],  # display_order
                    "priority"    # item type
                )
                
                # Create a list item and set its size
                item = QListWidgetItem(self.priorities_list)
                item.setSizeHint(QSize(priority_widget.sizeHint().width(), 60))
                
                # Add the widget to the list item
                self.priorities_list.setItemWidget(item, priority_widget)
    
    def load_statuses(self):
        """Load statuses from the database"""
        self.statuses_list.clear()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, color, display_order FROM statuses ORDER BY display_order")
            statuses = cursor.fetchall()
            
            for status in statuses:
                # Create a pill item for each status
                status_widget = SettingPillItem(
                    status[0],  # id
                    status[1],  # name
                    status[2],  # color
                    status[3],  # display_order
                    "status"    # item type
                )
                
                # Create a list item and set its size
                item = QListWidgetItem(self.statuses_list)
                item.setSizeHint(QSize(status_widget.sizeHint().width(), 60))
                
                # Add the widget to the list item
                self.statuses_list.setItemWidget(item, status_widget)
    
    def reorder_items(self, item_type, source_id, target_id):
        """Handle reordering via drag and drop"""
        if item_type not in ["priority", "status"]:
            return  # Only ordered types can be reordered
            
        # Get correct table name (handle special plurals)
        if item_type == "status":
            table_name = "statuses"
        elif item_type == "priority":
            table_name = "priorities"
        else:
            return  # Should never happen
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current display orders
            cursor.execute(f"SELECT id, display_order FROM {table_name} ORDER BY display_order")
            items = cursor.fetchall()
            
            # Find source and target orders
            source_order = next((order for id, order in items if id == source_id), None)
            target_order = next((order for id, order in items if id == target_id), None)
            
            if source_order is None or target_order is None:
                return
            
            # Determine direction of move
            if source_order < target_order:
                # Moving down: decrement items in between
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET display_order = display_order - 1
                    WHERE display_order > ? AND display_order <= ?
                """, (source_order, target_order))
            else:
                # Moving up: increment items in between
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET display_order = display_order + 1
                    WHERE display_order < ? AND display_order >= ?
                """, (source_order, target_order))
            
            # Set the dragged item to its new position
            cursor.execute(f"""
                UPDATE {table_name}
                SET display_order = ?
                WHERE id = ?
            """, (target_order, source_id))
            
            conn.commit()
        
        # Reload the appropriate list
        if item_type == "priority":
            self.load_priorities()
        elif item_type == "status":
            self.load_statuses()
    
    def edit_item(self, item_type, item_id):
        """Open dialog to edit an item"""
        dialog = EditItemDialog(item_type, item_id, self)
        if dialog.exec():
            # Reload the appropriate list
            if item_type == "category":
                self.load_categories()
            elif item_type == "priority":
                self.load_priorities()
            elif item_type == "status":
                self.load_statuses()
    
    def delete_item(self, item_type, item_id):
        """Delete an item after confirmation"""
        # Get correct table name (handle special plurals)
        if item_type == "status":
            table_name = "statuses"
        elif item_type == "priority":
            table_name = "priorities"
        else:
            table_name = f"{item_type}s"  # categories
            
        foreign_key = f"{item_type}_id" if item_type == "category" else item_type
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # First check if it's the Completed status
            if item_type == "status":
                cursor.execute("SELECT name FROM statuses WHERE id = ?", (item_id,))
                name = cursor.fetchone()[0]
                if name == "Completed":
                    QMessageBox.warning(self, "Cannot Delete", 
                                    "The Completed status cannot be deleted as it's required by the system.")
                    return
            
            # Check if any tasks are using this item
            if item_type == "category":
                cursor.execute("SELECT COUNT(*) FROM tasks WHERE category_id = ?", (item_id,))
            else:  # priority or status
                # Need to get the name first
                cursor.execute(f"SELECT name FROM {table_name} WHERE id = ?", (item_id,))
                name = cursor.fetchone()[0]
                cursor.execute(f"SELECT COUNT(*) FROM tasks WHERE {item_type} = ?", (name,))
            
            count = cursor.fetchone()[0]
            
            if count > 0:
                QMessageBox.warning(self, "Error", 
                                   f"Cannot delete this {item_type} because it is used by {count} tasks. " +
                                   "Please reassign those tasks first.")
                return
            
            # Delete the item
            cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (item_id,))
            
            # If this was a priority or status, reorder the remaining items
            if item_type in ["priority", "status"]:
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET display_order = display_order - 1
                    WHERE display_order > (SELECT display_order FROM {table_name} WHERE id = ?)
                """, (item_id,))
            
            conn.commit()
        
        # Reload the appropriate list
        if item_type == "category":
            self.load_categories()
        elif item_type == "priority":
            self.load_priorities()
        elif item_type == "status":
            self.load_statuses()
    
    def add_item(self):
        """Add a new item of the current type"""
        current_type = self.setting_type_combo.currentText().lower()
        if current_type.endswith("s"):  # Convert "Categories" to "category"
            item_type = current_type[:-1]
        else:
            item_type = current_type
        
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", f"{item_type.title()} name is required.")
            return
            
        if not hasattr(self, 'selected_color'):
            # Default colors based on type
            if item_type == "category":
                self.selected_color = "#F0F7FF"  # Light blue
            elif item_type == "priority":
                self.selected_color = "#F44336"  # Red
            else:  # status
                self.selected_color = "#E0E0E0"  # Light gray
        
        table_name = f"{item_type}s"  # categories, priorities, or statuses
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check for duplicate name - case insensitive
            cursor.execute(f"SELECT name FROM {table_name} WHERE LOWER(name) = LOWER(?)", (name,))
            existing = cursor.fetchone()
            if existing:
                QMessageBox.warning(self, "Error", 
                                f"A {item_type} with this name already exists.")
                return
            
            # Handle priorities and statuses differently (they have display_order)
            if item_type in ["priority", "status"]:
                # Get max display order
                cursor.execute(f"SELECT MAX(display_order) FROM {table_name}")
                max_order = cursor.fetchone()[0]
                display_order = (max_order or 0) + 1
                
                cursor.execute(f"""
                    INSERT INTO {table_name} (name, color, display_order)
                    VALUES (?, ?, ?)
                """, (name, self.selected_color, display_order))
            else:
                # Categories don't have display_order
                cursor.execute(f"""
                    INSERT INTO {table_name} (name, color)
                    VALUES (?, ?)
                """, (name, self.selected_color))
            
            conn.commit()
        
        # Clear inputs and refresh
        self.name_input.clear()
        self.color_btn.setStyleSheet("")
        if hasattr(self, 'selected_color'):
            delattr(self, 'selected_color')
        
        # Reload the appropriate list
        if item_type == "category":
            self.load_categories()
        elif item_type == "priority":
            self.load_priorities()
        elif item_type == "status":
            self.load_statuses()

# Dialog for editing any item type
class EditItemDialog(QDialog):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    def __init__(self, item_type, item_id, parent=None):
        super().__init__(parent)
        self.item_type = item_type
        self.item_id = item_id
        self.setWindowTitle(f"Edit {item_type.title()}")
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setFixedHeight(30)
        
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_input)
        
        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setFixedHeight(30)
        save_btn.clicked.connect(self.save_changes)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(30)
        cancel_btn.clicked.connect(self.reject)
        
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setLayout(layout)
        self.load_data()
    
    def load_data(self):
        table_name = f"{self.item_type}s"  # categories, priorities, or statuses
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT name FROM {table_name} WHERE id = ?", (self.item_id,))
            name = cursor.fetchone()[0]
            self.name_input.setText(name)
    
    def save_changes(self):
        new_name = self.name_input.text().strip()
        
        if not new_name:
            QMessageBox.warning(self, "Error", f"{self.item_type.title()} name is required.")
            return
        
        # Get correct table name (handle special plurals)
        if self.item_type == "status":
            table_name = "statuses"
        elif self.item_type == "priority":
            table_name = "priorities"
        else:
            table_name = f"{self.item_type}s"  # categories
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get the old name
            cursor.execute(f"SELECT name FROM {table_name} WHERE id = ?", (self.item_id,))
            old_name = cursor.fetchone()[0]
            
            # Check for duplicate name - case insensitive
            cursor.execute(f"""
                SELECT name FROM {table_name} 
                WHERE LOWER(name) = LOWER(?) AND id != ?
            """, (new_name, self.item_id))
            existing = cursor.fetchone()
            if existing:
                QMessageBox.warning(self, "Error", 
                                   f"A {self.item_type} with this name already exists.")
                return
            
            # Update the item name
            cursor.execute(f"""
                UPDATE {table_name} 
                SET name = ?
                WHERE id = ?""", 
                (new_name, self.item_id))
            
            # For priorities and statuses, also update any tasks using them
            if self.item_type in ["priority", "status"]:
                cursor.execute(f"""
                    UPDATE tasks 
                    SET {self.item_type} = ?
                    WHERE {self.item_type} = ?""", 
                    (new_name, old_name))
                
            conn.commit()
        
        self.accept()