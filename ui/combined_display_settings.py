# src/ui/combined_display_settings.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox, QCheckBox,
    QRadioButton, QButtonGroup, QGroupBox, QPushButton, QColorDialog, QLineEdit,
    QFormLayout, QMessageBox, QScrollArea, QFrame, QSizePolicy, QSplitter
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt, QSignalBlocker
import platform

# Import debug utilities
from utils.debug_logger import get_debug_logger
from utils.debug_decorator import debug_method

# Import UI components
from ui.task_pill_preview import TaskPillPreviewWidget
from ui.task_pill_delegate import TaskPillDelegate

# Get debug logger instance
debug = get_debug_logger()

class CombinedDisplaySettingsWidget(QWidget):
    @debug_method
    def __init__(self, main_window):
        debug.debug("Initializing CombinedDisplaySettingsWidget")
        super().__init__()
        self.main_window = main_window
        self.settings = main_window.settings
        
        # Fixed panel widths - these are constants
        self.left_panel_width = 100  # Fixed width for left panel
        self.right_panel_width = 100  # Fixed width for right panel
        
        self.setup_ui()
        self.load_current_settings()
        debug.debug("CombinedDisplaySettingsWidget initialized")
    
    @debug_method
    def setup_ui(self):
        """Set up the main layout and components"""
        debug.debug("Setting up main UI for CombinedDisplaySettingsWidget")
        # Create a main layout for the entire widget
        main_layout = QVBoxLayout(self)
        
        # Add top buttons and header
        self._setup_header_section(main_layout)
        
        # Add scroll area for settings
        debug.debug("Creating scroll area for settings")
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Create a container widget for the scroll area
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setSpacing(15)
        
        # Add all settings sections
        debug.debug("Setting up font settings section")
        self._setup_font_settings(content_layout)
        debug.debug("Setting up color settings section")
        self._setup_color_settings(content_layout)
        debug.debug("Setting up panel layout section")
        self._setup_panel_layout(content_layout)
        debug.debug("Setting up preview section")
        self._setup_preview_section(content_layout)
        
        # Set the content widget for the scroll area
        scroll_area.setWidget(scroll_content)
        
        # Add the scroll area to the main layout
        main_layout.addWidget(scroll_area, 1)  # 1 = stretch factor
        
        # Add bottom buttons
        self._setup_bottom_buttons(main_layout)
        debug.debug("UI setup completed")

    @debug_method
    def _setup_font_settings(self, parent_layout):
        """Set up the font settings section as three panels side by side with equal width"""
        debug.debug("Creating font settings section with three panels")
        # Create horizontal layout for the three panels
        font_settings_layout = QHBoxLayout()
        
        # ===== PANEL 1: Font Family and Sizes =====
        debug.debug("Creating font basics panel")
        font_basics_panel = QGroupBox("Font Basics")
        font_basics_layout = QVBoxLayout(font_basics_panel)
        
        # Create and configure widgets
        self.font_family_combo = QComboBox()
        self.font_family_combo.setMaximumWidth(200)
        self._populate_font_combo()
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(10)
        self.font_size_spin.setFixedWidth(60)
        
        self.left_panel_size_spin = QSpinBox()
        self.left_panel_size_spin.setRange(6, 14)
        self.left_panel_size_spin.setValue(8)
        self.left_panel_size_spin.setFixedWidth(60)
        
        # Add Font Family (horizontal layout)
        font_family_layout = QHBoxLayout()
        font_family_label = QLabel("Font Family:")
        font_family_layout.addWidget(font_family_label)
        font_family_layout.addWidget(self.font_family_combo)
        font_family_layout.addStretch()
        font_basics_layout.addLayout(font_family_layout)
        
        # Add Main Text Size (horizontal layout)
        main_size_layout = QHBoxLayout()
        main_size_label = QLabel("Main Text Size:")
        main_size_layout.addWidget(main_size_label)
        main_size_layout.addWidget(self.font_size_spin)
        main_size_layout.addStretch()
        font_basics_layout.addLayout(main_size_layout)
        
        # Add Panel Text Size (horizontal layout)
        panel_size_layout = QHBoxLayout()
        panel_size_label = QLabel("Panel Text Size:")
        panel_size_layout.addWidget(panel_size_label)
        panel_size_layout.addWidget(self.left_panel_size_spin)
        panel_size_layout.addStretch()
        font_basics_layout.addLayout(panel_size_layout)
        
        # Add stretch to push everything to the top
        font_basics_layout.addStretch()
        
        # ===== PANEL 2: Font Weight =====
        debug.debug("Creating font weight panel")
        font_weight_panel = QGroupBox("Font Weight")
        font_weight_layout = QVBoxLayout(font_weight_panel)
        
        # Create and configure widgets
        self.weight_group = QButtonGroup(self)
        
        self.regular_radio = QRadioButton("Regular")
        self.regular_radio.setChecked(True)
        self.weight_group.addButton(self.regular_radio, 0)
        
        self.medium_radio = QRadioButton("Medium")
        self.weight_group.addButton(self.medium_radio, 1)
        
        self.bold_radio = QRadioButton("Bold")
        self.weight_group.addButton(self.bold_radio, 2)
        
        # Add radio buttons to layout
        font_weight_layout.addWidget(self.regular_radio)
        font_weight_layout.addWidget(self.medium_radio)
        font_weight_layout.addWidget(self.bold_radio)
        
        # Add stretch to push everything to the top
        font_weight_layout.addStretch()
        
        # ===== PANEL 3: Style Options =====
        debug.debug("Creating style options panel")
        style_options_panel = QGroupBox("Style Options")
        style_options_layout = QVBoxLayout(style_options_panel)
        
        # Create and configure widgets
        self.bold_titles_check = QCheckBox("Bold titles")
        self.bold_titles_check.setChecked(True)
        
        self.italic_desc_check = QCheckBox("Italic descriptions")
        
        self.compact_view_check = QCheckBox("Use compact view by default")
        
        self.left_panel_bold_check = QCheckBox("Bold panel text")
        
        # Add checkboxes to layout
        style_options_layout.addWidget(self.bold_titles_check)
        style_options_layout.addWidget(self.italic_desc_check)
        style_options_layout.addWidget(self.compact_view_check)
        style_options_layout.addWidget(self.left_panel_bold_check)
        
        # Add stretch to push everything to the top
        style_options_layout.addStretch()
        
        # Set equal width for all panels using size policies
        for panel in [font_basics_panel, font_weight_panel, style_options_panel]:
            panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Add all three panels to the horizontal layout with equal width (1:1:1 ratio)
        font_settings_layout.addWidget(font_basics_panel, 1)
        font_settings_layout.addWidget(font_weight_panel, 1)
        font_settings_layout.addWidget(style_options_panel, 1)
        
        # Add the horizontal layout to the parent layout
        parent_layout.addLayout(font_settings_layout)
        debug.debug("Font settings section setup complete")

    @debug_method
    def _populate_font_combo(self):
        """Populate the font family combo box with available fonts"""
        debug.debug("Populating font family combo box")
        cross_platform_fonts = [
            "Arial", "Helvetica", "Times New Roman", "Times",
            "Courier New", "Courier", "Verdana", "Georgia",
            "Tahoma", "Trebuchet MS"
        ]
        
        # Add system fonts based on platform
        system = platform.system()
        debug.debug(f"Current platform: {system}")
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
        debug.debug(f"Adding {len(cross_platform_fonts)} fonts to combo box")
        self.font_family_combo.addItems(cross_platform_fonts)
        
        # Set default font based on platform
        default_font = "Segoe UI" if system == "Windows" else "San Francisco" if system == "Darwin" else "Arial"
        index = self.font_family_combo.findText(default_font)
        if index >= 0:
            debug.debug(f"Setting default font to: {default_font}")
            self.font_family_combo.setCurrentIndex(index)
        else:
            debug.warning(f"Default font {default_font} not found in font list")

    @debug_method
    def _setup_style_options(self):
        """Set up style options section"""
        debug.debug("Setting up style options section")
        style_options_layout = QVBoxLayout()
        style_options_label = QLabel("Style Options:")
        style_options_layout.addWidget(style_options_label)
        
        # Option checkboxes
        self.bold_titles_check = QCheckBox("Bold titles")
        self.bold_titles_check.setChecked(True)
        
        self.italic_desc_check = QCheckBox("Italic descriptions")
        
        self.compact_view_check = QCheckBox("Use compact view by default")
        
        # Moved the panel bold check here
        self.left_panel_bold_check = QCheckBox("Bold panel text")
        
        style_options_layout.addWidget(self.bold_titles_check)
        style_options_layout.addWidget(self.italic_desc_check)
        style_options_layout.addWidget(self.compact_view_check)
        style_options_layout.addWidget(self.left_panel_bold_check)
        
        return style_options_layout

    @debug_method
    def _setup_font_weight(self):
        """Set up font weight section"""
        debug.debug("Setting up font weight section")
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
        
        return font_weight_layout

    @debug_method
    def _setup_color_settings(self, parent_layout):
        """Set up the color settings section"""
        debug.debug("Setting up color settings section")
        
        # Create all color buttons and hex fields first
        self.title_color_btn = QPushButton()
        self.title_color_hex = QLineEdit("#333333")
        self.desc_color_btn = QPushButton()
        self.desc_color_hex = QLineEdit("#666666")
        self.due_color_btn = QPushButton()
        self.due_color_hex = QLineEdit("#888888")
        self.left_panel_color_btn = QPushButton()
        self.left_panel_color_hex = QLineEdit("#FFFFFF")
        
        # Configure buttons
        for btn, color in [
            (self.title_color_btn, "#333333"),
            (self.desc_color_btn, "#666666"),
            (self.due_color_btn, "#888888"),
            (self.left_panel_color_btn, "#FFFFFF")
        ]:
            btn.setFixedSize(30, 20)
            btn.setStyleSheet(f"background-color: {color}; border: 1px solid #666666;")
        
        # Configure hex fields
        for hex_field in [self.title_color_hex, self.desc_color_hex, 
                        self.due_color_hex, self.left_panel_color_hex]:
            hex_field.setFixedWidth(80)
        
        # Connect signals
        debug.debug("Connecting color buttons and hex fields signals")
        self.title_color_btn.clicked.connect(lambda: self.pick_color("title"))
        self.title_color_hex.textChanged.connect(lambda: self.update_color_from_hex("title"))
        self.desc_color_btn.clicked.connect(lambda: self.pick_color("description"))
        self.desc_color_hex.textChanged.connect(lambda: self.update_color_from_hex("description"))
        self.due_color_btn.clicked.connect(lambda: self.pick_color("due_date"))
        self.due_color_hex.textChanged.connect(lambda: self.update_color_from_hex("due_date"))
        self.left_panel_color_btn.clicked.connect(lambda: self.pick_color("left_panel"))
        self.left_panel_color_hex.textChanged.connect(lambda: self.update_color_from_hex("left_panel"))
        
        # Now create the group and layout
        colors_group = QGroupBox("Text Colors")
        colors_layout = QVBoxLayout()
        
        # First row: Title and Description
        first_row = QHBoxLayout()
        
        # Title color layout
        title_layout = QVBoxLayout()
        title_layout.addWidget(QLabel("Task Title:"))
        title_color_row = QHBoxLayout()
        title_color_row.addWidget(self.title_color_btn)
        title_color_row.addWidget(self.title_color_hex)
        title_color_row.addStretch()
        title_layout.addLayout(title_color_row)
        
        # Description color layout
        desc_layout = QVBoxLayout()
        desc_layout.addWidget(QLabel("Task Description:"))
        desc_color_row = QHBoxLayout()
        desc_color_row.addWidget(self.desc_color_btn)
        desc_color_row.addWidget(self.desc_color_hex)
        desc_color_row.addStretch()
        desc_layout.addLayout(desc_color_row)
        
        first_row.addLayout(title_layout)
        first_row.addLayout(desc_layout)
        
        # Due date color layout
        due_layout = QVBoxLayout()
        due_layout.addWidget(QLabel("Due Date:"))
        due_color_row = QHBoxLayout()
        due_color_row.addWidget(self.due_color_btn)
        due_color_row.addWidget(self.due_color_hex)
        due_color_row.addStretch()
        due_layout.addLayout(due_color_row)
        
        # Panel color layout
        panel_layout = QVBoxLayout()
        panel_layout.addWidget(QLabel("Left/Right Panel Text:"))
        panel_color_row = QHBoxLayout()
        panel_color_row.addWidget(self.left_panel_color_btn)
        panel_color_row.addWidget(self.left_panel_color_hex)
        panel_color_row.addStretch()
        panel_layout.addLayout(panel_color_row)
        
        first_row.addLayout(panel_layout)
        first_row.addLayout(due_layout)
        
        # Add rows to main layout
        colors_layout.addLayout(first_row)
        
        colors_group.setLayout(colors_layout)
        parent_layout.addWidget(colors_group)
        debug.debug("Color settings section setup complete")
        
    @debug_method
    def _create_color_picker_compact(self, label_text, color_type, default_color):
        """Helper method to create a compact color picker column"""
        debug.debug(f"Creating compact color picker for {color_type} with default {default_color}")
        color_layout = QVBoxLayout()
        label = QLabel(label_text)
        
        picker_layout = QHBoxLayout()
        color_btn = QPushButton()
        color_btn.setFixedSize(30, 20)
        color_btn.setStyleSheet(f"background-color: {default_color}; border: 1px solid #666666;")
        
        color_hex = QLineEdit(default_color)
        color_hex.setFixedWidth(80)
        
        # Store references to the widgets
        if color_type == "title":
            self.title_color_btn = color_btn
            self.title_color_hex = color_hex
            color_btn.clicked.connect(lambda: self.pick_color("title"))
            color_hex.textChanged.connect(lambda: self.update_color_from_hex("title"))
        elif color_type == "description":
            self.desc_color_btn = color_btn
            self.desc_color_hex = color_hex
            color_btn.clicked.connect(lambda: self.pick_color("description"))
            color_hex.textChanged.connect(lambda: self.update_color_from_hex("description"))
        elif color_type == "due_date":
            self.due_color_btn = color_btn
            self.due_color_hex = color_hex
            color_btn.clicked.connect(lambda: self.pick_color("due_date"))
            color_hex.textChanged.connect(lambda: self.update_color_from_hex("due_date"))
        elif color_type == "left_panel":
            self.left_panel_color_btn = color_btn
            self.left_panel_color_hex = color_hex
            color_btn.clicked.connect(lambda: self.pick_color("left_panel"))
            color_hex.textChanged.connect(lambda: self.update_color_from_hex("left_panel"))
        
        picker_layout.addWidget(color_btn)
        picker_layout.addWidget(color_hex)
        picker_layout.addStretch()
        
        color_layout.addWidget(label)
        color_layout.addLayout(picker_layout)
        
        debug.debug(f"Compact color picker created for {color_type}")
        return color_layout
    
    @debug_method
    def _create_color_picker(self, label_text, color_type, default_color):
        """Helper method to create a consistent color picker row"""
        debug.debug(f"Creating standard color picker for {color_type} with default {default_color}")
        color_layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setMinimumWidth(100)
        
        color_btn = QPushButton()
        color_btn.setFixedSize(30, 20)
        color_btn.setStyleSheet(f"background-color: {default_color}; border: 1px solid #666666;")
        
        color_hex = QLineEdit(default_color)
        color_hex.setFixedWidth(80)
        
        # Store references to the widgets
        if color_type == "title":
            self.title_color_btn = color_btn
            self.title_color_hex = color_hex
            color_btn.clicked.connect(lambda: self.pick_color("title"))
            color_hex.textChanged.connect(lambda: self.update_color_from_hex("title"))
        elif color_type == "description":
            self.desc_color_btn = color_btn
            self.desc_color_hex = color_hex
            color_btn.clicked.connect(lambda: self.pick_color("description"))
            color_hex.textChanged.connect(lambda: self.update_color_from_hex("description"))
        elif color_type == "due_date":
            self.due_color_btn = color_btn
            self.due_color_hex = color_hex
            color_btn.clicked.connect(lambda: self.pick_color("due_date"))
            color_hex.textChanged.connect(lambda: self.update_color_from_hex("due_date"))
        elif color_type == "left_panel":
            self.left_panel_color_btn = color_btn
            self.left_panel_color_hex = color_hex
            color_btn.clicked.connect(lambda: self.pick_color("left_panel"))
            color_hex.textChanged.connect(lambda: self.update_color_from_hex("left_panel"))
        
        color_layout.addWidget(label)
        color_layout.addWidget(color_btn)
        color_layout.addWidget(color_hex)
        color_layout.addStretch()
        
        debug.debug(f"Standard color picker created for {color_type}")
        return color_layout

    @debug_method
    def _setup_panel_layout(self, parent_layout):
        """Set up the panel layout section"""
        debug.debug("Setting up panel layout section")
        panel_layout_group = QGroupBox("Task Pill Layout")
        panel_layout = QHBoxLayout()
        
        # Create all combo boxes first
        self.top_left_combo = QComboBox()
        self.bottom_left_combo = QComboBox()
        self.top_right_combo = QComboBox()
        self.bottom_right_combo = QComboBox()
        
        # Populate the dropdowns
        panel_options = [
            "None", "Category", "Status", "Priority", "Due Date",
            "Link", "Progress", "Completion Date", "Tag", "Files"
        ]
        debug.debug(f"Adding {len(panel_options)} options to panel layout combo boxes")
        for combo in [self.top_left_combo, self.bottom_left_combo, 
                    self.top_right_combo, self.bottom_right_combo]:
            combo.addItems(panel_options)
        
        # Connect combo box signals to update preview directly
        self.top_left_combo.currentTextChanged.connect(self.force_preview_update)
        self.bottom_left_combo.currentTextChanged.connect(self.force_preview_update)
        self.top_right_combo.currentTextChanged.connect(self.force_preview_update)
        self.bottom_right_combo.currentTextChanged.connect(self.force_preview_update)
            
        # Left Panel Configuration
        left_panel_layout = QVBoxLayout()
        
        # Top Left Section - left justified
        top_left_layout = QHBoxLayout()
        top_left_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        top_left_label = QLabel("Top Left:")
        top_left_label.setMinimumWidth(50)
        top_left_layout.addWidget(top_left_label)
        top_left_layout.addWidget(self.top_left_combo)
        top_left_layout.addStretch()
        left_panel_layout.addLayout(top_left_layout)
        
        # Bottom Left Section - left justified
        bottom_left_layout = QHBoxLayout()
        bottom_left_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        bottom_left_label = QLabel("Bottom Left:")
        bottom_left_label.setMinimumWidth(50)
        bottom_left_layout.addWidget(bottom_left_label)
        bottom_left_layout.addWidget(self.bottom_left_combo)
        bottom_left_layout.addStretch()
        left_panel_layout.addLayout(bottom_left_layout)
        
        # Right Panel Configuration
        right_panel_layout = QVBoxLayout()

        # Top Right Section - left justified
        top_right_layout = QHBoxLayout()
        top_right_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        top_right_label = QLabel("Top Right:")
        top_right_label.setMinimumWidth(50)
        top_right_layout.addWidget(top_right_label)
        top_right_layout.addWidget(self.top_right_combo)
        top_right_layout.addStretch()
        right_panel_layout.addLayout(top_right_layout)
        
        # Bottom Right Section - left justified
        bottom_right_layout = QHBoxLayout()
        bottom_right_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        bottom_right_label = QLabel("Bottom Right:")
        bottom_right_label.setMinimumWidth(50)
        bottom_right_layout.addWidget(bottom_right_label)
        bottom_right_layout.addWidget(self.bottom_right_combo)
        bottom_right_layout.addStretch()
        right_panel_layout.addLayout(bottom_right_layout)
        
        # Add both panel configurations to the layout
        panel_layout.addLayout(left_panel_layout)
        panel_layout.addLayout(right_panel_layout)
        
        panel_layout_group.setLayout(panel_layout)
        parent_layout.addWidget(panel_layout_group)
        debug.debug("Panel layout section setup complete")

    @debug_method
    def _populate_panel_dropdowns(self):
        """Populate the panel dropdowns with content options"""
        debug.debug("Populating panel dropdowns")
        options = [
            "None", "Category", "Status", "Priority", "Due Date",
            "Link", "Progress", "Completion Date", "Tag", "Files"
        ]
        
        # Add options to all dropdowns
        self.top_left_combo.addItems(options)
        self.bottom_left_combo.addItems(options)
        self.top_right_combo.addItems(options)
        self.bottom_right_combo.addItems(options)
        debug.debug(f"Added {len(options)} options to each dropdown")

    @debug_method
    def force_preview_update(self, check = False):
        """Force a direct update of the preview when panel dropdowns change"""
        debug.debug("Forcing preview update due to panel dropdown change")
        # Get current settings
        left_contents = []
        right_contents = []
        
        # Left panel contents
        if self.top_left_combo.currentText() != "None":
            left_contents.append(self.top_left_combo.currentText())
        
        if self.bottom_left_combo.currentText() != "None":
            left_contents.append(self.bottom_left_combo.currentText())
        
        # Right panel contents
        if self.top_right_combo.currentText() != "None":
            right_contents.append(self.top_right_combo.currentText())
        
        if self.bottom_right_combo.currentText() != "None":
            right_contents.append(self.bottom_right_combo.currentText())
        
        # Use special values if the lists are empty
        left_final = ["__NONE__"] if len(left_contents) == 0 else left_contents
        right_final = ["__NONE__"] if len(right_contents) == 0 else right_contents
        
        debug.debug(f"Left panel contents: {left_final}")
        debug.debug(f"Right panel contents: {right_final}")
        
        # Save settings directly
        self.settings.set_setting("left_panel_contents", left_final)
        self.settings.set_setting("right_panel_contents", right_final)
        
        # Force settings to save to disk
        self.settings.save_settings(self.settings.settings)
        
        # Directly modify the delegate if it exists
        if hasattr(self.task_preview, 'sample_tree') and self.task_preview.sample_tree:
            delegate = self.task_preview.sample_tree.itemDelegate()
            if delegate:
                debug.debug("Updating delegate panel contents directly")
                delegate.left_panel_contents = left_contents  # Note: use actual empty list, not placeholder
                delegate.right_panel_contents = right_contents
        
        # Force a complete recreation of the sample items
        if hasattr(self.task_preview, 'create_sample_items'):
            debug.debug("Recreating sample items")
            self.task_preview.create_sample_items()
            
        # Force a viewport repaint
        if hasattr(self.task_preview, 'sample_tree') and self.task_preview.sample_tree:
            debug.debug("Forcing viewport update")
            self.task_preview.sample_tree.viewport().update()
    
    @debug_method
    def _setup_preview_section(self, parent_layout):
        """Set up the preview section with a single group box"""
        debug.debug("Setting up preview section")
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        # Add instruction label
        instruction_label = QLabel("Click the toggle button above the task pill to switch between compact and full views")
        instruction_label.setStyleSheet("color: #666666; font-style: italic;")
        preview_layout.addWidget(instruction_label)
        
        # Create and add task pill preview widget WITHOUT its own group box
        debug.debug("Creating TaskPillPreviewWidget")
        self.task_preview = TaskPillPreviewWidget(self, use_group_box=False)
        preview_layout.addWidget(self.task_preview)
        
        # Set layout margins to reduce white space
        preview_layout.setContentsMargins(10, 10, 10, 10)
        preview_layout.setSpacing(5)
        
        parent_layout.addWidget(preview_group)
        debug.debug("Preview section setup complete")
    
    @debug_method
    def pick_color(self, color_type):
        """Open color picker dialog for the specified color type"""
        debug.debug(f"Opening color picker for {color_type}")
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
            debug.debug(f"Selected color for {color_type}: {hex_color}")
            color_btn.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #666666;")
            color_hex.setText(hex_color)
        else:
            debug.debug(f"Color selection cancelled for {color_type}")
    
    @debug_method
    def _setup_header_section(self, parent_layout):
        """Set up the header section with top buttons"""
        debug.debug("Setting up header section")
        # Add top buttons for Save and Cancel (left-aligned)
        top_button_layout = QHBoxLayout()
        
        save_btn_top = QPushButton("Save Settings")
        save_btn_top.setFixedSize(100, 30)
        save_btn_top.setStyleSheet("""
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
        """)
        save_btn_top.clicked.connect(self.save_and_return)
        
        cancel_btn_top = QPushButton("Cancel")
        cancel_btn_top.setFixedSize(100, 30)
        cancel_btn_top.setStyleSheet("""
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
        """)
        cancel_btn_top.clicked.connect(self.cancel_and_return)
        
        top_button_layout.addWidget(save_btn_top)
        top_button_layout.addWidget(cancel_btn_top)
        top_button_layout.addStretch()  # Push buttons to the left by placing stretch AFTER the buttons
        
        parent_layout.addLayout(top_button_layout)
        debug.debug("Header section setup complete")

    @debug_method
    def _setup_bottom_buttons(self, parent_layout):
        """Set up the bottom button section (left-aligned)"""
        debug.debug("Setting up bottom buttons")
        bottom_button_layout = QHBoxLayout()
        
        save_btn_bottom = QPushButton("Save Settings")
        save_btn_bottom.setFixedSize(100, 30)
        save_btn_bottom.setStyleSheet("""
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
        """)
        save_btn_bottom.clicked.connect(self.save_and_return)
        
        cancel_btn_bottom = QPushButton("Cancel")
        cancel_btn_bottom.setFixedSize(100, 30)
        cancel_btn_bottom.setStyleSheet("""
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
        """)
        cancel_btn_bottom.clicked.connect(self.cancel_and_return)
        
        bottom_button_layout.addWidget(save_btn_bottom)
        bottom_button_layout.addWidget(cancel_btn_bottom)
        bottom_button_layout.addStretch()  # Push buttons to the left by placing stretch AFTER the buttons
        
        parent_layout.addLayout(bottom_button_layout)
        debug.debug("Bottom buttons setup complete")
    
    @debug_method
    def update_color_from_hex(self, color_type):
        """Update color button when hex value changes"""
        debug.debug(f"Updating color from hex value for {color_type}")
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
        debug.debug(f"New hex value: {hex_value}")
        
        if hex_value.startswith("#") and len(hex_value) == 7:
            try:
                QColor(hex_value)  # Test if valid color
                color_btn.setStyleSheet(f"background-color: {hex_value}; border: 1px solid #666666;")
                debug.debug(f"Valid color, button updated for {color_type}")
            except Exception as e:
                debug.error(f"Invalid color format for {color_type}: {e}")
        else:
            debug.warning(f"Invalid hex format for {color_type}: {hex_value}")
    
    @debug_method
    def save_settings(self):
        """Save all display settings to the settings manager and apply changes immediately"""
        debug.debug("Saving all display settings")
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

        # Convert empty lists to special placeholder
        if len(left_contents) == 0:
            left_contents = ["__NONE__"]
        if len(right_contents) == 0:
            right_contents = ["__NONE__"]

        debug.debug(f"Saving panel contents - Left: {left_contents}, Right: {right_contents}")

        # Always save with 2 sections for consistency
        self.settings.set_setting("left_panel_sections", 2)
        self.settings.set_setting("right_panel_sections", 2)

        self.settings.set_setting("left_panel_contents", left_contents)
        self.settings.set_setting("right_panel_contents", right_contents)
        
        # Save panel widths (though they're fixed, we still save them for consistency)
        self.settings.set_setting("left_panel_width", self.left_panel_width)
        self.settings.set_setting("right_panel_width", self.right_panel_width)

        # Explicitly save settings to disk
        self.settings.save_settings(self.settings.settings)
        debug.debug("Settings saved to disk")
    
        # Notify the user
        QMessageBox.information(self, "Settings Saved", 
                            "Display settings have been saved. Changes will be applied immediately.")
        debug.debug("User notified about successful settings save")
        
        # Update the preview
        if hasattr(self, 'task_preview'):
            debug.debug("Updating preview after save")
            self.task_preview.update_preview()
        
        # APPLY CHANGES IMMEDIATELY
        debug.debug("Applying changes to all tabs")
        self.apply_changes_to_all_tabs()
   
    @debug_method
    def save_and_return(self, check = False):
        """Save settings and return to task view"""
        debug.debug("Saving settings and returning to task view")
        # First save all settings
        self.save_settings()
        
        # Then return to task view
        debug.debug("Returning to task view")
        self.main_window.show_task_view()

    @debug_method
    def cancel_and_return(self, check = False):
        """Cancel changes and return to task view"""
        debug.debug("Canceling changes and returning to task view")
        # Restore original settings
        self.load_current_settings()
        
        # Return to task view without saving
        debug.debug("Returning to task view without saving")
        self.main_window.show_task_view()
    
    @debug_method
    def load_current_settings(self):
        """Load current settings from settings manager"""
        debug.debug("Loading current settings from settings manager")
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
            debug.debug(f"Loaded font family: {font_family}")
            if font_family:
                index = self.font_family_combo.findText(font_family)
                if index >= 0:
                    self.font_family_combo.setCurrentIndex(index)
                else:
                    debug.warning(f"Font family {font_family} not found in combo box")
            
            font_size = self.settings.get_setting("font_size", 0)
            debug.debug(f"Loaded font size: {font_size}")
            if font_size:
                self.font_size_spin.setValue(int(font_size))
            
            # Style options
            bold_titles = self.settings.get_setting("bold_titles", True)
            italic_descriptions = self.settings.get_setting("italic_descriptions", False)
            compact_view_default = self.settings.get_setting("compact_view_default", False)
            debug.debug(f"Loaded style options - Bold titles: {bold_titles}, Italic desc: {italic_descriptions}, Compact view: {compact_view_default}")
            
            self.bold_titles_check.setChecked(bold_titles)
            self.italic_desc_check.setChecked(italic_descriptions)
            self.compact_view_check.setChecked(compact_view_default)
            
            # Font weight
            weight = self.settings.get_setting("font_weight", 0)  # 0=Regular, 1=Medium, 2=Bold
            debug.debug(f"Loaded font weight: {weight}")
            
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
            debug.debug(f"Loaded text colors - Title: {title_color}, Desc: {desc_color}, Due: {due_color}")
            
            self.title_color_hex.setText(title_color)
            self.desc_color_hex.setText(desc_color)
            self.due_color_hex.setText(due_color)
            
            self.title_color_btn.setStyleSheet(f"background-color: {title_color}; border: 1px solid #666666;")
            self.desc_color_btn.setStyleSheet(f"background-color: {desc_color}; border: 1px solid #666666;")
            self.due_color_btn.setStyleSheet(f"background-color: {due_color}; border: 1px solid #666666;")
            
            # Left panel settings
            left_panel_color = self.settings.get_setting("left_panel_color", "#FFFFFF")
            left_panel_size = self.settings.get_setting("left_panel_size", 8)
            left_panel_bold = self.settings.get_setting("left_panel_bold", False)
            debug.debug(f"Loaded left panel settings - Color: {left_panel_color}, Size: {left_panel_size}, Bold: {left_panel_bold}")
            
            self.left_panel_color_hex.setText(left_panel_color)
            self.left_panel_color_btn.setStyleSheet(f"background-color: {left_panel_color}; border: 1px solid #666666;")

            if left_panel_size:
                self.left_panel_size_spin.setValue(int(left_panel_size))

            self.left_panel_bold_check.setChecked(left_panel_bold)
            
            # Panel layout settings
            left_contents = self.settings.get_setting("left_panel_contents", ["Category", "Status"])
            debug.debug(f"Loaded left panel contents: {left_contents}")
            
            # Handle the special "__NONE__" value
            if left_contents == ["__NONE__"]:
                debug.debug("Using empty list for left panel contents")
                left_contents = []
                
            # Set top left content - index 0 = "None" if not present
            self.top_left_combo.setCurrentIndex(0)  # Default to "None"
            if len(left_contents) > 0:
                idx = self.top_left_combo.findText(left_contents[0])
                if idx >= 0:
                    debug.debug(f"Setting top left combo to: {left_contents[0]}")
                    self.top_left_combo.setCurrentIndex(idx)
            
            # Set bottom left content - index 0 = "None" if not present  
            self.bottom_left_combo.setCurrentIndex(0)  # Default to "None"
            if len(left_contents) > 1:
                idx = self.bottom_left_combo.findText(left_contents[1])
                if idx >= 0:
                    debug.debug(f"Setting bottom left combo to: {left_contents[1]}")
                    self.bottom_left_combo.setCurrentIndex(idx)
            
            # Right section content settings
            right_contents = self.settings.get_setting("right_panel_contents", ["Link", "Due Date"])
            debug.debug(f"Loaded right panel contents: {right_contents}")
            
            # Handle the special "__NONE__" value
            if right_contents == ["__NONE__"]:
                debug.debug("Using empty list for right panel contents")
                right_contents = []
            
            # Set top right content - index 0 = "None" if not present
            self.top_right_combo.setCurrentIndex(0)  # Default to "None"
            if len(right_contents) > 0:
                idx = self.top_right_combo.findText(right_contents[0])
                if idx >= 0:
                    debug.debug(f"Setting top right combo to: {right_contents[0]}")
                    self.top_right_combo.setCurrentIndex(idx)
            
            # Set bottom right content - index 0 = "None" if not present
            self.bottom_right_combo.setCurrentIndex(0)  # Default to "None"
            if len(right_contents) > 1:
                idx = self.bottom_right_combo.findText(right_contents[1])
                if idx >= 0:
                    debug.debug(f"Setting bottom right combo to: {right_contents[1]}")
                    self.bottom_right_combo.setCurrentIndex(idx)
                    
            # After loading settings, update the preview
            if hasattr(self, 'task_preview'):
                debug.debug("Updating preview after loading settings")
                self.task_preview.update_preview()
        
        debug.debug("Current settings loaded successfully")
                
    @debug_method
    def apply_changes_to_all_tabs(self):
        """Apply display settings changes to all task trees immediately"""
        debug.debug("Applying display settings to all task trees")
        # Find the main window
        main_window = self.main_window
        
        # Get the tab widget from the main window
        if hasattr(main_window, 'tabs'):
            tabs = main_window.tabs
            debug.debug(f"Found tabs widget with {tabs.count()} tabs")
            
            # Apply changes to each tab's task tree
            updated_tabs = 0
            for i in range(tabs.count()):
                tab = tabs.widget(i)
                if hasattr(tab, 'task_tree'):
                    task_tree = tab.task_tree
                    debug.debug(f"Updating task tree for tab {i}")
                    
                    # Create a new delegate with the updated settings
                    new_delegate = TaskPillDelegate(task_tree)
                    
                    # Apply the new delegate to the task tree
                    task_tree.setItemDelegate(new_delegate)
                    
                    # Force a viewport update to redraw with new settings
                    task_tree.viewport().update()
                    updated_tabs += 1
            
            debug.debug(f"Applied changes to {updated_tabs} task trees")
    
    @debug_method
    def update_preview_now(self):
        """Immediately update settings and refresh the preview"""
        debug.debug("Immediately updating preview")
        # Get current combo box values
        left_contents = []
        right_contents = []
        
        # Left panel contents
        if self.top_left_combo.currentText() != "None":
            left_contents.append(self.top_left_combo.currentText())
        
        if self.bottom_left_combo.currentText() != "None":
            left_contents.append(self.bottom_left_combo.currentText())
        
        # Right panel contents
        if self.top_right_combo.currentText() != "None":
            right_contents.append(self.top_right_combo.currentText())
        
        if self.bottom_right_combo.currentText() != "None":
            right_contents.append(self.bottom_right_combo.currentText())
        
        debug.debug(f"Current panel contents - Left: {left_contents}, Right: {right_contents}")
        
        # Save settings immediately
        debug.debug("Saving panel contents to settings")
        self.settings.set_setting("left_panel_contents", left_contents)
        self.settings.set_setting("right_panel_contents", right_contents)
        
        # Update the preview if it exists
        if hasattr(self, 'task_preview'):
            debug.debug("Updating preview")
            self.task_preview.update_preview()
        else:
            debug.warning("No task_preview found, cannot update preview")