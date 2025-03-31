# src/ui/status_manager.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QListWidget, QListWidgetItem,
                             QColorDialog, QMessageBox, QDialog)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
import sqlite3
from pathlib import Path
from ui.task_dialogs import EditStatusDialog

class StatusItem(QWidget):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    def __init__(self, status_id, name, color, display_order):
        super().__init__()
        self.status_id = status_id
        self.display_order = display_order
        
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Status level indicator
        level_label = QLabel(f"Order {display_order}:")
        level_label.setStyleSheet("font-weight: bold; min-width: 60px;")
        layout.addWidget(level_label)
        
        # Status name
        name_label = QLabel(name)
        name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        # Move up button
        self.up_btn = QPushButton("↑")
        self.up_btn.setFixedWidth(30)
        self.up_btn.setToolTip("Move status up (higher in list)")
        self.up_btn.clicked.connect(self.move_up)
        layout.addWidget(self.up_btn)
        
        # Move down button
        self.down_btn = QPushButton("↓")
        self.down_btn.setFixedWidth(30)
        self.down_btn.setToolTip("Move status down (lower in list)")
        self.down_btn.clicked.connect(self.move_down)
        layout.addWidget(self.down_btn)
        
        # Color button
        color_btn = QPushButton()
        color_btn.setFixedSize(30, 30)
        color_btn.setStyleSheet(f"background-color: {color}; border-radius: 15px;")
        color_btn.clicked.connect(self.change_color)
        layout.addWidget(color_btn)
        
        # Edit button
        edit_btn = QPushButton("Edit")
        edit_btn.setFixedWidth(60)
        edit_btn.clicked.connect(self.edit_status)
        layout.addWidget(edit_btn)
        
        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setFixedWidth(60)
        delete_btn.clicked.connect(self.delete_status)
        layout.addWidget(delete_btn)
        
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
    
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
    
    def update_color_in_db(self, color):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE statuses SET color = ? WHERE id = ?",
                         (color, self.status_id))
            conn.commit()
    
    def move_up(self):
        """Move this status up (higher in list)"""
        # Find the StatusManager instance
        parent = self
        while parent and not isinstance(parent, StatusManager):
            parent = parent.parent()
        
        if parent:
            parent.move_status(self.status_id, self.display_order, move_up=True)
    
    def move_down(self):
        """Move this status down (lower in list)"""
        # Find the StatusManager instance
        parent = self
        while parent and not isinstance(parent, StatusManager):
            parent = parent.parent()
        
        if parent:
            parent.move_status(self.status_id, self.display_order, move_up=False)

    def edit_status(self):
        dialog = EditStatusDialog(self.status_id, self)
        if dialog.exec():
            # Find the StatusManager instance and refresh
            parent = self
            while parent and not isinstance(parent, StatusManager):
                parent = parent.parent()
            if parent:
                parent.load_statuses()

    def delete_status(self):
        reply = QMessageBox.question(self, 'Delete Status', 
                                'Are you sure you want to delete this status?',
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if any tasks are using this status
                cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = ?", 
                             (self.findChildren(QLabel)[1].text(),))  # Get the name label
                count = cursor.fetchone()[0]
                
                if count > 0:
                    QMessageBox.warning(self, "Error", 
                                       f"Cannot delete this status because it is used by {count} tasks. " +
                                       "Please reassign those tasks first.")
                    return
                
                # Delete the status
                cursor.execute("DELETE FROM statuses WHERE id = ?", (self.status_id,))
                conn.commit()
            
            # Find the StatusManager instance and refresh
            parent = self
            while parent and not isinstance(parent, StatusManager):
                parent = parent.parent()
            if parent:
                parent.load_statuses()

