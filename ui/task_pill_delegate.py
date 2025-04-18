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
        self.left_section_width = 100
        self.right_section_width = 100
        
        # Hover tracking
        self.hover_item = None
        self.toggle_button_rect = None
        self.all_button_rects = {}
        
        # Track compact states
        self.compact_items = set()
        self.load_compact_states()
        
        # Install event filter on parent widget's viewport
        if parent:
            print("Setting up mouse tracking and event filter")
            parent.setMouseTracking(True)
            parent.viewport().setMouseTracking(True)
            
            # Install event filter on both parent and viewport for redundancy
            parent.installEventFilter(self)
            parent.viewport().installEventFilter(self)
            print("Event filter installed on parent viewport")

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
                    print("Added is_compact column to tasks table")
                
                # Now load all task IDs that are marked as compact
                cursor.execute("SELECT id FROM tasks WHERE is_compact = 1")
                for row in cursor.fetchall():
                    self.compact_items.add(row[0])
                
                print(f"Loaded {len(self.compact_items)} compact states from database")
        except Exception as e:
            print(f"Error loading compact states: {e}")
    
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

    def _draw_task_item(self, painter, option, index):
        """Draw a regular task item - modified to include category and status indicators"""
        # Extract data using our existing method
        user_data, item_id, title, description, link, status, priority, due_date_str, category = self._extract_item_data(index)
        
        # Check if compact
        is_compact = item_id in self.compact_items
        
        # Get the category and status colors
        category_color = self.get_category_color(category)
        status_color = self.get_status_color(status)
        
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
        
        # Draw category and status indicators on the left - get the width used
        try:
            left_section_width = self._draw_category_indicator(painter, path, rect, is_compact, 
                                        category_color, status_color, category, status)
            # Ensure we have a valid width even if None is returned
            if left_section_width is None:
                left_section_width = 60  # Default fallback width
        except Exception as e:
            print(f"Error in _draw_category_indicator: {e}")
            left_section_width = 60  # Default fallback width if exception occurs
        
        # Draw content (title, description, due date) - pass the left_section_width
        self._draw_task_content(painter, rect, is_compact, title, description, due_date_str, item_id, left_section_width)
        
        # Draw right details section
        self._draw_right_panel(painter, path, rect, link)
        
        # Draw toggle button if needed
        self._draw_toggle_button(painter, index, item_id, rect)
        
        # Restore painter
        painter.restore()

    def _draw_category_indicator(self, painter, path, rect, is_compact, category_color, status_color, category, status):
        """Draw category and status indicators in the left side of the task pill with auto-adjusting width"""
        # Get font settings from SettingsManager to apply the same font family
        settings = self.get_settings_manager()
        font_family = settings.get_setting("font_family", "Segoe UI")
        left_panel_color = settings.get_setting("left_panel_color", "#FFFFFF")
        left_panel_size = int(settings.get_setting("left_panel_size", 8))
        left_panel_bold = settings.get_setting("left_panel_bold", False)
        
        # Set up font for text measurement
        left_panel_font = QFont(font_family)
        left_panel_font.setPointSize(left_panel_size)
        if left_panel_bold:
            left_panel_font.setBold(True)
        
        # Measure text width
        font_metrics = QFontMetrics(left_panel_font)
        category_text = category or "No Cat"
        status_text = status or "No Status"
        
        # Calculate width needed for each label (adding padding)
        category_width = font_metrics.horizontalAdvance(category_text) + 20  # 10px padding on each side
        status_width = font_metrics.horizontalAdvance(status_text) + 20
        
        # Use the wider of the two with a minimum of 40px and maximum of 100px
        left_section_width = max(40, min(100, max(category_width, status_width)))
        
        # Use clipping to ensure proper drawing within the pill
        painter.setClipPath(path)
        
        # Split the left section into two parts - top half for category, bottom half for status
        category_rect = QRectF(
            rect.left(),
            rect.top(),
            left_section_width,  # Auto-adjusted width
            rect.height() / 2  # Top half for category
        )
        
        status_rect = QRectF(
            rect.left(),
            rect.top() + rect.height() / 2,  # Start at middle
            left_section_width,  # Auto-adjusted width
            rect.height() / 2  # Bottom half for status
        )
        
        # Fill the category section
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(category_color))
        painter.drawRect(category_rect)
        
        # Fill the status section
        painter.setBrush(QBrush(status_color))
        painter.drawRect(status_rect)
        
        # Draw labels in the sections if not compact view
        if not is_compact:
            painter.setFont(left_panel_font)
            painter.setPen(QColor(left_panel_color))
            
            # Draw category label - centered in the category rect
            painter.drawText(
                category_rect,
                Qt.AlignmentFlag.AlignCenter,
                category_text
            )
            
            # Draw status label - centered in the status rect
            painter.drawText(
                status_rect,
                Qt.AlignmentFlag.AlignCenter,
                status_text
            )
        
        # Remove clipping
        painter.setClipping(False)
        
        # Draw a divider line at the new position
        painter.setPen(QPen(QColor("#cccccc"), 1))
        painter.drawLine(
            rect.left() + left_section_width,  # Updated right edge of indicators
            rect.top(),
            rect.left() + left_section_width,
            rect.bottom()
        )
        
        # Make sure to return the width value
        return left_section_width

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

    def _draw_left_panel(self, painter, path, rect, is_compact, priority, priority_color, category, category_color, status, status_color):
        """Draw the left panel with priority, category and status sections"""
        # Calculate section heights
        section_height = rect.height() / 3
        
        # Get settings for left panel text
        settings = self.get_settings_manager()
        left_panel_color = settings.get_setting("left_panel_color", "#FFFFFF")
        left_panel_size = int(settings.get_setting("left_panel_size", 8))
        left_panel_bold = settings.get_setting("left_panel_bold", False)
        
        # Use clipping to ensure proper drawing within the pill
        painter.setClipPath(path)
        
        # Draw priority section (top left)
        priority_rect = QRectF(
            rect.left(),
            rect.top(),
            self.left_section_width,
            section_height
        )
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(priority_color))
        painter.drawRect(priority_rect)
        
        # Draw priority text on top of the color (only in full mode)
        if not is_compact:
            # Set up font for left panel text
            left_panel_font = QFont(painter.font())
            left_panel_font.setPointSize(left_panel_size)
            if left_panel_bold:
                left_panel_font.setBold(True)
                
            painter.setFont(left_panel_font)
            painter.setPen(QColor(left_panel_color))  # Use custom text color
            
            painter.drawText(
                priority_rect,
                Qt.AlignmentFlag.AlignCenter,
                priority or "No Priority"
            )
        
        # Draw category section (middle left)
        category_rect = QRectF(
            rect.left(),
            rect.top() + section_height,
            self.left_section_width,
            section_height
        )
        painter.setBrush(QBrush(category_color))
        painter.drawRect(category_rect)
        
        # Draw category text (only in full mode)
        if not is_compact:
            painter.drawText(
                category_rect,
                Qt.AlignmentFlag.AlignCenter,
                category or "No Category"
            )
        
        # Draw status section (bottom left)
        status_rect = QRectF(
            rect.left(),
            rect.top() + section_height * 2,
            self.left_section_width,
            section_height
        )
        painter.setBrush(QBrush(status_color))
        painter.drawRect(status_rect)
        
        # Draw status text (only in full mode)
        if not is_compact:
            painter.drawText(
                status_rect,
                Qt.AlignmentFlag.AlignCenter,
                status or "Not Started"
            )
        
        # Remove clipping
        painter.setClipping(False)
        
        # Draw left divider line
        painter.setPen(QPen(QColor("#cccccc"), 1))
        painter.drawLine(
            rect.left() + self.left_section_width,
            rect.top(),
            rect.left() + self.left_section_width,
            rect.bottom()
        )

    def _draw_task_content(self, painter, rect, is_compact, title, description, due_date_str, item_id, left_section_width):
        """Draw the main task content (title, description, due date)"""
        # Get font settings from SettingsManager
        settings = self.get_settings_manager()
        font_family = settings.get_setting("font_family", "Segoe UI")
        font_size = int(settings.get_setting("font_size", 10))
        
        # Draw the title with custom font settings
        self._draw_title(painter, rect, is_compact, title, font_family, font_size, settings, left_section_width)
        
        # Draw description if in full mode
        if not is_compact and description:
            self._draw_description(painter, rect, description, font_family, font_size, settings, left_section_width)
        
        # Draw due date if available
        if due_date_str:
            self._draw_due_date(painter, rect, is_compact, due_date_str, font_family, font_size, settings, left_section_width)
            
    def _draw_title(self, painter, rect, is_compact, title, font_family, font_size, settings, left_section_width):
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
        
        # Define title_rect based on compact mode - using the updated left_section_width
        if is_compact:
            # In compact mode, title takes top half width
            title_rect = QRectF(
                rect.left() + left_section_width + self.text_padding,
                rect.top(),
                rect.width() - left_section_width - self.right_section_width - self.text_padding * 2,
                rect.height() / 2  # Only take the top half now
            )
        else:
            # In full mode, title is at the top
            title_rect = QRectF(
                rect.left() + left_section_width + self.text_padding,
                rect.top() + 10,
                rect.width() - left_section_width - self.right_section_width - self.text_padding * 2,
                20  # Height for title
            )

        # Draw title with ellipsis if too long
        elidedTitle = painter.fontMetrics().elidedText(
            title, Qt.TextElideMode.ElideRight, int(title_rect.width()))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elidedTitle)

    def _draw_description(self, painter, rect, description, font_family, font_size, settings, left_section_width):
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
        
        # Define description rect - using left_section_width
        desc_rect = QRectF(
            rect.left() + left_section_width + self.text_padding,
            rect.top() + 30,
            rect.width() - left_section_width - self.right_section_width - self.text_padding * 2,
            30  # Height for description
        )
        
        # Truncate description if too long and add ellipsis
        elidedText = painter.fontMetrics().elidedText(
            description, Qt.TextElideMode.ElideRight, int(desc_rect.width()))
        painter.drawText(desc_rect, Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, elidedText)

    def _draw_due_date(self, painter, rect, is_compact, due_date_str, font_family, font_size, settings, left_section_width):
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
                rect.left() + left_section_width + self.text_padding,  # Use left_section_width
                title_rect_bottom,
                rect.width() - left_section_width - self.right_section_width - self.text_padding * 2,
                rect.height() / 2 - 2
            )
            # Draw text left-aligned
            painter.drawText(date_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, f"Due: {due_date_str}")
        else:
            # In full mode, show due date at bottom
            date_rect = QRectF(
                rect.left() + left_section_width + self.text_padding,  # Use left_section_width
                rect.top() + rect.height() - 18,
                rect.width() - left_section_width - self.right_section_width - self.text_padding * 2,
                15
            )
            painter.drawText(date_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"Due: {due_date_str}")

    def _draw_right_panel(self, painter, path, rect, link):
        """Draw the right details section (Link indicator)"""
        # Draw right details section
        details_rect = QRectF(
            rect.right() - self.right_section_width,
            rect.top(),
            self.right_section_width,
            rect.height()
        )
        
        # Use the same clipping approach
        painter.setClipPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#f5f5f5")))  # Light gray background
        painter.drawRect(details_rect)
        painter.setClipping(False)
        
        # Draw second vertical divider
        painter.setPen(QPen(QColor("#cccccc"), 1))
        painter.drawLine(
            rect.right() - self.right_section_width,
            rect.top(),
            rect.right() - self.right_section_width,
            rect.bottom()
        )
        
        # Draw details section (Link)
        if link:
            link_font = QFont(painter.font())
            link_font.setPointSize(9)
            painter.setFont(link_font)
            painter.setPen(QColor(0, 0, 255))  # Blue text for link
            
            # Draw link icon
            link_icon_rect = QRectF(
                rect.right() - self.right_section_width + 20,
                rect.top() + (rect.height() - 16) / 2,
                16, 16
            )
            # Draw a simple link icon as a circle
            painter.setBrush(QBrush(QColor(0, 0, 255, 50)))  # Transparent blue
            painter.setPen(QPen(QColor(0, 0, 255), 1))
            painter.drawEllipse(link_icon_rect)
            
            # Draw "Link" text
            link_text_rect = QRectF(
                rect.right() - self.right_section_width + 40,
                rect.top(),
                self.right_section_width - 50,
                rect.height()
            )
            painter.drawText(link_text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Link")
        else:
            # Draw "No Link" text
            font = QFont(painter.font())
            font.setPointSize(8)
            painter.setFont(font)
            painter.setPen(QColor(150, 150, 150))  # Light gray text
            painter.drawText(
                QRectF(rect.right() - self.right_section_width, rect.top(), self.right_section_width, rect.height()),
                Qt.AlignmentFlag.AlignCenter,
                "No Link"
            )

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