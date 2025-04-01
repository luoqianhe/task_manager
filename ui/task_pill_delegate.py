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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_padding = 10  # Padding between text and pill edge
        self.pill_height = 80   # Reduced height of the pill
        self.pill_radius = 15   # Corner radius for the pill
        self.item_margin = 5    # Margin between items
        self.left_section_width = 100  # Width of the left section - slightly reduced
        self.right_section_width = 100  # Width of the right section - slightly reduced
    
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
    
    def paint(self, painter, option, index):
        # Get data directly from UserRole since we're using a single column tree
        user_data = index.data(Qt.ItemDataRole.UserRole)
        
        # Extract all data from the dictionary stored in UserRole
        if isinstance(user_data, dict):
            title = user_data.get('title', '')
            description = user_data.get('description', '')
            link = user_data.get('link', '')
            status = user_data.get('status', 'Not Started')
            priority = user_data.get('priority', '')
            due_date_str = user_data.get('due_date', '')
            category = user_data.get('category', '')
        else:
            # Fallback if UserRole data is missing or malformed
            title = index.data(Qt.ItemDataRole.DisplayRole) or ""
            description = link = ""
            status = "Not Started"
            priority = ""
            due_date_str = ""
            category = ""
        
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
        
        # Calculate section positions and heights
        left_section_width = self.left_section_width
        right_section_width = self.right_section_width
        content_section_width = rect.width() - left_section_width - right_section_width
        section_height = rect.height() / 3  # Divide left panel into 3 equal sections
        
        # Note: The main pill is drawn right before drawing the priority section
        
        # Draw priority section (top left)
        priority_rect = QRectF(
            rect.left(),
            rect.top(),
            left_section_width,
            section_height
        )
        
        # Draw the main pill first
        painter.setPen(QPen(QColor("#cccccc"), 1))
        painter.setBrush(QBrush(QColor("#f5f5f5")))
        painter.drawPath(path)
        
        # Draw priority section (top left)
        priority_rect = QRectF(
            rect.left(),
            rect.top(),
            left_section_width,
            section_height
        )
        
        # Create a path for the top-left section with top-left corner rounded
        priority_path = QPainterPath()
        priority_path.addRoundedRect(priority_rect, self.pill_radius, self.pill_radius)
        
        # Use clipping to only show the part within the main pill
        painter.setClipPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(priority_color))
        painter.drawRect(priority_rect)
        
        # Draw category section (middle left) - simple rectangle for middle section
        category_rect = QRectF(
            rect.left(),
            rect.top() + section_height,
            left_section_width,
            section_height
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(category_color))
        painter.drawRect(category_rect)
        
        # Draw status section (bottom left)
        status_rect = QRectF(
            rect.left(),
            rect.top() + section_height * 2,
            left_section_width,
            section_height
        )
        
        # Draw status section (bottom left)
        status_rect = QRectF(
            rect.left(),
            rect.top() + section_height * 2,
            left_section_width,
            section_height
        )
        
        # Use the same clipping approach for consistency
        painter.setClipPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(status_color))
        painter.drawRect(status_rect)
        
        # Draw first vertical divider
        painter.setPen(QPen(QColor("#cccccc"), 1))
        painter.drawLine(
            rect.left() + left_section_width,
            rect.top(),
            rect.left() + left_section_width,
            rect.bottom()
        )
        
        # Draw right details section
        details_rect = QRectF(
            rect.right() - right_section_width,
            rect.top(),
            right_section_width,
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
            rect.right() - right_section_width,
            rect.top(),
            rect.right() - right_section_width,
            rect.bottom()
        )
        
        # Draw priority text in priority section
        font = QFont(option.font)
        font.setPointSize(10)
        painter.setFont(font)
        painter.setPen(QColor("white"))  # White text on colored background
        
        painter.drawText(
            QRectF(
                rect.left(),
                rect.top(),
                left_section_width,
                section_height
            ),
            Qt.AlignmentFlag.AlignCenter,
            priority or "No Priority"
        )
        
        # Draw category text in category section
        painter.drawText(
            QRectF(
                rect.left(),
                rect.top() + section_height,
                left_section_width,
                section_height
            ),
            Qt.AlignmentFlag.AlignCenter,
            category or "No Category"
        )
        
        # Draw status text in status section
        painter.drawText(
            QRectF(
                rect.left(),
                rect.top() + section_height * 2,
                left_section_width,
                section_height
            ),
            Qt.AlignmentFlag.AlignCenter,
            status or "Not Started"
        )
        
        # Draw task content in the middle section
        # Title - bold
        title_font = QFont(option.font)
        title_font.setBold(True)
        title_font.setPointSize(10)
        painter.setFont(title_font)
        painter.setPen(QColor(0, 0, 0))  # Black text
        
        title_rect = QRectF(
            rect.left() + left_section_width + self.text_padding,
            rect.top() + 10,
            content_section_width - self.text_padding * 2,
            30  # Height for title
        )
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title or "")
        
        # Description - smaller gray text
        if description:
            desc_font = QFont(option.font)
            desc_font.setPointSize(8)
            painter.setFont(desc_font)
            painter.setPen(QColor(100, 100, 100))  # Gray text
            
            desc_rect = QRectF(
                rect.left() + left_section_width + self.text_padding,
                rect.top() + 40,
                content_section_width - self.text_padding * 2,
                40  # Height for description
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
            
            date_rect = QRectF(
                rect.left() + left_section_width + self.text_padding,
                rect.top() + rect.height() - 30,
                content_section_width,
                20
            )
            painter.drawText(date_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"Due: {due_date_str}")
        
        # Draw details section (Link)
        if link:
            link_font = QFont(option.font)
            link_font.setPointSize(10)
            painter.setFont(link_font)
            painter.setPen(QColor(0, 0, 255))  # Blue text for link
            
            # Draw link icon
            link_icon_rect = QRectF(
                rect.right() - right_section_width + 25,
                rect.top() + (rect.height() - 20) / 2,
                20, 20
            )
            # Draw a simple link icon as a circle
            painter.setBrush(QBrush(QColor(0, 0, 255, 50)))  # Transparent blue
            painter.setPen(QPen(QColor(0, 0, 255), 1))
            painter.drawEllipse(link_icon_rect)
            
            # Draw "Link" text
            link_text_rect = QRectF(
                rect.right() - right_section_width + 50,
                rect.top(),
                right_section_width - 60,
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
                QRectF(rect.right() - right_section_width, rect.top(), right_section_width, rect.height()),
                Qt.AlignmentFlag.AlignCenter,
                "No Link"
            )
        
        # Restore painter
        painter.restore()
    
    def sizeHint(self, option, index):
        # Return a size that accounts for our custom drawing
        # Increased height to accommodate the three sections on the left
        return QSize(option.rect.width(), self.pill_height + self.item_margin * 2)