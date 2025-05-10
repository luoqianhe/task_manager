# src/ui/task_dialogs.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QPushButton, QTextEdit,
                             QDateEdit, QFormLayout, QWidget, QListWidget,
                             QListWidgetItem, QInputDialog, QMessageBox,
                             QScrollArea)
from pathlib import Path
import sqlite3
from PyQt6.QtGui import QKeySequence, QShortcut, QIcon
from PyQt6.QtCore import Qt, QDate, QTimer
from datetime import datetime, date

# Import the debug logger and decorator
from utils.debug_logger import get_debug_logger
from utils.debug_decorator import debug_method

# Get debug logger instance
debug = get_debug_logger()

class AddTaskDialog(QDialog):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    @debug_method
    def __init__(self, parent=None):
        debug.debug("Initializing AddTaskDialog")
        super().__init__(parent)
        self.setWindowTitle("Add New Task")
        self.setMinimumWidth(500)
        self.setMinimumHeight(500)
        self.setup_ui()
        self.load_statuses()
        self.data = None  # Store the data here
        debug.debug("AddTaskDialog initialization complete")
    
    @debug_method
    def load_priorities(self):
        """Load priorities including 'Unprioritized' option"""
        debug.debug("Loading priorities")
        self.priority_combo.clear()  # Clear existing items
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM priorities ORDER BY display_order")
            priorities = cursor.fetchall()
            debug.debug(f"Loaded {len(priorities)} priorities from database")
            
            # Add all priorities to the combo box
            for pri_id, name in priorities:
                self.priority_combo.addItem(name, pri_id)
            
            # Find and select the "Unprioritized" option
            unprioritized_index = self.priority_combo.findText("Unprioritized")
            if unprioritized_index >= 0:
                debug.debug("Setting default priority to 'Unprioritized'")
                self.priority_combo.setCurrentIndex(unprioritized_index)
            else:
                # If "Unprioritized" not found, select first item
                debug.debug("'Unprioritized' not found, selecting first item instead")
                self.priority_combo.setCurrentIndex(0)

    @debug_method
    def accept(self, checked=None):
        debug.debug("Accept button clicked - collecting task data")
        # Store the data before closing
        due_date = None
        if self.due_date_edit.date() != QDate(2000, 1, 1):  # Default empty date
            due_date = self.due_date_edit.date().toString("yyyy-MM-dd")
            debug.debug(f"Due date set: {due_date}")
        
        # Get the selected priority directly from the combo box
        selected_priority = self.priority_combo.currentText()
        debug.debug(f"Selected priority: {selected_priority}")
        
        # Get links from the links widget
        links = self.links_widget.get_links()
        debug.debug(f"Links collected: {len(links)} links")
        
        # Get files from the files widget
        files = self.files_widget.get_files()
        debug.debug(f"Files collected: {len(files)} files")
        
        self.data = {
            'title': self.title_input.text(),
            'description': self.description_input.toPlainText(),
            'links': links,  # List of (id, url, label) tuples
            'files': files,  # List of (id, file_path, file_name) tuples
            'status': self.status_combo.currentText(),
            'priority': selected_priority,
            'due_date': due_date,
            'category': self.category_combo.currentText() if self.category_combo.currentIndex() > 0 else None,
            'parent_id': self.parent_combo.currentData()
        }
        debug.debug(f"Task data collected: {self.data['title']}")
        super().accept()

    def get_data(self):
        return self.data
    
    @debug_method
    def setup_ui(self):
        debug.debug("Setting up AddTaskDialog UI")
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Title
        self.title_input = QLineEdit()
        self.title_input.setFixedHeight(30)
        self.title_input.setMinimumWidth(400)  # Make title wider
        form_layout.addRow("Title:", self.title_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMinimumHeight(80)
        self.description_input.setMinimumWidth(400)  # Make description wider
        form_layout.addRow("Description:", self.description_input)
        
        # Parent Task
        self.parent_combo = QComboBox()
        self.parent_combo.setFixedHeight(30)
        self.load_possible_parents()
        form_layout.addRow("Parent Task:", self.parent_combo)
        
        layout.addLayout(form_layout)
        
        # Status/Priority and Category/Due Date section in a 2x2 grid
        grid_layout = QHBoxLayout()
        
        # Left column: Status and Priority
        left_column = QFormLayout()
        left_column.setSpacing(10)
        
        # Status
        self.status_combo = QComboBox()
        self.status_combo.setFixedHeight(30)
        left_column.addRow("Status:", self.status_combo)
        
        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.setFixedHeight(30)
        self.load_priorities()
        left_column.addRow("Priority:", self.priority_combo)
        
        # Right column: Category and Due Date
        right_column = QFormLayout()
        right_column.setSpacing(10)
        
        # Category
        self.category_combo = QComboBox()
        self.category_combo.setFixedHeight(30)
        self.load_categories()
        right_column.addRow("Category:", self.category_combo)
        
        # Due Date
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setFixedHeight(30)
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDate(QDate(2000, 1, 1))  # Default empty date
        self.due_date_edit.setSpecialValueText("No Due Date")
        right_column.addRow("Due Date:", self.due_date_edit)
        
        # Add both columns to the grid with equal size
        left_widget = QWidget()
        left_widget.setLayout(left_column)
        
        right_widget = QWidget()
        right_widget.setLayout(right_column)
        
        grid_layout.addWidget(left_widget)
        grid_layout.addWidget(right_widget)
        
        layout.addLayout(grid_layout)
        
        # Links and Files side by side with labels
        attachments_layout = QVBoxLayout()
        
        # Labels for sections
        labels_layout = QHBoxLayout()
        links_label = QLabel("Links:")
        files_label = QLabel("Files:")
        links_label.setStyleSheet("font-weight: bold;")
        files_label.setStyleSheet("font-weight: bold;")
        
        # Equal width for both sides
        labels_layout.addWidget(links_label)
        labels_layout.addWidget(files_label)
        attachments_layout.addLayout(labels_layout)
        
        # Widget containers
        widgets_layout = QHBoxLayout()
        
        # Links widget - using existing LinkListWidget
        self.links_widget = LinkListWidget(self)
        
        # Files widget - using existing FileListWidget
        self.files_widget = FileListWidget(self)
        
        # Add both widgets to horizontal layout
        widgets_layout.addWidget(self.links_widget)
        widgets_layout.addWidget(self.files_widget)
        
        # Add widgets layout to attachments layout
        attachments_layout.addLayout(widgets_layout)
        
        # Add attachments layout to main layout
        layout.addLayout(attachments_layout)
        
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
        self.setTabOrder(self.description_input, self.parent_combo)
        self.setTabOrder(self.parent_combo, self.status_combo)
        self.setTabOrder(self.status_combo, self.priority_combo)
        self.setTabOrder(self.priority_combo, self.category_combo)
        self.setTabOrder(self.category_combo, self.due_date_edit)
        self.setTabOrder(self.due_date_edit, save_btn)
        self.setTabOrder(save_btn, cancel_btn)
        debug.debug("AddTaskDialog UI setup complete")
    
    @debug_method
    def add_link(self):
        """Add a new link to the list"""
        debug.debug("Adding new link")
        link_dialog = LinkDialog(self)
        if link_dialog.exec():
            url = link_dialog.url_input.text().strip()
            label = link_dialog.label_input.text().strip()
            debug.debug(f"Link added: URL={url}, Label={label}")
            
            # Create a new item for the links list
            display_text = f"{label or url}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, {"url": url, "label": label})
            self.links_list.addItem(item)

    @debug_method
    def edit_link(self):
        """Edit the selected link"""
        debug.debug("Editing selected link")
        selected_items = self.links_list.selectedItems()
        if not selected_items:
            debug.debug("No link selected for editing")
            return
            
        item = selected_items[0]
        link_data = item.data(Qt.ItemDataRole.UserRole)
        debug.debug(f"Editing link: URL={link_data['url']}, Label={link_data['label']}")
        
        link_dialog = LinkDialog(self, link_data["url"], link_data["label"])
        if link_dialog.exec():
            url = link_dialog.url_input.text().strip()
            label = link_dialog.label_input.text().strip()
            debug.debug(f"Link updated: URL={url}, Label={label}")
            
            # Update the item
            display_text = f"{label or url}"
            item.setText(display_text)
            item.setData(Qt.ItemDataRole.UserRole, {"url": url, "label": label})

    @debug_method
    def remove_link(self):
        """Remove the selected link"""
        debug.debug("Removing selected link")
        selected_items = self.links_list.selectedItems()
        if not selected_items:
            debug.debug("No link selected for removal")
            return
            
        row = self.links_list.row(selected_items[0])
        self.links_list.takeItem(row)
        debug.debug(f"Link removed from row {row}")
        
        # Update button state
        self.update_link_buttons()

    @debug_method
    def update_link_buttons(self):
        """Enable/disable edit and remove buttons based on selection"""
        debug.debug("Updating link buttons state")
        has_selection = len(self.links_list.selectedItems()) > 0
        self.edit_link_btn.setEnabled(has_selection)
        self.remove_link_btn.setEnabled(has_selection)
        debug.debug(f"Link buttons enabled: {has_selection}")

    @debug_method
    def load_categories(self):
        debug.debug("Loading categories")
        self.category_combo.addItem("None", None)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM categories ORDER BY name")
            categories = cursor.fetchall()
            debug.debug(f"Loaded {len(categories)} categories from database")
            for cat_id, name in cursor.fetchall():
                self.category_combo.addItem(name, cat_id)
    
    @debug_method
    def load_statuses(self):
        """Load statuses from the database"""
        debug.debug("Loading statuses")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM statuses ORDER BY display_order")
            statuses = cursor.fetchall()
            debug.debug(f"Loaded {len(statuses)} statuses from database")
            
            for status in statuses:
                self.status_combo.addItem(status[0])
            
            # Default to "Not Started" if it exists
            not_started_index = self.status_combo.findText("Not Started")
            if not_started_index >= 0:
                debug.debug("Setting default status to 'Not Started'")
                self.status_combo.setCurrentIndex(not_started_index)
    
    @debug_method
    def load_possible_parents(self):
        debug.debug("Loading possible parent tasks")
        self.parent_combo.addItem("None", None)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Modified query to exclude completed tasks and include priority
            cursor.execute("""
                SELECT t.id, t.title, t.priority 
                FROM tasks t
                WHERE t.status != 'Completed'
                ORDER BY t.priority, t.title
            """)
            tasks = cursor.fetchall()
            debug.debug(f"Loaded {len(tasks)} possible parent tasks")
            for task_id, title, priority in tasks:
                # Format as [Priority]: Task Title
                display_text = f"[{priority}]: {title}"
                self.parent_combo.addItem(display_text, task_id)
                
class EditTaskDialog(QDialog):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    @debug_method
    def __init__(self, task_data, parent=None):
        debug.debug(f"Initializing EditTaskDialog for task: {task_data['title']}")
        super().__init__(parent)
        self.task_data = task_data
        self.setWindowTitle("Edit Task")
        self.setMinimumWidth(500)
        self.setMinimumHeight(500)
        self.setup_ui()
        self.load_statuses()
        debug.debug("EditTaskDialog initialization complete")

    @debug_method
    def setup_ui(self):
        debug.debug("Setting up EditTaskDialog UI")
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Title
        self.title_input = QLineEdit(self.task_data['title'])
        self.title_input.setFixedHeight(30)
        self.title_input.setMinimumWidth(400)  # Make title wider
        form_layout.addRow("Title:", self.title_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMinimumHeight(80)
        self.description_input.setMinimumWidth(400)  # Make description wider
        self.description_input.setText(self.task_data['description'] or "")
        form_layout.addRow("Description:", self.description_input)
        
        # Parent Task
        self.parent_combo = QComboBox()
        self.parent_combo.setFixedHeight(30)
        self.load_possible_parents()
        form_layout.addRow("Parent Task:", self.parent_combo)
        
        layout.addLayout(form_layout)
        
        # Status/Priority and Category/Due Date section in a 2x2 grid
        grid_layout = QHBoxLayout()
        
        # Left column: Status and Priority
        left_column = QFormLayout()
        left_column.setSpacing(10)
        
        # Status
        self.status_combo = QComboBox()
        self.status_combo.setFixedHeight(30)
        self.status_combo.setCurrentText(self.task_data['status'] or "Not Started")
        left_column.addRow("Status:", self.status_combo)
        
        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.setFixedHeight(30)
        self.load_priorities()
        left_column.addRow("Priority:", self.priority_combo)
        
        # Right column: Category and Due Date
        right_column = QFormLayout()
        right_column.setSpacing(10)
        
        # Category
        self.category_combo = QComboBox()
        self.category_combo.setFixedHeight(30)
        self.load_categories()
        right_column.addRow("Category:", self.category_combo)
        
        # Due Date
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setFixedHeight(30)
        self.due_date_edit.setCalendarPopup(True)
        
        # Set the current due date if it exists
        if self.task_data['due_date']:
            try:
                due_date = QDate.fromString(self.task_data['due_date'], "yyyy-MM-dd")
                self.due_date_edit.setDate(due_date)
                debug.debug(f"Set due date: {self.task_data['due_date']}")
            except ValueError:
                self.due_date_edit.setDate(QDate(2000, 1, 1))  # Default empty date
                debug.error(f"Invalid due date format: {self.task_data['due_date']}")
        else:
            self.due_date_edit.setDate(QDate(2000, 1, 1))  # Default empty date
            debug.debug("No due date set")
            
        self.due_date_edit.setSpecialValueText("No Due Date")
        right_column.addRow("Due Date:", self.due_date_edit)
        
        # Add both columns to the grid with equal size
        left_widget = QWidget()
        left_widget.setLayout(left_column)
        
        right_widget = QWidget()
        right_widget.setLayout(right_column)
        
        grid_layout.addWidget(left_widget)
        grid_layout.addWidget(right_widget)
        
        layout.addLayout(grid_layout)
        
        # Links and Files side by side with labels
        attachments_layout = QVBoxLayout()
        
        # Labels for sections
        labels_layout = QHBoxLayout()
        links_label = QLabel("Links:")
        files_label = QLabel("Files:")
        links_label.setStyleSheet("font-weight: bold;")
        files_label.setStyleSheet("font-weight: bold;")
        
        # Equal width for both sides
        labels_layout.addWidget(links_label)
        labels_layout.addWidget(files_label)
        attachments_layout.addLayout(labels_layout)
        
        # Widget containers
        widgets_layout = QHBoxLayout()
        
        # Links widget - using existing LinkListWidget
        self.links_widget = LinkListWidget(self)
        self.load_links()  # Load existing links
        
        # Files widget - using existing FileListWidget
        self.files_widget = FileListWidget(self)
        self.load_files()  # Load existing files
        
        # Add both widgets to horizontal layout
        widgets_layout.addWidget(self.links_widget)
        widgets_layout.addWidget(self.files_widget)
        
        # Add widgets layout to attachments layout
        attachments_layout.addLayout(widgets_layout)
        
        # Add attachments layout to main layout
        layout.addLayout(attachments_layout)
        
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
        self.setTabOrder(self.description_input, self.parent_combo)
        self.setTabOrder(self.parent_combo, self.status_combo)
        self.setTabOrder(self.status_combo, self.priority_combo)
        self.setTabOrder(self.priority_combo, self.category_combo)
        self.setTabOrder(self.category_combo, self.due_date_edit)
        self.setTabOrder(self.due_date_edit, save_btn)
        self.setTabOrder(save_btn, cancel_btn)
        debug.debug("EditTaskDialog UI setup complete")

    def get_data(self):
        return self.data

    @debug_method
    def load_priorities(self):
        """Load priorities for editing a task"""
        debug.debug("Loading priorities")
        self.priority_combo.clear()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM priorities ORDER BY display_order")
            priorities = cursor.fetchall()
            debug.debug(f"Loaded {len(priorities)} priorities from database")
            
            # Add all priorities to the combo box
            for pri_id, name in priorities:
                self.priority_combo.addItem(name, pri_id)
                
                # If this is the current priority of the task, select it
                if name == self.task_data['priority']:
                    debug.debug(f"Setting current priority: {name}")
                    self.priority_combo.setCurrentIndex(self.priority_combo.count() - 1)
        
        # If no matching priority was found (or priority is None),
        # look for the "Unprioritized" option
        if self.task_data['priority'] is None or self.priority_combo.currentText() != self.task_data['priority']:
            unprioritized_index = self.priority_combo.findText("Unprioritized")
            if unprioritized_index >= 0:
                debug.debug("Setting default priority to 'Unprioritized'")
                self.priority_combo.setCurrentIndex(unprioritized_index)        

    @debug_method
    def load_statuses(self):
        """Load statuses from the database"""
        debug.debug("Loading statuses")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM statuses ORDER BY display_order")
            statuses = cursor.fetchall()
            debug.debug(f"Loaded {len(statuses)} statuses from database")
            
            for status in statuses:
                self.status_combo.addItem(status[0])
            
            # Select the current status
            current_status = self.task_data.get('status', 'Not Started')
            index = self.status_combo.findText(current_status)
            if index >= 0:
                debug.debug(f"Setting current status: {current_status}")
                self.status_combo.setCurrentIndex(index)

    @debug_method
    def load_links(self):
        """Load existing links for the task"""
        debug.debug(f"Loading links for task: {self.task_data['id']}")
        try:
            # Get links from the task_data (passed in during initialization)
            links = self.task_data.get('links', [])
            debug.debug(f"Found {len(links)} links to load")
            self.links_widget.set_links(links)
        except Exception as e:
            debug.error(f"Error loading links: {e}")
            import traceback
            traceback.print_exc()

    @debug_method
    def add_link(self):
        """Add a new link to the list"""
        debug.debug("Adding new link")
        link_dialog = LinkDialog(self)
        if link_dialog.exec():
            url = link_dialog.url_input.text().strip()
            label = link_dialog.label_input.text().strip()
            debug.debug(f"Link added: URL={url}, Label={label}")
            
            # Create a new item for the links list
            display_text = f"{label or url}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, {"url": url, "label": label, "id": None})
            self.links_list.addItem(item)

    @debug_method
    def edit_link(self):
        """Edit the selected link"""
        debug.debug("Editing selected link")
        selected_items = self.links_list.selectedItems()
        if not selected_items:
            debug.debug("No link selected for editing")
            return
            
        item = selected_items[0]
        link_data = item.data(Qt.ItemDataRole.UserRole)
        debug.debug(f"Editing link: URL={link_data['url']}, Label={link_data['label']}")
        
        link_dialog = LinkDialog(self, link_data["url"], link_data["label"])
        if link_dialog.exec():
            url = link_dialog.url_input.text().strip()
            label = link_dialog.label_input.text().strip()
            debug.debug(f"Link updated: URL={url}, Label={label}")
            
            # Update the item
            display_text = f"{label or url}"
            item.setText(display_text)
            
            # Preserve the link ID if it exists
            item.setData(Qt.ItemDataRole.UserRole, {
                "url": url, 
                "label": label, 
                "id": link_data.get("id")
            })

    @debug_method
    def remove_link(self):
        """Remove the selected link"""
        debug.debug("Removing selected link")
        selected_items = self.links_list.selectedItems()
        if not selected_items:
            debug.debug("No link selected for removal")
            return
            
        row = self.links_list.row(selected_items[0])
        self.links_list.takeItem(row)
        debug.debug(f"Link removed from row {row}")
        
        # Update button state
        self.update_link_buttons()

    @debug_method
    def update_link_buttons(self):
        """Enable/disable edit and remove buttons based on selection"""
        debug.debug("Updating link buttons state")
        has_selection = len(self.links_list.selectedItems()) > 0
        self.edit_link_btn.setEnabled(has_selection)
        self.remove_link_btn.setEnabled(has_selection)
        debug.debug(f"Link buttons enabled: {has_selection}")
        
    @debug_method
    def accept(self, checked=None):
        debug.debug("Accept button clicked - collecting task data")
        # Collect data to be saved
        due_date = None
        if self.due_date_edit.date() != QDate(2000, 1, 1):  # Default empty date
            due_date = self.due_date_edit.date().toString("yyyy-MM-dd")
            debug.debug(f"Due date set: {due_date}")

        # Get selected priority directly from combo box
        selected_priority = self.priority_combo.currentText()
        debug.debug(f"Selected priority: {selected_priority}")
                
        # Get links from the widget
        links = self.links_widget.get_links()
        debug.debug(f"Links collected: {len(links)} links")

        # Get files from the widget
        files = self.files_widget.get_files()
        debug.debug(f"Files collected: {len(files)} files")

        self.data = {
        'id': self.task_data['id'],
        'title': self.title_input.text(),
        'description': self.description_input.toPlainText(),
        'links': links,  # List of (id, url, label) tuples
        'files': files,  # List of (id, file_path, file_name) tuples
        'status': self.status_combo.currentText(),
        'priority': selected_priority,
        'due_date': due_date,
        'category': self.category_combo.currentText() if self.category_combo.currentIndex() > 0 else None,
        'parent_id': self.parent_combo.currentData()
        }
        debug.debug(f"Task data collected: {self.data['title']}")
        super().accept()

    @debug_method
    def load_categories(self):
        debug.debug("Loading categories")
        self.category_combo.addItem("None", None)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM categories ORDER BY name")
            categories = cursor.fetchall()
            debug.debug(f"Loaded {len(categories)} categories from database")
            for cat_id, name in cursor.fetchall():
                self.category_combo.addItem(name, cat_id)
                if name == self.task_data['category']:
                    debug.debug(f"Setting current category: {name}")
                    self.category_combo.setCurrentIndex(self.category_combo.count() - 1)
    
    @debug_method
    def load_possible_parents(self):
        debug.debug(f"Loading possible parent tasks for task {self.task_data['id']}")
        self.parent_combo.addItem("None", None)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Modified query to exclude completed tasks and this task itself, and include priority
            cursor.execute("""
                SELECT t.id, t.title, t.priority
                FROM tasks t
                WHERE t.id != ? AND t.status != 'Completed'
                AND t.id NOT IN (SELECT id FROM tasks WHERE parent_id = ?)
                ORDER BY t.priority, t.title
            """, (self.task_data['id'], self.task_data['id']))
            
            tasks = cursor.fetchall()
            debug.debug(f"Loaded {len(tasks)} possible parent tasks")
            
            current_parent = self.task_data.get('parent_id')
            for task_id, title, priority in tasks:
                # Format as [Priority]: Task Title
                display_text = f"[{priority}]: {title}"
                self.parent_combo.addItem(display_text, task_id)
                
    @debug_method
    def load_files(self):
        """Load existing files for the task"""
        debug.debug(f"Loading files for task: {self.task_data['id']}")
        try:
            # Get files from the task_data (passed in during initialization)
            files = self.task_data.get('files', [])
            debug.debug(f"Found {len(files)} files to load")
            self.files_widget.set_files(files)
        except Exception as e:
            debug.error(f"Error loading files: {e}")
            import traceback
            traceback.print_exc()
            
class EditStatusDialog(QDialog):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
   
    @debug_method
    def __init__(self, status_id, parent=None):
        debug.debug(f"Initializing EditStatusDialog for status ID: {status_id}")
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
        debug.debug("EditStatusDialog initialization complete")
    
    @debug_method
    def load_data(self):
        debug.debug(f"Loading data for status ID: {self.status_id}")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM statuses WHERE id = ?", (self.status_id,))
            name = cursor.fetchone()[0]
            debug.debug(f"Loaded status name: {name}")
            self.name_input.setText(name)
    
    @debug_method
    def save_changes(self):
        debug.debug("Saving status changes")
        new_name = self.name_input.text().strip()
        
        if not new_name:
            debug.debug("Status name is empty, showing warning")
            QMessageBox.warning(self, "Error", "Status name is required.")
            return
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get the old name
            cursor.execute("SELECT name FROM statuses WHERE id = ?", (self.status_id,))
            old_name = cursor.fetchone()[0]
            debug.debug(f"Current status name: {old_name}")
            
            # Check for duplicate name - case insensitive
            cursor.execute("""
                SELECT name FROM statuses 
                WHERE LOWER(name) = LOWER(?) AND id != ?
            """, (new_name, self.status_id))
            existing = cursor.fetchone()
            if existing:
                debug.debug(f"Duplicate status name found: {existing[0]}")
                QMessageBox.warning(self, "Error", 
                                   "A status with this name already exists.")
                return
            
            # Update the status name
            debug.debug(f"Updating status name to: {new_name}")
            cursor.execute("""
                UPDATE statuses 
                SET name = ?
                WHERE id = ?""", 
                (new_name, self.status_id))
            
            # Update all tasks that use the old status name
            debug.debug(f"Updating tasks with old status name: {old_name}")
            cursor.execute("""
                UPDATE tasks 
                SET status = ?
                WHERE status = ?""", 
                (new_name, old_name))
                
            conn.commit()
            debug.debug("Status changes saved successfully")
        
        self.accept()

# New component for task_dialogs.py
class LinkListWidget(QWidget):
    """Widget for managing multiple links for a task"""
    
    @debug_method
    def __init__(self, parent=None):
        debug.debug("Initializing LinkListWidget")
        super().__init__(parent)
        self.links = []  # List of (id, url, label) tuples, id can be None for new links
        self.setup_ui()
        debug.debug("LinkListWidget initialization complete")
    
    @debug_method
    def setup_ui(self):
        debug.debug("Setting up LinkListWidget UI")
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Links list
        self.links_layout = QVBoxLayout()
        self.links_layout.setSpacing(5)
        
        # Create a scroll area for links
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setLayout(self.links_layout)
        scroll_area.setWidget(scroll_content)
        scroll_area.setMaximumHeight(150)
        
        # Add scroll area to main layout
        layout.addWidget(scroll_area)
        
        # Add link button
        add_link_button = QPushButton("Add Link")
        add_link_button.setIcon(QIcon.fromTheme("list-add"))
        add_link_button.clicked.connect(self.add_link)
        layout.addWidget(add_link_button)
        debug.debug("LinkListWidget UI setup complete")
    
    @debug_method
    def add_link(self):
        """Open dialog to add a new link"""
        debug.debug("Adding new link")
        dialog = LinkDialog(self)
        if dialog.exec():
            url = dialog.url_input.text().strip()
            label = dialog.label_input.text().strip()
            debug.debug(f"New link added: URL={url}, Label={label}")
            
            # Add to internal list (None for id means it's a new link)
            self.links.append((None, url, label))
            
            # Update UI
            self.refresh_links()
    
    @debug_method
    def edit_link(self, index):
        """Edit a link at the specified index"""
        debug.debug(f"Editing link at index {index}")
        link_id, url, label = self.links[index]
        
        dialog = LinkDialog(self, url, label)
        if dialog.exec():
            new_url = dialog.url_input.text().strip()
            new_label = dialog.label_input.text().strip()
            debug.debug(f"Link updated: URL={new_url}, Label={new_label}")
            
            # Update in internal list
            self.links[index] = (link_id, new_url, new_label)
            
            # Update UI
            self.refresh_links()
    
    @debug_method
    def remove_link(self, index):
        """Remove a link at the specified index"""
        debug.debug(f"Removing link at index {index}")
        # Ask for confirmation
        confirm = QMessageBox.question(
            self, "Remove Link", 
            "Are you sure you want to remove this link?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            debug.debug("Link removal confirmed")
            # Remove from internal list
            self.links.pop(index)
            
            # Update UI
            self.refresh_links()
    
    @debug_method
    def set_links(self, links):
        """Set the list of links (id, url, label) tuples"""
        debug.debug(f"Setting {len(links)} links")
        self.links = list(links)  # Create a copy
        self.refresh_links()
    
    @debug_method
    def get_links(self):
        """Get the current list of links"""
        debug.debug(f"Getting {len(self.links)} links")
        return list(self.links)  # Return a copy
    
    @debug_method
    def refresh_links(self):
        """Refresh the links display"""
        debug.debug("Refreshing links display")
        # Clear existing widgets
        while self.links_layout.count():
            item = self.links_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add link items
        for i, (link_id, url, label) in enumerate(self.links):
            link_item = QWidget()
            item_layout = QHBoxLayout(link_item)
            item_layout.setContentsMargins(0, 0, 0, 0)
            
            # Link display label - show label (if exists) and URL
            display_text = f"{label}: {url}" if label else url
            link_label = QLabel(display_text)
            link_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            item_layout.addWidget(link_label)
            
            # Spacer to push buttons to the right
            item_layout.addStretch()
            
            # Edit button
            edit_button = QPushButton("Edit")
            edit_button.setFixedWidth(60)
            edit_button.clicked.connect(lambda checked, idx=i: self.edit_link(idx))
            item_layout.addWidget(edit_button)
            
            # Remove button
            remove_button = QPushButton("Remove")
            remove_button.setFixedWidth(60)
            remove_button.clicked.connect(lambda checked, idx=i: self.remove_link(idx))
            item_layout.addWidget(remove_button)
            
            # Add to links layout
            self.links_layout.addWidget(link_item)
        
        # Add a stretch at the end
        self.links_layout.addStretch()
        debug.debug(f"Refreshed display with {len(self.links)} links")

class LinkDialog(QDialog):
    """Dialog for adding or editing a link"""
    
    @debug_method
    def __init__(self, parent=None, url="", label=""):
        debug.debug(f"Initializing LinkDialog: URL={url}, Label={label}")
        super().__init__(parent)
        self.setWindowTitle("Link Details")
        self.setMinimumWidth(400)
        self.setup_ui(url, label)
        debug.debug("LinkDialog initialization complete")
    
    @debug_method
    def setup_ui(self, url, label):
        debug.debug("Setting up LinkDialog UI")
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # URL input
        self.url_input = QLineEdit(url)
        self.url_input.setPlaceholderText("https://example.com")
        form_layout.addRow("URL:", self.url_input)
        
        # Label input
        self.label_input = QLineEdit(label)
        self.label_input.setPlaceholderText("Optional description for this link")
        form_layout.addRow("Label (optional):", self.label_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.validate_and_accept)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        debug.debug("LinkDialog UI setup complete")
    
    @debug_method
    def validate_and_accept(self):
        """Validate URL and accept dialog"""
        debug.debug("Validating URL")
        url = self.url_input.text().strip()
        
        if not url:
            debug.debug("URL is empty, showing warning")
            QMessageBox.warning(self, "Validation Error", "URL cannot be empty.")
            return
        
        # Basic URL validation
        if not (url.startswith("http://") or url.startswith("https://") or url.startswith("ftp://")):
            debug.debug(f"URL missing protocol: {url}")
            # Ask user if they want to prepend https://
            reply = QMessageBox.question(
                self, "Add Protocol",
                f"Would you like to prepend 'https://' to '{url}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                debug.debug(f"Adding https:// to URL: {url}")
                self.url_input.setText(f"https://{url}")
            else:
                debug.debug("User declined to add protocol, returning without accepting")
                return
        
        debug.debug("URL validation passed, accepting dialog")
        self.accept()
        
class FileListWidget(QWidget):
    """Widget for managing multiple file attachments for a task"""
    
    @debug_method
    def __init__(self, parent=None):
        debug.debug("Initializing FileListWidget")
        super().__init__(parent)
        self.files = []  # List of (id, file_path, file_name) tuples, id can be None for new files
        self.setup_ui()
        debug.debug("FileListWidget initialization complete")
    
    @debug_method
    def setup_ui(self):
        debug.debug("Setting up FileListWidget UI")
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Files list
        self.files_layout = QVBoxLayout()
        self.files_layout.setSpacing(5)
        
        # Create a scroll area for files
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setLayout(self.files_layout)
        scroll_area.setWidget(scroll_content)
        scroll_area.setMaximumHeight(150)
        
        # Add scroll area to main layout
        layout.addWidget(scroll_area)
        
        # Add file button
        add_file_button = QPushButton("Add File")
        add_file_button.setIcon(QIcon.fromTheme("list-add"))
        add_file_button.clicked.connect(self.add_file)
        layout.addWidget(add_file_button)
        debug.debug("FileListWidget UI setup complete")
    
    @debug_method
    def add_file(self):
        """Open dialog to select a new file"""
        debug.debug("Opening file selection dialog")
        from PyQt6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select File", "", "All Files (*.*)"
        )
        
        if file_path:
            debug.debug(f"File selected: {file_path}")
            # Extract filename for display
            from pathlib import Path
            file_name = Path(file_path).name
            
            # Add to internal list (None for id means it's a new file)
            self.files.append((None, file_path, file_name))
            debug.debug(f"Added file: {file_name}")
            
            # Update UI
            self.refresh_files()
    
    @debug_method
    def edit_file(self, index):
        """Edit a file path at the specified index"""
        debug.debug(f"Editing file at index {index}")
        file_id, old_path, old_name = self.files[index]
        
        from PyQt6.QtWidgets import QFileDialog
        
        # Start dialog in the directory of the current file if possible
        start_dir = str(Path(old_path).parent) if old_path else ""
        debug.debug(f"Opening file dialog at: {start_dir}")
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Update File", start_dir, "All Files (*.*)"
        )
        
        if file_path:
            debug.debug(f"New file selected: {file_path}")
            # Extract filename for display
            from pathlib import Path
            file_name = Path(file_path).name
            
            # Update in internal list
            self.files[index] = (file_id, file_path, file_name)
            debug.debug(f"Updated file to: {file_name}")
            
            # Update UI
            self.refresh_files()
    
    @debug_method
    def remove_file(self, index):
        """Remove a file at the specified index"""
        debug.debug(f"Removing file at index {index}")
        # Ask for confirmation
        from PyQt6.QtWidgets import QMessageBox
        
        confirm = QMessageBox.question(
            self, "Remove File", 
            "Are you sure you want to remove this file?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            debug.debug("File removal confirmed")
            # Remove from internal list
            self.files.pop(index)
            
            # Update UI
            self.refresh_files()
    
    @debug_method
    def set_files(self, files):
        """Set the list of files (id, file_path, file_name) tuples"""
        debug.debug(f"Setting {len(files)} files")
        self.files = list(files)  # Create a copy
        self.refresh_files()
    
    @debug_method
    def get_files(self):
        """Get the current list of files"""
        debug.debug(f"Getting {len(self.files)} files")
        return list(self.files)  # Return a copy
    
    @debug_method
    def refresh_files(self):
        """Refresh the files display"""
        debug.debug("Refreshing files display")
        # Clear existing widgets
        while self.files_layout.count():
            item = self.files_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add file items
        for i, (file_id, file_path, file_name) in enumerate(self.files):
            file_item = QWidget()
            item_layout = QHBoxLayout(file_item)
            item_layout.setContentsMargins(0, 0, 0, 0)
            
            # File display label - show filename
            file_label = QLabel(file_name)
            file_label.setToolTip(file_path)  # Show full path on hover
            file_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            item_layout.addWidget(file_label)
            
            # Spacer to push buttons to the right
            item_layout.addStretch()
            
            # Open button
            open_button = QPushButton("Open")
            open_button.setFixedWidth(60)
            open_button.clicked.connect(lambda checked, path=file_path: self.open_file(path))
            item_layout.addWidget(open_button)
            
            # Edit button
            edit_button = QPushButton("Change")
            edit_button.setFixedWidth(60)
            edit_button.clicked.connect(lambda checked, idx=i: self.edit_file(idx))
            item_layout.addWidget(edit_button)
            
            # Remove button
            remove_button = QPushButton("Remove")
            remove_button.setFixedWidth(60)
            remove_button.clicked.connect(lambda checked, idx=i: self.remove_file(idx))
            item_layout.addWidget(remove_button)
            
            # Add to files layout
            self.files_layout.addWidget(file_item)
        
        # Add a stretch at the end
        self.files_layout.addStretch()
        debug.debug(f"Refreshed display with {len(self.files)} files")
    
    @debug_method
    def open_file(self, file_path):
        """Open a file with the default application"""
        debug.debug(f"Attempting to open file: {file_path}")
        if not file_path:
            debug.debug("No file path provided")
            return
            
        try:
            import os
            import platform
            
            # Check if file exists
            if not os.path.exists(file_path):
                debug.debug(f"File does not exist: {file_path}")
                # Handle file not found
                from PyQt6.QtWidgets import QMessageBox
                
                debug.debug("Showing file not found dialog")
                reply = QMessageBox.question(
                    self,
                    "File Not Found",
                    f"The file '{file_path}' could not be found. Would you like to update the file path?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | 
                    QMessageBox.StandardButton.Discard
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    debug.debug("User chose to update file path")
                    # Find the index of this file in the list
                    for i, (_, path, _) in enumerate(self.files):
                        if path == file_path:
                            self.edit_file(i)
                            break
                elif reply == QMessageBox.StandardButton.Discard:
                    debug.debug("User chose to remove file")
                    # Remove the file
                    for i, (_, path, _) in enumerate(self.files):
                        if path == file_path:
                            self.remove_file(i)
                            break
                return
            
            # Open file with default application based on platform
            system = platform.system()
            debug.debug(f"Opening file on platform: {system}")
            
            if system == 'Windows':
                os.startfile(file_path)
                debug.debug("File opened with Windows startfile")
            elif system == 'Darwin':  # macOS
                import subprocess
                subprocess.call(('open', file_path))
                debug.debug("File opened with macOS 'open' command")
            else:  # Linux and others
                import subprocess
                subprocess.call(('xdg-open', file_path))
                debug.debug("File opened with Linux 'xdg-open' command")
                
        except Exception as e:
            debug.error(f"Error opening file: {e}")
            
            # Handle other errors if we have an item reference
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Could not open file: {str(e)}")