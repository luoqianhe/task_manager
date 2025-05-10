# src/ui/category_manager.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QScrollArea, QColorDialog,
                             QDialog, QMessageBox, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QBrush
import sqlite3
from pathlib import Path

# Import debug utilities
from utils.debug_logger import get_debug_logger
from utils.debug_decorator import debug_method

# Get debug logger instance
debug = get_debug_logger()

class CategoryItem(QWidget):
    @staticmethod
    def get_connection():
        debug.debug("Getting database connection from overridden method")
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    @debug_method
    def __init__(self, category_id, name, color):
        super().__init__()
        self.category_id = category_id
        debug.debug(f"Initializing CategoryItem: id={category_id}, name='{name}', color={color}")
        
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 17, 15, 17)  # Horizontal padding only
        layout.setSpacing(10)  # Space between controls
        
        # Calculate text color based on background brightness
        # This ensures text is visible regardless of background color
        bg_color = QColor(color)
        brightness = (bg_color.red() * 299 + bg_color.green() * 587 + bg_color.blue() * 114) / 1000
        text_color = "black" if brightness > 128 else "white"
        
        # Category name with larger font and contrast-based text color
        name_label = QLabel(name)
        name_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {text_color};")
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        # Color button
        color_btn = QPushButton()
        color_btn.setFixedSize(30, 30)
        color_btn.setStyleSheet(f"background-color: {color}; border-radius: 20px;")
        color_btn.clicked.connect(self.change_color)
        layout.addWidget(color_btn)
        
        # Edit button - set specialButton property
        edit_btn = QPushButton("Edit Name")
        edit_btn.setFixedSize(80, 30)
        edit_btn.setProperty("specialButton", True)  # Mark as special button for styling
        edit_btn.clicked.connect(self.edit_category)
        layout.addWidget(edit_btn)
        
        # Delete button - set specialButton property
        delete_btn = QPushButton("Delete")
        delete_btn.setFixedSize(80, 30)
        delete_btn.setProperty("specialButton", True)  # Mark as special button for styling
        delete_btn.clicked.connect(self.delete_category)
        layout.addWidget(delete_btn)
        
        self.setLayout(layout)
        self.setFixedHeight(60)  # Set a fixed height for the item - doubled from typical 30
        self.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        debug.debug(f"CategoryItem initialized: {name}")
        
        # Move up button - make sure it's visible with explicit styling
        self.up_btn = QPushButton("↑")
        self.up_btn.setFixedWidth(30)
        self.up_btn.setToolTip("Move category up (higher importance)")
        self.up_btn.setStyleSheet("background-color: #f0f0f0; color: black; border: 1px solid #cccccc;")
        self.up_btn.clicked.connect(self.move_up)
        layout.addWidget(self.up_btn)
        
        # Move down button - make sure it's visible with explicit styling
        self.down_btn = QPushButton("↓")
        self.down_btn.setFixedWidth(30)
        self.down_btn.setToolTip("Move category down (lower importance)")
        self.down_btn.setStyleSheet("background-color: #f0f0f0; color: black; border: 1px solid #cccccc;")
        self.down_btn.clicked.connect(self.move_down)
        layout.addWidget(self.down_btn)
        
    @debug_method
    def change_color(self):
        debug.debug(f"Opening color picker for category ID: {self.category_id}")
        color = QColorDialog.getColor()
        if color.isValid():
            new_color = color.name()
            debug.debug(f"New color selected: {new_color}")
            self.update_color_in_db(new_color)
            self.setStyleSheet(f"background-color: {new_color}; border-radius: 5px;")
            
            # Update color button
            for child in self.findChildren(QPushButton):
                if child.width() == 30 and child.height() == 30:
                    child.setStyleSheet(f"background-color: {new_color}; border-radius: 15px;")
                    debug.debug("Updated color button appearance")
                    break
            debug.debug(f"Category color updated to {new_color}")
        else:
            debug.debug("Color selection cancelled")
    
    @debug_method
    def update_color_in_db(self, color):
        debug.debug(f"Updating category ID {self.category_id} color to {color} in database")
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE categories SET color = ? WHERE id = ?",
                            (color, self.category_id))
                conn.commit()
                debug.debug("Database update successful")
        except Exception as e:
            debug.error(f"Error updating category color in database: {e}")

    @debug_method
    def edit_category(self):
        debug.debug(f"Opening edit dialog for category ID: {self.category_id}")
        dialog = EditCategoryDialog(self.category_id, self)
        if dialog.exec():
            debug.debug("Category edit dialog accepted, finding CategoryManager to refresh")
            # Find the CategoryManager instance and refresh
            parent = self
            while parent and not isinstance(parent, CategoryManager):
                parent = parent.parent()
            if parent:
                debug.debug("Found CategoryManager, reloading categories")
                parent.load_categories()
            else:
                debug.warning("Could not find parent CategoryManager")
        else:
            debug.debug("Category edit dialog cancelled")

    @debug_method
    def delete_category(self):
        debug.debug(f"Delete button clicked for category ID: {self.category_id}")
        reply = QMessageBox.question(self, 'Delete Category', 
                                'Are you sure you want to delete this category?',
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            debug.debug("User confirmed category deletion")
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Check if any tasks are using this category
                    debug.debug(f"Checking if category ID {self.category_id} is in use")
                    cursor.execute("SELECT COUNT(*) FROM tasks WHERE category_id = ?", (self.category_id,))
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        debug.warning(f"Cannot delete category - it is used by {count} tasks")
                        QMessageBox.warning(self, "Error", 
                                        f"Cannot delete this category because it is used by {count} tasks. " +
                                        "Please reassign those tasks first.")
                        return
                    
                    # Delete the category
                    debug.debug(f"Deleting category ID {self.category_id}")
                    cursor.execute("DELETE FROM categories WHERE id = ?", (self.category_id,))
                    conn.commit()
                    debug.debug("Category deleted successfully")
            except Exception as e:
                debug.error(f"Error deleting category: {e}")
                return
            
            # Find the CategoryManager instance and refresh
            debug.debug("Finding CategoryManager to refresh after deletion")
            parent = self
            while parent and not isinstance(parent, CategoryManager):
                parent = parent.parent()
            if parent:
                debug.debug("Found CategoryManager, reloading categories")
                parent.load_categories()
            else:
                debug.warning("Could not find parent CategoryManager")
        else:
            debug.debug("User cancelled category deletion")

class CategoryManager(QWidget):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        debug.debug("Getting database connection from overridden method")
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    @debug_method
    def __init__(self):
        debug.debug("Initializing CategoryManager")
        super().__init__()
        self.init_ui()
        self.load_categories()
        # Keep minimal styling while ensuring buttons are visible
        self.setStyleSheet("""
            QLineEdit {
                max-height: 25px;
                padding: 2px 5px;
                border-radius: 3px;
            }
            QListWidget {
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 1px;
                margin: 1px;
            }
            /* Ensure buttons are visible */
            QPushButton[flat="false"] {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
            }
        """)
        debug.debug("CategoryManager initialized")
    
    @debug_method
    def init_ui(self):
        debug.debug("Setting up CategoryManager UI")
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header_label = QLabel("Categories")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(header_label)
        
        # List of existing categories
        debug.debug("Creating categories list widget")
        self.categories_list = QListWidget()
        self.categories_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        main_layout.addWidget(self.categories_list)
        
        # Add new category form
        debug.debug("Creating add category form")
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
        debug.debug("CategoryManager UI setup complete")
            
    @debug_method
    def pick_color(self):
        debug.debug("Opening color picker dialog")
        self.selected_color = QColorDialog.getColor().name()
        debug.debug(f"Selected color: {self.selected_color}")
        self.color_btn.setStyleSheet(f"background-color: {self.selected_color}; border-radius: 5px;")
    
    @debug_method
    def load_categories(self):
        debug.debug("Loading categories from database")
        # Clear existing items
        self.categories_list.clear()
                
        # Load categories from database
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM categories ORDER BY name")
                categories = cursor.fetchall()
                debug.debug(f"Found {len(categories)} categories")
                
                for category in categories:
                    # Create a custom widget for each category
                    debug.debug(f"Creating widget for category: {category[1]}")
                    category_widget = CategoryItem(category[0], category[1], category[2])
                    
                    # Create a list item and set its size
                    item = QListWidgetItem(self.categories_list)
                    # Set a larger size hint to accommodate the taller CategoryItem
                    item.setSizeHint(QSize(category_widget.sizeHint().width(), 40))  # Increased height
                    
                    # Add the widget to the list item
                    self.categories_list.setItemWidget(item, category_widget)
            debug.debug("Categories loaded successfully")
        except Exception as e:
            debug.error(f"Error loading categories: {e}")
    
    @debug_method
    def add_category(self):
        name = self.name_input.text().strip()
        debug.debug(f"Adding new category: '{name}'")
        
        if not name:
            debug.warning("Category name is empty")
            QMessageBox.warning(self, "Error", "Category name is required.")
            return
            
        if not hasattr(self, 'selected_color'):
            debug.debug("No color selected, using default light blue")
            self.selected_color = "#F0F7FF"  # Default light blue
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check for duplicate name - case insensitive
                debug.debug(f"Checking for duplicate category name: '{name}'")
                cursor.execute("SELECT name FROM categories WHERE LOWER(name) = LOWER(?)", (name,))
                existing = cursor.fetchone()
                if existing:
                    debug.warning(f"A category with name '{name}' already exists")
                    QMessageBox.warning(self, "Error", 
                                    "A category with this name already exists.")
                    return
                    
                debug.debug(f"Adding new category '{name}' with color {self.selected_color}")
                cursor.execute("""
                    INSERT INTO categories (name, color)
                    VALUES (?, ?)
                """, (name, self.selected_color))
                conn.commit()
                debug.debug("Category added successfully")
        except Exception as e:
            debug.error(f"Error adding category: {e}")
            return
        
        # Clear inputs and refresh
        self.name_input.clear()
        self.color_btn.setStyleSheet("")
        if hasattr(self, 'selected_color'):
            delattr(self, 'selected_color')
        self.load_categories()
        debug.debug("Categories reloaded after adding new category")

class EditCategoryDialog(QDialog):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        debug.debug("Getting database connection from overridden method")
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    @debug_method
    def __init__(self, category_id, parent=None):
        super().__init__(parent)
        self.category_id = category_id
        debug.debug(f"Initializing EditCategoryDialog for category ID: {category_id}")
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
        debug.debug("EditCategoryDialog initialized")
    
    @debug_method
    def load_data(self):
        debug.debug(f"Loading data for category ID: {self.category_id}")
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM categories WHERE id = ?", (self.category_id,))
                result = cursor.fetchone()
                if result:
                    name = result[0]
                    debug.debug(f"Loaded category name: '{name}'")
                    self.name_input.setText(name)
                else:
                    debug.warning(f"No category found with ID {self.category_id}")
        except Exception as e:
            debug.error(f"Error loading category data: {e}")
    
    @debug_method
    def save_changes(self, checked = False):
        new_name = self.name_input.text().strip()
        debug.debug(f"Saving category with new name: '{new_name}'")
        
        if not new_name:
            debug.warning("Category name is empty")
            QMessageBox.warning(self, "Error", "Category name is required.")
            return
            
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check for duplicate name - case insensitive
                debug.debug(f"Checking for duplicate category name: '{new_name}'")
                cursor.execute("""
                    SELECT name FROM categories 
                    WHERE LOWER(name) = LOWER(?) AND id != ?
                """, (new_name, self.category_id))
                existing = cursor.fetchone()
                if existing:
                    debug.warning(f"A category with name '{new_name}' already exists")
                    QMessageBox.warning(self, "Error", 
                                    "A category with this name already exists.")
                    return
                    
                debug.debug(f"Updating category ID {self.category_id} with new name: '{new_name}'")
                cursor.execute("""
                    UPDATE categories 
                    SET name = ?
                    WHERE id = ?""", 
                    (new_name, self.category_id))
                conn.commit()
                debug.debug("Category updated successfully")
        except Exception as e:
            debug.error(f"Error updating category: {e}")
            return
        
        debug.debug("Category edit dialog completed successfully")
        self.accept()