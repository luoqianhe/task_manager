# src/ui/priority_manager.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QListWidget, QListWidgetItem,
                             QColorDialog, QMessageBox, QDialog)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
import sqlite3
from pathlib import Path

class PriorityItem(QWidget):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    def __init__(self, priority_id, name, color, display_order):
        super().__init__()
        self.priority_id = priority_id
        self.display_order = display_order
        
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Priority level indicator
        level_label = QLabel(f"Level {display_order}:")
        level_label.setStyleSheet("font-weight: bold; min-width: 60px;")
        layout.addWidget(level_label)
        
        # Priority name
        name_label = QLabel(name)
        name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        # Move up button
        self.up_btn = QPushButton("↑")
        self.up_btn.setFixedWidth(30)
        self.up_btn.setToolTip("Move priority up (higher importance)")
        self.up_btn.clicked.connect(self.move_up)
        layout.addWidget(self.up_btn)
        
        # Move down button
        self.down_btn = QPushButton("↓")
        self.down_btn.setFixedWidth(30)
        self.down_btn.setToolTip("Move priority down (lower importance)")
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
        edit_btn.clicked.connect(self.edit_priority)
        layout.addWidget(edit_btn)
        
        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setFixedWidth(60)
        delete_btn.clicked.connect(self.delete_priority)
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
            cursor.execute("UPDATE priorities SET color = ? WHERE id = ?",
                         (color, self.priority_id))
            conn.commit()
    
    def move_up(self):
        """Move this priority up (higher importance)"""
        # Find the PriorityManager instance
        parent = self
        while parent and not isinstance(parent, PriorityManager):
            parent = parent.parent()
        
        if parent:
            parent.move_priority(self.priority_id, self.display_order, move_up=True)
    
    def move_down(self):
        """Move this priority down (lower importance)"""
        # Find the PriorityManager instance
        parent = self
        while parent and not isinstance(parent, PriorityManager):
            parent = parent.parent()
        
        if parent:
            parent.move_priority(self.priority_id, self.display_order, move_up=False)

    def edit_priority(self):
        dialog = EditPriorityDialog(self.priority_id, self)
        if dialog.exec():
            # Find the PriorityManager instance and refresh
            parent = self
            while parent and not isinstance(parent, PriorityManager):
                parent = parent.parent()
            if parent:
                parent.load_priorities()

    def delete_priority(self):
        reply = QMessageBox.question(self, 'Delete Priority', 
                                'Are you sure you want to delete this priority?',
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if any tasks are using this priority
                cursor.execute("SELECT COUNT(*) FROM tasks WHERE priority = ?", 
                             (self.findChildren(QLabel)[1].text(),))  # Get the name label
                count = cursor.fetchone()[0]
                
                if count > 0:
                    QMessageBox.warning(self, "Error", 
                                       f"Cannot delete this priority because it is used by {count} tasks. " +
                                       "Please reassign those tasks first.")
                    return
                
                # Delete the priority
                cursor.execute("DELETE FROM priorities WHERE id = ?", (self.priority_id,))
                conn.commit()
            
            # Find the PriorityManager instance and refresh
            parent = self
            while parent and not isinstance(parent, PriorityManager):
                parent = parent.parent()
            if parent:
                parent.load_priorities()

class PriorityManager(QWidget):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_priorities()
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
        header_label = QLabel("Priority Levels")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(header_label)
        
        # Description
        desc_label = QLabel("Higher priorities (lower level numbers) will appear at the top of the task list.")
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)
        
        # List of existing priorities
        self.priorities_list = QListWidget()
        self.priorities_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.priorities_list.setSpacing(5)
        main_layout.addWidget(self.priorities_list)
        
        # Add new priority form
        form_layout = QHBoxLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Priority Name")
        self.name_input.setFixedHeight(30)
        
        self.color_btn = QPushButton("Pick Color")
        self.color_btn.setFixedHeight(30)
        self.color_btn.clicked.connect(self.pick_color)
        
        self.add_btn = QPushButton("Add Priority")
        self.add_btn.setFixedHeight(30)
        self.add_btn.clicked.connect(self.add_priority)
        
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(self.color_btn)
        form_layout.addWidget(self.add_btn)
        
        main_layout.addLayout(form_layout)
        self.setLayout(main_layout)
            
    def pick_color(self):
        self.selected_color = QColorDialog.getColor().name()
        self.color_btn.setStyleSheet(f"background-color: {self.selected_color}; border-radius: 5px;")
    
    def load_priorities(self):
        # Clear existing items
        self.priorities_list.clear()
                
        # Load priorities from database
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, color, display_order FROM priorities ORDER BY display_order")
            priorities = cursor.fetchall()
            
            for priority in priorities:
                # Create a custom widget for each priority
                priority_id = priority[0]
                name = priority[1]
                color = priority[2]
                display_order = priority[3]
                
                priority_widget = PriorityItem(priority_id, name, color, display_order)
                
                # Create a list item and set its size
                item = QListWidgetItem(self.priorities_list)
                item.setSizeHint(priority_widget.sizeHint())
                
                # Add the widget to the list item
                self.priorities_list.setItemWidget(item, priority_widget)
            
            # Disable up/down buttons as needed
            self.update_move_buttons()
    
    def update_move_buttons(self):
        """Update the enabled state of move up/down buttons"""
        count = self.priorities_list.count()
        
        for i in range(count):
            item_widget = self.priorities_list.itemWidget(self.priorities_list.item(i))
            
            # Disable up button for first item
            item_widget.up_btn.setEnabled(i > 0)
            
            # Disable down button for last item
            item_widget.down_btn.setEnabled(i < count - 1)
    
    def move_priority(self, priority_id, current_order, move_up=True):
        """Move a priority up or down in the order"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Calculate target order
            target_order = current_order - 1 if move_up else current_order + 1
            
            # Find the priority at the target position
            cursor.execute("""
                SELECT id FROM priorities 
                WHERE display_order = ?
            """, (target_order,))
            
            swap_id = cursor.fetchone()
            if not swap_id:
                return  # No priority to swap with
            
            swap_id = swap_id[0]
            
            # Swap the display orders
            cursor.execute("""
                UPDATE priorities SET display_order = ? WHERE id = ?
            """, (target_order, priority_id))
            
            cursor.execute("""
                UPDATE priorities SET display_order = ? WHERE id = ?
            """, (current_order, swap_id))
            
            conn.commit()
        
        # Reload priorities
        self.load_priorities()
    
    def add_priority(self):
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "Priority name is required.")
            return
            
        if not hasattr(self, 'selected_color'):
            self.selected_color = "#F44336"  # Default red color
        
        # Ask if this is a high priority or lower priority
        new_priority_dialog = QDialog(self)
        new_priority_dialog.setWindowTitle("Set Priority Level")
        new_priority_dialog.setFixedSize(350, 150)
        
        vbox = QVBoxLayout(new_priority_dialog)
        vbox.addWidget(QLabel(f"Where should '{name}' be placed in the priority hierarchy?"))
        
        # Add radio buttons for position
        high_radio = QPushButton("Make Highest Priority (Top)")
        high_radio.setStyleSheet("text-align: left; padding: 8px;")
        high_radio.clicked.connect(lambda: new_priority_dialog.done(1))
        
        low_radio = QPushButton("Make Lowest Priority (Bottom)")
        low_radio.setStyleSheet("text-align: left; padding: 8px;")
        low_radio.clicked.connect(lambda: new_priority_dialog.done(2))
        
        vbox.addWidget(high_radio)
        vbox.addWidget(low_radio)
        
        result = new_priority_dialog.exec()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check for duplicate name - case insensitive
            cursor.execute("SELECT name FROM priorities WHERE LOWER(name) = LOWER(?)", (name,))
            existing = cursor.fetchone()
            if existing:
                QMessageBox.warning(self, "Error", 
                                "A priority with this name already exists.")
                return
            
            if result == 1:  # High priority (top of list)
                # Shift all existing priorities down by 1
                cursor.execute("""
                    UPDATE priorities
                    SET display_order = display_order + 1
                """)
                
                # Insert at position 1
                display_order = 1
            else:  # Low priority (bottom of list)
                # Get max display order
                cursor.execute("SELECT MAX(display_order) FROM priorities")
                max_order = cursor.fetchone()[0]
                display_order = (max_order or 0) + 1
            
            cursor.execute("""
                INSERT INTO priorities (name, color, display_order)
                VALUES (?, ?, ?)
            """, (name, self.selected_color, display_order))
            conn.commit()
        
        # Clear inputs and refresh
        self.name_input.clear()
        self.color_btn.setStyleSheet("")
        if hasattr(self, 'selected_color'):
            delattr(self, 'selected_color')
        self.load_priorities()

class EditPriorityDialog(QDialog):
    DB_PATH = Path(__file__).parent.parent / "database" / "task_manager.db"
    
    def __init__(self, priority_id, parent=None):
        super().__init__(parent)
        self.priority_id = priority_id
        self.setWindowTitle("Edit Priority")
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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM priorities WHERE id = ?", (self.priority_id,))
            name = cursor.fetchone()[0]
            self.name_input.setText(name)
    
    def save_changes(self):
        new_name = self.name_input.text().strip()
        
        if not new_name:
            QMessageBox.warning(self, "Error", "Priority name is required.")
            return
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get the old name
            cursor.execute("SELECT name FROM priorities WHERE id = ?", (self.priority_id,))
            old_name = cursor.fetchone()[0]
            
            # Check for duplicate name - case insensitive
            cursor.execute("""
                SELECT name FROM priorities 
                WHERE LOWER(name) = LOWER(?) AND id != ?
            """, (new_name, self.priority_id))
            existing = cursor.fetchone()
            if existing:
                QMessageBox.warning(self, "Error", 
                                   "A priority with this name already exists.")
                return
            
            # Update the priority name
            cursor.execute("""
                UPDATE priorities 
                SET name = ?
                WHERE id = ?""", 
                (new_name, self.priority_id))
            
            # Update all tasks that use the old priority name
            cursor.execute("""
                UPDATE tasks 
                SET priority = ?
                WHERE priority = ?""", 
                (new_name, old_name))
                
            conn.commit()
        
        self.accept()