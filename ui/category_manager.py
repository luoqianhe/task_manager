# src/ui/category_manager.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QScrollArea, QColorDialog,
                             QDialog, QMessageBox, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QBrush
import sqlite3
from pathlib import Path

class CategoryItem(QWidget):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    def __init__(self, category_id, name, color):
        super().__init__()
        self.category_id = category_id
        
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 17, 15, 17)  # Horizontal padding only
        layout.setSpacing(10)  # Space between controls
        
        # Category name with larger font
        name_label = QLabel(name)
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")  # Increased font size
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        # Color button
        color_btn = QPushButton()
        color_btn.setFixedSize(30, 30)
        color_btn.setStyleSheet(f"background-color: {color}; border-radius: 20px;")
        color_btn.setText("Edit Color")
        color_btn.clicked.connect(self.change_color)
        layout.addWidget(color_btn)
        
        # Edit button - increased width and height
        edit_btn = QPushButton("Edit Name")
        edit_btn.setFixedSize(80, 30)  # Increased width from 60 to 80
        edit_btn.clicked.connect(self.edit_category)
        layout.addWidget(edit_btn)
        
        # Delete button - increased width and height
        delete_btn = QPushButton("Delete")
        delete_btn.setFixedSize(80, 30)  # Increased width from 60 to 80
        delete_btn.clicked.connect(self.delete_category)
        layout.addWidget(delete_btn)
        
        self.setLayout(layout)
        self.setFixedHeight(60)  # Set a fixed height for the item - doubled from typical 30
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
            cursor.execute("UPDATE categories SET color = ? WHERE id = ?",
                         (color, self.category_id))
            conn.commit()

    def edit_category(self):
        dialog = EditCategoryDialog(self.category_id, self)
        if dialog.exec():
            # Find the CategoryManager instance and refresh
            parent = self
            while parent and not isinstance(parent, CategoryManager):
                parent = parent.parent()
            if parent:
                parent.load_categories()

    def delete_category(self):
        reply = QMessageBox.question(self, 'Delete Category', 
                                'Are you sure you want to delete this category?',
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if any tasks are using this category
                cursor.execute("SELECT COUNT(*) FROM tasks WHERE category_id = ?", (self.category_id,))
                count = cursor.fetchone()[0]
                
                if count > 0:
                    QMessageBox.warning(self, "Error", 
                                       f"Cannot delete this category because it is used by {count} tasks. " +
                                       "Please reassign those tasks first.")
                    return
                
                # Delete the category
                cursor.execute("DELETE FROM categories WHERE id = ?", (self.category_id,))
                conn.commit()
            
            # Find the CategoryManager instance and refresh
            parent = self
            while parent and not isinstance(parent, CategoryManager):
                parent = parent.parent()
            if parent:
                parent.load_categories()

class CategoryManager(QWidget):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_categories()
        self.setStyleSheet("""
            QPushButton { 
                background-color: #f0f0f0;
                color: black;
                padding:5px;
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
                padding: 1px;  /* Reduced from 5px */
                margin: 1px;   /* Reduced from 2px */
            }
        """)
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header_label = QLabel("Categories")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(header_label)
        
        # List of existing categories
        self.categories_list = QListWidget()
        self.categories_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        main_layout.addWidget(self.categories_list)
        self.categories_list.setStyleSheet("""
        QListWidget {
                border: 1px solid #cccccc;
                background-color: white;
                border-radius: 5px;
                spacing: 0px;  /* This controls the gap between items */
            }
            QListWidget::item {
                padding: 0px;  /* No padding */
                margin: 0px;   /* No margin */
            }
        """)
        
        # Add new category form
        form_layout = QHBoxLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Category Name")
        self.name_input.setFixedHeight(30)
        
        self.color_btn = QPushButton("Pick Color")
        self.color_btn.setFixedHeight(30)
        self.color_btn.clicked.connect(self.pick_color)
        
        self.add_btn = QPushButton("Add Category")
        self.add_btn.setFixedHeight(30)
        self.add_btn.clicked.connect(self.add_category)
        
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(self.color_btn)
        form_layout.addWidget(self.add_btn)
        
        main_layout.addLayout(form_layout)
        self.setLayout(main_layout)
            
    def pick_color(self):
        self.selected_color = QColorDialog.getColor().name()
        self.color_btn.setStyleSheet(f"background-color: {self.selected_color}; border-radius: 5px;")
    
    def load_categories(self):
        # Clear existing items
        self.categories_list.clear()
                
        # Load categories from database
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categories ORDER BY name")
            categories = cursor.fetchall()
            
            for category in categories:
                # Create a custom widget for each category
                category_widget = CategoryItem(category[0], category[1], category[2])
                
                # Create a list item and set its size
                item = QListWidgetItem(self.categories_list)
                # Set a larger size hint to accommodate the taller CategoryItem
                item.setSizeHint(QSize(category_widget.sizeHint().width(), 40))  # Increased height
                
                # Add the widget to the list item
                self.categories_list.setItemWidget(item, category_widget)
    
    def add_category(self):
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "Category name is required.")
            return
            
        if not hasattr(self, 'selected_color'):
            self.selected_color = "#F0F7FF"  # Default light blue
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check for duplicate name - case insensitive
            cursor.execute("SELECT name FROM categories WHERE LOWER(name) = LOWER(?)", (name,))
            existing = cursor.fetchone()
            if existing:
                QMessageBox.warning(self, "Error", 
                                "A category with this name already exists.")
                return
                
            cursor.execute("""
                INSERT INTO categories (name, color)
                VALUES (?, ?)
            """, (name, self.selected_color))
            conn.commit()
        
        # Clear inputs and refresh
        self.name_input.clear()
        self.color_btn.setStyleSheet("")
        if hasattr(self, 'selected_color'):
            delattr(self, 'selected_color')
        self.load_categories()

class EditCategoryDialog(QDialog):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    def __init__(self, category_id, parent=None):
        super().__init__(parent)
        self.category_id = category_id
        self.setWindowTitle("Edit Category")
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
            cursor.execute("SELECT name FROM categories WHERE id = ?", (self.category_id,))
            name = cursor.fetchone()[0]
            self.name_input.setText(name)
    
    def save_changes(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check for duplicate name - case insensitive
            cursor.execute("""
                SELECT name FROM categories 
                WHERE LOWER(name) = LOWER(?) AND id != ?
            """, (self.name_input.text(), self.category_id))
            existing = cursor.fetchone()
            if existing:
                QMessageBox.warning(self, "Error", 
                                   "A category with this name already exists.")
                return
                
            cursor.execute("""
                UPDATE categories 
                SET name = ?
                WHERE id = ?""", 
                (self.name_input.text(), self.category_id))
            conn.commit()
        
        self.accept()