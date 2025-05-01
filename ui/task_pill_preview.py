# src/ui/task_pill_preview.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QSizePolicy, 
    QTreeWidget, QTreeWidgetItem, QHBoxLayout, QGroupBox,
    QPushButton
)
from PyQt6.QtCore import Qt, QSize, QRectF, QPointF, QEvent
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QBrush, QPen, QFont

from .task_pill_delegate import TaskPillDelegate
from .task_tree import PriorityHeaderItem


class TaskPillPreviewWidget(QWidget):
    """Widget that shows a preview of task pills based on current display settings"""
    
    def __init__(self, parent=None, use_group_box=True):
        print("DEBUG: TaskPillPreviewWidget.__init__ called")
        super().__init__(parent)
        self.settings_widget = parent
        self.main_window = self._find_main_window()
        self.use_group_box = use_group_box
        self.setup_ui()
        
        # Connect to settings changes
        if self.settings_widget:
            # Find all input widgets in the settings panel and connect to their signals
            self._connect_to_settings_changes()
            
        # Setup a timer to simulate hover for toggle button visibility
        from PyQt6.QtCore import QTimer
        self.hover_timer = QTimer(self)
        self.hover_timer.timeout.connect(self.simulate_hover)
        self.hover_timer.start(2000)  # Every 2 seconds
        
    def _find_main_window(self):
        """Find the main window by traversing parents"""
        parent = self.parent()
        while parent and not hasattr(parent, 'main_window'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'main_window'):
            return parent.main_window
        return None
    
    def _connect_to_settings_changes(self):
        """Connect to signals of all relevant settings widgets"""
        try:
            # Font family changes
            if hasattr(self.settings_widget, 'font_family_combo'):
                self.settings_widget.font_family_combo.currentTextChanged.connect(
                    self.update_preview)
            
            # Font size changes
            if hasattr(self.settings_widget, 'font_size_spin'):
                self.settings_widget.font_size_spin.valueChanged.connect(
                    self.update_preview)
            
            # Style option changes
            if hasattr(self.settings_widget, 'bold_titles_check'):
                self.settings_widget.bold_titles_check.toggled.connect(
                    self.update_preview)
            
            if hasattr(self.settings_widget, 'italic_desc_check'):
                self.settings_widget.italic_desc_check.toggled.connect(
                    self.update_preview)
            
            # Font weight changes
            if hasattr(self.settings_widget, 'weight_group'):
                self.settings_widget.weight_group.buttonClicked.connect(
                    self.update_preview)
            
            # Color changes
            for color_type in ['title', 'description', 'due_date', 'left_panel']:
                hex_field = getattr(self.settings_widget, f'{color_type}_color_hex', None)
                if hex_field:
                    hex_field.textChanged.connect(self.update_preview)
            
            # Panel content changes - ensure immediate update when changed
            for panel in ['top_left', 'bottom_left', 'top_right', 'bottom_right']:
                combo = getattr(self.settings_widget, f'{panel}_combo', None)
                if combo:
                    # Disconnect any existing connection first to avoid duplicates
                    try:
                        combo.currentTextChanged.disconnect(self.update_preview)
                    except:
                        pass
                    # Connect with immediate update
                    combo.currentTextChanged.connect(self.immediate_update_preview)
                    
            # Left panel settings
            if hasattr(self.settings_widget, 'left_panel_size_spin'):
                self.settings_widget.left_panel_size_spin.valueChanged.connect(
                    self.update_preview)
                
            if hasattr(self.settings_widget, 'left_panel_bold_check'):
                self.settings_widget.left_panel_bold_check.toggled.connect(
                    self.update_preview)
                
        except Exception as e:
            print(f"Error connecting to settings changes: {e}")
    
    def setup_ui(self):
        """Set up the preview UI"""
        layout = QVBoxLayout(self)
        
        # Create the actual content without a group box
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # Create sample tree widget
        self.sample_tree = SampleTaskTreeWidget(self)
        self.sample_tree.setFixedHeight(200)  # Fixed height to show header + one task
        
        # Apply custom delegate
        self.delegate = TaskPillDelegate(self.sample_tree)
        self.sample_tree.setItemDelegate(self.delegate)
        
        content_layout.addWidget(self.sample_tree)
        
        # If we should use a group box, wrap the content in it
        if self.use_group_box:
            # Add header to group box
            header_label = QLabel("Task Pill Preview")
            header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
            layout.addWidget(header_label)
            
            # Add description
            desc_label = QLabel("This shows how your tasks will look based on current settings")
            layout.addWidget(desc_label)
            
            layout.addWidget(content_widget)
            
            # Add instruction label inside the group box if we're using one
            instruction_label = QLabel("Click the toggle button above the task pill to switch between compact and full views")
            instruction_label.setStyleSheet("color: #666666; font-style: italic;")
            layout.addWidget(instruction_label)
        else:
            # Just add the content directly without a group box
            layout.addWidget(content_widget)
        
        # Initialize preview items
        self.create_sample_items()
        
    def create_sample_items(self):
        """Create sample items for the preview"""
        self.sample_tree.clear()
        
        # Add a sample priority header
        header_item = PriorityHeaderItem("SAMPLE PRIORITY LEVEL", "#F44336")
        self.sample_tree.addTopLevelItem(header_item)
        
        # Add a sample task
        task_item = QTreeWidgetItem()
        task_item.task_id = 999  # Sample ID
        
        # Set sample data
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
        height = self.delegate.compact_height if is_compact else self.delegate.pill_height
        task_item.setSizeHint(0, QSize(self.sample_tree.viewport().width(), 
                                        height + self.delegate.item_margin * 2))
        
        # Add task to header
        header_item.addChild(task_item)
        
        # Expand the header to show the task
        self.sample_tree.expandItem(header_item)
        
        # Store reference to the task item for hover simulation
        self.sample_task_item = task_item
    
    def update_preview(self):
        """Update the preview based on current settings"""
        print("TaskPillPreviewWidget.update_preview called")
        
        # First apply the current settings to the delegate
        self.apply_current_settings()
        
        # Recreate the preview items to apply new settings
        self.create_sample_items()
        
        # Force repaint
        print("Forcing viewport update")
        self.sample_tree.viewport().update()
    
    def immediate_update_preview(self):
        """Immediately update the preview with current settings"""
        # Apply current settings directly to settings manager
        from ui.app_settings import SettingsManager
        settings = SettingsManager()
        
        # Store combo box values
        left_contents = []
        right_contents = []
        
        # Left panel contents
        top_left = getattr(self.settings_widget, 'top_left_combo', None)
        if top_left and top_left.currentText() != "None":
            left_contents.append(top_left.currentText())
        
        bottom_left = getattr(self.settings_widget, 'bottom_left_combo', None)
        if bottom_left and bottom_left.currentText() != "None":
            left_contents.append(bottom_left.currentText())
        
        # Right panel contents
        top_right = getattr(self.settings_widget, 'top_right_combo', None)
        if top_right and top_right.currentText() != "None":
            right_contents.append(top_right.currentText())
        
        bottom_right = getattr(self.settings_widget, 'bottom_right_combo', None)
        if bottom_right and bottom_right.currentText() != "None":
            right_contents.append(bottom_right.currentText())
        
        # Apply settings immediately
        settings.set_setting("left_panel_contents", left_contents)
        settings.set_setting("right_panel_contents", right_contents)
        
        # Update the preview
        self.update_preview()
    
    def simulate_hover(self):
        """Simulate hover events to show the toggle button"""
        if hasattr(self, 'sample_task_item') and self.sample_task_item:
            # Get the index for the sample task
            index = self.sample_tree.indexFromItem(self.sample_task_item)
            
            # Set the hover item in the delegate
            self.delegate.hover_item = index
            
            # Calculate and set the toggle button rect
            rect = self.sample_tree.visualRect(index)
            self.delegate.toggle_button_rect = QRectF(
                rect.center().x() - 12,  # 12 = half of button size
                rect.top() - 12,         # Position button above item
                24, 24                   # Button size
            )
            
            # Store in all_button_rects too for click handling
            if not hasattr(self.delegate, 'all_button_rects'):
                self.delegate.all_button_rects = {}
                
            self.delegate.all_button_rects[999] = (self.delegate.toggle_button_rect, index)
            
            # Force repaint to show the button
            self.sample_tree.viewport().update()

    def apply_current_settings(self):
        """Apply the current settings to the delegate"""
        # We'll need the settings manager
        from ui.app_settings import SettingsManager
        settings = SettingsManager()
        
        # Get all current values from the settings widgets
        if hasattr(self.settings_widget, 'font_family_combo'):
            font_family = self.settings_widget.font_family_combo.currentText()
            settings.set_setting("font_family", font_family)
        
        if hasattr(self.settings_widget, 'font_size_spin'):
            font_size = self.settings_widget.font_size_spin.value()
            settings.set_setting("font_size", font_size)
        
        if hasattr(self.settings_widget, 'bold_titles_check'):
            bold_titles = self.settings_widget.bold_titles_check.isChecked()
            settings.set_setting("bold_titles", bold_titles)
        
        if hasattr(self.settings_widget, 'italic_desc_check'):
            italic_desc = self.settings_widget.italic_desc_check.isChecked()
            settings.set_setting("italic_descriptions", italic_desc)
        
        # Font weight
        if hasattr(self.settings_widget, 'weight_group'):
            weight = 0  # Default to regular
            if self.settings_widget.medium_radio.isChecked():
                weight = 1
            elif self.settings_widget.bold_radio.isChecked():
                weight = 2
            settings.set_setting("font_weight", weight)
        
        # Colors
        for color_type in ['title', 'description', 'due_date', 'left_panel']:
            hex_field = getattr(self.settings_widget, f'{color_type}_color_hex', None)
            if hex_field:
                color_value = hex_field.text()
                settings.set_setting(f"{color_type}_color", color_value)
        
        # Panel contents - get them from the settings widget, not directly
        left_contents = []
        right_contents = []
        
        # Only try to access these attributes on the parent widget, not self
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
        
        # Left panel settings
        if hasattr(self.settings_widget, 'left_panel_size_spin'):
            panel_size = self.settings_widget.left_panel_size_spin.value()
            settings.set_setting("left_panel_size", panel_size)
            
        if hasattr(self.settings_widget, 'left_panel_bold_check'):
            panel_bold = self.settings_widget.left_panel_bold_check.isChecked()
            settings.set_setting("left_panel_bold", panel_bold)    

