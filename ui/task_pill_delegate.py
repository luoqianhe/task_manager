# src/ui/task_pill_delegate.py

from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QApplication, QStyle
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QBrush, QPen, QFont, QFontMetrics
from PyQt6.QtCore import QRectF, Qt, QSize, QPoint, QPointF
from datetime import datetime, date
import sqlite3
from pathlib import Path


class TaskPillDelegate(QStyledItemDelegate):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Initialize attributes
        self.text_padding = 10
        self.pill_height = 80
        self.compact_height = 40
        self.pill_radius = 15
        self.item_margin = 5
        
        # Load panel settings from SettingsManager
        settings = self.get_settings_manager()
        self.left_section_width = settings.get_setting("left_panel_width", 100)
        self.right_section_width = settings.get_setting("right_panel_width", 100)
        
        # Fixed section count for both panels (2)
        self.left_panel_count = 2
        self.right_panel_count = 2
        
        # Load panel contents
        self.left_panel_contents = settings.get_setting("left_panel_contents", ["Category", "Status"])
        self.right_panel_contents = settings.get_setting("right_panel_contents", ["Link", "Due Date"])
        
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
                print("Setting up mouse tracking and event filter")
                parent.setMouseTracking(True)
                
                # Check if parent has viewport method before using it
                if hasattr(parent, 'viewport') and callable(parent.viewport):
                    parent.viewport().setMouseTracking(True)
                    parent.viewport().installEventFilter(self)
                    print("Event filter installed on parent viewport")
                
                # Install event filter on parent
                parent.installEventFilter(self)
                print("Event filter installed on parent")
            except Exception as e:
                print(f"Error setting up event filters: {e}")

    def _get_section_data(self, user_data, section_type):
        """Get data for a specific section type"""
        
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

    def _get_section_color(self, section_type, section_data):
        """Get color for a specific section type"""
        if section_type == "Category":
            return self.get_category_color(section_data)
        elif section_type == "Status":
            return self.get_status_color(section_data)
        elif section_type == "Priority":
            return self.get_priority_color(section_data)
        elif section_type == "Due Date":
            return QColor("#E1F5FE")  # Light blue
        elif section_type == "Link":
            return QColor("#f5f5f5")  # Light gray
        elif section_type == "Files":  # New section type for files
            return QColor("#E8F5E9")  # Light green
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
        print(f"DEBUG: Links in handle_links_click: {links}")
        
        # If no links, return
        if not links:
            print("DEBUG: No links found")
            return
        
        # Create links menu
        menu = QMenu(self)
        
        # Add individual links with labels if available
        for link_id, url, label in links:
            action_text = label if label else url
            action = menu.addAction(action_text)
            action.setData(url)
            print(f"DEBUG: Added link menu item: {action_text}")
        
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
            print(f"DEBUG: Selected action: {action_data}")
            
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
    
    def load_compact_states(self):
        """Load compact states from the database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First check if the is_compact column exists in the tasks table
                try:
                    cursor.execute("SELECT is_compact FROM tasks LIMIT 1")
                except sqlite3.OperationalError:
                    # Column doesn't exist, need to add it
                    cursor.execute("ALTER TABLE tasks ADD COLUMN is_compact INTEGER NOT NULL DEFAULT 0")
                    conn.commit()
                
                # Now load all task IDs that are marked as compact
                cursor.execute("SELECT id FROM tasks WHERE is_compact = 1")
                for row in cursor.fetchall():
                    self.compact_items.add(row[0])
                
                print(f"Loaded {len(self.compact_items)} compact states from database")
        except Exception as e:
            print(f"Error loading compact states: {e}")
    
    def _draw_task_item(self, painter, option, index):
        """Draw a regular task item - modified to support customizable panels"""
        print(f"DEBUG: Drawing task item")
        
        # Extract data using our existing method
        user_data, item_id, title, description, link, status, priority, due_date_str, category = self._extract_item_data(index)
        
        # Check if compact
        is_compact = item_id in self.compact_items
        
        # Save painter state and prepare to draw
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate pill rect and create path
        rect, path = self._create_pill_path(option)
        
        # Draw selection highlight if needed
        if option.state & QStyle.StateFlag.State_Selected:
            self._draw_selection_highlight(painter, path)
        
        # Draw the main pill background
        self._draw_pill_background(painter, path)
        
        # Calculate widths for left and right panels
        left_width = self.left_section_width if self.left_panel_contents else 0
        right_width = self.right_section_width if self.right_panel_contents else 0
        
        # Draw left panel if content is configured
        if left_width > 0 and self.left_panel_contents:
            self._draw_custom_panel(painter, path, rect, is_compact, 
                                   self.left_panel_contents, 
                                   user_data, left_width, "left")
        
        # Draw right panel if content is configured
        if right_width > 0 and self.right_panel_contents:
            self._draw_custom_panel(painter, path, rect, is_compact, 
                                   self.right_panel_contents, 
                                   user_data, right_width, "right")
        
        # Draw content (title, description, due date)
        self._draw_task_content(painter, rect, is_compact, title, description, due_date_str, item_id, left_width, right_width)
        
        # Draw toggle button if needed
        self._draw_toggle_button(painter, index, item_id, rect)
        
        # Restore painter
        painter.restore()
    
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
    
    def _draw_custom_panel(self, painter, path, rect, is_compact, content_types, 
                           user_data, panel_width, panel_side="left"):
        """Draw custom panel with multiple sections based on settings"""
        # Get settings for panel text
        settings = self.get_settings_manager()
        text_color = settings.get_setting("left_panel_color", "#FFFFFF")
        text_size = int(settings.get_setting("left_panel_size", 8))
        text_bold = settings.get_setting("left_panel_bold", False)
        
        # Use clipping to ensure proper drawing within the pill
        painter.setClipPath(path)
        
        # Calculate section height - ensure it's evenly divided
        section_count = len(content_types)
        section_height = rect.height() / section_count
        
        # Draw each section
        for i, content_type in enumerate(content_types):
            # Skip if content type is None
            if content_type == "None":
                continue
                
            # Get section data
            section_data = self._get_section_data(user_data, content_type)
            print(f"DEBUG: Drawing section {content_type} with data: {section_data}")
            
            # Get color based on content type
            section_color = self._get_section_color(content_type, section_data)
            
            # Calculate section rectangle
            if panel_side == "left":
                section_rect = QRectF(
                    rect.left(),
                    rect.top() + (i * section_height),
                    panel_width,
                    section_height
                )
            else:  # right panel
                section_rect = QRectF(
                    rect.right() - panel_width,
                    rect.top() + (i * section_height),
                    panel_width,
                    section_height
                )
            
            # Fill the section
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(section_color))
            painter.drawRect(section_rect)
            
            # Draw text if not in compact mode
            if not is_compact:
                # Set up font for section text
                section_font = QFont(painter.font())
                section_font.setPointSize(text_size)
                if text_bold:
                    section_font.setBold(True)
                    
                painter.setFont(section_font)
                painter.setPen(QColor(text_color))
                
                # Draw section text
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
        """Draw the task title with custom font settings"""
        # Get title style settings
        bold_titles = settings.get_setting("bold_titles", True)
        title_color = settings.get_setting("title_color", "#333333")
        
        # Create title font
        title_font = QFont(font_family, font_size)
        if bold_titles:
            title_font.setBold(True)
        
        # Set font weight based on settings
        weight = settings.get_setting("font_weight", 0)  # 0=Regular, 1=Medium, 2=Bold
        if weight == 1:
            title_font.setWeight(QFont.Weight.Medium)
        elif weight == 2:
            title_font.setWeight(QFont.Weight.Bold)
        
        painter.setFont(title_font)
        painter.setPen(QColor(title_color))
        
        # Define title_rect based on compact mode - using the updated left_width and right_width
        if is_compact:
            # In compact mode, title takes top half width
            title_rect = QRectF(
                rect.left() + left_width + self.text_padding,
                rect.top(),
                rect.width() - left_width - right_width - self.text_padding * 2,
                rect.height() / 2  # Only take the top half in compact mode
            )
        else:
            # In full mode, title is at the top
            title_rect = QRectF(
                rect.left() + left_width + self.text_padding,
                rect.top() + 10,
                rect.width() - left_width - right_width - self.text_padding * 2,
                20  # Height for title
            )

        # Draw title with ellipsis if too long
        elidedTitle = painter.fontMetrics().elidedText(
            title, Qt.TextElideMode.ElideRight, int(title_rect.width()))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elidedTitle)
        
    def eventFilter(self, source, event):
        """Handle mouse events for hover detection and button clicks"""
        # Check if we're handling a tree widget or its viewport
        is_tree_widget = hasattr(source, 'indexAt')
        is_viewport = hasattr(source, 'parent') and hasattr(source.parent(), 'indexAt')
        
        # Handle mouse movement for hover effects
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
                # No need to adjust position for viewport
            else:
                # Not a tree widget or viewport, can't handle
                return super().eventFilter(source, event)
            
            # Now use tree_widget to find item at position
            index = tree_widget.indexAt(pos)
            if index.isValid():
                # Set hover item and force redraw
                self.hover_item = index
                # Calculate button position
                rect = tree_widget.visualRect(index)
                self.toggle_button_rect = QRectF(
                    rect.center().x() - 12,  # 12 = half of button size
                    rect.top() - 12,  # Position button above item
                    24, 24  # Button size
                )
                tree_widget.viewport().update()
            else:
                # Clear hover state if not over an item
                if self.hover_item:
                    self.hover_item = None
                    tree_widget.viewport().update()
                    print("Cleared hover state")
        
        # Handle mouse clicks for toggle button
        elif event.type() == event.Type.MouseButtonPress:
            print("Mouse button press detected")
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
                print(f"Mouse position: QPoint({pos.x()}, {pos.y()}) converted to QPointF({pos_f.x()}, {pos_f.y()})")
            except Exception as e:
                print(f"Error getting mouse position: {e}")
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
                    print("Toggle button clicked")
                    
                    # Get the item data to find the ID
                    item_data = self.hover_item.data(Qt.ItemDataRole.UserRole)
                    if isinstance(item_data, dict) and 'id' in item_data:
                        item_id = item_data['id']
                        print(f"Item ID: {item_id}")
                        
                        # Toggle compact state
                        is_compact = item_id in self.compact_items
                        if is_compact:
                            self.compact_items.remove(item_id)
                        else:
                            self.compact_items.add(item_id)
                        
                        # Save state to database
                        self.save_compact_state(item_id, not is_compact)
                        
                        # Get tree widget item
                        item = None
                        if hasattr(tree_widget, 'itemFromIndex'):
                            item = tree_widget.itemFromIndex(self.hover_item)
                        
                        # Update item size if found
                        if item:
                            height = self.compact_height if not is_compact else self.pill_height
                            item.setSizeHint(0, QSize(tree_widget.viewport().width(), 
                                                    height + self.item_margin * 2))
                            tree_widget.scheduleDelayedItemsLayout()  # Force layout update
                            print(f"Item size updated, new height: {height}")
                        
                        # Force repaint
                        tree_widget.viewport().update()
                        return True  # Event handled
            
            # Also check the all_button_rects dictionary for clicks (for items not under hover)
            if hasattr(self, 'all_button_rects'):
                for item_id, (button_rect, item_index) in self.all_button_rects.items():
                    if button_rect.contains(pos_f):
                        print(f"Toggle button clicked for item ID: {item_id}")
                        
                        # Toggle compact state for this item
                        is_compact = item_id in self.compact_items
                        
                        if is_compact:
                            self.compact_items.remove(item_id)
                        else:
                            self.compact_items.add(item_id)
                        
                        # Save state to database
                        self.save_compact_state(item_id, not is_compact)
                        
                        # Update the item size
                        item = None
                        if hasattr(tree_widget, 'itemFromIndex'):
                            item = tree_widget.itemFromIndex(item_index)
                        
                        # Update item size if found
                        if item:
                            height = self.compact_height if not is_compact else self.pill_height
                            item.setSizeHint(0, QSize(tree_widget.viewport().width(), 
                                                height + self.item_margin * 2))
                            tree_widget.scheduleDelayedItemsLayout()  # Force layout update
                            print(f"Item size updated, new height: {height}")
                        
                        # Force repaint
                        tree_widget.viewport().update()
                        return True  # Event handled
                        
        return super().eventFilter(source, event)

    def save_compact_state(self, task_id, is_compact):
        """Save compact state to the database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE tasks SET is_compact = ? WHERE id = ?",
                    (1 if is_compact else 0, task_id)
                )
                conn.commit()
        except Exception as e:
            print(f"Error saving compact state: {e}")
    
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

    def paint(self, painter, option, index):
        # Get data from the index
        user_data = index.data(Qt.ItemDataRole.UserRole)
        
        # Check if this is a priority header
        if isinstance(user_data, dict) and user_data.get('is_priority_header', False):
            self._draw_priority_header(painter, option, index, user_data)
        else:
            # Regular task item
            self._draw_task_item(painter, option, index)

    def _draw_priority_header(self, painter, option, index, user_data):
        """Draw a priority header item"""
        # Save painter state
        painter.save()
        
        # Get data
        priority = user_data.get('priority', 'Medium')
        color = user_data.get('color', '#FFC107')
        expanded = user_data.get('expanded', True)
        
        # Calculate rect - REDUCE MARGINS HERE
        rect = option.rect.adjusted(
            self.item_margin,
            self.item_margin,  # Reduce top margin
            -self.item_margin,
            -self.item_margin  # Reduce bottom margin
        )
        
        # Draw background
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 5, 5)
        painter.fillPath(path, QBrush(QColor(color)))
        
        # Draw priority text
        # Get font settings from SettingsManager
        settings = self.get_settings_manager()
        font_family = settings.get_setting("font_family", "Segoe UI")
        font_size = int(settings.get_setting("font_size", 12))
        
        header_font = QFont(font_family)
        header_font.setPointSize(font_size)
        header_font.setBold(True)
        
        painter.setFont(header_font)
        painter.setPen(QColor("#FFFFFF"))
        
        header_text_rect = QRectF(
            rect.left() + 40,  # Position after arrow
            rect.top(),
            rect.width() - 50,
            rect.height()
        )
        
        painter.drawText(header_text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                        priority.upper())
        
        # Restore painter
        painter.restore()

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

    def _draw_description(self, painter, rect, description, font_family, font_size, settings, left_width, right_width):
        """Draw the task description with custom font settings"""
        # Get description style settings
        italic_desc = settings.get_setting("italic_descriptions", False)
        desc_color = settings.get_setting("description_color", "#666666")
        
        # Create description font
        desc_font = QFont(font_family, font_size - 2)  # Slightly smaller
        if italic_desc:
            desc_font.setItalic(True)
        
        painter.setFont(desc_font)
        painter.setPen(QColor(desc_color))
        
        # Define description rect with adjusted panel widths
        desc_rect = QRectF(
            rect.left() + left_width + self.text_padding,
            rect.top() + 30,
            rect.width() - left_width - right_width - self.text_padding * 2,
            30  # Height for description
        )
        
        # Truncate description if too long and add ellipsis
        elidedText = painter.fontMetrics().elidedText(
            description, Qt.TextElideMode.ElideRight, int(desc_rect.width()))
        painter.drawText(desc_rect, Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, elidedText)

    def _draw_due_date(self, painter, rect, is_compact, due_date_str, font_family, font_size, settings, left_width, right_width):
        """Draw the due date with custom font settings"""
        # Get due date style settings
        due_color = settings.get_setting("due_date_color", "#888888")
        
        # Create due date font
        date_font = QFont(font_family, font_size - 2)  # Slightly smaller
        painter.setFont(date_font)
        painter.setPen(QColor(due_color))
        
        if is_compact:
            # In compact mode, show due date below title but still compact
            title_rect_bottom = rect.top() + rect.height() / 2 + 2  # Just below vertical center
            date_rect = QRectF(
                rect.left() + left_width + self.text_padding,
                title_rect_bottom,
                rect.width() - left_width - right_width - self.text_padding * 2,
                rect.height() / 2 - 2
            )
            # Draw text left-aligned
            painter.drawText(date_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, f"Due: {due_date_str}")
        else:
            # In full mode, show due date at bottom
            date_rect = QRectF(
                rect.left() + left_width + self.text_padding,
                rect.top() + rect.height() - 18,
                rect.width() - left_width - right_width - self.text_padding * 2,
                15
            )
            painter.drawText(date_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"Due: {due_date_str}")

    def _draw_toggle_button(self, painter, index, item_id, rect):
        """Draw the toggle button for all items (including headers)"""
        # Get data from the index
        user_data = index.data(Qt.ItemDataRole.UserRole)
        
        # Continue with drawing the toggle button
        if self.hover_item and self.hover_item == index and self.toggle_button_rect:
            # Save current state
            painter.save()

            # Clear any clipping that might interfere
            painter.setClipping(False)

            # Calculate button position - centered at top of pill
            button_size = 24
            button_top = rect.top() - button_size // 2
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

    def sizeHint(self, option, index):
        """Return appropriate size based on compact state or header type"""
        user_data = index.data(Qt.ItemDataRole.UserRole)
        
        # Check if this is a priority header
        if isinstance(user_data, dict) and user_data.get('is_priority_header', False):
            # Use a fixed smaller height for priority headers
            header_height = 25  # Smaller fixed height value
            return QSize(option.rect.width(), header_height + self.item_margin * 2)
        
        # Regular task item sizing
        item_id = 0
        if isinstance(user_data, dict) and 'id' in user_data:
            item_id = user_data['id']
        
        height = self.compact_height if item_id in self.compact_items else self.pill_height
        return QSize(option.rect.width(), height + self.item_margin * 2)

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
        
    def get_settings_manager(self):
        """Get the settings manager instance"""
        try:
            # Try to get it from the tree widget's parent (MainWindow)
            tree_widget = self.parent()
            if tree_widget and hasattr(tree_widget, 'parent') and hasattr(tree_widget.parent(), 'settings'):
                return tree_widget.parent().settings
        except:
            pass
        
        # Fallback to creating a new instance
        from ui.app_settings import SettingsManager
        return SettingsManager()

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