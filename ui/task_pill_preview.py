# src/ui/task_pill_preview.py

# Import the debug utilities
from utils.debug_logger import get_debug_logger
from utils.debug_decorator import debug_method

# Initialize the debugger
debug = get_debug_logger()
debug.debug("Loading task_pill_preview.py module")

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QSizePolicy, 
    QTreeWidget, QTreeWidgetItem, QHBoxLayout, QGroupBox,
    QPushButton
)
from PyQt6.QtCore import Qt, QSize, QRectF, QPointF, QEvent, QTimer
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QBrush, QPen, QFont
import time
import traceback

from .task_pill_delegate import TaskPillDelegate
from .task_tree import PriorityHeaderItem


class TaskPillPreviewWidget(QWidget):
    """Widget that shows a preview of task pills based on current display settings"""
    
    @debug_method
    def __init__(self, parent=None, use_group_box=True):
        debug.debug(f"Initializing TaskPillPreviewWidget with use_group_box={use_group_box}")
        super().__init__(parent)
        self.settings_widget = parent
        self.main_window = self._find_main_window()
        debug.debug(f"Found main window: {self.main_window is not None}")
        self.use_group_box = use_group_box
        debug.debug("Setting up UI")
        self.setup_ui()
        
        # Connect to settings changes
        if self.settings_widget:
            debug.debug("Connecting to settings changes")
            # Find all input widgets in the settings panel and connect to their signals
            self._connect_to_settings_changes()
        
    @debug_method
    def _find_main_window(self):
        """Find the main window by traversing parents"""
        debug.debug("Finding main window by traversing parents")
        parent = self.parent()
        parent_chain = []
        
        while parent:
            parent_type = type(parent).__name__
            parent_chain.append(parent_type)
            debug.debug(f"Found parent: {parent_type}")
            
            if hasattr(parent, 'main_window'):
                debug.debug(f"Found parent with main_window attribute: {parent_type}")
                return parent.main_window
                
            parent = parent.parent()
        
        debug.debug(f"Main window not found. Parent chain: {' -> '.join(parent_chain)}")
        return None
    
    @debug_method
    def _connect_to_settings_changes(self):
        """Connect to signals of all relevant settings widgets"""
        try:
            debug.debug("Connecting to settings widget signals")
            # Font family changes
            if hasattr(self.settings_widget, 'font_family_combo'):
                debug.debug("Connecting to font_family_combo")
                self.settings_widget.font_family_combo.currentTextChanged.connect(
                    self.update_preview)
            
            # Font size changes
            if hasattr(self.settings_widget, 'font_size_spin'):
                debug.debug("Connecting to font_size_spin")
                self.settings_widget.font_size_spin.valueChanged.connect(
                    self.update_preview)
            
            # Style option changes
            if hasattr(self.settings_widget, 'bold_titles_check'):
                debug.debug("Connecting to bold_titles_check")
                self.settings_widget.bold_titles_check.toggled.connect(
                    self.update_preview)
            
            if hasattr(self.settings_widget, 'italic_desc_check'):
                debug.debug("Connecting to italic_desc_check")
                self.settings_widget.italic_desc_check.toggled.connect(
                    self.update_preview)
            
            # Font weight changes
            if hasattr(self.settings_widget, 'weight_group'):
                debug.debug("Connecting to weight_group")
                self.settings_widget.weight_group.buttonClicked.connect(
                    self.update_preview)
            
            # Color changes
            for color_type in ['title', 'description', 'due_date', 'left_panel']:
                hex_field = getattr(self.settings_widget, f'{color_type}_color_hex', None)
                if hex_field:
                    debug.debug(f"Connecting to {color_type}_color_hex")
                    hex_field.textChanged.connect(self.update_preview)
            
            # Panel content changes - ensure immediate update when changed
            for panel in ['top_left', 'bottom_left', 'top_right', 'bottom_right']:
                combo = getattr(self.settings_widget, f'{panel}_combo', None)
                if combo:
                    debug.debug(f"Connecting to {panel}_combo")
                    # Disconnect any existing connection first to avoid duplicates
                    try:
                        combo.currentTextChanged.disconnect(self.update_preview)
                        debug.debug(f"Disconnected existing signal from {panel}_combo")
                    except:
                        debug.debug(f"No existing connection to disconnect for {panel}_combo")
                        
                    # Connect with immediate update
                    combo.currentTextChanged.connect(self.immediate_update_preview)
                    debug.debug(f"Connected {panel}_combo to immediate_update_preview")
                    
            # Left panel settings
            if hasattr(self.settings_widget, 'left_panel_size_spin'):
                debug.debug("Connecting to left_panel_size_spin")
                self.settings_widget.left_panel_size_spin.valueChanged.connect(
                    self.update_preview)
                
            if hasattr(self.settings_widget, 'left_panel_bold_check'):
                debug.debug("Connecting to left_panel_bold_check")
                self.settings_widget.left_panel_bold_check.toggled.connect(
                    self.update_preview)
                
            # Auto panel text color checkbox
            if hasattr(self.settings_widget, 'auto_panel_text_color_check'):
                debug.debug("Connecting to auto_panel_text_color_check")
                self.settings_widget.auto_panel_text_color_check.toggled.connect(
                    self.update_preview)
            
            debug.debug("All signal connections complete")
                    
        except Exception as e:
            debug.error(f"Error connecting to settings changes: {e}")
            debug.error(traceback.format_exc())
    
    @debug_method
    def apply_current_settings(self):
        """Apply the current settings to the delegate"""
        debug.debug("Applying current settings to delegate")
        start_time = time.time()
        
        from ui.app_settings import SettingsManager
        settings = SettingsManager()
        
        debug.debug("Reading values from settings widgets")
        
        # Font family
        if hasattr(self.settings_widget, 'font_family_combo'):
            font_family = self.settings_widget.font_family_combo.currentText()
            debug.debug(f"Font family: {font_family}")
            settings.set_setting("font_family", font_family)
        
        # Individual font settings from the font objects in the settings widget
        if hasattr(self.settings_widget, 'task_title_font'):
            title_font = self.settings_widget.task_title_font
            settings.set_setting("title_font_family", title_font.family())
            settings.set_setting("title_font_size", title_font.pointSize())
            settings.set_setting("title_font_bold", title_font.bold())
            settings.set_setting("title_font_italic", title_font.italic())
            settings.set_setting("title_font_underline", title_font.underline())
            debug.debug(f"Title font: family={title_font.family()}, size={title_font.pointSize()}, bold={title_font.bold()}")
        
        if hasattr(self.settings_widget, 'task_description_font'):
            desc_font = self.settings_widget.task_description_font
            settings.set_setting("description_font_family", desc_font.family())
            settings.set_setting("description_font_size", desc_font.pointSize())
            settings.set_setting("description_font_bold", desc_font.bold())
            settings.set_setting("description_font_italic", desc_font.italic())
            settings.set_setting("description_font_underline", desc_font.underline())
            debug.debug(f"Description font: family={desc_font.family()}, size={desc_font.pointSize()}, bold={desc_font.bold()}")
        
        if hasattr(self.settings_widget, 'task_due_date_font'):
            due_date_font = self.settings_widget.task_due_date_font
            settings.set_setting("due_date_font_family", due_date_font.family())
            settings.set_setting("due_date_font_size", due_date_font.pointSize())
            settings.set_setting("due_date_font_bold", due_date_font.bold())
            settings.set_setting("due_date_font_italic", due_date_font.italic())
            settings.set_setting("due_date_font_underline", due_date_font.underline())
            debug.debug(f"Due date font: family={due_date_font.family()}, size={due_date_font.pointSize()}, bold={due_date_font.bold()}")
        
        if hasattr(self.settings_widget, 'panel_text_font'):
            panel_font = self.settings_widget.panel_text_font
            settings.set_setting("panel_font_family", panel_font.family())
            settings.set_setting("panel_font_size", panel_font.pointSize())
            settings.set_setting("panel_font_bold", panel_font.bold())
            settings.set_setting("panel_font_italic", panel_font.italic())
            settings.set_setting("panel_font_underline", panel_font.underline())
            debug.debug(f"Panel font: family={panel_font.family()}, size={panel_font.pointSize()}, bold={panel_font.bold()}")

        # Font color settings - CORRECTED
        if hasattr(self.settings_widget, 'title_color_hex'):
            title_color = self.settings_widget.title_color_hex.text()
            settings.set_setting("title_color", title_color)
            debug.debug(f"Title color: {title_color}")
        
        if hasattr(self.settings_widget, 'desc_color_hex'):
            desc_color = self.settings_widget.desc_color_hex.text()
            settings.set_setting("description_color", desc_color)
            debug.debug(f"Description color: {desc_color}")
        
        if hasattr(self.settings_widget, 'date_color_hex'):
            date_color = self.settings_widget.date_color_hex.text()
            settings.set_setting("due_date_color", date_color)
            debug.debug(f"Due date color: {date_color}")
        
        if hasattr(self.settings_widget, 'panel_color_hex'):
            panel_color = self.settings_widget.panel_color_hex.text()
            settings.set_setting("panel_color", panel_color)  # Changed from "left_panel_color" to "panel_color"
            debug.debug(f"Panel color: {panel_color}")

        # Background colors
        if hasattr(self.settings_widget, 'files_bg_color_hex'):
            files_bg_color = self.settings_widget.files_bg_color_hex.text()
            settings.set_setting("files_background_color", files_bg_color)

        if hasattr(self.settings_widget, 'links_bg_color_hex'):
            links_bg_color = self.settings_widget.links_bg_color_hex.text()
            settings.set_setting("links_background_color", links_bg_color)
        
        if hasattr(self.settings_widget, 'due_date_bg_color_hex'):
            due_date_bg_color = self.settings_widget.due_date_bg_color_hex.text()
            settings.set_setting("due_date_background_color", due_date_bg_color)

        # Auto panel text color setting
        if hasattr(self.settings_widget, 'auto_panel_text_color_check'):
            auto_color = self.settings_widget.auto_panel_text_color_check.isChecked()
            debug.debug(f"Auto panel text color: {auto_color}")
            settings.set_setting("auto_panel_text_color", auto_color)

        # Panel contents
        left_contents = []
        right_contents = []
        
        if hasattr(self.settings_widget, 'top_left_combo'):
            if self.settings_widget.top_left_combo.currentText() != "None":
                left_contents.append(self.settings_widget.top_left_combo.currentText())
        
        if hasattr(self.settings_widget, 'bottom_left_combo'):
            if self.settings_widget.bottom_left_combo.currentText() != "None":
                left_contents.append(self.settings_widget.bottom_left_combo.currentText())
        
        if hasattr(self.settings_widget, 'top_right_combo'):
            if self.settings_widget.top_right_combo.currentText() != "None":
                right_contents.append(self.settings_widget.top_right_combo.currentText())
        
        if hasattr(self.settings_widget, 'bottom_right_combo'):
            if self.settings_widget.bottom_right_combo.currentText() != "None":
                right_contents.append(self.settings_widget.bottom_right_combo.currentText())
        
        settings.set_setting("left_panel_contents", left_contents)
        settings.set_setting("right_panel_contents", right_contents)
        
        end_time = time.time()
        debug.debug(f"Settings applied in {end_time - start_time:.3f} seconds")
      
    @debug_method
    def setup_ui(self):
        """Set up the preview UI"""
        debug.debug("Setting up preview UI")
        layout = QVBoxLayout(self)
        
        # Create the actual content without a group box
        debug.debug("Creating content widget")
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # Create sample tree widget
        debug.debug("Creating sample tree widget")
        self.sample_tree = SampleTaskTreeWidget(self)
        self.sample_tree.setFixedHeight(200)  # Fixed height to show header + one task
        debug.debug("Set sample tree fixed height to 200")
        
        # Apply custom delegate
        debug.debug("Creating and applying TaskPillDelegate")
        self.delegate = TaskPillDelegate(self.sample_tree)
        self.sample_tree.setItemDelegate(self.delegate)
        
        content_layout.addWidget(self.sample_tree)
        
        # If we should use a group box, wrap the content in it
        if self.use_group_box:
            debug.debug("Using group box for preview")
            # Add header to group box
            debug.debug("Creating header label")
            header_label = QLabel("Task Pill Preview")
            header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
            layout.addWidget(header_label)
            
            # Add description
            debug.debug("Creating description label")
            desc_label = QLabel("This shows how your tasks will look based on current settings")
            layout.addWidget(desc_label)
            
            layout.addWidget(content_widget)
            
            # Add instruction label inside the group box if we're using one
            debug.debug("Creating instruction label")
            instruction_label = QLabel("Click the toggle button above the task pill to switch between compact and full views")
            instruction_label.setStyleSheet("color: #666666; font-style: italic;")
            layout.addWidget(instruction_label)
        else:
            # Just add the content directly without a group box
            debug.debug("Not using group box, adding content directly")
            layout.addWidget(content_widget)
        
        # Initialize preview items
        debug.debug("Creating sample items")
        self.create_sample_items()
        debug.debug("Preview UI setup complete")
        
    @debug_method
    def create_sample_items(self):
        """Create sample items for the preview"""
        debug.debug("Creating sample items for preview")
        self.sample_tree.clear()
        
        # Add a sample priority header
        debug.debug("Adding sample priority header")
        header_item = PriorityHeaderItem("SAMPLE PRIORITY LEVEL", "#F44336")
        self.sample_tree.addTopLevelItem(header_item)
        
        # Add a sample task
        debug.debug("Creating sample task item")
        task_item = QTreeWidgetItem()
        task_item.task_id = 999  # Sample ID
        
        # Set sample data
        debug.debug("Setting sample task data")
        task_item.setData(0, Qt.ItemDataRole.UserRole, {
            'id': 999,
            'title': 'Sample Task',
            'description': 'This is a sample task description to show how your settings will look.',
            'link': 'https://example.com',
            'status': 'In Progress',
            'priority': 'High',
            'due_date': '2025-05-15',
            'category': 'Work',
            'completed_at': None
        })
        
        # Set appropriate size hint
        is_compact = 999 in self.delegate.compact_items
        debug.debug(f"Task is compact: {is_compact}")
        height = self.delegate.compact_height if is_compact else self.delegate.pill_height
        debug.debug(f"Setting task item height to {height + self.delegate.item_margin * 2}")
        task_item.setSizeHint(0, QSize(self.sample_tree.viewport().width(), 
                                        height + self.delegate.item_margin * 2))
        
        # Add task to header
        debug.debug("Adding task item to header")
        header_item.addChild(task_item)
        
        # Expand the header to show the task
        debug.debug("Expanding header item")
        self.sample_tree.expandItem(header_item)
        
        # Store reference to the task item for hover simulation
        debug.debug("Storing reference to sample task item")
        self.sample_task_item = task_item
        debug.debug("Sample items created successfully")
    
    @debug_method
    def update_preview(self, check=False):
        """Update the preview based on current settings"""
        debug.debug("Updating preview based on current settings")
        start_time = time.time()
        
        # First apply the current settings to the delegate
        debug.debug("Applying current settings to delegate")
        self.apply_current_settings()
        
        # Recreate the preview items to apply new settings
        debug.debug("Recreating preview items")
        self.create_sample_items()
        
        # Force repaint
        debug.debug("Forcing viewport update")
        self.sample_tree.viewport().update()
        
        end_time = time.time()
        debug.debug(f"Preview update completed in {end_time - start_time:.3f} seconds")
    
    @debug_method
    def immediate_update_preview(self, check=False):
        """Immediately update the preview with current settings"""
        debug.debug("Immediately updating preview")
        start_time = time.time()
        
        # Apply current settings directly to settings manager
        debug.debug("Applying settings directly to settings manager")
        from ui.app_settings import SettingsManager
        settings = SettingsManager()
        
        # Store combo box values
        debug.debug("Getting panel contents from combo boxes")
        left_contents = []
        right_contents = []
        
        # Left panel contents
        top_left = getattr(self.settings_widget, 'top_left_combo', None)
        if top_left and top_left.currentText() != "None":
            debug.debug(f"Adding top left content: {top_left.currentText()}")
            left_contents.append(top_left.currentText())
        
        bottom_left = getattr(self.settings_widget, 'bottom_left_combo', None)
        if bottom_left and bottom_left.currentText() != "None":
            debug.debug(f"Adding bottom left content: {bottom_left.currentText()}")
            left_contents.append(bottom_left.currentText())
        
        # Right panel contents
        top_right = getattr(self.settings_widget, 'top_right_combo', None)
        if top_right and top_right.currentText() != "None":
            debug.debug(f"Adding top right content: {top_right.currentText()}")
            right_contents.append(top_right.currentText())
        
        bottom_right = getattr(self.settings_widget, 'bottom_right_combo', None)
        if bottom_right and bottom_right.currentText() != "None":
            debug.debug(f"Adding bottom right content: {bottom_right.currentText()}")
            right_contents.append(bottom_right.currentText())
        
        # Apply settings immediately
        debug.debug(f"Saving panel contents to settings - left: {left_contents}, right: {right_contents}")
        settings.set_setting("left_panel_contents", left_contents)
        settings.set_setting("right_panel_contents", right_contents)
        
        # Update the preview
        debug.debug("Updating preview")
        self.update_preview()
        
        end_time = time.time()
        debug.debug(f"Immediate preview update completed in {end_time - start_time:.3f} seconds")

    @debug_method
    def apply_current_settings(self):
        """Apply the current settings to the delegate (no font colors)"""
        debug.debug("Applying current settings to delegate")
        start_time = time.time()
        
        from ui.app_settings import SettingsManager
        settings = SettingsManager()
        
        debug.debug("Reading values from settings widgets")
        
        # Font family
        if hasattr(self.settings_widget, 'font_family_combo'):
            font_family = self.settings_widget.font_family_combo.currentText()
            debug.debug(f"Font family: {font_family}")
            settings.set_setting("font_family", font_family)
        
        # Individual font settings from the font objects in the settings widget
        if hasattr(self.settings_widget, 'task_title_font'):
            title_font = self.settings_widget.task_title_font
            settings.set_setting("title_font_family", title_font.family())
            settings.set_setting("title_font_size", title_font.pointSize())
            settings.set_setting("title_font_bold", title_font.bold())
            settings.set_setting("title_font_italic", title_font.italic())
            settings.set_setting("title_font_underline", title_font.underline())
            debug.debug(f"Title font: family={title_font.family()}, size={title_font.pointSize()}, bold={title_font.bold()}")
        
        if hasattr(self.settings_widget, 'task_description_font'):
            desc_font = self.settings_widget.task_description_font
            settings.set_setting("description_font_family", desc_font.family())
            settings.set_setting("description_font_size", desc_font.pointSize())
            settings.set_setting("description_font_bold", desc_font.bold())
            settings.set_setting("description_font_italic", desc_font.italic())
            settings.set_setting("description_font_underline", desc_font.underline())
            debug.debug(f"Description font: family={desc_font.family()}, size={desc_font.pointSize()}, bold={desc_font.bold()}")
        
        if hasattr(self.settings_widget, 'task_due_date_font'):
            due_date_font = self.settings_widget.task_due_date_font
            settings.set_setting("due_date_font_family", due_date_font.family())
            settings.set_setting("due_date_font_size", due_date_font.pointSize())
            settings.set_setting("due_date_font_bold", due_date_font.bold())
            settings.set_setting("due_date_font_italic", due_date_font.italic())
            settings.set_setting("due_date_font_underline", due_date_font.underline())
            debug.debug(f"Due date font: family={due_date_font.family()}, size={due_date_font.pointSize()}, bold={due_date_font.bold()}")
        
        if hasattr(self.settings_widget, 'panel_text_font'):
            panel_font = self.settings_widget.panel_text_font
            settings.set_setting("panel_font_family", panel_font.family())
            settings.set_setting("panel_font_size", panel_font.pointSize())
            settings.set_setting("panel_font_bold", panel_font.bold())
            settings.set_setting("panel_font_italic", panel_font.italic())
            settings.set_setting("panel_font_underline", panel_font.underline())
            debug.debug(f"Panel font: family={panel_font.family()}, size={panel_font.pointSize()}, bold={panel_font.bold()}")

        # Background colors
        if hasattr(self.settings_widget, 'files_bg_color_hex'):
            files_bg_color = self.settings_widget.files_bg_color_hex.text()
            settings.set_setting("files_background_color", files_bg_color)

        if hasattr(self.settings_widget, 'links_bg_color_hex'):
            links_bg_color = self.settings_widget.links_bg_color_hex.text()
            settings.set_setting("links_background_color", links_bg_color)
        
        if hasattr(self.settings_widget, 'due_date_bg_color_hex'):
            due_date_bg_color = self.settings_widget.due_date_bg_color_hex.text()
            settings.set_setting("due_date_background_color", due_date_bg_color)

        # Auto panel text color setting - always enabled
        settings.set_setting("auto_panel_text_color", True)
        debug.debug("Set auto_panel_text_color to True (always enabled)")

        # Panel contents
        left_contents = []
        right_contents = []
        
        if hasattr(self.settings_widget, 'top_left_combo'):
            if self.settings_widget.top_left_combo.currentText() != "None":
                left_contents.append(self.settings_widget.top_left_combo.currentText())
        
        if hasattr(self.settings_widget, 'bottom_left_combo'):
            if self.settings_widget.bottom_left_combo.currentText() != "None":
                left_contents.append(self.settings_widget.bottom_left_combo.currentText())
        
        if hasattr(self.settings_widget, 'top_right_combo'):
            if self.settings_widget.top_right_combo.currentText() != "None":
                right_contents.append(self.settings_widget.top_right_combo.currentText())
        
        if hasattr(self.settings_widget, 'bottom_right_combo'):
            if self.settings_widget.bottom_right_combo.currentText() != "None":
                right_contents.append(self.settings_widget.bottom_right_combo.currentText())
        
        settings.set_setting("left_panel_contents", left_contents)
        settings.set_setting("right_panel_contents", right_contents)
        
        end_time = time.time()
        debug.debug(f"Settings applied in {end_time - start_time:.3f} seconds")

