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
        """Set up the main layout and components"""
        # Create a main layout for the entire widget
        main_layout = QVBoxLayout(self)
        
        # Add top buttons and header
        self._setup_header_section(main_layout)
        
        # Add scroll area for settings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Create a container widget for the scroll area
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setSpacing(15)
        
        # Add all settings sections
        self._setup_font_settings(content_layout)
        self._setup_color_settings(content_layout)
        self._setup_panel_layout(content_layout)
        self._setup_preview_section(content_layout)
        
        # Set the content widget for the scroll area
        scroll_area.setWidget(scroll_content)
        
        # Add the scroll area to the main layout
        main_layout.addWidget(scroll_area, 1)  # 1 = stretch factor
        
        # Add bottom buttons
        self._setup_bottom_buttons(main_layout)

    def _setup_font_settings(self, parent_layout):
        """Set up the font settings section as three panels side by side with equal width"""
        # Create horizontal layout for the three panels
        font_settings_layout = QHBoxLayout()
        
        # ===== PANEL 1: Font Family and Sizes =====
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

    def _populate_font_combo(self):
        """Populate the font family combo box with available fonts"""
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

    def _setup_style_options(self):
        """Set up style options section"""
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

    def _setup_font_weight(self):
        """Set up font weight section"""
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

    def _setup_color_settings(self, parent_layout):
        """Set up the color settings section"""
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

    def _create_color_picker_compact(self, label_text, color_type, default_color):
        """Helper method to create a compact color picker column"""
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
        
        return color_layout
    
    def _create_color_picker(self, label_text, color_type, default_color):
        """Helper method to create a consistent color picker row"""
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
        
        return color_layout

    def _setup_panel_layout(self, parent_layout):
        """Set up the panel layout section"""
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
        for combo in [self.top_left_combo, self.bottom_left_combo, 
                    self.top_right_combo, self.bottom_right_combo]:
            combo.addItems(panel_options)
        
        # Connect combo box signals to update preview directly
        self.top_left_combo.currentIndexChanged.connect(self.force_preview_update)
        self.bottom_left_combo.currentIndexChanged.connect(self.force_preview_update)
        self.top_right_combo.currentIndexChanged.connect(self.force_preview_update)
        self.bottom_right_combo.currentIndexChanged.connect(self.force_preview_update)
            
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

    def _populate_panel_dropdowns(self):
        """Populate the panel dropdowns with content options"""
        options = [
            "None", "Category", "Status", "Priority", "Due Date",
            "Link", "Progress", "Completion Date", "Tag", "Files"
        ]
        
        # Add options to all dropdowns
        self.top_left_combo.addItems(options)
        self.bottom_left_combo.addItems(options)
        self.top_right_combo.addItems(options)
        self.bottom_right_combo.addItems(options)

    def force_preview_update(self):
        """Force a direct update of the preview when panel dropdowns change"""
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
        
        # Save settings directly
        self.settings.set_setting("left_panel_contents", left_contents)
        self.settings.set_setting("right_panel_contents", right_contents)
        
        # Directly modify the delegate if it exists
        if hasattr(self.task_preview, 'sample_tree') and self.task_preview.sample_tree:
            delegate = self.task_preview.sample_tree.itemDelegate()
            if delegate:
                delegate.left_panel_contents = left_contents
                delegate.right_panel_contents = right_contents
        
        # Force a complete recreation of the sample items
        if hasattr(self.task_preview, 'create_sample_items'):
            self.task_preview.create_sample_items()
            
        # Force a viewport repaint
        if hasattr(self.task_preview, 'sample_tree') and self.task_preview.sample_tree:
            self.task_preview.sample_tree.viewport().update()

    def _setup_preview_section(self, parent_layout):
        """Set up the preview section with a single group box"""
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        # Add instruction label
        instruction_label = QLabel("Click the toggle button above the task pill to switch between compact and full views")
        instruction_label.setStyleSheet("color: #666666; font-style: italic;")
        preview_layout.addWidget(instruction_label)
        
        # Create and add task pill preview widget WITHOUT its own group box
        self.task_preview = TaskPillPreviewWidget(self, use_group_box=False)
        preview_layout.addWidget(self.task_preview)
        
        # Set layout margins to reduce white space
        preview_layout.setContentsMargins(10, 10, 10, 10)
        preview_layout.setSpacing(5)
        
        parent_layout.addWidget(preview_group)
    
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
    
    def _setup_header_section(self, parent_layout):
        """Set up the header section with top buttons"""
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

    def _setup_bottom_buttons(self, parent_layout):
        """Set up the bottom button section (left-aligned)"""
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
   
    def save_and_return(self):
            """Save settings and return to task view"""
            # First save all settings
            self.save_settings()
            
            # Then return to task view
            self.main_window.show_task_view()

    def cancel_and_return(self):
        """Cancel changes and return to task view"""
        # Restore original settings
        self.load_current_settings()
        
        # Return to task view without saving
        self.main_window.show_task_view()
        # Close the settings window     
    
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
    
    def update_preview_now(self):
        """Immediately update settings and refresh the preview"""
        print("PREVIEW DEBUG: update_preview_now called!")
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
        
        # Save settings immediately
        print(f"PREVIEW DEBUG: Saving settings: left={left_contents}, right={right_contents}")
        self.settings.set_setting("left_panel_contents", left_contents)
        self.settings.set_setting("right_panel_contents", right_contents)
        
        # Update the preview if it exists
        if hasattr(self, 'task_preview'):
            print("PREVIEW DEBUG: Calling task_preview.update_preview()")
            self.task_preview.update_preview()
        else:
            print("PREVIEW DEBUG: Warning: task_preview doesn't exist!")