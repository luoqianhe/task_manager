# src/ui/combined_display_settings.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox, QCheckBox,
    QRadioButton, QButtonGroup, QGroupBox, QPushButton, QColorDialog, QLineEdit,
    QFormLayout, QMessageBox, QScrollArea, QFrame, QSizePolicy, QSplitter,
    QFontDialog, QGridLayout
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
        
        # Set the standard font family for your application
        self.standard_font_family = self.settings.get_setting("font_family", "Arial")
        
        # Initialize fonts for different elements
        self.task_title_font = QFont(self.standard_font_family, 14, QFont.Weight.Bold)
        self.task_description_font = QFont(self.standard_font_family, 10)
        self.task_due_date_font = QFont(self.standard_font_family, 9)
        self.panel_text_font = QFont(self.standard_font_family, 8)
        
        self.setup_ui()
        self.load_current_settings()
        debug.debug("CombinedDisplaySettingsWidget initialized")
    
    @debug_method
    def setup_ui(self):
        """Setup the main UI with scroll area and remove keyboard shortcuts section"""
        debug.debug("Setting up UI")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
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
        
        # Add all settings sections (REMOVED keyboard shortcuts section)
        debug.debug("Setting up font settings section")
        self._setup_font_settings(content_layout)
        debug.debug("Setting up panel layout section")
        self._setup_panel_layout(content_layout)
        debug.debug("Setting up pill background colors section")
        self._setup_pill_background_colors(content_layout)
        debug.debug("Setting up preview section")
        self._setup_preview_section(content_layout)
        
        # Set the content widget for the scroll area
        scroll_area.setWidget(scroll_content)
        
        # Add the scroll area to the main layout
        main_layout.addWidget(scroll_area, 1)  # 1 = stretch factor
        
        # Add bottom buttons
        self._setup_bottom_buttons(main_layout)
        debug.debug("UI setup completed (keyboard shortcuts section removed)")
            
    @debug_method
    def _setup_font_settings(self, parent_layout):
        """Set up the font settings section with font controls only (no color pickers)"""
        debug.debug("Creating font settings section without color pickers")
        
        # Create single Font Settings panel
        font_settings_panel = QGroupBox("Font Settings")
        font_settings_layout = QVBoxLayout(font_settings_panel)
        
        # Create 2x2 grid layout for font controls
        font_grid = QGridLayout()
        font_grid.setSpacing(15)  # Add some spacing between grid items
        
        # Row 1, Column 1: Task Title Font
        self.title_font_button = QPushButton("Change")
        self.title_font_button.setProperty("fontSettings", True)
        self.title_font_button.clicked.connect(lambda: self.open_font_dialog("title"))
        self.title_font_button.setToolTip("Task Title Font Settings")
        self.title_preview = QLabel("Sample Task Title")
        self.title_preview.setFont(self.task_title_font)
        
        title_layout = QHBoxLayout()
        title_layout.addWidget(self.title_preview)
        title_layout.addStretch()
        title_layout.addWidget(self.title_font_button)
        font_grid.addLayout(title_layout, 0, 0)  # Row 0, Column 0
        
        # Row 1, Column 2: Task Description Font
        self.desc_font_button = QPushButton("Change")
        self.desc_font_button.setProperty("fontSettings", True)
        self.desc_font_button.clicked.connect(lambda: self.open_font_dialog("description"))
        self.desc_font_button.setToolTip("Task Description Font Settings")
        self.desc_preview = QLabel("Sample task description text")
        self.desc_preview.setFont(self.task_description_font)
        
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(self.desc_preview)
        desc_layout.addStretch()
        desc_layout.addWidget(self.desc_font_button)
        font_grid.addLayout(desc_layout, 0, 1)  # Row 0, Column 1
        
        # Row 2, Column 1: Due Date Font
        self.date_font_button = QPushButton("Change")
        self.date_font_button.setProperty("fontSettings", True)
        self.date_font_button.clicked.connect(lambda: self.open_font_dialog("due_date"))
        self.date_font_button.setToolTip("Due Date Font Settings")
        self.date_preview = QLabel("Due: 2025-05-30")
        self.date_preview.setFont(self.task_due_date_font)
        
        date_layout = QHBoxLayout()
        date_layout.addWidget(self.date_preview)
        date_layout.addStretch()
        date_layout.addWidget(self.date_font_button)
        font_grid.addLayout(date_layout, 1, 0)  # Row 1, Column 0
        
        # Row 2, Column 2: Panel Text Font
        self.panel_font_button = QPushButton("Change")
        self.panel_font_button.setProperty("fontSettings", True)
        self.panel_font_button.clicked.connect(lambda: self.open_font_dialog("panel"))
        self.panel_font_button.setToolTip("Left/Right Panel Font Settings")
        self.panel_preview = QLabel("Category | Status")
        self.panel_preview.setFont(self.panel_text_font)
        
        panel_layout = QHBoxLayout()
        panel_layout.addWidget(self.panel_preview)
        panel_layout.addStretch()
        panel_layout.addWidget(self.panel_font_button)
        font_grid.addLayout(panel_layout, 1, 1)  # Row 1, Column 1
        
        # Add the grid to the main layout
        font_settings_layout.addLayout(font_grid)
        
        # Add some spacing
        font_settings_layout.addSpacing(15)
        
        # Reset button below the grid
        reset_fonts_btn = QPushButton("Reset All Fonts to System Default")
        reset_fonts_btn.clicked.connect(self.reset_all_fonts)
        reset_fonts_btn.setFixedHeight(30)  # Make it slightly taller
        font_settings_layout.addWidget(reset_fonts_btn)
        
        # Add stretch to push everything to the top
        font_settings_layout.addStretch()
        
        # Add the panel to parent layout
        parent_layout.addWidget(font_settings_panel)
        debug.debug("Font settings section setup complete (without color pickers)")

    @debug_method
    def reset_all_fonts(self, checked = False):
        """Reset all fonts to system defaults (no color reset)"""
        debug.debug("Resetting all fonts to system defaults")
        
        # Determine system default font based on platform
        import platform
        system = platform.system()
        
        if system == "Windows":
            default_family = "Segoe UI"
        elif system == "Darwin":  # macOS
            default_family = "San Francisco"
        else:  # Linux
            default_family = "Ubuntu"
        
        # Update the standard font family
        self.standard_font_family = default_family
        
        # Reset all fonts to defaults
        self.task_title_font = QFont(default_family, 14, QFont.Weight.Bold)
        self.task_description_font = QFont(default_family, 10)
        self.task_due_date_font = QFont(default_family, 9)
        self.panel_text_font = QFont(default_family, 8)
        
        # Update all preview labels with fonts only (no colors)
        self.title_preview.setFont(self.task_title_font)
        self.desc_preview.setFont(self.task_description_font)
        self.date_preview.setFont(self.task_due_date_font)
        self.panel_preview.setFont(self.panel_text_font)
        
        # Save all the reset font settings
        self.save_font_setting("title", self.task_title_font)
        self.save_font_setting("description", self.task_description_font)
        self.save_font_setting("due_date", self.task_due_date_font)
        self.save_font_setting("panel", self.panel_text_font)
        
        # Save the font family setting
        self.settings.set_setting("font_family", default_family)
        
        # Update preview
        if hasattr(self, 'task_preview'):
            self.task_preview.update_preview()
        
        debug.debug(f"All fonts reset to {default_family}")
 
    @debug_method
    def open_font_dialog(self, font_type):
        """Open Qt's own font dialog with current font pre-selected"""
        debug.debug(f"Opening Qt font dialog for {font_type}")
        
        # Get current font based on type
        if font_type == "title":
            current_font = self.task_title_font
            preview_label = self.title_preview
        elif font_type == "description":
            current_font = self.task_description_font
            preview_label = self.desc_preview
        elif font_type == "due_date":
            current_font = self.task_due_date_font
            preview_label = self.date_preview
        elif font_type == "panel":
            current_font = self.panel_text_font
            preview_label = self.panel_preview
        else:
            debug.warning(f"Unknown font type: {font_type}")
            return
        
        debug.debug(f"Current font for {font_type}: {current_font.family()}, size={current_font.pointSize()}, bold={current_font.bold()}")
        
        # Create dialog with current font pre-selected and DontUseNativeDialog option
        dialog = QFontDialog(current_font, self)
        dialog.setOption(QFontDialog.FontDialogOption.DontUseNativeDialog)
        dialog.setWindowTitle(f"Choose {font_type.replace('_', ' ').title()} Font")
        
        # Explicitly set the current font to ensure it's selected
        dialog.setCurrentFont(current_font)
        debug.debug(f"Pre-selected font in dialog: {current_font.family()}")
        
        if dialog.exec():
            font = dialog.selectedFont()
            debug.debug(f"User selected font: {font.family()}, size={font.pointSize()}, bold={font.bold()}")
            
            # Update the standard font family to match the selected font family
            self.standard_font_family = font.family()
            
            # Apply the selected font to the appropriate font object
            if font_type == "title":
                self.task_title_font = font
            elif font_type == "description":
                self.task_description_font = font
            elif font_type == "due_date":
                self.task_due_date_font = font
            elif font_type == "panel":
                self.panel_text_font = font
            
            # Update preview label
            preview_label.setFont(font)
            
            # Save the font settings
            self.save_font_setting(font_type, font)
            
            # Update preview
            if hasattr(self, 'task_preview'):
                self.task_preview.update_preview()
            
            debug.debug(f"Font updated for {font_type}: family={font.family()}, size={font.pointSize()}, bold={font.bold()}, italic={font.italic()}")
        else:
            debug.debug(f"Font dialog cancelled for {font_type}")
 
    @debug_method
    def load_font_settings(self, font_type, font_obj, preview_label):
        """Load font settings for a specific font type"""
        debug.debug(f"Loading font settings for {font_type}")
        
        # Load font properties from settings, including element-specific font family
        # Try element-specific font family first, then fall back to global, then to standard
        font_family = self.settings.get_setting(f"{font_type}_font_family", 
                                                self.settings.get_setting("font_family", self.standard_font_family))
        size = self.settings.get_setting(f"{font_type}_font_size", font_obj.pointSize())
        bold = self.settings.get_setting(f"{font_type}_font_bold", font_obj.bold())
        italic = self.settings.get_setting(f"{font_type}_font_italic", font_obj.italic())
        underline = self.settings.get_setting(f"{font_type}_font_underline", font_obj.underline())
        
        debug.debug(f"Font settings for {font_type}: family={font_family}, size={size}, bold={bold}, italic={italic}, underline={underline}")
        
        # Apply settings to font object
        font_obj.setFamily(font_family)
        font_obj.setPointSize(size)
        font_obj.setBold(bold)
        font_obj.setItalic(italic)
        font_obj.setUnderline(underline)
        
        # Update preview label
        preview_label.setFont(font_obj)
        
        # IMPORTANT: Also save the font settings to ensure consistency
        self.settings.set_setting(f"{font_type}_font_family", font_family)
        self.settings.set_setting(f"{font_type}_font_size", size)
        self.settings.set_setting(f"{font_type}_font_bold", bold)
        self.settings.set_setting(f"{font_type}_font_italic", italic)
        self.settings.set_setting(f"{font_type}_font_underline", underline)

    @debug_method
    def save_font_setting(self, font_type, font):
        """Save individual font settings to the settings manager"""
        debug.debug(f"Saving font settings for {font_type}")
        
        # Save element-specific font family and all font properties
        self.settings.set_setting(f"{font_type}_font_family", font.family())
        self.settings.set_setting(f"{font_type}_font_size", font.pointSize())
        self.settings.set_setting(f"{font_type}_font_bold", font.bold())
        self.settings.set_setting(f"{font_type}_font_italic", font.italic())
        self.settings.set_setting(f"{font_type}_font_underline", font.underline())
        
        # Also update the global font_family setting for backward compatibility
        self.settings.set_setting("font_family", font.family())
        
        debug.debug(f"Saved {font_type} font: family={font.family()}, size={font.pointSize()}, bold={font.bold()}, italic={font.italic()}, underline={font.underline()}")

    def _setup_pill_background_colors(self, parent_layout):
        """Set up the pill background colors section with main pill background"""
        debug.debug("Setting up pill background colors section")
        
        # Create all color buttons and hex fields including main pill background
        self.main_pill_bg_color_btn = QPushButton()
        self.main_pill_bg_color_hex = QLineEdit("#f5f5f5")  # Light gray default
        self.files_bg_color_btn = QPushButton()
        self.files_bg_color_hex = QLineEdit("#E8F4FD")  # Light blue default
        self.links_bg_color_btn = QPushButton()
        self.links_bg_color_hex = QLineEdit("#FFF2E8")  # Light orange default
        self.due_date_bg_color_btn = QPushButton()
        self.due_date_bg_color_hex = QLineEdit("#E1F5FE")  # Light blue default
        
        # Configure all buttons with the colorPicker property
        for btn, color in [
            (self.main_pill_bg_color_btn, "#f5f5f5"),
            (self.files_bg_color_btn, "#E8F4FD"),
            (self.links_bg_color_btn, "#FFF2E8"),
            (self.due_date_bg_color_btn, "#E1F5FE")
        ]:
            btn.setProperty("colorPicker", True)
            btn.setStyleSheet(f"background-color: {color};")
        
        # Configure hex fields
        for hex_field in [self.main_pill_bg_color_hex, self.files_bg_color_hex, self.links_bg_color_hex, self.due_date_bg_color_hex]:
            hex_field.setFixedWidth(80)
        
        # Connect signals for main pill background
        self.main_pill_bg_color_btn.clicked.connect(lambda: self.pick_color_and_update_preview("main_pill_background"))
        self.main_pill_bg_color_hex.textChanged.connect(lambda: self.update_color_and_preview("main_pill_background"))
        
        # Connect signals for other backgrounds
        self.files_bg_color_btn.clicked.connect(lambda: self.pick_color_and_update_preview("files_background"))
        self.links_bg_color_btn.clicked.connect(lambda: self.pick_color_and_update_preview("links_background"))
        self.due_date_bg_color_btn.clicked.connect(lambda: self.pick_color_and_update_preview("due_date_background"))

        self.files_bg_color_hex.textChanged.connect(lambda: self.update_color_and_preview("files_background"))
        self.links_bg_color_hex.textChanged.connect(lambda: self.update_color_and_preview("links_background"))
        self.due_date_bg_color_hex.textChanged.connect(lambda: self.update_color_and_preview("due_date_background"))

        # Create the group
        pill_bg_colors_group = QGroupBox("Pill Background Colors")
        pill_bg_colors_layout = QHBoxLayout()
        
        # Main pill background color layout
        main_pill_bg_layout = QVBoxLayout()
        main_pill_bg_layout.addWidget(QLabel("Main Pill Background:"))
        main_pill_bg_color_row = QHBoxLayout()
        main_pill_bg_color_row.addWidget(self.main_pill_bg_color_btn)
        main_pill_bg_color_row.addWidget(self.main_pill_bg_color_hex)
        main_pill_bg_color_row.addStretch()
        main_pill_bg_layout.addLayout(main_pill_bg_color_row)
        
        # Files background color layout
        files_bg_layout = QVBoxLayout()
        files_bg_layout.addWidget(QLabel("Files Background:"))
        files_bg_color_row = QHBoxLayout()
        files_bg_color_row.addWidget(self.files_bg_color_btn)
        files_bg_color_row.addWidget(self.files_bg_color_hex)
        files_bg_color_row.addStretch()
        files_bg_layout.addLayout(files_bg_color_row)
        
        # Links background color layout
        links_bg_layout = QVBoxLayout()
        links_bg_layout.addWidget(QLabel("Links Background:"))
        links_bg_color_row = QHBoxLayout()
        links_bg_color_row.addWidget(self.links_bg_color_btn)
        links_bg_color_row.addWidget(self.links_bg_color_hex)
        links_bg_color_row.addStretch()
        links_bg_layout.addLayout(links_bg_color_row)
        
        # Due Date background color layout
        due_date_bg_layout = QVBoxLayout()
        due_date_bg_layout.addWidget(QLabel("Due Date Background:"))
        due_date_bg_color_row = QHBoxLayout()
        due_date_bg_color_row.addWidget(self.due_date_bg_color_btn)
        due_date_bg_color_row.addWidget(self.due_date_bg_color_hex)
        due_date_bg_color_row.addStretch()
        due_date_bg_layout.addLayout(due_date_bg_color_row)
        
        # Add background color layouts to row
        pill_bg_colors_layout.addLayout(main_pill_bg_layout)
        pill_bg_colors_layout.addLayout(files_bg_layout)
        pill_bg_colors_layout.addLayout(links_bg_layout)
        pill_bg_colors_layout.addLayout(due_date_bg_layout)
        pill_bg_colors_layout.addStretch()  # Push to left
        
        pill_bg_colors_group.setLayout(pill_bg_colors_layout)
        parent_layout.addWidget(pill_bg_colors_group)
        
        debug.debug("Pill background colors section setup complete")

    @debug_method
    def _setup_keyboard_shortcuts_section(self, parent_layout):
        """Set up the keyboard shortcuts section"""
        debug.debug("Setting up keyboard shortcuts section")
        
        # Create keyboard shortcuts group
        shortcuts_group = QGroupBox("Keyboard Shortcuts")
        shortcuts_layout = QVBoxLayout(shortcuts_group)
        
        # Create a form layout for shortcuts
        shortcuts_form = QFormLayout()
        shortcuts_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
        # Define shortcuts with their descriptions
        shortcuts_data = [
            ("Ctrl+N", "Add New Task"),
            ("Ctrl+E", "Edit Selected Task"),
            ("Ctrl+S", "Open Settings"),
            ("Ctrl+I", "Import from CSV"),
            ("Ctrl+X", "Export to CSV"),
            ("Ctrl+1", "Switch to Current Tasks Tab"),
            ("Ctrl+2", "Switch to Backlog Tab"),
            ("Ctrl+3", "Switch to Completed Tasks Tab"),
            ("Del", "Delete Selected Task"),
            ("F5", "Refresh Task List"),
            ("Esc", "Close Current Dialog")
        ]
        
        # Add shortcuts to form
        for shortcut, description in shortcuts_data:
            shortcut_label = QLabel(shortcut)
            shortcut_label.setStyleSheet("font-family: 'Courier New', monospace; font-weight: bold; background-color: #f0f0f0; padding: 2px 6px; border: 1px solid #ccc; border-radius: 3px;")
            shortcut_label.setFixedWidth(80)
            
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            
            shortcuts_form.addRow(shortcut_label, desc_label)
        
        shortcuts_layout.addLayout(shortcuts_form)
        
        # Add note about customization
        note_label = QLabel("Note: Keyboard shortcuts are currently not customizable and use standard system conventions.")
        note_label.setStyleSheet("color: #666; font-style: italic; font-size: 10px;")
        note_label.setWordWrap(True)
        shortcuts_layout.addWidget(note_label)
        
        # Add stretch to push content to top
        shortcuts_layout.addStretch()
        
        parent_layout.addWidget(shortcuts_group)
        debug.debug("Keyboard shortcuts section setup complete")
        
    @debug_method
    def _setup_panel_layout(self, parent_layout):
        """Set up the panel layout section with auto-sized dropdowns (no auto-adjust checkbox)"""
        debug.debug("Setting up panel layout section")
        panel_layout_group = QGroupBox("Task Pill Layout")
        main_layout = QHBoxLayout()
        
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
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
            combo.setFixedHeight(30)
        
        # Connect combo box signals to update preview directly
        self.top_left_combo.currentTextChanged.connect(self.force_preview_update)
        self.bottom_left_combo.currentTextChanged.connect(self.force_preview_update)
        self.top_right_combo.currentTextChanged.connect(self.force_preview_update)
        self.bottom_right_combo.currentTextChanged.connect(self.force_preview_update)
            
        # Left Panel Configuration using QFormLayout like the dialogs
        left_panel_layout = QFormLayout()
        left_panel_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        left_panel_layout.addRow("Top Left:", self.top_left_combo)
        left_panel_layout.addRow("Bottom Left:", self.bottom_left_combo)
        
        # Right Panel Configuration using QFormLayout like the dialogs
        right_panel_layout = QFormLayout()
        right_panel_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        right_panel_layout.addRow("Top Right:", self.top_right_combo)
        right_panel_layout.addRow("Bottom Right:", self.bottom_right_combo)
        
        # Create containers for the form layouts
        left_widget = QWidget()
        left_widget.setLayout(left_panel_layout)
        
        right_widget = QWidget()
        right_widget.setLayout(right_panel_layout)
        
        # Add both panel configurations to the main layout
        main_layout.addWidget(left_widget)
        main_layout.addWidget(right_widget)
        
        panel_layout_group.setLayout(main_layout)
        parent_layout.addWidget(panel_layout_group)
        debug.debug("Panel layout section setup complete (without auto-adjust checkbox)")

    @debug_method
    def force_preview_update(self, check=False):
        """Force a direct update of the preview when panel dropdowns change (no font colors)"""
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
        
        # Set auto text color to always be enabled
        self.settings.set_setting("auto_panel_text_color", True)
        
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
        """Set up the preview section with reduced spacing"""
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
        
        # Reduce margins and spacing to minimize empty space
        preview_layout.setContentsMargins(10, 10, 10, 5)  # Reduced bottom margin
        preview_layout.setSpacing(3)  # Reduced spacing
        
        # Set a fixed height for the preview to prevent excessive space
        preview_group.setMaximumHeight(250)  # Limit the height
        
        parent_layout.addWidget(preview_group)
        debug.debug("Preview section setup complete")
        
    @debug_method
    def _setup_header_section(self, parent_layout):
        """Set up the header section with top buttons"""
        debug.debug("Setting up header section")
        # Top Save/Cancel buttons
        top_button_layout = QHBoxLayout()
        save_btn_top = QPushButton("Save Settings")
        save_btn_top.setFixedHeight(30)
        save_btn_top.setMinimumWidth(120)  # Set a consistent minimum width
        save_btn_top.clicked.connect(self.save_settings)
        save_btn_top.setProperty("primary", True)  # Add the primary property
        save_btn_top.setDefault(True)

        cancel_btn_top = QPushButton("Cancel")
        cancel_btn_top.setFixedHeight(30)
        cancel_btn_top.setMinimumWidth(120)  # Set a consistent minimum width
        cancel_btn_top.setProperty("secondary", True)  # Add the secondary property
        cancel_btn_top.clicked.connect(self.main_window.show_task_view)

        # Add buttons to the top_button_layout
        top_button_layout.addWidget(save_btn_top)
        top_button_layout.addWidget(cancel_btn_top)
        top_button_layout.addStretch()  # This pushes buttons to the left
        
        parent_layout.addLayout(top_button_layout)
        debug.debug("Header section setup complete")

    @debug_method
    def _setup_bottom_buttons(self, parent_layout):
        """Set up the bottom button section (left-aligned)"""
        debug.debug("Setting up bottom buttons")
        
        # Add Save and Cancel buttons at the bottom
        bottom_button_layout = QHBoxLayout()
        save_button = QPushButton("Save Settings")
        save_button.setFixedHeight(30)
        save_button.setMinimumWidth(120)
        save_button.clicked.connect(self.save_settings)
        save_button.setProperty("primary", True)  # Add the primary property
        save_button.setDefault(True)

        cancel_button = QPushButton("Cancel")
        cancel_button.setFixedHeight(30)
        cancel_button.setMinimumWidth(120)
        cancel_button.clicked.connect(self.main_window.show_task_view)
        cancel_button.setProperty("secondary", True)  # Add the secondary property
        
        bottom_button_layout.addWidget(save_button)
        bottom_button_layout.addWidget(cancel_button)
        bottom_button_layout.addStretch()
        
        parent_layout.addLayout(bottom_button_layout)
        debug.debug("Bottom buttons setup complete")

    def pick_color_and_update_preview(self, color_type):
        """Open color picker and update preview"""
        debug.debug(f"Opening color picker for {color_type}")
        
        try:
            if color_type == "main_pill_background":
                hex_field = self.main_pill_bg_color_hex
            elif color_type == "files_background":
                hex_field = self.files_bg_color_hex
            elif color_type == "links_background":
                hex_field = self.links_bg_color_hex
            elif color_type == "due_date_background":
                hex_field = self.due_date_bg_color_hex
            else:
                debug.debug(f"Unknown color type: {color_type}")
                return
            
            current_color = QColor(hex_field.text())
            color = QColorDialog.getColor(current_color, self, f"Choose {color_type.replace('_', ' ').title()} Color")
            
            if color.isValid():
                hex_color = color.name()
                hex_field.setText(hex_color)
                debug.debug(f"Color picked for {color_type}: {hex_color}")
                
        except Exception as e:
            debug.debug(f"Error picking color for {color_type}: {e}")
            
    @debug_method
    def pick_color(self, color_type):
        """Open color picker dialog for the specified color type"""
        debug.debug(f"Opening color picker for {color_type}")
        color_btn = None
        color_hex = None
        
        if color_type == "files_background":
            color_btn = self.files_bg_color_btn
            color_hex = self.files_bg_color_hex
        elif color_type == "links_background":
            color_btn = self.links_bg_color_btn
            color_hex = self.links_bg_color_hex
        elif color_type == "due_date_background":
            color_btn = self.due_date_bg_color_btn
            color_hex = self.due_date_bg_color_hex
        
        if color_btn and color_hex:
            current_color = QColor(color_hex.text())
            color = QColorDialog.getColor(current_color, self)
            
            if color.isValid():
                hex_color = color.name()
                debug.debug(f"Selected color for {color_type}: {hex_color}")
                
                # Only set background color - let OS style manager handle size/borders
                color_btn.setStyleSheet(f"background-color: {hex_color};")
                color_hex.setText(hex_color)
            else:
                debug.debug(f"Color selection cancelled for {color_type}")

    def update_color_and_preview(self, color_type):
        """Update color button and refresh preview with settings save"""
        debug.debug(f"Updating color and preview for {color_type}")
        self.update_color_from_hex(color_type)
        
        # Save the color setting immediately
        if color_type == "main_pill_background":
            self.settings.set_setting("main_pill_background_color", self.main_pill_bg_color_hex.text())
        elif color_type == "files_background":
            self.settings.set_setting("files_background_color", self.files_bg_color_hex.text())
        elif color_type == "links_background":
            self.settings.set_setting("links_background_color", self.links_bg_color_hex.text())
        elif color_type == "due_date_background":
            self.settings.set_setting("due_date_background_color", self.due_date_bg_color_hex.text())
        
        # Force settings to save to disk
        self.settings.save_settings(self.settings.settings)
        
        if hasattr(self, 'task_preview'):
            self.task_preview.update_preview()
            
    def update_color_from_hex(self, color_type):
        """Update color button from hex field value"""
        debug.debug(f"Updating {color_type} color from hex field")
        
        try:
            if color_type == "main_pill_background":
                hex_field = self.main_pill_bg_color_hex
                btn = self.main_pill_bg_color_btn
            elif color_type == "files_background":
                hex_field = self.files_bg_color_hex
                btn = self.files_bg_color_btn
            elif color_type == "links_background":
                hex_field = self.links_bg_color_hex
                btn = self.links_bg_color_btn
            elif color_type == "due_date_background":
                hex_field = self.due_date_bg_color_hex
                btn = self.due_date_bg_color_btn
            else:
                debug.debug(f"Unknown color type: {color_type}")
                return
                
            hex_color = hex_field.text()
            if QColor.isValidColor(hex_color):
                btn.setStyleSheet(f"background-color: {hex_color};")
                debug.debug(f"Updated {color_type} button color to {hex_color}")
            else:
                debug.debug(f"Invalid hex color for {color_type}: {hex_color}")
                
        except Exception as e:
            debug.debug(f"Error updating {color_type} color from hex: {e}")

    @debug_method
    def save_color_setting(self, color_type):
        """Save a specific color setting immediately"""
        debug.debug(f"Saving color setting for {color_type}")
        
        if color_type == "files_background":
            color_value = self.files_bg_color_hex.text()
            self.settings.set_setting("files_background_color", color_value)
        elif color_type == "links_background":
            color_value = self.links_bg_color_hex.text()
            self.settings.set_setting("links_background_color", color_value)
        elif color_type == "due_date_background":
            color_value = self.due_date_bg_color_hex.text()
            self.settings.set_setting("due_date_background_color", color_value)
        
        debug.debug(f"Saved {color_type} = {color_value}")
        
        # Force settings to save to disk
        self.settings.save_settings(self.settings.settings)

    @debug_method
    def load_current_settings(self):
        """Load current settings from settings manager (with main pill background)"""
        debug.debug("Loading current settings from settings manager")
        
        # Block signals during loading to prevent multiple preview updates
        with QSignalBlocker(self.top_left_combo), \
            QSignalBlocker(self.bottom_left_combo), \
            QSignalBlocker(self.top_right_combo), \
            QSignalBlocker(self.bottom_right_combo):
            
            # Font family
            font_family = self.settings.get_setting("font_family", "Arial")
            debug.debug(f"Loaded font family: {font_family}")
            
            # Update standard font family
            self.standard_font_family = font_family
            
            # Load individual font settings (no colors)
            self.load_font_settings("title", self.task_title_font, self.title_preview)
            self.load_font_settings("description", self.task_description_font, self.desc_preview)
            self.load_font_settings("due_date", self.task_due_date_font, self.date_preview)
            self.load_font_settings("panel", self.panel_text_font, self.panel_preview)
            
            # Load panel layout settings
            left_contents = self.settings.get_setting("left_panel_contents", ["Category", "Status"])
            right_contents = self.settings.get_setting("right_panel_contents", ["Link", "Due Date"])
            
            # Convert special placeholder back to empty selections
            if left_contents == ["__NONE__"]:
                left_contents = []
            if right_contents == ["__NONE__"]:
                right_contents = []
            
            debug.debug(f"Loaded panel contents - Left: {left_contents}, Right: {right_contents}")
            
            # Set combo box selections
            self.top_left_combo.setCurrentText(left_contents[0] if len(left_contents) > 0 else "None")
            self.bottom_left_combo.setCurrentText(left_contents[1] if len(left_contents) > 1 else "None")
            self.top_right_combo.setCurrentText(right_contents[0] if len(right_contents) > 0 else "None")
            self.bottom_right_combo.setCurrentText(right_contents[1] if len(right_contents) > 1 else "None")
            
            # Load background colors INCLUDING main pill background
            self.main_pill_bg_color_hex.setText(self.settings.get_setting("main_pill_background_color", "#f5f5f5"))
            self.files_bg_color_hex.setText(self.settings.get_setting("files_background_color", "#E8F4FD"))
            self.links_bg_color_hex.setText(self.settings.get_setting("links_background_color", "#FFF2E8"))
            self.due_date_bg_color_hex.setText(self.settings.get_setting("due_date_background_color", "#E1F5FE"))
            
            # Update background color buttons
            self.update_color_from_hex("main_pill_background")
            self.update_color_from_hex("files_background")
            self.update_color_from_hex("links_background")
            self.update_color_from_hex("due_date_background")
            
            debug.debug("All settings loaded successfully")
            
    def save_settings(self, checked=False):
        """Save all display settings to the settings manager and return to main task view"""
        debug.debug("Saving all display settings")
        
        # Save font family
        self.settings.set_setting("font_family", self.standard_font_family)
        
        # Save font settings for each element (no colors)
        self.save_font_setting("title", self.task_title_font)
        self.save_font_setting("description", self.task_description_font)
        self.save_font_setting("due_date", self.task_due_date_font)
        self.save_font_setting("panel", self.panel_text_font)
        
        # Save main pill background color and other background colors
        self.settings.set_setting("main_pill_background_color", self.main_pill_bg_color_hex.text())
        self.settings.set_setting("files_background_color", self.files_bg_color_hex.text())
        self.settings.set_setting("links_background_color", self.links_bg_color_hex.text())
        self.settings.set_setting("due_date_background_color", self.due_date_bg_color_hex.text())
        
        # Save panel layout settings
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
        
        debug.debug(f"Saving panel contents - Left: {left_final}, Right: {right_final}")
        
        self.settings.set_setting("left_panel_contents", left_final)
        self.settings.set_setting("right_panel_contents", right_final)
        
        debug.debug("Display settings saved successfully")
        
        # Return to main task view
        debug.debug("Returning to main task view")
        self.main_window.show_task_view()
        
    @debug_method
    def save_font_color_setting(self, font_type, color):
        """Save a specific font color setting immediately"""
        debug.debug(f"Saving font color setting for {font_type}: {color}")
        
        # Save to settings based on the naming convention used in task_pill_delegate.py
        if font_type == "panel":
            # Save panel text color with the correct key
            self.settings.set_setting("panel_color", color)
        else:
            self.settings.set_setting(f"{font_type}_color", color)
        
        debug.debug(f"Saved {font_type}_color = {color}")
        
        # Force settings to save to disk
        self.settings.save_settings(self.settings.settings)

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
    def pick_font_color(self, font_type):
        """Open color picker dialog for the specified font color"""
        debug.debug(f"Opening color picker for {font_type} font color")
        color_btn = None
        color_hex = None
        
        if font_type == "title":
            color_btn = self.title_color_btn
            color_hex = self.title_color_hex
        elif font_type == "description":
            color_btn = self.desc_color_btn
            color_hex = self.desc_color_hex
        elif font_type == "due_date":
            color_btn = self.date_color_btn
            color_hex = self.date_color_hex
        elif font_type == "panel":
            color_btn = self.panel_color_btn
            color_hex = self.panel_color_hex
        
        if color_btn and color_hex:
            current_color = QColor(color_hex.text())
            color = QColorDialog.getColor(current_color, self)
            
            if color.isValid():
                hex_color = color.name()
                debug.debug(f"Selected color for {font_type} font: {hex_color}")
                
                # Update button and hex field
                color_btn.setStyleSheet(f"background-color: {hex_color};")
                color_hex.setText(hex_color)
                
                # Update preview label color immediately
                self.update_preview_font_color(font_type, hex_color)
                
                # Save the color setting
                self.save_font_color_setting(font_type, hex_color)
            else:
                debug.debug(f"Font color selection cancelled for {font_type}")

    @debug_method
    def update_font_color_from_hex(self, font_type):
        """Update font color button and preview when hex value changes"""
        debug.debug(f"Updating font color from hex value for {font_type}")
        color_btn = None
        color_hex = None
        
        if font_type == "title":
            color_btn = self.title_color_btn
            color_hex = self.title_color_hex
        elif font_type == "description":
            color_btn = self.desc_color_btn
            color_hex = self.desc_color_hex
        elif font_type == "due_date":
            color_btn = self.date_color_btn
            color_hex = self.date_color_hex
        elif font_type == "panel":
            color_btn = self.panel_color_btn
            color_hex = self.panel_color_hex
        
        if color_btn and color_hex:
            hex_value = color_hex.text()
            debug.debug(f"New hex value: {hex_value}")
            
            if hex_value.startswith("#") and len(hex_value) == 7:
                try:
                    QColor(hex_value)  # Test if valid color
                    
                    # Update button color
                    color_btn.setStyleSheet(f"background-color: {hex_value};")
                    
                    # Update preview label color
                    self.update_preview_font_color(font_type, hex_value)
                    
                    # Save the color setting
                    self.save_font_color_setting(font_type, hex_value)
                    
                    debug.debug(f"Valid color, updated {font_type} font color")
                except Exception as e:
                    debug.error(f"Invalid color format for {font_type}: {e}")
            else:
                debug.warning(f"Invalid hex format for {font_type}: {hex_value}")

    @debug_method
    def update_preview_font_color(self, font_type, color):
        """Update the preview label's font color"""
        debug.debug(f"Updating preview font color for {font_type} to {color}")
        
        if font_type == "title":
            self.title_preview.setStyleSheet(f"color: {color};")
        elif font_type == "description":
            self.desc_preview.setStyleSheet(f"color: {color};")
        elif font_type == "due_date":
            self.date_preview.setStyleSheet(f"color: {color};")
        elif font_type == "panel":
            self.panel_preview.setStyleSheet(f"color: {color};")
        
        # Force preview update if it exists
        if hasattr(self, 'task_preview'):
            self.task_preview.update_preview()

    @debug_method
    def save_font_color_setting(self, font_type, color):
        """Save a specific font color setting immediately"""
        debug.debug(f"Saving font color setting for {font_type}: {color}")
        
        # Save to settings based on the naming convention used in task_pill_delegate.py
        self.settings.set_setting(f"{font_type}_color", color)
        
        debug.debug(f"Saved {font_type}_color = {color}")
        
        # Force settings to save to disk
        self.settings.save_settings(self.settings.settings)

    @debug_method
    def load_font_color_settings(self):
        """Load font color settings from the settings manager"""
        debug.debug("Loading font color settings")
        
        # Load colors for each font type
        title_color = self.settings.get_setting("title_color", "#333333")
        desc_color = self.settings.get_setting("description_color", "#666666")
        date_color = self.settings.get_setting("due_date_color", "#888888")
        panel_color = self.settings.get_setting("panel_color", "#FFFFFF")  # Changed from "left_panel_color" to "panel_color"
        
        debug.debug(f"Loaded colors - title: {title_color}, desc: {desc_color}, date: {date_color}, panel: {panel_color}")
        
        # Update hex fields
        self.title_color_hex.setText(title_color)
        self.desc_color_hex.setText(desc_color)
        self.date_color_hex.setText(date_color)
        self.panel_color_hex.setText(panel_color)
        
        # Update color buttons
        self.title_color_btn.setStyleSheet(f"background-color: {title_color};")
        self.desc_color_btn.setStyleSheet(f"background-color: {desc_color};")
        self.date_color_btn.setStyleSheet(f"background-color: {date_color};")
        self.panel_color_btn.setStyleSheet(f"background-color: {panel_color};")
        
        # Update preview label colors
        self.title_preview.setStyleSheet(f"color: {title_color};")
        self.desc_preview.setStyleSheet(f"color: {desc_color};")
        self.date_preview.setStyleSheet(f"color: {date_color};")
        self.panel_preview.setStyleSheet(f"color: {panel_color};")