class SampleTaskTreeWidget(QTreeWidget):
    """Specialized tree widget for the sample task preview"""
    
    @debug_method
    def __init__(self, parent=None):
        debug.debug("Initializing SampleTaskTreeWidget")
        super().__init__(parent)
        self.preview_widget = parent  # Store parent reference to access delegate
        self.setRootIsDecorated(False)
        self.setHeaderHidden(True)
        self.setColumnCount(1)
        self.setIndentation(40)
        
        # Set up styles and properties similar to the real task tree
        debug.debug("Setting up widget properties")
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        
        # Set alternating row colors to false to prevent default styling
        debug.debug("Setting alternatingRowColors to False")
        self.setAlternatingRowColors(False)
        
        # Connect double-click signal to toggle function
        debug.debug("Connecting itemDoubleClicked signal")
        self.itemDoubleClicked.connect(self.toggle_item_compact)
        
        # Install event filter to catch mouse presses for toggle button
        debug.debug("Installing event filter on viewport")
        self.viewport().installEventFilter(self)
        debug.debug("SampleTaskTreeWidget initialization complete")
    
    @debug_method
    def eventFilter(self, source, event):
        """Handle mouse events for the toggle button"""
        if source == self.viewport() and event.type() == event.Type.MouseButtonPress:
            debug.debug("Mouse button press detected in viewport")
            # Get the position
            try:
                if hasattr(event, 'position'):
                    pos = event.position().toPoint()
                elif hasattr(event, 'pos'):
                    pos = event.pos()
                else:
                    pos = event.globalPos()
                
                # Create a QPointF from the QPoint coordinates
                pos_f = QPointF(pos.x(), pos.y())
                debug.debug(f"Mouse position: {pos.x()}, {pos.y()}")
            except Exception as e:
                debug.error(f"Error getting mouse position: {e}")
                debug.error(traceback.format_exc())
                return super().eventFilter(source, event)
            
            # Check if click was on the toggle button
            delegate = self.itemDelegate()
            if hasattr(delegate, 'all_button_rects'):
                debug.debug(f"Checking {len(delegate.all_button_rects)} button rects")
                for item_id, (button_rect, item_index) in delegate.all_button_rects.items():
                    if button_rect.contains(pos_f):
                        debug.debug(f"Toggle button clicked for item ID: {item_id}")
                        
                        # Find the item
                        item = self.itemFromIndex(item_index)
                        if item:
                            debug.debug(f"Found item for index: {item.text(0)}")
                            # Toggle compact state
                            self.toggle_item_compact(item, 0)
                            return True  # Event handled
                        else:
                            debug.debug("No item found for index")
            else:
                debug.debug("No button rects found in delegate")
            
        # Let the parent class handle other events
        return super().eventFilter(source, event)
    
    @debug_method
    def get_settings_manager(self):
        """Get the settings manager - needed by the TaskPillDelegate"""
        debug.debug("Getting settings manager")
        from ui.app_settings import SettingsManager
        return SettingsManager()
    
    @staticmethod
    def get_connection():
        """Get database connection - needed by TaskPillDelegate"""
        debug.debug("Getting database connection")
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()

    @debug_method
    def mouseMoveEvent(self, event):
        """Handle mouse movement to show the toggle button on hover"""
        debug.debug("Mouse move in sample tree")
        pos = event.position().toPoint()
        index = self.indexAt(pos)
        
        delegate = self.itemDelegate()
        if index.isValid() and hasattr(delegate, 'hover_item'):
            # Set the hover item in the delegate
            delegate.hover_item = index
            
            # Calculate and set the toggle button rect
            rect = self.visualRect(index)
            delegate.toggle_button_rect = QRectF(
                rect.center().x() - 12,  # 12 = half of button size
                rect.top() - 12,         # Position button above item
                24, 24                   # Button size
            )
            
            # Store in all_button_rects too for click handling
            if not hasattr(delegate, 'all_button_rects'):
                delegate.all_button_rects = {}
            
            # Get the item data to find the ID
            item = self.itemFromIndex(index)
            if hasattr(item, 'task_id'):
                task_id = item.task_id
                delegate.all_button_rects[task_id] = (delegate.toggle_button_rect, index)
            
            # Force repaint to show the button
            self.viewport().update()
        elif hasattr(delegate, 'hover_item') and delegate.hover_item:
            # Clear hover state when not over an item
            delegate.hover_item = None
            self.viewport().update()
        
        super().mouseMoveEvent(event)

    @debug_method
    def leaveEvent(self, event):
        """Clear hover state when mouse leaves the widget"""
        debug.debug("Mouse leave event in sample tree")
        delegate = self.itemDelegate()
        if hasattr(delegate, 'hover_item') and delegate.hover_item:
            delegate.hover_item = None
            self.viewport().update()
        
        super().leaveEvent(event)
        
    @debug_method
    def toggle_item_compact(self, item, column):
        """Toggle compact view of task when clicked"""
        debug.debug(f"Toggle item compact: {item.text(0)}")
        
        # Skip handling if it's a header
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and data.get('is_priority_header', False):
            debug.debug("Item is a priority header, skipping toggle")
            return
            
        # Get the item ID
        if hasattr(item, 'task_id'):
            task_id = item.task_id
            debug.debug(f"Task ID: {task_id}")
            
            # Try multiple ways to get the delegate
            delegate = self.itemDelegate()
            
            # If that failed, try to get it from the parent widget
            if not delegate or not hasattr(delegate, 'compact_items'):
                debug.debug("Delegate not found from itemDelegate(), trying parent widget")
                if hasattr(self, 'preview_widget') and self.preview_widget and hasattr(self.preview_widget, 'delegate'):
                    delegate = self.preview_widget.delegate
                    debug.debug("Found delegate from preview_widget")
                else:
                    debug.error("No proper delegate found")
                    return
                
            # Toggle compact state in delegate
            is_currently_compact = task_id in delegate.compact_items
            debug.debug(f"Current compact state: {is_currently_compact}")
            
            if is_currently_compact:
                debug.debug(f"Removing task {task_id} from compact items")
                delegate.compact_items.remove(task_id)
            else:
                debug.debug(f"Adding task {task_id} to compact items")
                delegate.compact_items.add(task_id)
            
            # Update item size
            height = delegate.compact_height if not is_currently_compact else delegate.pill_height
            debug.debug(f"Setting new item height: {height + delegate.item_margin * 2}")
            item.setSizeHint(0, QSize(self.viewport().width(), 
                                    height + delegate.item_margin * 2))
            
            # Force repaint
            debug.debug("Forcing viewport update")
            self.viewport().update()
        else:
            debug.debug("Item has no task_id attribute")