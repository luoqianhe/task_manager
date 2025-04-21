# src/ui/task_dialogs.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QPushButton, QTextEdit,
                             QDateEdit, QFormLayout, QWidget)
from pathlib import Path
import sqlite3
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtCore import Qt, QDate
from datetime import datetime, date

class AddTaskDialog(QDialog):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Task")
        self.setMinimumWidth(500)
        self.setMinimumHeight(500)
        self.setup_ui()
        self.load_statuses()
        self.data = None  # Store the data here
    
    def load_priorities(self):
        """Load priorities including 'Unprioritized' option"""
        self.priority_combo.clear()  # Clear existing items
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM priorities ORDER BY display_order")
            priorities = cursor.fetchall()
            print("ADD DIALOG PRIORITIES:", priorities)
            
            # Add all priorities to the combo box
            for pri_id, name in priorities:
                self.priority_combo.addItem(name, pri_id)
            
            # Find and select the "Unprioritized" option
            unprioritized_index = self.priority_combo.findText("Unprioritized")
            if unprioritized_index >= 0:
                self.priority_combo.setCurrentIndex(unprioritized_index)
            else:
                # If "Unprioritized" not found, select first item
                self.priority_combo.setCurrentIndex(0)

    def accept(self):
        # Store the data before closing
        due_date = None
        if self.due_date_edit.date() != QDate(2000, 1, 1):  # Default empty date
            due_date = self.due_date_edit.date().toString("yyyy-MM-dd")
        
        # Get the selected priority directly from the combo box
        selected_priority = self.priority_combo.currentText()
        
        self.data = {
            'title': self.title_input.text(),
            'description': self.description_input.toPlainText(),
            'link': self.link_input.text(),
            'status': self.status_combo.currentText(),
            'priority': selected_priority,
            'due_date': due_date,
            'category': self.category_combo.currentText() if self.category_combo.currentIndex() > 0 else None,
            'parent_id': self.parent_combo.currentData()
        }
        super().accept()
        
    def get_data(self):
        return self.data
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Title
        self.title_input = QLineEdit()
        self.title_input.setFixedHeight(30)
        form_layout.addRow("Title:", self.title_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMinimumHeight(80)
        form_layout.addRow("Description:", self.description_input)
        
        # Link
        self.link_input = QLineEdit()
        self.link_input.setFixedHeight(30)
        self.link_input.setPlaceholderText("https://")
        form_layout.addRow("Link (optional):", self.link_input)
        
        # Status
        self.status_combo = QComboBox()
        self.status_combo.setFixedHeight(30)
        form_layout.addRow("Status:", self.status_combo)
        
        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.setFixedHeight(30)
        self.load_priorities()
        form_layout.addRow("Priority:", self.priority_combo)
        
        # Due Date
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setFixedHeight(30)
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDate(QDate(2000, 1, 1))  # Default empty date
        self.due_date_edit.setSpecialValueText("No Due Date")
        form_layout.addRow("Due Date:", self.due_date_edit)
        
        # Category
        self.category_combo = QComboBox()
        self.category_combo.setFixedHeight(30)
        self.load_categories()
        form_layout.addRow("Category:", self.category_combo)
        
        # Parent Task
        self.parent_combo = QComboBox()
        self.parent_combo.setFixedHeight(30)
        self.load_possible_parents()
        form_layout.addRow("Parent Task:", self.parent_combo)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setFixedHeight(30)
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(30)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        # Set tab order
        self.setTabOrder(self.title_input, self.description_input)
        self.setTabOrder(self.description_input, self.link_input)
        self.setTabOrder(self.link_input, self.status_combo)
        self.setTabOrder(self.status_combo, self.priority_combo)
        self.setTabOrder(self.priority_combo, self.due_date_edit)
        self.setTabOrder(self.due_date_edit, self.category_combo)
        self.setTabOrder(self.category_combo, self.parent_combo)
        self.setTabOrder(self.parent_combo, save_btn)
        self.setTabOrder(save_btn, cancel_btn)
    
    def load_categories(self):
        self.category_combo.addItem("None", None)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM categories ORDER BY name")
            for cat_id, name in cursor.fetchall():
                self.category_combo.addItem(name, cat_id)
    
    def load_statuses(self):
        """Load statuses from the database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM statuses ORDER BY display_order")
            statuses = cursor.fetchall()
            
            for status in statuses:
                self.status_combo.addItem(status[0])
            
            # Default to "Not Started" if it exists
            not_started_index = self.status_combo.findText("Not Started")
            if not_started_index >= 0:
                self.status_combo.setCurrentIndex(not_started_index)
    
    def load_possible_parents(self):
        self.parent_combo.addItem("None", None)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title FROM tasks ORDER BY title")
            for task_id, title in cursor.fetchall():
                self.parent_combo.addItem(title, task_id)

class EditTaskDialog(QDialog):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    def __init__(self, task_data, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self.setWindowTitle("Edit Task")
        self.setMinimumWidth(500)
        self.setMinimumHeight(500)
        self.setup_ui()
        self.load_statuses()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Title
        self.title_input = QLineEdit(self.task_data['title'])
        self.title_input.setFixedHeight(30)
        form_layout.addRow("Title:", self.title_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMinimumHeight(80)
        self.description_input.setText(self.task_data['description'] or "")
        form_layout.addRow("Description:", self.description_input)
        
        # Link
        self.link_input = QLineEdit(self.task_data['link'] or "")
        self.link_input.setFixedHeight(30)
        self.link_input.setPlaceholderText("https://")
        form_layout.addRow("Link (optional):", self.link_input)
        
        # Status
        self.status_combo = QComboBox()
        self.status_combo.setFixedHeight(30)
        self.status_combo.setCurrentText(self.task_data['status'] or "Not Started")
        form_layout.addRow("Status:", self.status_combo)
        
        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.setFixedHeight(30)
        self.load_priorities()
        form_layout.addRow("Priority:", self.priority_combo)
        
        # Due Date
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setFixedHeight(30)
        self.due_date_edit.setCalendarPopup(True)
        
        # Set the current due date if it exists
        if self.task_data['due_date']:
            try:
                due_date = QDate.fromString(self.task_data['due_date'], "yyyy-MM-dd")
                self.due_date_edit.setDate(due_date)
            except ValueError:
                self.due_date_edit.setDate(QDate(2000, 1, 1))  # Default empty date
        else:
            self.due_date_edit.setDate(QDate(2000, 1, 1))  # Default empty date
            
        self.due_date_edit.setSpecialValueText("No Due Date")
        form_layout.addRow("Due Date:", self.due_date_edit)
        
        # Category
        self.category_combo = QComboBox()
        self.category_combo.setFixedHeight(30)
        self.load_categories()
        form_layout.addRow("Category:", self.category_combo)
        
        # Parent Task
        self.parent_combo = QComboBox()
        self.parent_combo.setFixedHeight(30)
        self.load_possible_parents()
        form_layout.addRow("Parent Task:", self.parent_combo)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setFixedHeight(30)
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(30)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        # Set tab order
        self.setTabOrder(self.title_input, self.description_input)
        self.setTabOrder(self.description_input, self.link_input)
        self.setTabOrder(self.link_input, self.status_combo)
        self.setTabOrder(self.status_combo, self.priority_combo)
        self.setTabOrder(self.priority_combo, self.due_date_edit)
        self.setTabOrder(self.due_date_edit, self.category_combo)
        self.setTabOrder(self.category_combo, self.parent_combo)
        self.setTabOrder(self.parent_combo, save_btn)
        self.setTabOrder(save_btn, cancel_btn)
    
    def get_data(self):
        return self.data

    def load_priorities(self):
        """Load priorities for editing a task"""
        self.priority_combo.clear()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM priorities ORDER BY display_order")
            priorities = cursor.fetchall()
            
            # Add all priorities to the combo box
            for pri_id, name in priorities:
                self.priority_combo.addItem(name, pri_id)
                
                # If this is the current priority of the task, select it
                if name == self.task_data['priority']:
                    self.priority_combo.setCurrentIndex(self.priority_combo.count() - 1)
        
        # If no matching priority was found (or priority is None),
        # look for the "Unprioritized" option
        if self.task_data['priority'] is None or self.priority_combo.currentText() != self.task_data['priority']:
            unprioritized_index = self.priority_combo.findText("Unprioritized")
            if unprioritized_index >= 0:
                self.priority_combo.setCurrentIndex(unprioritized_index)        

    def load_statuses(self):
        """Load statuses from the database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM statuses ORDER BY display_order")
            statuses = cursor.fetchall()
            
            for status in statuses:
                self.status_combo.addItem(status[0])
            
            # Select the current status
            current_status = self.task_data.get('status', 'Not Started')
            index = self.status_combo.findText(current_status)
            if index >= 0:
                self.status_combo.setCurrentIndex(index)
                
    def accept(self):
        # Store the data before closing
        due_date = None
        if self.due_date_edit.date() != QDate(2000, 1, 1):  # Default empty date
            due_date = self.due_date_edit.date().toString("yyyy-MM-dd")
        
        # Get selected priority directly from combo box
        selected_priority = self.priority_combo.currentText()
                
        self.data = {
            'id': self.task_data['id'],
            'title': self.title_input.text(),
            'description': self.description_input.toPlainText(),
            'link': self.link_input.text(),
            'status': self.status_combo.currentText(),
            'priority': selected_priority,
            'due_date': due_date,
            'category': self.category_combo.currentText() if self.category_combo.currentIndex() > 0 else None,
            'parent_id': self.parent_combo.currentData()
        }
        super().accept()
        
    def load_categories(self):
        self.category_combo.addItem("None", None)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM categories ORDER BY name")
            for cat_id, name in cursor.fetchall():
                self.category_combo.addItem(name, cat_id)
                if name == self.task_data['category']:
                    self.category_combo.setCurrentIndex(self.category_combo.count() - 1)
    
    def load_possible_parents(self):
        self.parent_combo.addItem("None", None)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Don't show the current task or its children as possible parents
            cursor.execute("""
                SELECT id, title FROM tasks 
                WHERE id != ? AND parent_id != ?
                ORDER BY title
            """, (self.task_data['id'], self.task_data['id']))
            
            current_parent = self.task_data.get('parent_id')
            for task_id, title in cursor.fetchall():
                self.parent_combo.addItem(title, task_id)
                if task_id == current_parent:
                    self.parent_combo.setCurrentIndex(self.parent_combo.count() - 1)
                    
class EditStatusDialog(QDialog):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
   
    def __init__(self, status_id, parent=None):
        super().__init__(parent)
        self.status_id = status_id
        self.setWindowTitle("Edit Status")
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
            cursor.execute("SELECT name FROM statuses WHERE id = ?", (self.status_id,))
            name = cursor.fetchone()[0]
            self.name_input.setText(name)
    
    def save_changes(self):
        new_name = self.name_input.text().strip()
        
        if not new_name:
            QMessageBox.warning(self, "Error", "Status name is required.")
            return
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get the old name
            cursor.execute("SELECT name FROM statuses WHERE id = ?", (self.status_id,))
            old_name = cursor.fetchone()[0]
            
            # Check for duplicate name - case insensitive
            cursor.execute("""
                SELECT name FROM statuses 
                WHERE LOWER(name) = LOWER(?) AND id != ?
            """, (new_name, self.status_id))
            existing = cursor.fetchone()
            if existing:
                QMessageBox.warning(self, "Error", 
                                   "A status with this name already exists.")
                return
            
            # Update the status name
            cursor.execute("""
                UPDATE statuses 
                SET name = ?
                WHERE id = ?""", 
                (new_name, self.status_id))
            
            # Update all tasks that use the old status name
            cursor.execute("""
                UPDATE tasks 
                SET status = ?
                WHERE status = ?""", 
                (new_name, old_name))
                
            conn.commit()
        
        self.accept()