class SampleTaskTreeWidget(QTreeWidget):
    """Specialized tree widget for the sample task preview"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.preview_widget = parent  # Store parent reference to access delegate
        self.setRootIsDecorated(False)
        self.setHeaderHidden(True)
        self.setColumnCount(1)
        self.setIndentation(40)
        
        # Set up styles and properties similar to the real task tree
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        
        self.setStyleSheet("""
            QTreeWidget {
                background-color: #f5f5f5;
                border: none;
                outline: none;
            }
            QTreeWidget::item {
                border: none;
                background-color: transparent;
            }
            QTreeWidget::item:selected {
                border: none;
                background-color: transparent;
            }
        """)
        
        # Set alternating row colors to false to prevent default styling
        self.setAlternatingRowColors(False)
        
        # Connect double-click signal to toggle function
        self.itemDoubleClicked.connect(self.toggle_item_compact)
        
        # Install event filter to catch mouse presses for toggle button
        self.viewport().installEventFilter(self)
    
    def eventFilter(self, source, event):
        """Handle mouse events for the toggle button"""
        if source == self.viewport() and event.type() == event.Type.MouseButtonPress:
            # Get the position
            pos = event.position().toPoint()
            pos_f = QPointF(pos.x(), pos.y())
            
            # Check if button click targets the toggle button
            delegate = self.itemDelegate()
            if hasattr(delegate, 'all_button_rects'):
                for item_id, (button_rect, item_index) in delegate.all_button_rects.items():
                    if button_rect.contains(pos_f):
                        # Find the item
                        item = self.itemFromIndex(item_index)
                        if item:
                            # Toggle compact state
                            self.toggle_item_compact(item, 0)
                            return True  # Event handled
            
        # Let the parent class handle other events
        return super().eventFilter(source, event)
    
    def get_settings_manager(self):
        """Get the settings manager - needed by the TaskPillDelegate"""
        from ui.app_settings import SettingsManager
        return SettingsManager()
    
    @staticmethod
    def get_connection():
        """Get database connection - needed by TaskPillDelegate"""
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
        
    def toggle_item_compact(self, item, column):
        """Toggle compact view of task when clicked"""
        # Skip handling if it's a header
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and data.get('is_priority_header', False):
            return
            
        # Get the item ID
        if hasattr(item, 'task_id'):
            task_id = item.task_id
            
            # Try multiple ways to get the delegate
            delegate = self.itemDelegate()
            
            # If that failed, try to get it from the parent widget
            if not delegate or not hasattr(delegate, 'compact_items'):
                if hasattr(self, 'preview_widget') and self.preview_widget and hasattr(self.preview_widget, 'delegate'):
                    delegate = self.preview_widget.delegate
                else:
                    print("Error: No proper delegate found")
                    return
                
            # Toggle compact state in delegate
            is_currently_compact = task_id in delegate.compact_items
            
            if is_currently_compact:
                delegate.compact_items.remove(task_id)
            else:
                delegate.compact_items.add(task_id)
            
            # Update item size
            height = delegate.compact_height if not is_currently_compact else delegate.pill_height
            item.setSizeHint(0, QSize(self.viewport().width(), 
                                    height + delegate.item_margin * 2))
            
            # Force repaint
            self.viewport().update()