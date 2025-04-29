# src/ui/combined_display_settings.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox, QCheckBox,
    QRadioButton, QButtonGroup, QGroupBox, QPushButton, QColorDialog, QLineEdit,
    QFormLayout, QMessageBox, QScrollArea, QFrame, QSizePolicy, QSplitter
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt, QSignalBlocker
import platform

from ui.task_pill_preview import TaskPillPreviewWidget
from ui.task_pill_delegate import TaskPillDelegate

class CombinedDisplaySettingsWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.settings = main_window.settings
        
        # Fixed panel widths - these are constants
        self.left_panel_width = 100  # Fixed width for left panel
        self.right_panel_width = 100  # Fixed width for right panel
        
        self.setup_ui()
        self.load_current_settings()
    
    def setup_ui(self):
        # Create a main layout for the entire widget
        main_layout = QHBoxLayout(self)
        
        # Add a splitter to allow resizing between controls and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create left side for settings controls
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header_label = QLabel("Task Display Settings")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        left_layout.addWidget(header_label)
        
        # Create a scroll area to contain the settings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Create a container widget for the scroll area
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setSpacing(15)
        
        # ==================== FONT SETTINGS GROUP ====================
        font_settings_group = QGroupBox("Font Settings")
        font_settings_layout = QHBoxLayout()
        
        # Left: Font and Size
        font_size_layout = QVBoxLayout()
        font_family_label = QLabel("Font Family:")
        self.font_family_combo = QComboBox()
        font_size_layout.addWidget(font_family_label)
        font_size_layout.addWidget(self.font_family_combo)
        
        # Add cross-platform safe fonts
        cross_platform_fonts = [
            "Arial", "Helvetica", "Times New Roman", "Times",
            "Courier New", "Courier", "Verdana", "Georgia",
            "Tahoma", "Trebuchet MS"
        ]
        
        # Add system fonts based on platform
        system = platform.system()
        if system == "Windows":
            windows_fonts = ["Segoe UI", "Calibri", "Cambria", "Consolas"]
            for font in windows_fonts:
                if font not in cross_platform_fonts:
                    cross_platform_fonts.append(font)
        elif system == "Darwin":  # macOS
            mac_fonts = ["San Francisco", "Helvetica Neue", "Lucida Grande", "Menlo"]
            for font in mac_fonts:
                if font not in cross_platform_fonts:
                    cross_platform_fonts.append(font)
        
        # Add fonts to combo box
        self.font_family_combo.addItems(cross_platform_fonts)
        
        # Set default font based on platform
        default_font = "Segoe UI" if system == "Windows" else "San Francisco" if system == "Darwin" else "Arial"
        index = self.font_family_combo.findText(default_font)
        if index >= 0:
            self.font_family_combo.setCurrentIndex(index)
        
        font_size_label = QLabel("Font Size:")
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(10)
        font_size_layout.addWidget(font_size_label)
        font_size_layout.addWidget(self.font_size_spin)
        font_size_layout.addStretch()
        
        # Middle: Style Options
        style_options_layout = QVBoxLayout()
        style_options_label = QLabel("Style Options:")
        style_options_layout.addWidget(style_options_label)
        
        self.bold_titles_check = QCheckBox("Bold titles")
        self.bold_titles_check.setChecked(True)
        
        self.italic_desc_check = QCheckBox("Italic descriptions")
        
        self.compact_view_check = QCheckBox("Use compact view by default")
        
        style_options_layout.addWidget(self.bold_titles_check)
        style_options_layout.addWidget(self.italic_desc_check)
        style_options_layout.addWidget(self.compact_view_check)
        style_options_layout.addStretch()
        
        # Right: Font Weight
        font_weight_layout = QVBoxLayout()
        font_weight_label = QLabel("Font Weight:")
        font_weight_layout.addWidget(font_weight_label)
        
        self.weight_group = QButtonGroup(self)
        
        self.regular_radio = QRadioButton("Regular")
        self.regular_radio.setChecked(True)
        self.weight_group.addButton(self.regular_radio, 0)
        
        self.medium_radio = QRadioButton("Medium")
        self.weight_group.addButton(self.medium_radio, 1)
        
        self.bold_radio = QRadioButton("Bold")
        self.weight_group.addButton(self.bold_radio, 2)
        
        font_weight_layout.addWidget(self.regular_radio)
        font_weight_layout.addWidget(self.medium_radio)
        font_weight_layout.addWidget(self.bold_radio)
        font_weight_layout.addStretch()
        
        # Combine all font settings sections
        font_settings_layout.addLayout(font_size_layout)
        font_settings_layout.addLayout(style_options_layout)
        font_settings_layout.addLayout(font_weight_layout)
        font_settings_group.setLayout(font_settings_layout)
        
        # Add to the content layout
        content_layout.addWidget(font_settings_group)
        
        # ==================== COLOR SETTINGS GROUP ====================
        colors_group = QGroupBox("Text Colors")
        colors_layout = QHBoxLayout()
        
        # Left column for main text colors
        main_colors_layout = QFormLayout()
        
        # Title color
        title_color_layout = QHBoxLayout()
        self.title_color_btn = QPushButton()
        self.title_color_btn.setFixedSize(30, 20)
        self.title_color_btn.setStyleSheet("background-color: #333333; border: 1px solid #666666;")
        self.title_color_btn.clicked.connect(lambda: self.pick_color("title"))
        
        self.title_color_hex = QLineEdit("#333333")
        self.title_color_hex.setFixedWidth(80)
        self.title_color_hex.textChanged.connect(lambda: self.update_color_from_hex("title"))
        
        title_color_layout.addWidget(self.title_color_btn)
        title_color_layout.addWidget(self.title_color_hex)
        
        # Description color
        desc_color_layout = QHBoxLayout()
        self.desc_color_btn = QPushButton()
        self.desc_color_btn.setFixedSize(30, 20)
        self.desc_color_btn.setStyleSheet("background-color: #666666; border: 1px solid #666666;")
        self.desc_color_btn.clicked.connect(lambda: self.pick_color("description"))
        
        self.desc_color_hex = QLineEdit("#666666")
        self.desc_color_hex.setFixedWidth(80)
        self.desc_color_hex.textChanged.connect(lambda: self.update_color_from_hex("description"))
        
        desc_color_layout.addWidget(self.desc_color_btn)
        desc_color_layout.addWidget(self.desc_color_hex)
        
        # Due date color
        due_color_layout = QHBoxLayout()
        self.due_color_btn = QPushButton()
        self.due_color_btn.setFixedSize(30, 20)
        self.due_color_btn.setStyleSheet("background-color: #888888; border: 1px solid #666666;")
        self.due_color_btn.clicked.connect(lambda: self.pick_color("due_date"))
        
        self.due_color_hex = QLineEdit("#888888")
        self.due_color_hex.setFixedWidth(80)
        self.due_color_hex.textChanged.connect(lambda: self.update_color_from_hex("due_date"))
        
        due_color_layout.addWidget(self.due_color_btn)
        due_color_layout.addWidget(self.due_color_hex)
        
        main_colors_layout.addRow("Title:", title_color_layout)
        main_colors_layout.addRow("Description:", desc_color_layout)
        main_colors_layout.addRow("Due Date:", due_color_layout)
        
        # Right column for panel text settings
        panel_settings_layout = QFormLayout()
        
        # Left panel font color
        left_panel_color_layout = QHBoxLayout()
        self.left_panel_color_btn = QPushButton()
        self.left_panel_color_btn.setFixedSize(30, 20)
        self.left_panel_color_btn.setStyleSheet("background-color: #FFFFFF; border: 1px solid #666666;")
        self.left_panel_color_btn.clicked.connect(lambda: self.pick_color("left_panel"))

        self.left_panel_color_hex = QLineEdit("#FFFFFF")
        self.left_panel_color_hex.setFixedWidth(80)
        self.left_panel_color_hex.textChanged.connect(lambda: self.update_color_from_hex("left_panel"))

        left_panel_color_layout.addWidget(self.left_panel_color_btn)
        left_panel_color_layout.addWidget(self.left_panel_color_hex)

        # Left panel font size
        self.left_panel_size_spin = QSpinBox()
        self.left_panel_size_spin.setRange(6, 14)  # Smaller range since panel is limited
        self.left_panel_size_spin.setValue(8)

        # Left panel font options
        self.left_panel_bold_check = QCheckBox("Bold panel text")
        
        panel_settings_layout.addRow("Panel Text:", left_panel_color_layout)
        panel_settings_layout.addRow("Panel Size:", self.left_panel_size_spin)
        panel_settings_layout.addRow("", self.left_panel_bold_check)
        
        # Add both columns to the colors layout
        colors_layout.addLayout(main_colors_layout)
        colors_layout.addLayout(panel_settings_layout)
        
        colors_group.setLayout(colors_layout)
        content_layout.addWidget(colors_group)
        
        # ==================== PANEL LAYOUT GROUP ====================
        panel_layout_group = QGroupBox("Task Pill Layout")
        panel_layout = QHBoxLayout()
        
        # Left Panel Configuration
        left_panel_layout = QVBoxLayout()
        left_panel_layout.addWidget(QLabel("Left Panel:"))
        
        # Top Left Section
        top_left_layout = QFormLayout()
        self.top_left_combo = QComboBox()
        self.top_left_combo.addItems([
            "None", "Category", "Status", "Priority", "Due Date",
            "Link", "Progress", "Completion Date", "Tag", "Files"
        ])
        top_left_layout.addRow("Top:", self.top_left_combo)
        left_panel_layout.addLayout(top_left_layout)
        
        # Bottom Left Section
        bottom_left_layout = QFormLayout()
        self.bottom_left_combo = QComboBox()
        self.bottom_left_combo.addItems([
            "None", "Category", "Status", "Priority", "Due Date",
            "Link", "Progress", "Completion Date", "Tag", "Files"
        ])
        bottom_left_layout.addRow("Bottom:", self.bottom_left_combo)
        left_panel_layout.addLayout(bottom_left_layout)
        
        # Right Panel Configuration
        right_panel_layout = QVBoxLayout()
        right_panel_layout.addWidget(QLabel("Right Panel:"))
        
        # Top Right Section
        top_right_layout = QFormLayout()
        self.top_right_combo = QComboBox()
        self.top_right_combo.addItems([
            "None", "Category", "Status", "Priority", "Due Date",
            "Link", "Progress", "Completion Date", "Tag", "Files"
        ])
        top_right_layout.addRow("Top:", self.top_right_combo)
        right_panel_layout.addLayout(top_right_layout)
        
        # Bottom Right Section
        bottom_right_layout = QFormLayout()
        self.bottom_right_combo = QComboBox()
        self.bottom_right_combo.addItems([
            "None", "Category", "Status", "Priority", "Due Date",
            "Link", "Progress", "Completion Date", "Tag", "Files"
        ])
        bottom_right_layout.addRow("Bottom:", self.bottom_right_combo)
        right_panel_layout.addLayout(bottom_right_layout)
        
        # Add both panel configurations to the layout
        panel_layout.addLayout(left_panel_layout)
        panel_layout.addLayout(right_panel_layout)
        
        panel_layout_group.setLayout(panel_layout)
        content_layout.addWidget(panel_layout_group)
        
        # Set the content widget for the scroll area
        scroll_area.setWidget(scroll_content)
        
        # Add the scroll area to the left layout
        left_layout.addWidget(scroll_area)
        
        # Add save button
        save_btn = QPushButton("Save Display Settings")
        save_btn.setFixedHeight(40)
        save_btn.setStyleSheet("""
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
        """)
        save_btn.clicked.connect(self.save_settings)
        
        left_layout.addWidget(save_btn)
        
        # Create the right side with preview
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        # Create and add task pill preview widget
        self.task_preview = TaskPillPreviewWidget(self)
        right_layout.addWidget(self.task_preview)
        
        # Set size policies and widths
        left_widget.setMinimumWidth(500)
        right_widget.setMinimumWidth(300)
        
        # Add widgets to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        
        # Set initial sizes (2:1 ratio)
        splitter.setSizes([600, 300])
        
        # Style the splitter handle
        splitter.setHandleWidth(6)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 1px;
            }
            QSplitter::handle:hover {
                background-color: #2196F3;
            }
        """)
        
        # Add splitter to main layout
        main_layout.addWidget(splitter)
    
    def pick_color(self, color_type):
        """Open color picker dialog for the specified color type"""
        color_btn = None
        color_hex = None
        
        if color_type == "title":
            color_btn = self.title_color_btn
            color_hex = self.title_color_hex
        elif color_type == "description":
            color_btn = self.desc_color_btn
            color_hex = self.desc_color_hex
        elif color_type == "due_date":
            color_btn = self.due_color_btn
            color_hex = self.due_color_hex
        elif color_type == "left_panel":
            color_btn = self.left_panel_color_btn
            color_hex = self.left_panel_color_hex
        
        current_color = QColor(color_hex.text())
        color = QColorDialog.getColor(current_color, self)
        
        if color.isValid():
            hex_color = color.name()
            color_btn.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #666666;")
            color_hex.setText(hex_color)
    
    def update_color_from_hex(self, color_type):
        """Update color button when hex value changes"""
        color_btn = None
        color_hex = None
        
        if color_type == "title":
            color_btn = self.title_color_btn
            color_hex = self.title_color_hex
        elif color_type == "description":
            color_btn = self.desc_color_btn
            color_hex = self.desc_color_hex
        elif color_type == "due_date":
            color_btn = self.due_color_btn
            color_hex = self.due_color_hex
        elif color_type == "left_panel":
            color_btn = self.left_panel_color_btn
            color_hex = self.left_panel_color_hex
        
        hex_value = color_hex.text()
        if hex_value.startswith("#") and len(hex_value) == 7:
            try:
                QColor(hex_value)  # Test if valid color
                color_btn.setStyleSheet(f"background-color: {hex_value}; border: 1px solid #666666;")
            except:
                pass
    
    def save_settings(self):
        """Save all display settings to the settings manager and apply changes immediately"""
        # Save font family and size
        self.settings.set_setting("font_family", self.font_family_combo.currentText())
        self.settings.set_setting("font_size", self.font_size_spin.value())
        
        # Save style options
        self.settings.set_setting("bold_titles", self.bold_titles_check.isChecked())
        self.settings.set_setting("italic_descriptions", self.italic_desc_check.isChecked())
        self.settings.set_setting("compact_view_default", self.compact_view_check.isChecked())
        
        # Save font weight
        weight = 0  # Regular
        if self.medium_radio.isChecked():
            weight = 1
        elif self.bold_radio.isChecked():
            weight = 2
        self.settings.set_setting("font_weight", weight)
        
        # Save colors
        self.settings.set_setting("title_color", self.title_color_hex.text())
        self.settings.set_setting("description_color", self.desc_color_hex.text())
        self.settings.set_setting("due_date_color", self.due_color_hex.text())

        # Save left panel settings
        self.settings.set_setting("left_panel_color", self.left_panel_color_hex.text())
        self.settings.set_setting("left_panel_size", self.left_panel_size_spin.value())
        self.settings.set_setting("left_panel_bold", self.left_panel_bold_check.isChecked())
        
        # Save panel layout settings
        left_contents = []
        if self.top_left_combo.currentText() != "None":
            left_contents.append(self.top_left_combo.currentText())
        if self.bottom_left_combo.currentText() != "None":
            left_contents.append(self.bottom_left_combo.currentText())
        
        right_contents = []
        if self.top_right_combo.currentText() != "None":
            right_contents.append(self.top_right_combo.currentText())
        if self.bottom_right_combo.currentText() != "None":
            right_contents.append(self.bottom_right_combo.currentText())
        
        # Always save with 2 sections for consistency
        self.settings.set_setting("left_panel_sections", 2)
        self.settings.set_setting("right_panel_sections", 2)
        
        self.settings.set_setting("left_panel_contents", left_contents)
        self.settings.set_setting("right_panel_contents", right_contents)
        
        # Save panel widths (though they're fixed, we still save them for consistency)
        self.settings.set_setting("left_panel_width", self.left_panel_width)
        self.settings.set_setting("right_panel_width", self.right_panel_width)
        
        # Notify the user
        QMessageBox.information(self, "Settings Saved", 
                            "Display settings have been saved. Changes will be applied immediately.")
        
        # Update the preview
        if hasattr(self, 'task_preview'):
            self.task_preview.update_preview()
        
        # APPLY CHANGES IMMEDIATELY
        self.apply_changes_to_all_tabs()
        
    def load_current_settings(self):
        """Load current settings from settings manager"""
        # Block signals during loading to prevent multiple preview updates
        with QSignalBlocker(self.font_family_combo), \
             QSignalBlocker(self.font_size_spin), \
             QSignalBlocker(self.bold_titles_check), \
             QSignalBlocker(self.italic_desc_check), \
             QSignalBlocker(self.compact_view_check), \
             QSignalBlocker(self.top_left_combo), \
             QSignalBlocker(self.bottom_left_combo), \
             QSignalBlocker(self.top_right_combo), \
             QSignalBlocker(self.bottom_right_combo):
            
            # Font settings
            font_family = self.settings.get_setting("font_family", "")
            if font_family:
                index = self.font_family_combo.findText(font_family)
                if index >= 0:
                    self.font_family_combo.setCurrentIndex(index)
            
            font_size = self.settings.get_setting("font_size", 0)
            if font_size:
                self.font_size_spin.setValue(int(font_size))
            
            # Style options
            self.bold_titles_check.setChecked(self.settings.get_setting("bold_titles", True))
            self.italic_desc_check.setChecked(self.settings.get_setting("italic_descriptions", False))
            self.compact_view_check.setChecked(self.settings.get_setting("compact_view_default", False))
            
            # Font weight
            weight = self.settings.get_setting("font_weight", 0)  # 0=Regular, 1=Medium, 2=Bold
            if weight == 0:
                self.regular_radio.setChecked(True)
            elif weight == 1:
                self.medium_radio.setChecked(True)
            else:
                self.bold_radio.setChecked(True)
            
            # Text colors
            title_color = self.settings.get_setting("title_color", "#333333")
            desc_color = self.settings.get_setting("description_color", "#666666")
            due_color = self.settings.get_setting("due_date_color", "#888888")
            
            self.title_color_hex.setText(title_color)
            self.desc_color_hex.setText(desc_color)
            self.due_color_hex.setText(due_color)
            
            self.title_color_btn.setStyleSheet(f"background-color: {title_color}; border: 1px solid #666666;")
            self.desc_color_btn.setStyleSheet(f"background-color: {desc_color}; border: 1px solid #666666;")
            self.due_color_btn.setStyleSheet(f"background-color: {due_color}; border: 1px solid #666666;")
            
            # Left panel settings
            left_panel_color = self.settings.get_setting("left_panel_color", "#FFFFFF")
            self.left_panel_color_hex.setText(left_panel_color)
            self.left_panel_color_btn.setStyleSheet(f"background-color: {left_panel_color}; border: 1px solid #666666;")

            left_panel_size = self.settings.get_setting("left_panel_size", 8)
            if left_panel_size:
                self.left_panel_size_spin.setValue(int(left_panel_size))

            self.left_panel_bold_check.setChecked(self.settings.get_setting("left_panel_bold", False))
            
            # Panel layout settings
            left_contents = self.settings.get_setting("left_panel_contents", ["Category", "Status"])
            
            # Set top left content
            if len(left_contents) > 0:
                self.top_left_combo.setCurrentText(left_contents[0])
            
            # Set bottom left content
            if len(left_contents) > 1:
                self.bottom_left_combo.setCurrentText(left_contents[1])
            
            # Right section content settings
            right_contents = self.settings.get_setting("right_panel_contents", ["Link", "Due Date"])
            
            # Set top right content
            if len(right_contents) > 0:
                self.top_right_combo.setCurrentText(right_contents[0])
            
            # Set bottom right content
            if len(right_contents) > 1:
                self.bottom_right_combo.setCurrentText(right_contents[1])
                
        # After loading settings, update the preview
        if hasattr(self, 'task_preview'):
            self.task_preview.update_preview()
            
    def apply_changes_to_all_tabs(self):
        """Apply display settings changes to all task trees immediately"""
        # Find the main window
        main_window = self.main_window
        
        # Get the tab widget from the main window
        if hasattr(main_window, 'tabs'):
            tabs = main_window.tabs
            
            # Apply changes to each tab's task tree
            for i in range(tabs.count()):
                tab = tabs.widget(i)
                if hasattr(tab, 'task_tree'):
                    task_tree = tab.task_tree
                    
                    # Create a new delegate with the updated settings
                    new_delegate = TaskPillDelegate(task_tree)
                    
                    # Apply the new delegate to the task tree
                    task_tree.setItemDelegate(new_delegate)
                    
                    # Force a viewport update to redraw with new settings
                    task_tree.viewport().update()
                    
            print("Display settings changes applied to all tabs")