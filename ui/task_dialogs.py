# src/ui/task_dialogs.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QPushButton, QTextEdit,
                             QDateEdit, QFormLayout, QWidget, QListWidget,
                             QListWidgetItem, QInputDialog, QMessageBox,
                             QScrollArea, QApplication)
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
        super().__init__(parent)
        self.setWindowTitle("Add New Task")
        self.setMinimumWidth(500)
        self.setMinimumHeight(500)
        
        # Detect OS style
        app = QApplication.instance()
        self.os_style = "Default"
        if app.property("style_manager"):
            self.os_style = app.property("style_manager").current_style
            debug.debug(f"AddTaskDialog using OS style: {self.os_style}")
        
        self.setup_ui()
        # Apply OS-specific styling
        self.apply_os_specific_adjustments()
        self.load_statuses()
        self.data = None  # Store the data here
        
    def apply_os_specific_adjustments(self):
        """Apply OS-specific adjustments to the dialog"""
        if self.os_style == "macOS":
            # macOS-specific adjustments
            self.setContentsMargins(20, 20, 20, 20)
            
            # More rounded corners for macOS
            for btn in self.findChildren(QPushButton):
                btn.setStyleSheet("border-radius: 5px;")
                
            # Adjust spacing for macOS
            for layout in self.findChildren(QFormLayout):
                layout.setSpacing(10)
                
        elif self.os_style == "Windows":
            # Windows-specific adjustments
            self.setContentsMargins(15, 15, 15, 15)
            
            # More rectangular elements for Windows
            for btn in self.findChildren(QPushButton):
                btn.setStyleSheet("border-radius: 2px;")
                
            # Adjust spacing for Windows
            for layout in self.findChildren(QFormLayout):
                layout.setSpacing(6)
                
        else:  # Linux
            # Linux-specific adjustments
            self.setContentsMargins(18, 18, 18, 18)
            
            # Medium roundness for Linux
            for btn in self.findChildren(QPushButton):
                btn.setStyleSheet("border-radius: 4px;")
                
            # Adjust spacing for Linux
            for layout in self.findChildren(QFormLayout):
                layout.setSpacing(8)
                
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
        # Set the form layout to expand horizontally
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        # Title
        self.title_input = QLineEdit()
        self.title_input.setFixedHeight(30)
        self.title_input.setMinimumWidth(400)  # Make title wider
        # Set title to expand horizontally too
        from PyQt6.QtWidgets import QSizePolicy
        self.title_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        form_layout.addRow("Title:", self.title_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMinimumHeight(80)
        self.description_input.setMinimumWidth(400)  # Make description wider
        # Set size policy to expand horizontally with window
        from PyQt6.QtWidgets import QSizePolicy
        self.description_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
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
        # Set field growth policy to allow fields to grow
        left_column.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
        # Status
        self.status_combo = QComboBox()
        self.status_combo.setFixedHeight(30)
        # Load statuses and auto-size immediately after creation
        self.load_statuses()
        left_column.addRow("Status:", self.status_combo)
        
        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.setFixedHeight(30)
        self.load_priorities()
        left_column.addRow("Priority:", self.priority_combo)
        
        # Right column: Category and Due Date
        right_column = QFormLayout()
        right_column.setSpacing(10)
        # Set field growth policy to allow fields to grow
        right_column.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
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
        
        # Links widget - using existing LinkListWidget (now without internal button)
        self.links_widget = LinkListWidget(self)
        
        # Files widget - using existing FileListWidget (now without internal button)
        self.files_widget = FileListWidget(self)
        
        # Add both widgets to horizontal layout
        widgets_layout.addWidget(self.links_widget)
        widgets_layout.addWidget(self.files_widget)
        
        # Add widgets layout to attachments layout
        attachments_layout.addLayout(widgets_layout)
        
        # Add left-aligned buttons for Links and Files (matching Save/Cancel style)
        buttons_container = QHBoxLayout()
        
        # Add Link button
        add_link_button = QPushButton("Add Link")
        add_link_button.setFixedWidth(120)
        add_link_button.setFixedHeight(32)
        add_link_button.setIcon(QIcon.fromTheme("list-add"))
        add_link_button.clicked.connect(self.links_widget.add_link)
        buttons_container.addWidget(add_link_button)
        
        # Add File button
        add_file_button = QPushButton("Add File")
        add_file_button.setFixedWidth(120)
        add_file_button.setFixedHeight(32)
        add_file_button.setIcon(QIcon.fromTheme("list-add"))
        add_file_button.clicked.connect(self.files_widget.add_file)
        buttons_container.addWidget(add_file_button)
        
        # Add buttons container to attachments layout
        attachments_layout.addLayout(buttons_container)
        
        # Add attachments layout to main layout
        layout.addLayout(attachments_layout)
        
        # Dialog control buttons (Save/Cancel)
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setFixedHeight(30)
        save_btn.setDefault(True)  # This will apply the default button style for the OS
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(30)
        cancel_btn.setProperty("secondary", True)  # Mark as secondary button
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
        self.setTabOrder(self.due_date_edit, add_link_button)
        self.setTabOrder(add_link_button, add_file_button)
        self.setTabOrder(add_file_button, save_btn)
        self.setTabOrder(save_btn, cancel_btn)
        debug.debug("AddTaskDialog UI setup complete")
        
    @debug_method
    def add_link(self, check = False):
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
    def edit_link(self, check = False):
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
    def remove_link(self, check = False):
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
            for cat_id, name in categories:  # Fixed - iterate over categories instead of calling fetchall() again
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
        self.parent_combo.clear()
        self.parent_combo.addItem("None", None)
        
        # Get database manager
        from database.memory_db_manager import get_memory_db_manager
        db_manager = get_memory_db_manager()
        
        try:
            # Modified query to exclude completed tasks and include priority
            query = """
                SELECT t.id, t.title, t.priority 
                FROM tasks t
                WHERE t.status != 'Completed'
                ORDER BY t.priority, t.title
            """
            
            tasks = db_manager.execute_query(query)
            debug.debug(f"Loaded {len(tasks)} possible parent tasks")
            
            for task_id, title, priority in tasks:
                # Format as [Priority]: Task Title
                display_text = f"[{priority}]: {title}"
                self.parent_combo.addItem(display_text, task_id)
        except Exception as e:
            debug.error(f"Error loading possible parents: {e}")
            import traceback
            traceback.print_exc()            
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
        
        # Detect OS style
        app = QApplication.instance()
        self.os_style = "Default"
        if app.property("style_manager"):
            self.os_style = app.property("style_manager").current_style
            debug.debug(f"EditTaskDialog using OS style: {self.os_style}")
        
        self.setup_ui()
        # Apply OS-specific styling
        self.apply_os_specific_adjustments()
        # self.load_statuses()
        debug.debug("EditTaskDialog initialization complete")
        
    @debug_method
    def setup_ui(self):
        debug.debug("Setting up EditTaskDialog UI")
        # Import QSizePolicy at the top for use throughout the method
        from PyQt6.QtWidgets import QSizePolicy
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        # Set the form layout to expand horizontally
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        # Title
        self.title_input = QLineEdit(self.task_data['title'])  # Load existing title
        self.title_input.setFixedHeight(30)
        self.title_input.setMinimumWidth(400)  # Make title wider
        # Set title to expand horizontally too
        self.title_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        form_layout.addRow("Title:", self.title_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMinimumHeight(80)
        self.description_input.setMinimumWidth(400)  # Make description wider
        # Set size policy to expand horizontally with window
        self.description_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.description_input.setText(self.task_data['description'] or "")  # Load existing description
        form_layout.addRow("Description:", self.description_input)
        
        # Parent Task
        self.parent_combo = QComboBox()
        self.parent_combo.setFixedHeight(30)
        self.load_possible_parents()  # This will set current parent
        form_layout.addRow("Parent Task:", self.parent_combo)
        
        layout.addLayout(form_layout)
        
        # Status/Priority and Category/Due Date section in a 2x2 grid
        grid_layout = QHBoxLayout()
        
        # Left column: Status and Priority
        left_column = QFormLayout()
        left_column.setSpacing(10)
        # Set field growth policy to allow fields to grow
        left_column.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
        # Status
        self.status_combo = QComboBox()
        self.status_combo.setFixedHeight(30)
        # Load statuses and auto-size immediately after creation
        self.load_statuses()  # This will set current status
        left_column.addRow("Status:", self.status_combo)
        
        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.setFixedHeight(30)
        self.load_priorities()  # This will set current priority
        left_column.addRow("Priority:", self.priority_combo)
        
        # Right column: Category and Due Date
        right_column = QFormLayout()
        right_column.setSpacing(10)
        # Set field growth policy to allow fields to grow
        right_column.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
        # Category
        self.category_combo = QComboBox()
        self.category_combo.setFixedHeight(30)
        self.load_categories()  # This will set current category
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
        
        # Links widget - using existing LinkListWidget (now without internal button)
        self.links_widget = LinkListWidget(self)
        self.load_links()  # Load existing links
        
        # Files widget - using existing FileListWidget (now without internal button)
        self.files_widget = FileListWidget(self)
        self.load_files()  # Load existing files
        
        # Add both widgets to horizontal layout
        widgets_layout.addWidget(self.links_widget)
        widgets_layout.addWidget(self.files_widget)
        
        # Add widgets layout to attachments layout
        attachments_layout.addLayout(widgets_layout)
        
        # Add left-aligned buttons for Links and Files (matching Save/Cancel style)
        buttons_container = QHBoxLayout()
        
        # Add Link button
        add_link_button = QPushButton("Add Link")
        add_link_button.setFixedWidth(120)
        add_link_button.setFixedHeight(32)
        add_link_button.setIcon(QIcon.fromTheme("list-add"))
        add_link_button.clicked.connect(self.links_widget.add_link)
        buttons_container.addWidget(add_link_button)
        
        # Add File button
        add_file_button = QPushButton("Add File")
        add_file_button.setFixedWidth(120)
        add_file_button.setFixedHeight(32)
        add_file_button.setIcon(QIcon.fromTheme("list-add"))
        add_file_button.clicked.connect(self.files_widget.add_file)
        buttons_container.addWidget(add_file_button)
        
        # Add buttons container to attachments layout
        attachments_layout.addLayout(buttons_container)
        
        # Add attachments layout to main layout
        layout.addLayout(attachments_layout)
        
        # Dialog control buttons (Save/Cancel)
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setFixedHeight(30)
        save_btn.setDefault(True)  # This will apply the default button style for the OS
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(30)
        cancel_btn.setProperty("secondary", True)  # Mark as secondary button
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
        self.setTabOrder(self.due_date_edit, add_link_button)
        self.setTabOrder(add_link_button, add_file_button)
        self.setTabOrder(add_file_button, save_btn)
        self.setTabOrder(save_btn, cancel_btn)
        debug.debug("EditTaskDialog UI setup complete")           
    
    def get_data(self):
        return self.data

    @debug_method
    def load_priorities(self):
        """Load priorities for editing a task with improved selection logic"""
        debug.debug("Loading priorities")
        self.priority_combo.clear()
        
        # Store current priority value for selection
        current_priority = self.task_data.get('priority', 'Medium')
        debug.debug(f"Current priority value: {current_priority}")
        
        # Get database manager
        from database.memory_db_manager import get_memory_db_manager
        db_manager = get_memory_db_manager()
        
        try:
            # Get all priorities from database
            priorities = db_manager.execute_query(
                "SELECT id, name FROM priorities ORDER BY display_order"
            )
            debug.debug(f"Loaded {len(priorities)} priorities from database")
            
            # Flag to track if we found the current priority
            priority_found = False
            
            # Add all priorities to the combo box
            for i, (pri_id, name) in enumerate(priorities):
                self.priority_combo.addItem(name, pri_id)
                
                # If this is the current priority, select it
                if name == current_priority:
                    debug.debug(f"Found matching priority at index {i}: {name}")
                    self.priority_combo.setCurrentIndex(i)
                    priority_found = True
            
            # If priority wasn't found, use Unprioritized or Medium as fallback
            if not priority_found:
                debug.debug(f"Priority '{current_priority}' not found in combo box items")
                
                # Try "Unprioritized" first
                unprioritized_index = self.priority_combo.findText("Unprioritized")
                if unprioritized_index >= 0:
                    debug.debug(f"Using fallback priority: Unprioritized at index {unprioritized_index}")
                    self.priority_combo.setCurrentIndex(unprioritized_index)
                else:
                    # If no "Unprioritized", try "Medium"
                    medium_index = self.priority_combo.findText("Medium")
                    if medium_index >= 0:
                        debug.debug(f"Using fallback priority: Medium at index {medium_index}")
                        self.priority_combo.setCurrentIndex(medium_index)
                    else:
                        # Last resort: just use the first item
                        debug.debug("Using first priority item as last resort")
                        self.priority_combo.setCurrentIndex(0)
        
        except Exception as e:
            debug.error(f"Error loading priorities: {e}")
            import traceback
            traceback.print_exc()

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
    def add_link(self, check = False):
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
    def edit_link(self, check = False):
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
    def remove_link(self, check = False):
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
            for cat_id, name in categories:  # Fixed - iterate over categories instead of calling fetchall() again
                self.category_combo.addItem(name, cat_id)
                if name == self.task_data['category']:
                    debug.debug(f"Setting current category: {name}")
                    self.category_combo.setCurrentIndex(self.category_combo.count() - 1)

    @debug_method
    def load_possible_parents(self):
        debug.debug(f"Loading possible parent tasks for task {self.task_data['id']}")
        
        # First add "None" option
        self.parent_combo.clear()
        self.parent_combo.addItem("None", None)
        
        # Store current parent_id for selection
        current_parent_id = self.task_data.get('parent_id')
        debug.debug(f"Current parent_id: {current_parent_id}")
        
        # If we have no parent, select the None option
        if current_parent_id is None:
            debug.debug("Task has no parent, selecting 'None' option")
            self.parent_combo.setCurrentIndex(0)
        
        # Get database manager
        from database.memory_db_manager import get_memory_db_manager
        db_manager = get_memory_db_manager()
        
        try:
            # Get all potential parent tasks - excluding current task, its descendants, and any tasks marked as completed
            task_id = self.task_data['id']
            
            # First get IDs of all tasks that can't be parents (current task and descendants)
            exclude_ids = [task_id]  # Start with current task
            
            # Find all direct children
            children = db_manager.execute_query(
                "SELECT id FROM tasks WHERE parent_id = ?", 
                (task_id,)
            )
            
            for child_id, in children:
                exclude_ids.append(child_id)
                # Get grandchildren (simple 2-level hierarchy for now)
                grandchildren = db_manager.execute_query(
                    "SELECT id FROM tasks WHERE parent_id = ?", 
                    (child_id,)
                )
                for grandchild_id, in grandchildren:
                    exclude_ids.append(grandchild_id)
            
            # Format for SQL query
            exclude_ids_str = ', '.join('?' for _ in exclude_ids)
            
            # Query for potential parents, excluding the invalid IDs, completed tasks, and ensuring they exist
            query = f"""
                SELECT t.id, t.title, t.priority
                FROM tasks t
                WHERE t.id NOT IN ({exclude_ids_str})
                AND t.status != 'Completed'
                ORDER BY t.priority, t.title
            """
            
            tasks = db_manager.execute_query(query, exclude_ids)
            debug.debug(f"Loaded {len(tasks)} possible parent tasks")
            
            # Set initial values
            parent_index_found = False
            
            for task_id, title, priority in tasks:
                # Format as [Priority]: Task Title
                display_text = f"[{priority}]: {title}"
                self.parent_combo.addItem(display_text, task_id)
                
                # If this is the current parent, select it
                if task_id == current_parent_id:
                    debug.debug(f"Found current parent task at index {self.parent_combo.count() - 1}")
                    self.parent_combo.setCurrentIndex(self.parent_combo.count() - 1)
                    parent_index_found = True
            
            # Diagnostics for parent selection
            if current_parent_id is not None and not parent_index_found:
                debug.debug(f"WARNING: Parent task {current_parent_id} not found in available list!")
                # Try to get more information about the missing parent
                parent_info = db_manager.execute_query(
                    "SELECT title FROM tasks WHERE id = ?", 
                    (current_parent_id,)
                )
                if parent_info and len(parent_info) > 0:
                    debug.debug(f"Missing parent title: {parent_info[0][0]}")
                else:
                    debug.debug(f"Parent task {current_parent_id} does not exist in database!")
                    # Reset parent to None if parent doesn't exist
                    debug.debug("Resetting parent to None")
                    self.parent_combo.setCurrentIndex(0)
        
        except Exception as e:
            debug.error(f"Error loading possible parents: {e}")
            import traceback
            traceback.print_exc()
    
    @debug_method
    def load_files(self, check = False):
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
   
    def apply_os_specific_adjustments(self):
        """Apply OS-specific adjustments to the dialog"""
        if self.os_style == "macOS":
            # macOS-specific adjustments
            self.setContentsMargins(20, 20, 20, 20)
            
            # More rounded corners for macOS
            for btn in self.findChildren(QPushButton):
                btn.setStyleSheet("border-radius: 5px;")
                    
            # Adjust spacing for macOS
            for layout in self.findChildren(QFormLayout):
                layout.setSpacing(10)
                    
        elif self.os_style == "Windows":
            # Windows-specific adjustments
            self.setContentsMargins(15, 15, 15, 15)
            
            # More rectangular elements for Windows
            for btn in self.findChildren(QPushButton):
                btn.setStyleSheet("border-radius: 2px;")
                    
            # Adjust spacing for Windows
            for layout in self.findChildren(QFormLayout):
                layout.setSpacing(6)
                    
        else:  # Linux
            # Linux-specific adjustments
            self.setContentsMargins(18, 18, 18, 18)
            
            # Medium roundness for Linux
            for btn in self.findChildren(QPushButton):
                btn.setStyleSheet("border-radius: 4px;")
                    
            # Adjust spacing for Linux
            for layout in self.findChildren(QFormLayout):
                layout.setSpacing(8)

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
        
        # Apply OS-specific styling
        self.apply_os_style()
        
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

    def apply_os_style(self):
        """Apply OS-specific styling to the dialog"""
        import platform
        os_name = platform.system()
        
        if os_name == "Darwin":  # macOS
            self.apply_macos_style()
        elif os_name == "Windows":
            self.apply_windows_style()
        else:  # Linux or other
            self.apply_linux_style()

    def apply_macos_style(self):
        """Apply macOS-specific styling to the dialog"""
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F7;
                border-radius: 10px;
            }
            QLabel {
                font-family: -apple-system, '.AppleSystemUIFont', 'SF Pro Text';
                color: #1D1D1F;
            }
            QLineEdit {
                border: 1px solid #D2D2D7;
                border-radius: 5px;
                background-color: white;
                padding: 5px 8px;
                height: 24px;
                font-family: -apple-system, '.AppleSystemUIFont';
                selection-background-color: #0071E3;
            }
            QLineEdit:focus {
                border: 1px solid #0071E3;
            }
            QPushButton {
                background-color: #E5E5EA;
                color: #1D1D1F;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                min-width: 80px;
                height: 24px;
                font-family: -apple-system, '.AppleSystemUIFont';
            }
            QPushButton:hover {
                background-color: #D1D1D6;
            }
            QPushButton:pressed {
                background-color: #C7C7CC;
            }
            QPushButton[primary="true"], QPushButton:default {
                background-color: #0071E3;
                color: white;
                font-weight: 500;
            }
        """)
        
        self.layout().setContentsMargins(20, 20, 20, 20)
        self.layout().setSpacing(12)
        
        # Set Save button as primary
        for button in self.findChildren(QPushButton):
            if "Save" in button.text():
                button.setProperty("primary", True)
                button.setDefault(True)
                button.style().unpolish(button)
                button.style().polish(button)

    def apply_windows_style(self):
        """Apply Windows-specific styling to the dialog"""
        self.setStyleSheet("""
            QDialog {
                background-color: #F0F0F0;
            }
            QLabel {
                font-family: 'Segoe UI', sans-serif;
                color: #000000;
            }
            QLineEdit {
                border: 1px solid #CCCCCC;
                border-radius: 2px;
                background-color: white;
                padding: 4px 6px;
                font-family: 'Segoe UI';
                selection-background-color: #0078D7;
            }
            QLineEdit:focus {
                border: 1px solid #0078D7;
            }
            QPushButton {
                background-color: #E1E1E1;
                color: #000000;
                border: 1px solid #ADADAD;
                border-radius: 2px;
                padding: 5px 10px;
                min-width: 80px;
                height: 28px;
                font-family: 'Segoe UI';
            }
            QPushButton:hover {
                background-color: #E5F1FB;
                border: 1px solid #0078D7;
            }
            QPushButton:default {
                background-color: #0078D7;
                color: white;
                border: 1px solid #0078D7;
            }
        """)
        
        self.layout().setContentsMargins(15, 15, 15, 15)
        self.layout().setSpacing(8)

    def apply_linux_style(self):
        """Apply Linux-specific styling to the dialog"""
        self.setStyleSheet("""
            QDialog {
                background-color: #F6F5F4;
            }
            QLabel {
                font-family: 'Ubuntu', 'Noto Sans', sans-serif;
                color: #3D3D3D;
            }
            QLineEdit {
                border: 1px solid #C6C6C6;
                border-radius: 4px;
                background-color: white;
                padding: 5px 8px;
                font-family: 'Ubuntu', 'Noto Sans';
                selection-background-color: #3584E4;
            }
            QLineEdit:focus {
                border: 1px solid #3584E4;
            }
            QPushButton {
                background-color: #FFFFFF;
                color: #3D3D3D;
                border: 1px solid #C6C6C6;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 80px;
                height: 30px;
                font-family: 'Ubuntu', 'Noto Sans';
            }
            QPushButton:hover {
                background-color: #F2F2F2;
                border: 1px solid #B8B8B8;
            }
            QPushButton:default {
                background-color: #3584E4;
                color: white;
                border: 1px solid #1E65BD;
            }
        """)
        
        self.layout().setContentsMargins(18, 18, 18, 18)
        self.layout().setSpacing(10)
        
class LinkListWidget(QWidget):
    """Widget for managing multiple links for a task"""
    
    @debug_method
    def __init__(self, parent=None):
            debug.debug("Initializing LinkListWidget")
            super().__init__(parent)
            self.links = []  # List of (id, url, label) tuples, id can be None for new links
            self.setup_ui()
            debug.debug("LinkListWidget initialization complete")
        
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
        
        debug.debug("LinkListWidget UI setup complete")
    
    @debug_method
    def add_link(self, check = False):
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
    def edit_link(self, index, check = False):
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
    def remove_link(self, index, check = False):
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
    def set_links(self, links, check = False):
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
        """Refresh the links display with hover-to-show buttons"""
        debug.debug("Refreshing links display")
        # Clear existing widgets
        while self.links_layout.count():
            item = self.links_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add link items
        for i, (link_id, url, label) in enumerate(self.links):
            # Create a custom widget that handles hover events
            link_item = LinkItemWidget(i, link_id, url, label, self)
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
        
        # Apply OS-specific styling
        # self.apply_os_style()
        
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
            # If No, continue without adding protocol - don't return early
            else:
                debug.debug("User declined to add protocol, continuing without it")
        
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
        
        debug.debug("FileListWidget UI setup complete")
    
    @debug_method
    def add_file(self, check = False):
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
    def edit_file(self, index, check = False):
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
    def remove_file(self, index, check = False):
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
        """Refresh the files display with hover-to-show buttons"""
        debug.debug("Refreshing files display")
        # Clear existing widgets
        while self.files_layout.count():
            item = self.files_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add file items
        for i, (file_id, file_path, file_name) in enumerate(self.files):
            # Create a custom widget that handles hover events
            file_item = FileItemWidget(i, file_id, file_path, file_name, self)
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
            
    def apply_os_style(self):
        """Apply OS-specific styling to the dialog"""
        import platform
        os_name = platform.system()
        
        if os_name == "Darwin":  # macOS
            self.apply_macos_style()
        elif os_name == "Windows":
            self.apply_windows_style()
        else:  # Linux or other
            self.apply_linux_style()

    def apply_macos_style(self):
        """Apply macOS-specific styling to the dialog"""
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F7;
                border-radius: 10px;
            }
            QLabel {
                font-family: -apple-system, '.AppleSystemUIFont', 'SF Pro Text';
                color: #1D1D1F;
            }
            QLineEdit {
                border: 1px solid #D2D2D7;
                border-radius: 5px;
                background-color: white;
                padding: 5px 8px;
                height: 24px;
                font-family: -apple-system, '.AppleSystemUIFont';
                selection-background-color: #0071E3;
            }
            QLineEdit:focus {
                border: 1px solid #0071E3;
            }
            QPushButton {
                background-color: #E5E5EA;
                color: #1D1D1F;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                min-width: 80px;
                height: 24px;
                font-family: -apple-system, '.AppleSystemUIFont';
            }
            QPushButton:hover {
                background-color: #D1D1D6;
            }
            QPushButton:pressed {
                background-color: #C7C7CC;
            }
            QPushButton[primary="true"], QPushButton:default {
                background-color: #0071E3;
                color: white;
                font-weight: 500;
            }
        """)
        
        self.layout().setContentsMargins(20, 20, 20, 20)
        self.layout().setSpacing(12)
        
        # Set Save button as primary
        for button in self.findChildren(QPushButton):
            if "Save" in button.text():
                button.setProperty("primary", True)
                button.setDefault(True)
                button.style().unpolish(button)
                button.style().polish(button)

    def apply_windows_style(self):
        """Apply Windows-specific styling to the dialog"""
        self.setStyleSheet("""
            QDialog {
                background-color: #F0F0F0;
            }
            QLabel {
                font-family: 'Segoe UI', sans-serif;
                color: #000000;
            }
            QLineEdit {
                border: 1px solid #CCCCCC;
                border-radius: 2px;
                background-color: white;
                padding: 4px 6px;
                font-family: 'Segoe UI';
                selection-background-color: #0078D7;
            }
            QLineEdit:focus {
                border: 1px solid #0078D7;
            }
            QPushButton {
                background-color: #E1E1E1;
                color: #000000;
                border: 1px solid #ADADAD;
                border-radius: 2px;
                padding: 5px 10px;
                min-width: 80px;
                height: 28px;
                font-family: 'Segoe UI';
            }
            QPushButton:hover {
                background-color: #E5F1FB;
                border: 1px solid #0078D7;
            }
            QPushButton:default {
                background-color: #0078D7;
                color: white;
                border: 1px solid #0078D7;
            }
        """)
        
        self.layout().setContentsMargins(15, 15, 15, 15)
        self.layout().setSpacing(8)

    def apply_linux_style(self):
        """Apply Linux-specific styling to the dialog"""
        self.setStyleSheet("""
            QDialog {
                background-color: #F6F5F4;
            }
            QLabel {
                font-family: 'Ubuntu', 'Noto Sans', sans-serif;
                color: #3D3D3D;
            }
            QLineEdit {
                border: 1px solid #C6C6C6;
                border-radius: 4px;
                background-color: white;
                padding: 5px 8px;
                font-family: 'Ubuntu', 'Noto Sans';
                selection-background-color: #3584E4;
            }
            QLineEdit:focus {
                border: 1px solid #3584E4;
            }
            QPushButton {
                background-color: #FFFFFF;
                color: #3D3D3D;
                border: 1px solid #C6C6C6;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 80px;
                height: 30px;
                font-family: 'Ubuntu', 'Noto Sans';
            }
            QPushButton:hover {
                background-color: #F2F2F2;
                border: 1px solid #B8B8B8;
            }
            QPushButton:default {
                background-color: #3584E4;
                color: white;
                border: 1px solid #1E65BD;
            }
        """)
        
        self.layout().setContentsMargins(18, 18, 18, 18)
        self.layout().setSpacing(10)