class StatusManager(QWidget):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_statuses()
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
                padding: 5px;
                margin: 2px;
            }
        """)
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header_label = QLabel("Status Types")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(header_label)
        
        # Description
        desc_label = QLabel("Manage the status types for your tasks.")
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)
        
        # List of existing statuses
        self.statuses_list = QListWidget()
        self.statuses_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.statuses_list.setSpacing(5)
        main_layout.addWidget(self.statuses_list)
        
        # Add new status form
        form_layout = QHBoxLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Status Name")
        self.name_input.setFixedHeight(30)
        
        self.color_btn = QPushButton("Pick Color")
        self.color_btn.setFixedHeight(30)
        self.color_btn.clicked.connect(self.pick_color)
        
        self.add_btn = QPushButton("Add Status")
        self.add_btn.setFixedHeight(30)
        self.add_btn.clicked.connect(self.add_status)
        
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(self.color_btn)
        form_layout.addWidget(self.add_btn)
        
        main_layout.addLayout(form_layout)
        self.setLayout(main_layout)
            
    def pick_color(self):
        self.selected_color = QColorDialog.getColor().name()
        self.color_btn.setStyleSheet(f"background-color: {self.selected_color}; border-radius: 5px;")
    
    def load_statuses(self):
        # Clear existing items
        self.statuses_list.clear()
                
        # Load statuses from database
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, color, display_order FROM statuses ORDER BY display_order")
            statuses = cursor.fetchall()
            
            for status in statuses:
                # Create a custom widget for each status
                status_id = status[0]
                name = status[1]
                color = status[2]
                display_order = status[3]
                
                status_widget = StatusItem(status_id, name, color, display_order)
                
                # Create a list item and set its size
                item = QListWidgetItem(self.statuses_list)
                item.setSizeHint(status_widget.sizeHint())
                
                # Add the widget to the list item
                self.statuses_list.setItemWidget(item, status_widget)
            
            # Disable up/down buttons as needed
            self.update_move_buttons()
    
    def update_move_buttons(self):
        """Update the enabled state of move up/down buttons"""
        count = self.statuses_list.count()
        
        for i in range(count):
            item_widget = self.statuses_list.itemWidget(self.statuses_list.item(i))
            
            # Disable up button for first item
            item_widget.up_btn.setEnabled(i > 0)
            
            # Disable down button for last item
            item_widget.down_btn.setEnabled(i < count - 1)
    
    def move_status(self, status_id, current_order, move_up=True):
        """Move a status up or down in the order"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Calculate target order
            target_order = current_order - 1 if move_up else current_order + 1
            
            # Find the status at the target position
            cursor.execute("""
                SELECT id FROM statuses 
                WHERE display_order = ?
            """, (target_order,))
            
            swap_id = cursor.fetchone()
            if not swap_id:
                return  # No status to swap with
            
            swap_id = swap_id[0]
            
            # Swap the display orders
            cursor.execute("""
                UPDATE statuses SET display_order = ? WHERE id = ?
            """, (target_order, status_id))
            
            cursor.execute("""
                UPDATE statuses SET display_order = ? WHERE id = ?
            """, (current_order, swap_id))
            
            conn.commit()
        
        # Reload statuses
        self.load_statuses()
    
    def add_status(self):
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "Status name is required.")
            return
            
        if not hasattr(self, 'selected_color'):
            self.selected_color = "#E0E0E0"  # Default light gray color
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check for duplicate name - case insensitive
            cursor.execute("SELECT name FROM statuses WHERE LOWER(name) = LOWER(?)", (name,))
            existing = cursor.fetchone()
            if existing:
                QMessageBox.warning(self, "Error", 
                                "A status with this name already exists.")
                return
            
            # Get max display order
            cursor.execute("SELECT MAX(display_order) FROM statuses")
            max_order = cursor.fetchone()[0]
            display_order = (max_order or 0) + 1
            
            cursor.execute("""
                INSERT INTO statuses (name, color, display_order)
                VALUES (?, ?, ?)
            """, (name, self.selected_color, display_order))
            conn.commit()