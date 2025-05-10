# src/ui/combined_settings.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox, QCheckBox,
    QRadioButton, QButtonGroup, QGroupBox, QPushButton, QColorDialog, QLineEdit,
    QFormLayout, QMessageBox, QScrollArea, QFrame, QSizePolicy, QSplitter, QListWidget, 
    QWidgetItem, QApplication, QListWidgetItem, QDialog
)
from PyQt6.QtGui import QColor, QFont, QDrag
from PyQt6.QtCore import Qt, QSignalBlocker, QMimeData, QSize
import platform
import json

# Import debug utilities
from utils.debug_logger import get_debug_logger
from utils.debug_decorator import debug_method

# Get debug logger instance
debug = get_debug_logger()

# Base class for setting items with consistent pill style
class SettingPillItem(QWidget):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        debug.debug("Getting database connection from overridden method")
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    @debug_method
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
        debug.debug(f"Created {self.item_type} pill: {self.name}")

    @debug_method
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.display_order is not None:
            # Start drag if this is a priority or status (has display_order)
            self.drag_start_position = event.position().toPoint()
            debug.debug(f"Mouse press at {self.drag_start_position} for {self.item_type}: {self.name}")
        super().mousePressEvent(event)
    
    @debug_method
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton) or self.display_order is None:
            # Only allow drag for items with display_order (priorities and statuses)
            super().mouseMoveEvent(event)
            return
            
        # Calculate distance to see if we should start a drag
        if (event.position().toPoint() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return
        
        debug.debug(f"Starting drag for {self.item_type}: {self.name}")
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
        debug.debug(f"Drag data: {data}")
        mime_data.setText(json.dumps(data))
        drag.setMimeData(mime_data)
        
        # Create a pixmap of this widget as drag visual
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.position().toPoint())
        
        # Execute drag
        debug.debug(f"Executing drag for {self.item_type}: {self.name}")
        drag.exec(Qt.DropAction.MoveAction)
    
    @debug_method
    def dragEnterEvent(self, event):
        # Only accept drags from same type of items
        if event.mimeData().hasText():
            try:
                data = json.loads(event.mimeData().text())
                if data['item_type'] == self.item_type and data['item_id'] != self.item_id:
                    debug.debug(f"Accepting drag enter for {self.item_type}: {self.name}")
                    event.acceptProposedAction()
                    return
                else:
                    debug.debug(f"Rejecting drag enter - type mismatch or same item: {data['item_type']} vs {self.item_type}")
            except (json.JSONDecodeError, KeyError) as e:
                debug.error(f"Error parsing drag data: {e}")
        debug.debug("Ignoring drag enter event")
        event.ignore()
    
    @debug_method
    def dropEvent(self, event):
        # Handle item reordering
        if event.mimeData().hasText():
            try:
                data = json.loads(event.mimeData().text())
                debug.debug(f"Processing drop event with data: {data}")
                
                # Find parent CombinedSettingsManager
                parent = self
                while parent and not isinstance(parent, CombinedSettingsManager):
                    parent = parent.parent()
                
                if parent:
                    # Call reorder method with source and target ids
                    debug.debug(f"Reordering items: {data['item_type']} from {data['item_id']} to {self.item_id}")
                    parent.reorder_items(
                        self.item_type,
                        data['item_id'],  # Source item
                        self.item_id      # Target item (where to drop)
                    )
                    event.acceptProposedAction()
                else:
                    debug.error("Could not find parent CombinedSettingsManager")
                    event.ignore()
            except (json.JSONDecodeError, KeyError) as e:
                debug.error(f"Error processing drop event: {e}")
                event.ignore()
        else:
            debug.debug("Drop event has no text data, ignoring")
            event.ignore()
    
    @debug_method
    def change_color(self, checked=None):
        debug.debug(f"Opening color dialog for {self.item_type}: {self.name}")
        color = QColorDialog.getColor()
        if color.isValid():
            new_color = color.name()
            debug.debug(f"New color selected: {new_color}")
            self.update_color_in_db(new_color)
            
            # Update the stored color
            self.color = new_color
            
            # Update the frame background
            self.frame.setStyleSheet(f"#coloredFrame {{ background-color: {new_color}; border-radius: 5px; }}")
            debug.debug(f"Updated color for {self.item_type}: {self.name}")
    
    @debug_method
    def update_color_in_db(self, color):
        # Get correct table name (handle special plurals)
        if self.item_type == "status":
            table_name = "statuses"
        elif self.item_type == "priority":
            table_name = "priorities"
        elif self.item_type == "category":
            table_name = "categories"
        else:
            table_name = f"{self.item_type}s"  # categories
        
        debug.debug(f"Updating color in database table {table_name} for {self.item_type} ID {self.item_id}")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE {table_name} SET color = ? WHERE id = ?",
                         (color, self.item_id))
            conn.commit()
            debug.debug(f"Color updated in database for {self.item_type} ID {self.item_id}")
    
    @debug_method
    def edit_item(self, check = False):
        debug.debug(f"Edit button clicked for {self.item_type}: {self.name}")
        # Find the CombinedSettingsManager instance
        parent = self
        while parent and not isinstance(parent, CombinedSettingsManager):
            parent = parent.parent()
        
        if parent:
            debug.debug(f"Opening edit dialog for {self.item_type} ID {self.item_id}")
            parent.edit_item(self.item_type, self.item_id)
        else:
            debug.error("Could not find parent CombinedSettingsManager")

    @debug_method
    def delete_item(self, check = False):
        # Don't allow deletion of Completed status
        if self.item_type == "status" and self.name == "Completed":
            debug.debug("Attempted to delete Completed status - operation not allowed")
            QMessageBox.information(self, "Cannot Delete", 
                                   "The Completed status cannot be deleted as it's required by the system.")
            return
        
        debug.debug(f"Delete button clicked for {self.item_type}: {self.name}")
        reply = QMessageBox.question(self, f'Delete {self.item_type.title()}', 
                                f'Are you sure you want to delete this {self.item_type}?',
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            debug.debug(f"User confirmed deletion of {self.item_type}: {self.name}")
            # Find the CombinedSettingsManager instance
            parent = self
            while parent and not isinstance(parent, CombinedSettingsManager):
                parent = parent.parent()
            
            if parent:
                debug.debug(f"Deleting {self.item_type} ID {self.item_id}")
                parent.delete_item(self.item_type, self.item_id)
            else:
                debug.error("Could not find parent CombinedSettingsManager")
        else:
            debug.debug(f"User canceled deletion of {self.item_type}: {self.name}")

# Main class for combined settings management
class CombinedSettingsManager(QWidget):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        debug.debug("Getting database connection from overridden method")
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    @debug_method
    def __init__(self):
        debug.debug("Initializing CombinedSettingsManager")
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
        debug.debug("CombinedSettingsManager initialized")
    
    @debug_method
    def init_ui(self):
        debug.debug("Setting up UI for CombinedSettingsManager")
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header_label = QLabel("Categories, Priorities, and Statuses")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(header_label)
        
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
        debug.debug("Creating categories list widget")
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
        
        debug.debug("Creating priorities list widget")
        self.priorities_list = QListWidget()
        self.priorities_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.priorities_list.setStyleSheet(self.categories_list.styleSheet())
        self.priorities_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        
        debug.debug("Creating statuses list widget")
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
        
        # Add stretch to push buttons to bottom
        main_layout.addStretch()
        
        # Add Save and Cancel buttons
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Save")
        save_button.setFixedHeight(30)
        save_button.setMinimumWidth(120)
        save_button.clicked.connect(self.save_settings)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setFixedHeight(30)
        cancel_button.setMinimumWidth(120)
        # Try to find the main window to connect to show_task_view
        parent = self.parent()
        while parent and not hasattr(parent, 'show_task_view'):
            parent = parent.parent()
        if parent and hasattr(parent, 'show_task_view'):
            debug.debug("Found parent with show_task_view method")
            cancel_button.clicked.connect(parent.show_task_view)
        else:
            debug.warning("Could not find parent with show_task_view method")
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        debug.debug("UI setup completed for CombinedSettingsManager")
    
    @debug_method
    def pick_color(self):
        debug.debug("Opening color picker dialog")
        self.selected_color = QColorDialog.getColor().name()
        debug.debug(f"Selected color: {self.selected_color}")
        self.color_btn.setStyleSheet(f"background-color: {self.selected_color}; border-radius: 5px;")
    
    @debug_method
    def change_setting_view(self, setting_type):
        """Switch between different setting views"""
        debug.debug(f"Switching setting view to: {setting_type}")
        # Hide all lists
        self.categories_list.hide()
        self.priorities_list.hide()
        self.statuses_list.hide()
        
        # Show the selected list
        if setting_type == "Categories":
            debug.debug("Showing categories list")
            self.categories_list.show()
            self.add_btn.setText("Add Category")
            self.name_input.setPlaceholderText("Category Name")
        elif setting_type == "Priorities":
            debug.debug("Showing priorities list")
            self.priorities_list.show()
            self.add_btn.setText("Add Priority")
            self.name_input.setPlaceholderText("Priority Name")
        else:  # Statuses
            debug.debug("Showing statuses list")
            self.statuses_list.show()
            self.add_btn.setText("Add Status")
            self.name_input.setPlaceholderText("Status Name")
    
    @debug_method
    def save_settings(self, checked=None):
        """Save settings and notify the user"""
        debug.debug("Saving settings")
        # You can add any additional saving logic here if needed
        
        QMessageBox.information(self, "Settings Saved", "Your settings have been saved.")
        debug.debug("Settings saved successfully")
        
        # Try to find main window to return to task view
        parent = self.parent()
        while parent and not hasattr(parent, 'show_task_view'):
            parent = parent.parent()
        if parent and hasattr(parent, 'show_task_view'):
            debug.debug("Returning to task view")
            parent.show_task_view()
        else:
            debug.warning("Could not find parent with show_task_view method")
    
    @debug_method
    def load_all_items(self):
        """Load all categories, priorities, and statuses"""
        debug.debug("Loading all setting items")
        self.load_categories()
        self.load_priorities()
        self.load_statuses()
        debug.debug("All setting items loaded")
    
    @debug_method
    def load_categories(self):
        """Load categories from the database"""
        debug.debug("Loading categories from database")
        self.categories_list.clear()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categories ORDER BY name")
            categories = cursor.fetchall()
            debug.debug(f"Found {len(categories)} categories")
            
            for category in categories:
                # Create a pill item for each category
                debug.debug(f"Creating pill item for category {category[1]}")
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
        debug.debug("Categories loaded successfully")
    
    @debug_method
    def load_priorities(self):
        """Load priorities from the database"""
        debug.debug("Loading priorities from database")
        self.priorities_list.clear()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, color, display_order FROM priorities ORDER BY display_order")
            priorities = cursor.fetchall()
            debug.debug(f"Found {len(priorities)} priorities")
            
            for priority in priorities:
                # Create a pill item for each priority
                debug.debug(f"Creating pill item for priority {priority[1]}")
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
        debug.debug("Priorities loaded successfully")
    
    @debug_method
    def load_statuses(self):
        """Load statuses from the database"""
        debug.debug("Loading statuses from database")
        self.statuses_list.clear()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, color, display_order FROM statuses ORDER BY display_order")
            statuses = cursor.fetchall()
            debug.debug(f"Found {len(statuses)} statuses")
            
            for status in statuses:
                # Create a pill item for each status
                debug.debug(f"Creating pill item for status {status[1]}")
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
        debug.debug("Statuses loaded successfully")
    
    @debug_method
    def reorder_items(self, item_type, source_id, target_id):
        """Handle reordering via drag and drop"""
        debug.debug(f"Reordering {item_type}s: source_id={source_id}, target_id={target_id}")
        if item_type not in ["priority", "status"]:
            debug.warning(f"Cannot reorder items of type {item_type} - only priority and status can be reordered")
            return  # Only ordered types can be reordered
            
        # Get correct table name (handle special plurals)
        if item_type == "status":
            table_name = "statuses"
        elif item_type == "priority":
            table_name = "priorities"
        else:
            debug.warning(f"Unknown item type: {item_type}")
            return  # Should never happen
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current display orders
                cursor.execute(f"SELECT id, display_order FROM {table_name} ORDER BY display_order")
                items = cursor.fetchall()
                
                # Find source and target orders
                source_order = next((order for id, order in items if id == source_id), None)
                target_order = next((order for id, order in items if id == target_id), None)
                
                if source_order is None or target_order is None:
                    debug.error(f"Could not find source order ({source_order}) or target order ({target_order})")
                    return
                
                debug.debug(f"Reordering from position {source_order} to {target_order}")
                
                # Determine direction of move
                if source_order < target_order:
                    # Moving down: decrement items in between
                    debug.debug(f"Moving down: decrementing items between {source_order} and {target_order}")
                    cursor.execute(f"""
                        UPDATE {table_name}
                        SET display_order = display_order - 1
                        WHERE display_order > ? AND display_order <= ?
                    """, (source_order, target_order))
                else:
                    # Moving up: increment items in between
                    debug.debug(f"Moving up: incrementing items between {target_order} and {source_order}")
                    cursor.execute(f"""
                        UPDATE {table_name}
                        SET display_order = display_order + 1
                        WHERE display_order < ? AND display_order >= ?
                    """, (source_order, target_order))
                
                # Set the dragged item to its new position
                debug.debug(f"Setting {item_type} {source_id} to position {target_order}")
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET display_order = ?
                    WHERE id = ?
                """, (target_order, source_id))
                
                conn.commit()
                debug.debug(f"Database updated successfully for {item_type} reordering")
            
            # Reload the appropriate list
            if item_type == "priority":
                debug.debug("Reloading priorities list")
                self.load_priorities()
            elif item_type == "status":
                debug.debug("Reloading statuses list")
                self.load_statuses()
                
        except Exception as e:
            debug.error(f"Error reordering items: {e}")
    
    @debug_method
    def edit_item(self, item_type, item_id):
        """Open dialog to edit an item"""
        debug.debug(f"Opening edit dialog for {item_type} ID {item_id}")
        dialog = EditItemDialog(item_type, item_id, self)
        if dialog.exec():
            debug.debug(f"Edit dialog accepted for {item_type} ID {item_id}")
            # Reload the appropriate list
            if item_type == "category":
                debug.debug("Reloading categories after edit")
                self.load_categories()
            elif item_type == "priority":
                debug.debug("Reloading priorities after edit")
                self.load_priorities()
            elif item_type == "status":
                debug.debug("Reloading statuses after edit")
                self.load_statuses()
        else:
            debug.warning(f"Unknown item type after edit: {item_type}")
    
    @debug_method
    def delete_item(self, item_type, item_id):
        """Delete an item after confirmation"""
        debug.debug(f"Deleting {item_type} with ID {item_id}")
        # Get correct table name (handle special plurals)
        if item_type == "status":
            table_name = "statuses"
        elif item_type == "priority":
            table_name = "priorities"
        else:
            table_name = f"{item_type}s"  # categories
            
        foreign_key = f"{item_type}_id" if item_type == "category" else item_type
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First check if it's the Completed status
                if item_type == "status":
                    cursor.execute("SELECT name FROM statuses WHERE id = ?", (item_id,))
                    result = cursor.fetchone()
                    if result:
                        name = result[0]
                        debug.debug(f"Status name: {name}")
                        if name == "Completed":
                            debug.warning("Attempted to delete Completed status - operation not allowed")
                            QMessageBox.warning(self, "Cannot Delete", 
                                            "The Completed status cannot be deleted as it's required by the system.")
                            return
                
                # Check if any tasks are using this item
                if item_type == "category":
                    debug.debug(f"Checking if category ID {item_id} is used by any tasks")
                    cursor.execute("SELECT COUNT(*) FROM tasks WHERE category_id = ?", (item_id,))
                else:  # priority or status
                    # Need to get the name first
                    cursor.execute(f"SELECT name FROM {table_name} WHERE id = ?", (item_id,))
                    name = cursor.fetchone()[0]
                    debug.debug(f"Checking if {item_type} '{name}' is used by any tasks")
                    cursor.execute(f"SELECT COUNT(*) FROM tasks WHERE {item_type} = ?", (name,))
                
                count = cursor.fetchone()[0]
                
                if count > 0:
                    debug.warning(f"Cannot delete {item_type} - it is used by {count} tasks")
                    QMessageBox.warning(self, "Error", 
                                    f"Cannot delete this {item_type} because it is used by {count} tasks. " +
                                    "Please reassign those tasks first.")
                    return
                
                # Delete the item
                debug.debug(f"Deleting {item_type} ID {item_id} from {table_name}")
                cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (item_id,))
                
                # If this was a priority or status, reorder the remaining items
                if item_type in ["priority", "status"]:
                    debug.debug(f"Reordering remaining {item_type}s after deletion")
                    cursor.execute(f"""
                        UPDATE {table_name}
                        SET display_order = display_order - 1
                        WHERE display_order > (SELECT display_order FROM {table_name} WHERE id = ?)
                    """, (item_id,))
                
                conn.commit()
                debug.debug(f"Successfully deleted {item_type} ID {item_id}")
        except Exception as e:
            debug.error(f"Error deleting {item_type}: {e}")
        
        # Reload the appropriate list
        if item_type == "category":
            debug.debug("Reloading categories after deletion")
            self.load_categories()
        elif item_type == "priority":
            debug.debug("Reloading priorities after deletion")
            self.load_priorities()
        elif item_type == "status":
            debug.debug("Reloading statuses after deletion")
            self.load_statuses()
    
    @debug_method
    def add_item(self, check = False):
        """Add a new item of the current type"""
        current_type = self.setting_type_combo.currentText().lower()
        debug.debug(f"Adding new item for setting type: {current_type}")
        
        if current_type == "statuses":
            item_type = "status"
        elif current_type == "priorities":
            item_type = "priority"
        elif current_type == "categories":
            item_type = "category"
        else:
            # Fallback for any other cases
            item_type = current_type.rstrip('s')
            debug.debug(f"Using fallback item_type: {item_type}")
        
        name = self.name_input.text().strip()
        
        if not name:
            debug.warning(f"{item_type.title()} name is required but was empty")
            QMessageBox.warning(self, "Error", f"{item_type.title()} name is required.")
            return
            
        if not hasattr(self, 'selected_color'):
            # Default colors based on type
            if item_type == "category":
                self.selected_color = "#F0F7FF"  # Light blue
                debug.debug(f"Using default category color: {self.selected_color}")
            elif item_type == "priority":
                self.selected_color = "#F44336"  # Red
                debug.debug(f"Using default priority color: {self.selected_color}")
            else:  # status
                self.selected_color = "#E0E0E0"  # Light gray
                debug.debug(f"Using default status color: {self.selected_color}")
        
        table_name = "statuses" if item_type == "status" else "priorities" if item_type == "priority" else f"{item_type}s"
        debug.debug(f"Using table name: {table_name}")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check for duplicate name - case insensitive
                debug.debug(f"Checking for duplicate {item_type} name: {name}")
                cursor.execute(f"SELECT name FROM {table_name} WHERE LOWER(name) = LOWER(?)", (name,))
                existing = cursor.fetchone()
                if existing:
                    debug.warning(f"A {item_type} with name '{name}' already exists")
                    QMessageBox.warning(self, "Error", 
                                    f"A {item_type} with this name already exists.")
                    return
                
                # Handle priorities and statuses differently (they have display_order)
                if item_type in ["priority", "status"]:
                    # Get max display order
                    debug.debug(f"Getting maximum display_order for {table_name}")
                    cursor.execute(f"SELECT MAX(display_order) FROM {table_name}")
                    max_order = cursor.fetchone()[0]
                    display_order = (max_order or 0) + 1
                    debug.debug(f"New display_order will be: {display_order}")
                    
                    debug.debug(f"Inserting new {item_type} with name '{name}' and color '{self.selected_color}'")
                    cursor.execute(f"""
                        INSERT INTO {table_name} (name, color, display_order)
                        VALUES (?, ?, ?)
                    """, (name, self.selected_color, display_order))
                else:
                    # Categories don't have display_order
                    debug.debug(f"Inserting new category with name '{name}' and color '{self.selected_color}'")
                    cursor.execute(f"""
                        INSERT INTO {table_name} (name, color)
                        VALUES (?, ?)
                    """, (name, self.selected_color))
                
                conn.commit()
                debug.debug(f"Successfully added {item_type}: {name}")
                
        except Exception as e:
            debug.error(f"Error adding {item_type}: {e}")
        
        # Clear inputs and refresh
        self.name_input.clear()
        self.color_btn.setStyleSheet("")
        if hasattr(self, 'selected_color'):
            delattr(self, 'selected_color')
        
        # Reload the appropriate list
        if item_type == "category":
            debug.debug("Reloading categories after adding new item")
            self.load_categories()
        elif item_type == "priority":
            debug.debug("Reloading priorities after adding new item")
            self.load_priorities()
        elif item_type == "status":
            debug.debug("Reloading statuses after adding new item")
            self.load_statuses()
        else:
            debug.warning(f"Unknown item type after add: {item_type}")

# Dialog for editing any item type
class EditItemDialog(QDialog):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        debug.debug("Getting database connection from overridden method")
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    @debug_method
    def __init__(self, item_type, item_id, parent=None):
        super().__init__(parent)
        self.item_type = item_type
        self.item_id = item_id
        debug.debug(f"Initializing EditItemDialog for {item_type} ID {item_id}")
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
        debug.debug("EditItemDialog initialized")
    
    @debug_method
    def load_data(self):
        debug.debug(f"Loading data for {self.item_type} ID {self.item_id}")
        if self.item_type == "category":
            table_name = "categories"
        elif self.item_type == "priority":
            table_name = "priorities"
        elif self.item_type == "status":
            table_name = "statuses"
        else:
            debug.error(f"Unknown item type: {self.item_type}")
            return
            
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT name FROM {table_name} WHERE id = ?", (self.item_id,))
                result = cursor.fetchone()
                if result:
                    name = result[0]
                    debug.debug(f"Loaded name: {name}")
                    self.name_input.setText(name)
                else:
                    debug.warning(f"No {self.item_type} found with ID {self.item_id}")
        except Exception as e:
            debug.error(f"Error loading data: {e}")
    
    @debug_method
    def save_changes(self, checked=False):
        debug.debug("Saving changes")
        new_name = self.name_input.text().strip()
        
        if not new_name:
            debug.warning(f"{self.item_type.title()} name is required but was empty")
            QMessageBox.warning(self, "Error", f"{self.item_type.title()} name is required.")
            return
        
        # Get correct table name (handle special plurals)
        if self.item_type == "status":
            table_name = "statuses"
        elif self.item_type == "priority":
            table_name = "priorities"
        else:
            table_name = f"{self.item_type}s"  # categories
        
        debug.debug(f"Using table name: {table_name}")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get the old name
                cursor.execute(f"SELECT name FROM {table_name} WHERE id = ?", (self.item_id,))
                result = cursor.fetchone()
                if not result:
                    debug.error(f"Could not find {self.item_type} with ID {self.item_id}")
                    return
                    
                old_name = result[0]
                debug.debug(f"Original name: {old_name}")
                
                # Check for duplicate name - case insensitive
                debug.debug(f"Checking for duplicate name: {new_name}")
                cursor.execute(f"""
                    SELECT name FROM {table_name} 
                    WHERE LOWER(name) = LOWER(?) AND id != ?
                """, (new_name, self.item_id))
                existing = cursor.fetchone()
                if existing:
                    debug.warning(f"A {self.item_type} with name '{new_name}' already exists")
                    QMessageBox.warning(self, "Error", 
                                    f"A {self.item_type} with this name already exists.")
                    return
                
                # Update the item name
                debug.debug(f"Updating {self.item_type} ID {self.item_id} name to: {new_name}")
                cursor.execute(f"""
                    UPDATE {table_name} 
                    SET name = ?
                    WHERE id = ?""", 
                    (new_name, self.item_id))
                
                # For priorities and statuses, also update any tasks using them
                if self.item_type in ["priority", "status"]:
                    debug.debug(f"Updating tasks using {self.item_type} '{old_name}' to '{new_name}'")
                    cursor.execute(f"""
                        UPDATE tasks 
                        SET {self.item_type} = ?
                        WHERE {self.item_type} = ?""", 
                        (new_name, old_name))
                    
                    # Log how many tasks were updated
                    rows_affected = cursor.rowcount
                    debug.debug(f"Updated {rows_affected} tasks from '{old_name}' to '{new_name}'")
                    
                conn.commit()
                debug.debug(f"Changes saved successfully for {self.item_type} ID {self.item_id}")
        except Exception as e:
            debug.error(f"Error saving changes: {e}")
            QMessageBox.critical(self, "Error", f"Failed to update {self.item_type}: {str(e)}")
            return
            
        debug.debug("Accepting dialog")
        self.accept()