class LinkItemWidget(QWidget):
    """Custom widget for link items with hover-to-show buttons"""
    
    def __init__(self, index, link_id, url, label, parent_widget):
        super().__init__()
        self.index = index
        self.link_id = link_id
        self.url = url
        self.label = label
        self.parent_widget = parent_widget
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
        # Create layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)  # Tighter spacing between buttons
        
        # Link display label
        self.link_label = QLabel(url)
        self.link_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        # Set tooltip
        if label and label.strip():
            self.link_label.setToolTip(f"{label}")
        else:
            self.link_label.setToolTip(url)
            
        self.layout.addWidget(self.link_label)
        
        # Spacer
        self.layout.addStretch()
        
        # Create buttons but hide them initially
        self.edit_button = QPushButton("✏️")
        self.edit_button.setProperty("emojiButton", True)  # Special property for styling
        self.edit_button.setFixedSize(24, 24)
        self.edit_button.setToolTip("Edit link")
        self.edit_button.clicked.connect(self.edit_link)
        self.edit_button.hide()  # Initially hidden
        self.layout.addWidget(self.edit_button)
        
        self.remove_button = QPushButton("🗑️")
        self.remove_button.setProperty("emojiButton", True)  # Special property for styling
        self.remove_button.setFixedSize(24, 24)
        self.remove_button.setToolTip("Remove link")
        self.remove_button.clicked.connect(self.remove_link)
        self.remove_button.hide()  # Initially hidden
        self.layout.addWidget(self.remove_button)
    
    def enterEvent(self, event):
        """Show buttons when mouse enters the widget"""
        self.edit_button.show()
        self.remove_button.show()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Hide buttons when mouse leaves the widget"""
        self.edit_button.hide()
        self.remove_button.hide()
        super().leaveEvent(event)
    
    def edit_link(self):
        """Handle edit button click"""
        self.parent_widget.edit_link(self.index)
    
    def remove_link(self):
        """Handle remove button click"""
        self.parent_widget.remove_link(self.index)

class FileItemWidget(QWidget):
    """Custom widget for file items with hover-to-show buttons"""
    
    def __init__(self, index, file_id, file_path, file_name, parent_widget):
        super().__init__()
        self.index = index
        self.file_id = file_id
        self.file_path = file_path
        self.file_name = file_name
        self.parent_widget = parent_widget
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
        # Create layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)  # Tighter spacing between buttons
        
        # File display label
        self.file_label = QLabel(file_name)
        self.file_label.setToolTip(file_path)  # Show full path on hover
        self.file_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.layout.addWidget(self.file_label)
        
        # Spacer
        self.layout.addStretch()
        
        # Create buttons but hide them initially
        self.open_button = QPushButton("📂")
        self.open_button.setProperty("emojiButton", True)  # Special property for styling
        self.open_button.setFixedSize(24, 24)
        self.open_button.setToolTip("Open file")
        self.open_button.clicked.connect(self.open_file)
        self.open_button.hide()  # Initially hidden
        self.layout.addWidget(self.open_button)
        
        self.edit_button = QPushButton("✏️")
        self.edit_button.setProperty("emojiButton", True)  # Special property for styling
        self.edit_button.setFixedSize(24, 24)
        self.edit_button.setToolTip("Change file")
        self.edit_button.clicked.connect(self.edit_file)
        self.edit_button.hide()  # Initially hidden
        self.layout.addWidget(self.edit_button)
        
        self.remove_button = QPushButton("🗑️")
        self.remove_button.setProperty("emojiButton", True)  # Special property for styling
        self.remove_button.setFixedSize(24, 24)
        self.remove_button.setToolTip("Remove file")
        self.remove_button.clicked.connect(self.remove_file)
        self.remove_button.hide()  # Initially hidden
        self.layout.addWidget(self.remove_button)
    
    def enterEvent(self, event):
        """Show buttons when mouse enters the widget"""
        self.open_button.show()
        self.edit_button.show()
        self.remove_button.show()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Hide buttons when mouse leaves the widget"""
        self.open_button.hide()
        self.edit_button.hide()
        self.remove_button.hide()
        super().leaveEvent(event)
    
    def open_file(self):
        """Handle open button click"""
        self.parent_widget.open_file(self.file_path)
    
    def edit_file(self):
        """Handle edit button click"""
        self.parent_widget.edit_file(self.index)
    
    def remove_file(self):
        """Handle remove button click"""
        self.parent_widget.remove_file(self.index)

