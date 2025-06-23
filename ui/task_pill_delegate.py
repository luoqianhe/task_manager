# src/ui/task_pill_delegate.py

from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QApplication, QStyle
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QBrush, QPen, QFont, QFontMetrics
from PyQt6.QtCore import QRectF, Qt, QSize, QPoint, QPointF
from datetime import datetime, date
import sqlite3
from pathlib import Path
from ui.os_style_manager import OSStyleManager

# Import the debug logger
from utils.debug_logger import get_debug_logger
from utils.debug_decorator import debug_method
debug = get_debug_logger()

class TaskPillDelegate(QStyledItemDelegate):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        debug.debug("Getting database connection from overridden method")
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Initialize attributes
        self.text_padding = 10
        
        # Get the OS style manager if available
        app = QApplication.instance()
        self.os_style = None
        if app.property("style_manager"):
            self.os_style = app.property("style_manager").current_style
            debug.debug(f"Task pill delegate using OS style: {self.os_style}")
            
            # Adjust sizes based on OS
            if self.os_style == "macOS":
                self.pill_height = 80
                self.pill_radius = 15
            elif self.os_style == "Windows":
                self.pill_height = 70
                self.pill_radius = 4  # Much less rounded for Windows
            else:  # Linux
                self.pill_height = 75
                self.pill_radius = 8  # Medium roundness for Linux
        else:
            # Default values if no OS style manager
            self.pill_height = 80
            self.pill_radius = 10
        
        # Calculate compact height dynamically based on title font size
        self.compact_height = self._calculate_compact_height()
        debug.debug(f"Calculated compact height: {self.compact_height}")
        
        self.item_margin = 5
        
        settings = self.get_settings_manager()
        # Load panel settings from SettingsManager
        settings = self.get_settings_manager()
        self.left_section_width = settings.get_setting("left_panel_width", 100)
        self.right_section_width = settings.get_setting("right_panel_width", 100)

        # Fixed section count for both panels (2)
        self.left_panel_count = 2
        self.right_panel_count = 2

        # Check for special "__NONE__" placeholder in panel contents
        left_contents = settings.get_setting("left_panel_contents", ["Category", "Status"])
        if left_contents == ["__NONE__"]:
            self.left_panel_contents = []  # Use empty list for display
        else:
            self.left_panel_contents = left_contents

        right_contents = settings.get_setting("right_panel_contents", ["Link", "Due Date"])
        if right_contents == ["__NONE__"]:
            self.right_panel_contents = []  # Use empty list for display
        else:
            self.right_panel_contents = right_contents

        debug.debug(f"Panel contents initialized: left={self.left_panel_contents}, right={self.right_panel_contents}")
        
        # Hover tracking
        self.hover_item = None
        self.toggle_button_rect = None
        self.all_button_rects = {}
        
        # Track compact states
        self.compact_items = set()
        self.load_compact_states()
        
        # Install event filter on parent widget's viewport
        if parent:
            try:
                debug.debug("Setting up mouse tracking and event filter")
                parent.setMouseTracking(True)
                
                # Check if parent has viewport method before using it
                if hasattr(parent, 'viewport') and callable(parent.viewport):
                    parent.viewport().setMouseTracking(True)
                    parent.viewport().installEventFilter(self)
                    debug.debug("Event filter installed on parent viewport")
                
                # Install event filter on parent
                parent.installEventFilter(self)
                debug.debug("Event filter installed on parent")
            except Exception as e:
                debug.error(f"Error setting up event filters: {e}")
             
    def _get_section_data(self, user_data, section_type):
        """Get data for a specific section type"""
        debug.debug(f"Getting section data for type: {section_type}")
        
        if section_type == "Category":
            return user_data.get('category', '')
        elif section_type == "Status":
            return user_data.get('status', 'Not Started')
        elif section_type == "Priority":
            return user_data.get('priority', '')
        elif section_type == "Due Date":
            return user_data.get('due_date', '')
        elif section_type == "Link":
            # Check for links
            links = user_data.get('links', [])
            if links and isinstance(links, list) and len(links) > 0:
                links_count = len(links)
                result = f"Links ({links_count})" if links_count > 1 else "Link"
                return result
            return "No Link"
        elif section_type == "Files":  # New section type for files
            # Check for file attachments
            files = user_data.get('files', [])
            if files and isinstance(files, list) and len(files) > 0:
                files_count = len(files)
                result = f"Files ({files_count})" if files_count > 1 else "File"
                return result
            return "No Files"
        elif section_type == "Completion Date":
            return user_data.get('completed_at', '')
        elif section_type == "Progress":
            # Could be enhanced to show actual progress if tracked
            status = user_data.get('status', 'Not Started')
            if status == 'Not Started':
                return "0%"
            elif status == 'In Progress':
                return "50%"
            elif status == 'Completed':
                return "100%"
            else:
                return ""
        elif section_type == "Tag":
            # Future enhancement for tags
            return user_data.get('tag', '')
        else:
            return ""

    def load_compact_states(self):
        """Load compact states from the database"""
        debug.debug("Loading compact states from database")
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First check if the is_compact column exists in the tasks table
                try:
                    debug.debug("Checking if is_compact column exists")
                    cursor.execute("SELECT is_compact FROM tasks LIMIT 1")
                except sqlite3.OperationalError:
                    # Column doesn't exist, need to add it
                    debug.debug("is_compact column doesn't exist, adding it")
                    cursor.execute("ALTER TABLE tasks ADD COLUMN is_compact INTEGER NOT NULL DEFAULT 0")
                    conn.commit()
                
                # Now load all task IDs that are marked as compact
                debug.debug("Loading compact task IDs")
                cursor.execute("SELECT id FROM tasks WHERE is_compact = 1")
                for row in cursor.fetchall():
                    self.compact_items.add(row[0])
                
                debug.debug(f"Loaded {len(self.compact_items)} compact states from database")
        except Exception as e:
            debug.error(f"Error loading compact states: {e}")
    
    def paint(self, painter, option, index):
        debug.debug(f"Painting item at index {index.row()}")
        # Get data from the index
        user_data = index.data(Qt.ItemDataRole.UserRole)
        
        # Check if this is a priority header
        if isinstance(user_data, dict) and user_data.get('is_priority_header', False):
            debug.debug("Drawing priority header")
            self._draw_priority_header(painter, option, index, user_data)
        else:
            # Regular task item
            debug.debug("Drawing regular task item")
            self._draw_task_item(painter, option, index)

    def _draw_task_item(self, painter, option, index):
        """Draw a regular task item - modified to support customizable panels"""
        debug.debug(f"Drawing task item at index {index.row()}")
        
        # Extract data using our existing method
        user_data, item_id, title, description, link, status, priority, due_date_str, category = self._extract_item_data(index)
        
        # Check if compact
        is_compact = item_id in self.compact_items
        debug.debug(f"Task {item_id} compact state: {is_compact}")
        
        # Save painter state and prepare to draw
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate pill rect and create path
        rect, path = self._create_pill_path(option)
        
        # Draw selection highlight if needed
        if option.state & QStyle.StateFlag.State_Selected:
            debug.debug("Drawing selection highlight")
            self._draw_selection_highlight(painter, path)
        
        # Draw the main pill background
        self._draw_pill_background(painter, path)
        
        # Calculate widths for left and right panels
        left_width = self.left_section_width if self.left_panel_contents else 0
        right_width = self.right_section_width if self.right_panel_contents else 0
        
        # Draw left panel if content is configured
        if left_width > 0 and self.left_panel_contents:
            debug.debug(f"Drawing left panel with content: {self.left_panel_contents}")
            self._draw_custom_panel(painter, path, rect, is_compact, 
                                   self.left_panel_contents, 
                                   user_data, left_width, "left")
        
        # Draw right panel if content is configured
        if right_width > 0 and self.right_panel_contents:
            debug.debug(f"Drawing right panel with content: {self.right_panel_contents}")
            self._draw_custom_panel(painter, path, rect, is_compact, 
                                   self.right_panel_contents, 
                                   user_data, right_width, "right")
        
        # Draw content (title, description, due date)
        self._draw_task_content(painter, rect, is_compact, title, description, due_date_str, item_id, left_width, right_width)
        
        # Draw toggle button if needed
        self._draw_toggle_button(painter, index, item_id, rect)
        
        # Restore painter
        painter.restore()

    def save_compact_state(self, task_id, is_compact):
        """Save compact state to the database"""
        debug.debug(f"Saving compact state for task {task_id}: {is_compact}")
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE tasks SET is_compact = ? WHERE id = ?",
                    (1 if is_compact else 0, task_id)
                )
                conn.commit()
                debug.debug("Compact state saved successfully")
        except Exception as e:
            debug.error(f"Error saving compact state: {e}")

    def eventFilter(self, source, event):
        """Handle mouse events for hover detection, button clicks, and tooltips"""
        # Check if we're handling a tree widget or its viewport
        is_tree_widget = hasattr(source, 'indexAt')
        is_viewport = hasattr(source, 'parent') and hasattr(source.parent(), 'indexAt')
        
        # Handle mouse movement for hover effects AND tooltips
        if event.type() == event.Type.MouseMove:
            # Get position and find item under cursor
            if hasattr(event, 'position'):
                pos = event.position().toPoint()
            elif hasattr(event, 'pos'):
                pos = event.pos()
            else:
                return super().eventFilter(source, event)
            
            # Get the tree widget and adjust position if needed
            tree_widget = None
            if is_tree_widget:
                tree_widget = source
            elif is_viewport:
                tree_widget = source.parent()
            else:
                return super().eventFilter(source, event)
            
            # Find item at position
            index = tree_widget.indexAt(pos)
            if index.isValid():
                # Get item data
                user_data = index.data(Qt.ItemDataRole.UserRole)
                
                # Skip if this is a priority header
                if isinstance(user_data, dict) and user_data.get('is_priority_header', False):
                    tree_widget.setToolTip("")  # Clear any existing tooltip
                    return super().eventFilter(source, event)
                
                # Check if this is a compact task
                item_id = user_data.get('id', 0) if isinstance(user_data, dict) else 0
                is_compact = item_id in self.compact_items
                
                if is_compact and isinstance(user_data, dict):
                    # Get the visual rectangle for this item
                    rect = tree_widget.visualRect(index)
                    
                    # Determine which section the mouse is over
                    hovered_section = self._get_hovered_section(pos, rect, is_compact)
                    
                    if hovered_section and hovered_section != "Title":
                        # Show tooltip for the hovered section
                        tooltip_text = self._get_section_tooltip_text(user_data, hovered_section)
                        tree_widget.setToolTip(tooltip_text)
                        debug.debug(f"Showing tooltip for {hovered_section}: {tooltip_text}")
                    else:
                        # Clear tooltip if hovering over title or outside sections
                        tree_widget.setToolTip("")
                else:
                    # Clear tooltip for non-compact tasks
                    tree_widget.setToolTip("")
                
                # Existing hover button logic
                self.hover_item = index
                rect = tree_widget.visualRect(index)
                self.toggle_button_rect = QRectF(
                    rect.center().x() - 12,
                    rect.top() - 12,
                    24, 24
                )
                tree_widget.viewport().update()
                debug.debug(f"Hover detected at row {index.row()}")
            else:
                # Clear hover state and tooltip if not over an item
                if self.hover_item:
                    self.hover_item = None
                    tree_widget.viewport().update()
                    tree_widget.setToolTip("")  # Clear tooltip
                    debug.debug("Cleared hover state and tooltip")
        
        # Handle mouse clicks for toggle button (existing code)
        elif event.type() == event.Type.MouseButtonPress:
            debug.debug("Mouse button press detected")
            # Get position
            try:
                if hasattr(event, 'position'):
                    pos = event.position().toPoint()
                elif hasattr(event, 'pos'):
                    pos = event.pos()
                else:
                    pos = event.globalPos()
                
                # Create a QPointF from the QPoint coordinates
                pos_f = QPointF(pos.x(), pos.y())
                debug.debug(f"Mouse position: QPoint({pos.x()}, {pos.y()}) converted to QPointF({pos_f.x()}, {pos_f.y()})")
            except Exception as e:
                debug.error(f"Error getting mouse position: {e}")
                return super().eventFilter(source, event)
            
            # Get the tree widget and adjust position if needed
            tree_widget = None
            if is_tree_widget:
                tree_widget = source
            elif is_viewport:
                tree_widget = source.parent()
            else:
                # Not a tree widget or viewport, can't handle
                return super().eventFilter(source, event)
                
            # Check if hover item exists and button is visible
            if self.hover_item and self.toggle_button_rect:
                # Check if click was on the toggle button
                if self.toggle_button_rect.contains(pos_f):
                    debug.debug("Toggle button clicked")
                    
                    # Get the item data to find the ID
                    item_data = self.hover_item.data(Qt.ItemDataRole.UserRole)
                    if isinstance(item_data, dict) and 'id' in item_data:
                        item_id = item_data['id']
                        debug.debug(f"Item ID: {item_id}")
                        
                        # Toggle compact state
                        is_compact = item_id in self.compact_items
                        if is_compact:
                            debug.debug(f"Removing task {item_id} from compact items")
                            self.compact_items.remove(item_id)
                        else:
                            debug.debug(f"Adding task {item_id} to compact items")
                            self.compact_items.add(item_id)
                        
                        # Save state to database
                        self.save_compact_state(item_id, not is_compact)
                        
                        # Get tree widget item
                        item = None
                        if hasattr(tree_widget, 'itemFromIndex'):
                            item = tree_widget.itemFromIndex(self.hover_item)
                        
                        # Update item size if found
                        if item:
                            current_compact_height = self._calculate_compact_height()
                            height = current_compact_height if not is_compact else self.pill_height
                            debug.debug(f"Toggle: item {item_id}, new compact state: {not is_compact}, height: {height}")

                            item.setSizeHint(0, QSize(tree_widget.viewport().width(), height + self.item_margin * 2))
                            debug.debug(f"Updated item {item_id} size hint to height: {height + self.item_margin * 2}")

                            tree_widget.scheduleDelayedItemsLayout()  # Force layout update
                        
                        # Force repaint
                        tree_widget.viewport().update()
                        return True  # Event handled
            
            # Also check the all_button_rects dictionary for clicks (for items not under hover)
            if hasattr(self, 'all_button_rects'):
                for item_id, (button_rect, item_index) in self.all_button_rects.items():
                    if button_rect.contains(pos_f):
                        debug.debug(f"Toggle button clicked for item ID: {item_id}")
                        
                        # Toggle compact state for this item
                        is_compact = item_id in self.compact_items
                        
                        if is_compact:
                            debug.debug(f"Removing task {item_id} from compact items")
                            self.compact_items.remove(item_id)
                        else:
                            debug.debug(f"Adding task {item_id} to compact items")
                            self.compact_items.add(item_id)
                        
                        # Save state to database
                        self.save_compact_state(item_id, not is_compact)
                        
                        # Update the item size
                        item = None
                        if hasattr(tree_widget, 'itemFromIndex'):
                            item = tree_widget.itemFromIndex(item_index)
                        
                        # Update item size if found
                        if item:
                            current_compact_height = self._calculate_compact_height()  
                            height = current_compact_height if not is_compact else self.pill_height
                            debug.debug(f"Toggle: item {item_id}, new compact state: {not is_compact}, height: {height}")

                            # And update the item size setting:
                            item.setSizeHint(0, QSize(tree_widget.viewport().width(), 
                                            height + self.item_margin * 2))
                            debug.debug(f"Updated item {item_id} size hint to height: {height + self.item_margin * 2}")
                            tree_widget.scheduleDelayedItemsLayout()  # Force layout update
                        
                        # Force repaint
                        tree_widget.viewport().update()
                        return True  # Event handled
                        
        return super().eventFilter(source, event)

    def get_settings_manager(self):
        """Get the settings manager instance"""
        debug.debug("Getting settings manager")
        try:
            # Try to get it from the tree widget's parent (MainWindow)
            tree_widget = self.parent()
            if tree_widget and hasattr(tree_widget, 'parent') and hasattr(tree_widget.parent(), 'settings'):
                debug.debug("Found settings manager from parent")
                return tree_widget.parent().settings
        except Exception as e:
            debug.error(f"Error getting settings manager from parent: {e}")
        
        # Fallback to creating a new instance
        debug.debug("Creating new SettingsManager instance")
        from ui.app_settings import SettingsManager
        return SettingsManager()
    
    def _get_section_color(self, section_type, section_data):
        """Get color for a specific section type"""
        if section_type == "Category":
            return self.get_category_color(section_data)
        elif section_type == "Status":
            return self.get_status_color(section_data)
        elif section_type == "Priority":
            return self.get_priority_color(section_data)
        elif section_type == "Due Date":
            # Get custom color from settings
            settings = self.get_settings_manager()
            custom_color = settings.get_setting("due_date_background_color", "#E1F5FE")
            return QColor(custom_color)
        elif section_type == "Link":
            # Get custom color from settings
            settings = self.get_settings_manager()
            custom_color = settings.get_setting("links_background_color", "#FFF2E8")
            return QColor(custom_color)
        elif section_type == "Files":
            # Get custom color from settings  
            settings = self.get_settings_manager()
            custom_color = settings.get_setting("files_background_color", "#E8F4FD")
            return QColor(custom_color)
        elif section_type == "Completion Date":
            return QColor("#F3E5F5")  # Light purple
        elif section_type == "Progress":
            # Color based on progress value
            if section_data == "0%":
                return QColor("#FFEBEE")  # Light red
            elif section_data == "50%":
                return QColor("#FFF8E1")  # Light yellow
            elif section_data == "100%":
                return QColor("#E8F5E9")  # Light green
            else:
                return QColor("#f0f0f0")  # Light gray
        elif section_type == "Tag":
            return QColor("#FFF8E1")  # Light yellow
        else:
            return QColor("#f0f0f0")  # Light gray    

    def handle_links_click(self, item, point_in_task_pill):
        """Handle clicks on the links section of a task pill"""
        # Get item data
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Check if we have any links
        links = data.get('links', [])
        
        # If no links, return
        if not links:
            return
        
        # Create links menu
        menu = QMenu(self)
        
        # Add individual links with labels if available
        for link_id, url, label in links:
            action_text = label if label else url
            action = menu.addAction(action_text)
            action.setData(url)
        
        # Add separator if we have more than one link
        if len(links) > 1:
            menu.addSeparator()
            
            # Add "Open All" actions
            open_all_action = menu.addAction("Open All Links")
            open_all_action.setData("open_all")
            
            open_all_new_window_action = menu.addAction("Open All in New Window")
            open_all_new_window_action.setData("open_all_new_window")
        
        # Execute menu
        action = menu.exec(self.mapToGlobal(point_in_task_pill))
        
        if action:
            action_data = action.data()
            
            if action_data == "open_all":
                # Open all links in current window
                for _, url, _ in links:
                    if url:
                        self.open_link(url)
            elif action_data == "open_all_new_window":
                # Open all links in new window
                self.open_links_in_new_window(links)
            else:
                # Open individual link
                self.open_link(action_data)

    def _extract_item_data(self, index):
        """Extract and normalize item data from the index"""
        user_data = index.data(Qt.ItemDataRole.UserRole)
        
        # Extract all data from the dictionary stored in UserRole
        if isinstance(user_data, dict):
            item_id = user_data.get('id', 0)
            title = user_data.get('title', '')
            description = user_data.get('description', '')
            link = user_data.get('link', '')
            status = user_data.get('status', 'Not Started')
            priority = user_data.get('priority', '')
            due_date_str = user_data.get('due_date', '')
            category = user_data.get('category', '')
        else:
            # Fallback if UserRole data is missing or malformed
            item_id = 0
            title = index.data(Qt.ItemDataRole.DisplayRole) or ""
            description = link = ""
            status = "Not Started"
            priority = ""
            due_date_str = ""
            category = ""
            
        return user_data, item_id, title, description, link, status, priority, due_date_str, category

    def _create_pill_path(self, option):
        """Create the pill rect and path"""
        # Calculate pill rect with margins
        rect = option.rect.adjusted(
            self.item_margin, 
            self.item_margin, 
            -self.item_margin, 
            -self.item_margin
        )
        
        # Create the pill path
        path = QPainterPath()
        rectF = QRectF(rect)
        path.addRoundedRect(rectF, self.pill_radius, self.pill_radius)
        
        return rect, path

    def _draw_selection_highlight(self, painter, path):
        """Draw selection highlight"""
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 120, 215, 40)))  # Light blue transparent
        painter.drawPath(path)

    def _draw_pill_background(self, painter, path):
        """Draw the main pill background"""
        painter.setPen(QPen(QColor("#cccccc"), 1))
        painter.setBrush(QBrush(QColor("#f5f5f5")))
        painter.drawPath(path)

    def _get_section_tooltip_text(self, user_data, section_type):
        """Get detailed tooltip text for a specific section type"""
        debug.debug(f"Getting tooltip text for section: {section_type}")
        
        if section_type == "Category":
            category = user_data.get('category', '')
            return f"Category: {category}" if category else "No Category"
        
        elif section_type == "Status":
            status = user_data.get('status', 'Not Started')
            return f"Status: {status}"
        
        elif section_type == "Priority":
            priority = user_data.get('priority', '')
            return f"Priority: {priority}" if priority else "No Priority"
        
        elif section_type == "Due Date":
            due_date = user_data.get('due_date', '')
            if due_date:
                # Try to format the date nicely
                try:
                    from datetime import datetime
                    # Assume the date is in YYYY-MM-DD format
                    date_obj = datetime.strptime(due_date, "%Y-%m-%d")
                    formatted_date = date_obj.strftime("%B %d, %Y")  # e.g., "May 15, 2025"
                    return f"Due: {formatted_date}"
                except:
                    return f"Due: {due_date}"
            return "No Due Date"
        
        elif section_type == "Link":
            links = user_data.get('links', [])
            if links and isinstance(links, list) and len(links) > 0:
                if len(links) == 1:
                    _, url, label = links[0]
                    link_text = label if label else url
                    return f"Link: {link_text}"
                else:
                    return f"Links: {len(links)} links available"
            return "No Links"
        
        elif section_type == "Files":
            files = user_data.get('files', [])
            if files and isinstance(files, list) and len(files) > 0:
                if len(files) == 1:
                    _, file_path, file_name = files[0]
                    display_name = file_name if file_name else file_path
                    return f"File: {display_name}"
                else:
                    return f"Files: {len(files)} files attached"
            return "No Files"
        
        elif section_type == "Completion Date":
            completed_at = user_data.get('completed_at', '')
            if completed_at:
                try:
                    from datetime import datetime
                    # Assume format is YYYY-MM-DD HH:MM:SS
                    date_obj = datetime.strptime(completed_at, "%Y-%m-%d %H:%M:%S")
                    formatted_date = date_obj.strftime("%B %d, %Y at %I:%M %p")
                    return f"Completed: {formatted_date}"
                except:
                    return f"Completed: {completed_at}"
            return "Not Completed"
        
        elif section_type == "Progress":
            status = user_data.get('status', 'Not Started')
            if status == 'Not Started':
                return "Progress: 0% (Not Started)"
            elif status == 'In Progress':
                return "Progress: 50% (In Progress)"
            elif status == 'Completed':
                return "Progress: 100% (Completed)"
            else:
                return f"Progress: {status}"
        
        elif section_type == "Tag":
            tag = user_data.get('tag', '')
            return f"Tag: {tag}" if tag else "No Tag"
        
        else:
            return f"{section_type}: Not Available"

    def _get_hovered_section(self, pos, rect, is_compact):
        """Determine which section the mouse is hovering over in a collapsed task"""
        if not is_compact:
            return None  # Only show tooltips for compact tasks
        
        # Calculate section boundaries
        left_width = self.left_section_width if self.left_panel_contents else 0
        right_width = self.right_section_width if self.right_panel_contents else 0
        
        # Check if mouse is in left panel
        if left_width > 0 and pos.x() >= rect.left() and pos.x() <= rect.left() + left_width:
            # In compact mode, left sections are stacked HORIZONTALLY (side by side)
            if len(self.left_panel_contents) >= 2:
                # Two sections - check if in left or right half of the left panel
                section_width = left_width / 2
                if pos.x() <= rect.left() + section_width:
                    return self.left_panel_contents[0]  # First (leftmost) section
                else:
                    return self.left_panel_contents[1]  # Second (rightmost) section
            elif len(self.left_panel_contents) == 1:
                return self.left_panel_contents[0]  # Only one left section
        
        # Check if mouse is in right panel
        elif right_width > 0 and pos.x() >= rect.right() - right_width and pos.x() <= rect.right():
            # In compact mode, right sections are stacked HORIZONTALLY (side by side)
            if len(self.right_panel_contents) >= 2:
                # Two sections - check if in left or right half of the right panel
                section_width = right_width / 2
                right_panel_start = rect.right() - right_width
                if pos.x() <= right_panel_start + section_width:
                    return self.right_panel_contents[0]  # First (leftmost) section
                else:
                    return self.right_panel_contents[1]  # Second (rightmost) section
            elif len(self.right_panel_contents) == 1:
                return self.right_panel_contents[0]  # Only one right section
        
        # Check if mouse is in center area (title)
        elif pos.x() > rect.left() + left_width and pos.x() < rect.right() - right_width:
            return "Title"  # Hovering over title area
        
        return None

    def _draw_task_content(self, painter, rect, is_compact, title, description, due_date_str, item_id, left_width, right_width):
        """Draw the main task content (title, description, due date)"""
        # Get font settings from SettingsManager
        settings = self.get_settings_manager()
        font_family = settings.get_setting("font_family", "Segoe UI")
        font_size = int(settings.get_setting("font_size", 10))
        
        # Draw the title with custom font settings
        self._draw_title(painter, rect, is_compact, title, font_family, font_size, settings, left_width, right_width)
        
        # Draw description if in full mode
        if not is_compact and description:
            self._draw_description(painter, rect, description, font_family, font_size, settings, left_width, right_width)
        
        # Draw due date if available and not already in a panel
        right_panel_has_due_date = any("Due Date" in content_type for content_type in self.right_panel_contents if content_type)
        left_panel_has_due_date = any("Due Date" in content_type for content_type in self.left_panel_contents if content_type)
        
        if due_date_str and not right_panel_has_due_date and not left_panel_has_due_date:
            self._draw_due_date(painter, rect, is_compact, due_date_str, font_family, font_size, settings, left_width, right_width)    

    def _draw_title(self, painter, rect, is_compact, title, font_family, font_size, settings, left_width, right_width):
        """Draw the task title with improved text fitting and proper descender space"""
        # Get title font from new font settings
        title_font = self._get_font_for_element("title")
        
        # Get title color from settings
        title_color = settings.get_setting("title_color", "#000000")
        
        painter.setFont(title_font)
        painter.setPen(QColor(title_color))
        
        # Get font metrics for proper text positioning
        font_metrics = painter.fontMetrics()
        
        # Calculate available width for title text
        available_width = rect.width() - left_width - right_width - (self.text_padding * 2)
        
        # Define title rect with proper positioning and font metrics
        if is_compact:
            # In compact mode, ensure enough height for descenders
            title_rect = QRectF(
                rect.left() + left_width + self.text_padding,
                rect.top() + 3,  # Small top padding
                available_width,
                font_metrics.height() + 2  # Use actual font height plus small buffer
            )
        else:
            # In normal mode, use font metrics for proper height
            title_rect = QRectF(
                rect.left() + left_width + self.text_padding,
                rect.top() + 5,  # Slightly more top padding
                available_width,
                font_metrics.height() + 2  # Ensure full font height including descenders
            )
        
        # Calculate if text needs to be elided
        text_width = font_metrics.horizontalAdvance(title)
        
        if text_width > available_width:
            # Text is too long, elide it intelligently
            elided_text = font_metrics.elidedText(
                title, 
                Qt.TextElideMode.ElideRight, 
                int(available_width)
            )
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, elided_text)
        else:
            # Text fits normally - use AlignTop to prevent cutting off descenders
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, title)

    def _draw_description(self, painter, rect, description, font_family, font_size, settings, left_width, right_width):
        """Draw the task description with dynamic height and proper word wrapping"""
        # Get description font from new font settings
        desc_font = self._get_font_for_element("description")
        
        # Get description color from settings
        desc_color = settings.get_setting("description_color", "#666666")
        
        painter.setFont(desc_font)
        painter.setPen(QColor(desc_color))
        
        # Calculate available space
        available_width = rect.width() - left_width - right_width - (self.text_padding * 2)
        
        # Get font metrics for proper line calculations
        font_metrics = painter.fontMetrics()
        line_height = font_metrics.height()
        
        # Define description rect - use available space more efficiently
        desc_start_y = rect.top() + 30  # Start below title
        # Use most of the available height, leaving less bottom padding
        available_height = rect.height() - 35  # Reduced from 40 to 35
        
        desc_rect = QRectF(
            rect.left() + left_width + self.text_padding,
            desc_start_y,
            available_width,
            available_height
        )
        
        # Calculate maximum lines that can fit
        max_lines = max(1, int(available_height / line_height))
        
        # Split description into words while preserving line breaks
        # First split by line breaks to preserve hard returns
        paragraphs = description.split('\n')
        lines = []
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                # Empty line - add it as a blank line
                lines.append("")
                continue
                
            # Process each paragraph for word wrapping
            words = paragraph.split()
            current_line = ""
            
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                test_width = font_metrics.horizontalAdvance(test_line)
                
                if test_width <= available_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                        current_line = word
                    else:
                        # Single word is too long, elide it
                        current_line = font_metrics.elidedText(word, Qt.TextElideMode.ElideRight, int(available_width))
                        lines.append(current_line)
                        current_line = ""
                    
                    # Check if we've reached max lines
                    if len(lines) >= max_lines:
                        break
            
            # Add remaining text from this paragraph
            if current_line and len(lines) < max_lines:
                lines.append(current_line)
                
            # Break if we've reached max lines
            if len(lines) >= max_lines:
                break
        
        # If we have too many lines, truncate and add ellipsis to last line
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            if lines:
                last_line = lines[-1]
                # Add ellipsis to last line if needed
                while font_metrics.horizontalAdvance(last_line + "...") > available_width and len(last_line) > 0:
                    last_line = last_line[:-1]
                lines[-1] = last_line + "..."
        
        # Draw the lines with proper spacing
        for i, line in enumerate(lines):
            line_rect = QRectF(
                desc_rect.left(),
                desc_rect.top() + (i * line_height),
                desc_rect.width(),
                line_height
            )
            painter.drawText(line_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, line)

    def sizeHint(self, option, index):
        """Return appropriate size based on compact state, content, and description length"""
        user_data = index.data(Qt.ItemDataRole.UserRole)
        
        # Use a consistent width regardless of expand/collapse state
        consistent_width = 100  # Fixed base width - let the tree widget handle actual width
        
        # Check if this is a priority header
        if isinstance(user_data, dict) and user_data.get('is_priority_header', False):
            # Use a fixed smaller height for priority headers
            header_height = 35  # Consistent header height
            debug.debug(f"Priority header size hint: width={consistent_width}, height={header_height}")
            return QSize(consistent_width, header_height)
        
        # Check if this is a task item
        if isinstance(user_data, dict) and 'id' in user_data:
            task_id = user_data['id']
            is_compact = task_id in self.compact_items
            
            if is_compact:
                # Use calculated compact height
                height = self.compact_height
                debug.debug(f"Task {task_id} compact size hint: width={consistent_width}, height={height + self.item_margin * 2}")
                return QSize(consistent_width, height + self.item_margin * 2)
            else:
                # Calculate dynamic height based on description content
                description = user_data.get('description', '')
                
                if description and description.strip():
                    # Get font settings for calculation
                    settings = self.get_settings_manager()
                    font_family = settings.get_setting("font_family", "Arial")
                    
                    # Create description font for measurement
                    desc_font = self._get_font_for_element("description")
                    font_metrics = QFontMetrics(desc_font)
                    line_height = font_metrics.height()
                    
                    # Use a fixed estimated width for consistency
                    estimated_width = 400  # Fixed estimate instead of dynamic calculation
                    left_width = sum(self.left_panel_widths) if hasattr(self, 'left_panel_widths') else 0
                    right_width = sum(self.right_panel_widths) if hasattr(self, 'right_panel_widths') else 0
                    available_width = estimated_width - left_width - right_width - (self.text_padding * 2)
                    
                    # Calculate lines needed for description (accounting for line breaks)
                    paragraphs = description.split('\n')
                    lines_needed = 0
                    
                    for paragraph in paragraphs:
                        if not paragraph.strip():
                            # Empty line
                            lines_needed += 1
                            continue
                            
                        # Calculate word wrapping for this paragraph
                        words = paragraph.split()
                        current_line = ""
                        
                        for word in words:
                            test_line = current_line + (" " if current_line else "") + word
                            test_width = font_metrics.horizontalAdvance(test_line)
                            
                            if test_width <= available_width:
                                current_line = test_line
                            else:
                                if current_line:
                                    lines_needed += 1
                                    current_line = word
                                else:
                                    lines_needed += 1
                                    current_line = ""
                        
                        if current_line:
                            lines_needed += 1
                    
                    # Calculate total height needed
                    # Title space (30px) + description lines + minimal bottom padding
                    description_height = lines_needed * line_height
                    total_height = 35 + description_height + 8  # Title + description + minimal padding
                    
                    # Ensure minimum height
                    total_height = max(total_height, self.pill_height)
                    
                    debug.debug(f"Task {task_id} expanded size hint: width={consistent_width}, description lines={lines_needed}, height={total_height + self.item_margin * 2}")
                    return QSize(consistent_width, total_height + self.item_margin * 2)
                else:
                    # No description, use standard height
                    debug.debug(f"Task {task_id} expanded (no description) size hint: width={consistent_width}, height={self.pill_height + self.item_margin * 2}")
                    return QSize(consistent_width, self.pill_height + self.item_margin * 2)
        
        # Default size for other items
        debug.debug(f"Default size hint: width={consistent_width}, height=50")
        return QSize(consistent_width, 50)
    
    def _draw_due_date(self, painter, rect, is_compact, due_date_str, font_family, font_size, settings, left_width, right_width):
        """Draw the due date with custom font settings"""
        # Get due date font from new font settings
        date_font = self._get_font_for_element("due_date")
        
        # Get due date color from settings
        due_color = settings.get_setting("due_date_color", "#888888")
        
        painter.setFont(date_font)
        painter.setPen(QColor(due_color))
        
        if is_compact:
            title_rect_bottom = rect.top() + rect.height() / 2 + 2
            date_rect = QRectF(
                rect.left() + left_width + self.text_padding,
                title_rect_bottom,
                rect.width() - left_width - right_width - self.text_padding * 2,
                rect.height() / 2 - 2
            )
            painter.drawText(date_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, f"Due: {due_date_str}")
        else:
            date_rect = QRectF(
                rect.left() + left_width + self.text_padding,
                rect.top() + rect.height() - 18,
                rect.width() - left_width - right_width - self.text_padding * 2,
                15
            )
            painter.drawText(date_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"Due: {due_date_str}")

    def _draw_toggle_button(self, painter, index, item_id, rect):
        """Draw the toggle button for all items with consistent positioning"""
        # Get data from the index
        user_data = index.data(Qt.ItemDataRole.UserRole)
        
        # Continue with drawing the toggle button
        if self.hover_item and self.hover_item == index and self.toggle_button_rect:
            # Save current state
            painter.save()

            # Clear any clipping that might interfere
            painter.setClipping(False)

            # Calculate button position - use a fixed reference point for consistency
            button_size = 24
            button_top = rect.top() - button_size // 2
            
            # Use the tree widget's viewport width for consistent positioning
            tree_widget = painter.device().parent() if hasattr(painter.device(), 'parent') else None
            if tree_widget and hasattr(tree_widget, 'viewport'):
                viewport_width = tree_widget.viewport().width()
                # Position button at a consistent location relative to viewport
                button_center = viewport_width // 2  # Always center in viewport
            else:
                # Fallback to rect-based positioning
                button_center = rect.left() + rect.width() // 2

            toggle_button_rect = QRectF(
                button_center - button_size // 2,
                button_top,
                button_size,
                button_size
            )

            # Draw shadow effect 
            shadow_rect = QRectF(
                toggle_button_rect.left() + 2,
                toggle_button_rect.top() + 2,
                toggle_button_rect.width(),
                toggle_button_rect.height()
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 50)))  # Darker shadow (50 -> 50)
            painter.drawEllipse(shadow_rect)

            # Determine if this is a header or a task
            is_header = isinstance(user_data, dict) and user_data.get('is_priority_header', False)
            
            # Draw button with darker border (previously #333333, now #111111)
            painter.setPen(QPen(QColor("#111111"), 2))  # Darker border
            
            # For headers, use a consistent color regardless of expanded state
            if is_header:
                expanded = user_data.get('expanded', True) if isinstance(user_data, dict) else True
                # Dark blue for header toggle buttons
                painter.setBrush(QBrush(QColor(50, 100, 200)))  # Darker blue
            else:
                # For regular tasks, highlight button based on state
                if item_id in self.compact_items:
                    # Expand button (down arrow) - darker green
                    painter.setBrush(QBrush(QColor(50, 200, 50)))  # Darker green
                else:
                    # Collapse button (up arrow) - darker blue
                    painter.setBrush(QBrush(QColor(50, 150, 200)))  # Darker blue
            
            painter.drawEllipse(toggle_button_rect)

            # Draw arrow icon with larger font and darker color
            toggle_font = QFont(painter.font())
            toggle_font.setPointSize(16)  # Larger size
            toggle_font.setBold(True)
            painter.setFont(toggle_font)
            painter.setPen(QColor("#000000"))  # Black text for better visibility

            # For headers, show right/down arrow based on expanded state
            if is_header:
                icon = "↓" if expanded else "→"
            else:
                # For tasks, show down arrow if compact (to expand), up arrow if expanded (to compact)
                icon = "↓" if item_id in self.compact_items else "↑"
                
            painter.drawText(toggle_button_rect, Qt.AlignmentFlag.AlignCenter, icon)

            # Store button rect for click detection (even when not hovering)
            if not hasattr(self, 'all_button_rects'):
                self.all_button_rects = {}
            self.all_button_rects[item_id] = (toggle_button_rect, index)

            # Restore painting settings
            painter.restore()
            
    def _get_font_for_element(self, element_type):
        """Get font settings for a specific element type from settings"""
        settings = self.get_settings_manager()
        
        # Get element-specific font family, fallback to global font_family, then Arial
        default_font_family = settings.get_setting("font_family", "Arial")
        
        if element_type == "title":
            font_family = settings.get_setting("title_font_family", default_font_family)
            size = settings.get_setting("title_font_size", 14)
            bold = settings.get_setting("title_font_bold", True)
            italic = settings.get_setting("title_font_italic", False)
            underline = settings.get_setting("title_font_underline", False)
        elif element_type == "description":
            font_family = settings.get_setting("description_font_family", default_font_family)
            size = settings.get_setting("description_font_size", 10)
            bold = settings.get_setting("description_font_bold", False)
            italic = settings.get_setting("description_font_italic", False)
            underline = settings.get_setting("description_font_underline", False)
        elif element_type == "due_date":
            font_family = settings.get_setting("due_date_font_family", default_font_family)
            size = settings.get_setting("due_date_font_size", 9)
            bold = settings.get_setting("due_date_font_bold", False)
            italic = settings.get_setting("due_date_font_italic", False)
            underline = settings.get_setting("due_date_font_underline", False)
        elif element_type == "panel":
            font_family = settings.get_setting("panel_font_family", default_font_family)
            size = settings.get_setting("panel_font_size", 8)
            bold = settings.get_setting("panel_font_bold", False)
            italic = settings.get_setting("panel_font_italic", False)
            underline = settings.get_setting("panel_font_underline", False)
        else:
            # Default fallback
            font_family = default_font_family
            size = 10
            bold = False
            italic = False
            underline = False
        
        font = QFont(font_family, size)
        font.setBold(bold)
        font.setItalic(italic)
        font.setUnderline(underline)
        
        return font

    def _calculate_compact_height(self):
        """Calculate compact height based on title font size with proper descender space"""
        debug.debug("Calculating compact height based on title font size")
        
        # Get title font settings
        settings = self.get_settings_manager()
        title_font_size = settings.get_setting("title_font_size", 14)
        debug.debug(f"Title font size: {title_font_size}")
        
        # Create a font to measure actual height
        font_family = settings.get_setting("font_family", "Arial")
        title_font = QFont(font_family, title_font_size)
        title_font.setBold(settings.get_setting("title_font_bold", True))
        
        # Get font metrics
        from PyQt6.QtGui import QFontMetrics
        font_metrics = QFontMetrics(title_font)
        font_height = font_metrics.height()
        ascent = font_metrics.ascent()
        descent = font_metrics.descent()
        debug.debug(f"Font metrics - height: {font_height}, ascent: {ascent}, descent: {descent}")
        
        # Calculate compact height: 
        # - 6 pixels top padding (more space from top edge)
        # - Full font height (includes ascent + descent for descenders)
        # - 2 pixels bottom padding (minimal bottom space)
        compact_height = 6 + font_height + 2
        
        # Ensure minimum height for usability (never smaller than 22 pixels)
        compact_height = max(compact_height, 22)
        
        debug.debug(f"Calculated compact height: {compact_height} (6 top + {font_height} font + 2 bottom)")
        return compact_height
    
    @debug_method
    def _draw_custom_panel(self, painter, path, rect, is_compact, content_types, 
                        user_data, panel_width, panel_side="left"):
        """Draw custom panel with multiple sections based on settings"""
        # Get panel font from new font settings
        panel_font = self._get_font_for_element("panel")
        
        # Get settings
        settings = self.get_settings_manager()
        
        # Check if auto text color is enabled (default: True for readability)
        auto_text_color = settings.get_setting("auto_panel_text_color", True)
        
        # Use clipping to ensure proper drawing within the pill
        painter.setClipPath(path)
        
        # Calculate section dimensions based on compact mode
        section_count = len(content_types)
        if is_compact:
            # In compact mode: stack horizontally (side by side)
            section_width = panel_width / section_count
            section_height = rect.height()
        else:
            # In expanded mode: stack vertically (top to bottom) 
            section_width = panel_width
            section_height = rect.height() / section_count
        
        # Draw each section
        for i, content_type in enumerate(content_types):
            if content_type == "None":
                continue
                
            # Get section data and color
            section_data = self._get_section_data(user_data, content_type)
            section_color = self._get_section_color(content_type, section_data)
            
            # Determine text color based on setting
            if auto_text_color:
                # Calculate text color based on background brightness for readability
                bg_color = section_color
                brightness = (bg_color.red() * 299 + bg_color.green() * 587 + bg_color.blue() * 114) / 1000
                text_color = "#000000" if brightness > 128 else "#FFFFFF"
            else:
                # Use user's custom panel text color from font color settings
                # This should use the panel text color, not the left_panel_color
                text_color = settings.get_setting("panel_color", "#FFFFFF")  # Changed from "left_panel_color" to "panel_color"
            
            # Calculate section rectangle based on compact mode and panel side
            if is_compact:
                # Compact mode: horizontal stacking
                if panel_side == "left":
                    section_rect = QRectF(
                        rect.left() + (i * section_width),
                        rect.top(),
                        section_width,
                        section_height
                    )
                else:  # right panel
                    section_rect = QRectF(
                        rect.right() - panel_width + (i * section_width),
                        rect.top(),
                        section_width,
                        section_height
                    )
            else:
                # Expanded mode: vertical stacking (original behavior)
                if panel_side == "left":
                    section_rect = QRectF(
                        rect.left(),
                        rect.top() + (i * section_height),
                        section_width,
                        section_height
                    )
                else:  # right panel
                    section_rect = QRectF(
                        rect.right() - panel_width,
                        rect.top() + (i * section_height),
                        section_width,
                        section_height
                    )
            
            # Fill the section
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(section_color))
            painter.drawRect(section_rect)
            
            # Draw text if not in compact mode (maintains current behavior)
            if not is_compact:
                painter.setFont(panel_font)
                painter.setPen(QColor(text_color))
                
                painter.drawText(
                    section_rect,
                    Qt.AlignmentFlag.AlignCenter,
                    str(section_data) or f"No {content_type}"
                )
        
        # Remove clipping
        painter.setClipping(False)
        
        # Draw divider line
        painter.setPen(QPen(QColor("#cccccc"), 1))
        if panel_side == "left":
            painter.drawLine(
                rect.left() + panel_width,
                rect.top(),
                rect.left() + panel_width,
                rect.bottom()
            )
        else:  # right panel
            painter.drawLine(
                rect.right() - panel_width,
                rect.top(),
                rect.right() - panel_width,
                rect.bottom()
            )
    
    def _draw_priority_header(self, painter, option, index, user_data):
        """Draw a priority header item"""
        painter.save()
        
        # Get data
        priority = user_data.get('priority', 'Medium')
        color = user_data.get('color', '#FFC107')
        expanded = user_data.get('expanded', True)
        
        # Calculate rect
        rect = option.rect.adjusted(
            self.item_margin,
            self.item_margin,
            -self.item_margin,
            -self.item_margin
        )
        
        # Draw background
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 5, 5)
        painter.fillPath(path, QBrush(QColor(color)))
        
        # Calculate text color based on background brightness
        bg_color = QColor(color)
        brightness = (bg_color.red() * 299 + bg_color.green() * 587 + bg_color.blue() * 114) / 1000
        text_color = "#000000" if brightness > 128 else "#FFFFFF"
        
        # Get font from settings
        settings = self.get_settings_manager()
        font_family = settings.get_setting("font_family", "Segoe UI")
        font_size = int(settings.get_setting("font_size", 12))
        
        header_font = QFont(font_family)
        header_font.setPointSize(font_size)
        header_font.setBold(True)
        
        painter.setFont(header_font)
        painter.setPen(QColor(text_color))
        
        header_text_rect = QRectF(
            rect.left() + 40,
            rect.top(),
            rect.width() - 50,
            rect.height()
        )
        
        painter.drawText(header_text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                        priority.upper())
        
        painter.restore()

    def _draw_panel_text_with_fitting(self, painter, text_rect, text, font, max_lines=2):
        """Draw panel text with improved fitting and multi-line support"""
        painter.setFont(font)
        font_metrics = painter.fontMetrics()
        line_height = font_metrics.height()
        available_width = text_rect.width() - 4  # Small padding
        
        # Split text into words
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            test_width = font_metrics.horizontalAdvance(test_line)
            
            if test_width <= available_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    # Single word too long, elide it
                    current_line = font_metrics.elidedText(word, Qt.TextElideMode.ElideRight, int(available_width))
                    lines.append(current_line)
                    current_line = ""
            
            if len(lines) >= max_lines:
                break
        
        if current_line and len(lines) < max_lines:
            lines.append(current_line)
        
        # Ensure we don't exceed max_lines
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            if lines:
                # Add ellipsis to last line
                last_line = lines[-1]
                while font_metrics.horizontalAdvance(last_line + "...") > available_width and len(last_line) > 0:
                    last_line = last_line[:-1]
                lines[-1] = last_line + "..."
        
        # Draw each line centered in the available space
        total_text_height = len(lines) * line_height
        start_y = text_rect.top() + (text_rect.height() - total_text_height) / 2
        
        for i, line in enumerate(lines):
            line_rect = QRectF(
                text_rect.left() + 2,  # Small left padding
                start_y + (i * line_height),
                text_rect.width() - 4,  # Account for padding
                line_height
            )
            painter.drawText(line_rect, Qt.AlignmentFlag.AlignCenter, line)
            
    def show_toggle_button(self, tree_widget, item_index):
        """Force show the toggle button for a specific item (for debugging)"""
        self.hover_item = item_index
        rect = tree_widget.visualRect(item_index)
        self.toggle_button_rect = QRectF(
            rect.center().x() - 12,
            rect.top() - 12,
            24, 24
        )
        # Force redraw
        tree_widget.viewport().update()
        print(f"Showing toggle button for item at index {item_index.row()}")
        
    def debug_toggle_buttons(self):
        """Debug method to force toggle buttons to appear on all items"""
        delegate = self.itemDelegate()
        if isinstance(delegate, TaskPillDelegate):
            for i in range(self.topLevelItemCount()):
                index = self.indexFromItem(self.topLevelItem(i))
                delegate.show_toggle_button(self, index)
        self.viewport().update()

    def _find_item_by_id(self, item, item_id):
        """Recursively find an item by its ID"""
        # Check if this is the item we're looking for
        user_data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(user_data, dict) and 'id' in user_data and user_data['id'] == item_id:
            return item
            
        # Check children
        for i in range(item.childCount()):
            result = self._find_item_by_id(item.child(i), item_id)
            if result:
                return result
                
        return None

    def get_status_color(self, status):
        """Get color for a status from the database"""
        if not status:
            return QColor("#E0E0E0")  # Default light gray
            
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT color FROM statuses WHERE name = ?", (status,))
                result = cursor.fetchone()
                if result:
                    return QColor(result[0])
        except Exception as e:
            print(f"Error getting status color: {e}")
        
        # Fallback to default statuses if not found
        status_colors = {
            'Not Started': '#F44336',  # Red
            'In Progress': '#FFC107',  # Amber
            'On Hold': '#9E9E9E',      # Gray
            'Completed': '#4CAF50'     # Green
        }
        return QColor(status_colors.get(status, "#E0E0E0"))

    def get_priority_color(self, priority):
        """Get color for a priority from the database"""
        if not priority:
            return QColor("#E0E0E0")  # Default light gray
            
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT color FROM priorities WHERE name = ?", (priority,))
                result = cursor.fetchone()
                if result:
                    return QColor(result[0])
        except Exception as e:
            print(f"Error getting priority color: {e}")
        
        # Fallback to default priorities if not found
        default_priority_colors = {
            'High': '#F44336',     # Red
            'Medium': '#FFC107',   # Amber
            'Low': '#4CAF50'       # Green
        }
        return QColor(default_priority_colors.get(priority, "#E0E0E0"))

    def get_category_color(self, category):
        """Get color for a category from the database"""
        if not category:
            return QColor("#E0E0E0")  # Default light gray
            
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT color FROM categories WHERE name = ?", (category,))
                result = cursor.fetchone()
                if result:
                    return QColor(result[0])
        except Exception as e:
            print(f"Error getting category color: {e}")
        
        # Fallback to a default color if not found
        return QColor("#E0E0E0")  # Light gray

    def debug_header_items(self, tree_widget):
        """Debug the header items in the tree widget"""
        print("\n===== HEADER ITEMS DEBUG =====")
        for i in range(tree_widget.topLevelItemCount()):
            item = tree_widget.topLevelItem(i)
            index = tree_widget.indexFromItem(item)
            user_data = index.data(Qt.ItemDataRole.UserRole)
            
            print(f"Top-level item {i}, data: {user_data}")
            
            # Check if this is supposed to be a header
            if hasattr(item, 'priority_name'):
                print(f"  Has priority_name attribute: {item.priority_name}")
                print(f"  But is_priority_header value: {user_data.get('is_priority_header') if isinstance(user_data, dict) else 'N/A'}")
        
        print("===== END DEBUG =====\n")