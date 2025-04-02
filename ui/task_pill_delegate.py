# src/ui/task_pill_delegate.py

from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QApplication, QStyle
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QBrush, QPen, QFont
from PyQt6.QtCore import QRectF, Qt, QSize, QPoint
from datetime import datetime, date
import sqlite3
from pathlib import Path

class TaskPillDelegate(QStyledItemDelegate):
    @staticmethod
    def get_connection():
        # This will be overridden in main.py to use the database manager
        from database.database_manager import get_db_manager
        return get_db_manager().get_connection()
    
    # Key updates to TaskPillDelegate class

    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_padding = 10  # Padding between text and pill edge
        self.pill_height = 80   # Default pill height (full view)
        self.compact_height = 40  # Compact pill height
        self.pill_radius = 15   # Corner radius for the pill
        self.item_margin = 5    # Margin between items
        self.left_section_width = 100  # Width of the left section
        self.right_section_width = 100  # Width of the right section
        
        # Track hover state and button position for each item
        self.hover_item = None
        self.hover_rect = None
        self.toggle_button_rect = None
        
        # Track compact/expanded state for each item - will be loaded from DB
        self.compact_items = set()
        
        # Load initial compact states from database
        self.load_compact_states()
        
        # Install event filter on parent for hover tracking
        if parent:
            parent.setMouseTracking(True)
            parent.viewport().setMouseTracking(True)  # IMPORTANT: Set on viewport too
            parent.installEventFilter(self)
            print("Event filter installed on parent widget")

    def eventFilter(self, source, event):
        """Handle mouse events for button clicks"""
        if event.type() == event.Type.MouseButtonPress:
            print("Mouse button press detected")
            # Get position
            try:
                if hasattr(event, 'position'):
                    pos = event.position().toPoint()
                elif hasattr(event, 'pos'):
                    pos = event.pos()
                else:
                    pos = event.globalPos()
            except Exception as e:
                print(f"Error getting mouse position: {e}")
                return super().eventFilter(source, event)
                
            # Check if click was on any toggle button
            if hasattr(self, 'all_button_rects'):
                for item_id, (button_rect, index) in self.all_button_rects.items():
                    if button_rect.contains(pos):
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
                        if hasattr(source, 'itemFromIndex'):
                            item = source.itemFromIndex(index)
                        else:
                            # Find item by ID
                            for i in range(source.topLevelItemCount()):
                                if self._find_item_by_id(source.topLevelItem(i), item_id):
                                    item = self._find_item_by_id(source.topLevelItem(i), item_id)
                                    break
                        
                        # Update item size if found
                        if item:
                            height = self.compact_height if not is_compact else self.pill_height
                            item.setSizeHint(0, QSize(self.all_button_rects[item_id][0].width() * 10, 
                                                height + self.item_margin * 2))
                            source.scheduleDelayedItemsLayout()  # Force layout update
                            print(f"Item size updated, new height: {height}")
                        
                        # Force repaint
                        source.viewport().update()
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
        # Get data directly from UserRole since we're using a single column tree
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
        
        # Check if this item should be compact
        is_compact = item_id in self.compact_items
        
        # Get colors for status, priority, and category
        status_color = self.get_status_color(status)
        priority_color = self.get_priority_color(priority)
        category_color = self.get_category_color(category)
        
        # Save painter state
        painter.save()
        
        # Prepare to draw
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
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
        
        # Draw selection highlight if item is selected
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 120, 215, 40)))  # Light blue transparent
            painter.drawPath(path)
        
        # Draw the main pill first
        painter.setPen(QPen(QColor("#cccccc"), 1))
        painter.setBrush(QBrush(QColor("#f5f5f5")))
        painter.drawPath(path)
        
        # Calculate section heights for the left panel
        # In compact mode, make each section smaller but preserve all three
        if is_compact:
            section_height = rect.height() / 3
        else:
            section_height = rect.height() / 3
        
        # Draw priority section (top left)
        priority_rect = QRectF(
            rect.left(),
            rect.top(),
            self.left_section_width,
            section_height
        )
        
        # Use clipping to ensure proper drawing within the pill
        painter.setClipPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(priority_color))
        painter.drawRect(priority_rect)
        
        # Draw priority text on top of the color (only in full mode)
        if not is_compact:
            font = QFont(option.font)
            font.setPointSize(7)  # Small font size to fit in the section
            painter.setFont(font)
            painter.setPen(QColor("white"))  # White text on colored background
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
        
        # Draw task title (bold)
        title_font = QFont(option.font)
        title_font.setBold(True)
        title_font.setPointSize(10)
        painter.setFont(title_font)
        painter.setPen(QColor(0, 0, 0))  # Black text
        
        if is_compact:
            # In compact mode, title takes full width
            title_rect = QRectF(
                rect.left() + self.left_section_width + self.text_padding,
                rect.top(),
                rect.width() - self.left_section_width - self.right_section_width - self.text_padding * 2,
                rect.height()
            )
        else:
            # In full mode, title is at the top
            title_rect = QRectF(
                rect.left() + self.left_section_width + self.text_padding,
                rect.top() + 10,
                rect.width() - self.left_section_width - self.right_section_width - self.text_padding * 2,
                20  # Height for title
            )
        
        # Draw title with ellipsis if too long
        elidedTitle = painter.fontMetrics().elidedText(
            title, Qt.TextElideMode.ElideRight, int(title_rect.width()))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elidedTitle)
        
        # In full mode, draw description
        if not is_compact and description:
            desc_font = QFont(option.font)
            desc_font.setPointSize(8)
            painter.setFont(desc_font)
            painter.setPen(QColor(100, 100, 100))  # Gray text
            
            desc_rect = QRectF(
                rect.left() + self.left_section_width + self.text_padding,
                rect.top() + 30,
                rect.width() - self.left_section_width - self.right_section_width - self.text_padding * 2,
                30  # Height for description
            )
            # Truncate description if too long and add ellipsis
            elidedText = painter.fontMetrics().elidedText(
                description, Qt.TextElideMode.ElideRight, int(desc_rect.width()))
            painter.drawText(desc_rect, Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, elidedText)
        
        # Draw due date if available
        if due_date_str:
            date_font = QFont(option.font)
            date_font.setPointSize(8)
            painter.setFont(date_font)
            painter.setPen(QColor(100, 100, 100))  # Gray text
            
            if is_compact:
                # In compact mode, show due date next to title
                title_width = painter.fontMetrics().horizontalAdvance(elidedTitle)
                date_rect = QRectF(
                    rect.left() + self.left_section_width + self.text_padding + title_width + 15,
                    rect.top(),
                    150,  # Fixed width for due date
                    rect.height()
                )
            else:
                # In full mode, show due date at bottom
                date_rect = QRectF(
                    rect.left() + self.left_section_width + self.text_padding,
                    rect.top() + rect.height() - 18,
                    rect.width() - self.left_section_width - self.right_section_width - self.text_padding * 2,
                    15
                )
            
            painter.drawText(date_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"Due: {due_date_str}")
        
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
            link_font = QFont(option.font)
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
            font = QFont(option.font)
            font.setPointSize(8)
            painter.setFont(font)
            painter.setPen(QColor(150, 150, 150))  # Light gray text
            painter.drawText(
                QRectF(rect.right() - self.right_section_width, rect.top(), self.right_section_width, rect.height()),
                Qt.AlignmentFlag.AlignCenter,
                "No Link"
            )
        
        # Draw toggle button if this is the hover item
        if self.hover_item and self.hover_item == index and self.toggle_button_rect:
            print(f"Drawing toggle button for item {index.row()}")
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
            painter.setBrush(QBrush(QColor(0, 0, 0, 30)))  # Semi-transparent black
            painter.drawEllipse(shadow_rect)

            # Draw button with strong border and bright fill
            painter.setPen(QPen(QColor("#333333"), 2))  # Thicker, darker border

            # Highlight button based on state
            if item_id in self.compact_items:
                # Expanded button (up arrow) - bright green
                painter.setBrush(QBrush(QColor(100, 255, 100)))
            else:
                # Collapse button (down arrow) - bright blue
                painter.setBrush(QBrush(QColor(100, 200, 255)))

            painter.drawEllipse(toggle_button_rect)

            # Draw arrow icon with larger font
            toggle_font = QFont(option.font)
            toggle_font.setPointSize(16)  # Larger size
            toggle_font.setBold(True)
            painter.setFont(toggle_font)
            painter.setPen(QColor("#000000"))  # Black text for better visibility

            # Show up arrow if compact (to expand), down arrow if expanded (to compact)
            icon = "↑" if item_id in self.compact_items else "↓"
            painter.drawText(toggle_button_rect, Qt.AlignmentFlag.AlignCenter, icon)

            # Store button rect for click detection (even when not hovering)
            if not hasattr(self, 'all_button_rects'):
                self.all_button_rects = {}
            self.all_button_rects[item_id] = (toggle_button_rect, index)

            # Restore painting settings
            painter.restore()        
        # Restore painter
        painter.restore()
    
    def sizeHint(self, option, index):
        """Return appropriate size based on compact state"""
        user_data = index.data(Qt.ItemDataRole.UserRole)
        
        # Get item ID and check if it's in the compact_items set
        item_id = 0
        if isinstance(user_data, dict) and 'id' in user_data:
            item_id = user_data['id']
        
        height = self.compact_height if item_id in self.compact_items else self.pill_height
        
        return QSize(option.rect.width(), height + self.item_margin * 2)