class AnimatedLinkItemWidget(QWidget):
    """Link item widget with fade animation on hover"""
    
    def __init__(self, index, link_id, url, label, parent_widget):
        super().__init__()
        self.index = index
        self.link_id = link_id
        self.url = url
        self.label = label
        self.parent_widget = parent_widget
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
        # Create layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Link display label
        self.link_label = QLabel(url)
        self.link_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        if label and label.strip():
            self.link_label.setToolTip(f"{label}")
        else:
            self.link_label.setToolTip(url)
            
        self.layout.addWidget(self.link_label)
        self.layout.addStretch()
        
        # Create buttons
        self.edit_button = QPushButton("✏️")
        self.edit_button.setFixedSize(12, 16)  # Smaller size
        self.edit_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 3px;
                font-size: 10px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #999999;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)
        self.edit_button.setToolTip("Edit link")
        self.edit_button.clicked.connect(self.edit_link)
        self.layout.addWidget(self.edit_button)
        
        self.remove_button = QPushButton("🗑️")
        self.remove_button.setFixedSize(12, 16)  # Smaller size
        self.remove_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 3px;
                font-size: 6px !important;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #999999;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)
        self.remove_button.setToolTip("Remove link")
        self.remove_button.clicked.connect(self.remove_link)
        self.layout.addWidget(self.remove_button)
        
        # Create fade animations
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        
        # Opacity effects
        self.edit_effect = QGraphicsOpacityEffect()
        self.remove_effect = QGraphicsOpacityEffect()
        self.edit_button.setGraphicsEffect(self.edit_effect)
        self.remove_button.setGraphicsEffect(self.remove_effect)
        
        # Animations
        self.edit_animation = QPropertyAnimation(self.edit_effect, b"opacity")
        self.edit_animation.setDuration(200)  # 200ms animation
        self.edit_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self.remove_animation = QPropertyAnimation(self.remove_effect, b"opacity")
        self.remove_animation.setDuration(200)
        self.remove_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Start hidden
        self.edit_effect.setOpacity(0)
        self.remove_effect.setOpacity(0)
    
    def enterEvent(self, event):
        """Fade in buttons when mouse enters"""
        self.edit_animation.setStartValue(0)
        self.edit_animation.setEndValue(1)
        self.edit_animation.start()
        
        self.remove_animation.setStartValue(0)
        self.remove_animation.setEndValue(1)
        self.remove_animation.start()
        
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Fade out buttons when mouse leaves"""
        self.edit_animation.setStartValue(1)
        self.edit_animation.setEndValue(0)
        self.edit_animation.start()
        
        self.remove_animation.setStartValue(1)
        self.remove_animation.setEndValue(0)
        self.remove_animation.start()
        
        super().leaveEvent(event)
    
    def edit_link(self):
        self.parent_widget.edit_link(self.index)
    
    def remove_link(self):
        self.parent_widget.remove_link(self.index)