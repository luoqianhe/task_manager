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
        self.pill_height = 60   # Height of the pill
        self.pill_radius = 15   # Corner radius for the pill
        self.item_margin = 5    # Margin between items
        
        # Status colors are now loaded from database
        
        # Priority colors are loaded from database
        self.priority_colors = {}  # Initialize as empty dict
    
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
            return QColor("#000000")  # Default black
            
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
        return QColor(default_priority_colors.get(priority, "#000000"))
    
    def paint(self, painter, option, index):
        # Get data for this item
        title = index.model().data(index.model().index(index.row(), 0, index.parent()))
        description = index.model().data(index.model().index(index.row(), 1, index.parent()))
        link = index.model().data(index.model().index(index.row(), 2, index.parent()))
        status = index.model().data(index.model().index(index.row(), 3, index.parent()))
        priority = index.model().data(index.model().index(index.row(), 4, index.parent()))
        due_date_str = index.model().data(index.model().index(index.row(), 5, index.parent()))
        category = index.model().data(index.model().index(index.row(), 6, index.parent()))
        
        # Get category colors from database
        category_color = QColor(245, 245, 245)  # Default light gray if no category
        if category:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT color FROM categories WHERE name = ?", (category,))
                    result = cursor.fetchone()
                    if result and result[0]:
                        color_str = result[0]
                        category_color = QColor(color_str)
                        print(f"Found category color: {color_str} for category: {category}")  # Debug
                    else:
                        print(f"No color found for category: {category}")  # Debug
            except Exception as e:
                print(f"Error getting category color: {e}")

        # Create transparent version for background
        transparent_category_color = QColor(category_color)
        transparent_category_color.setAlpha(80)  # Increase alpha for more visibility (0-255)
        
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
        rectF = QRectF(rect)  # Convert QRect to QRectF
        path.addRoundedRect(rectF, self.pill_radius, self.pill_radius)
        
        # Draw selection highlight if item is selected
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 120, 215, 40)))  # Light blue transparent
            painter.drawPath(path)
        
        # Calculate section widths
        status_section_width = 120  # Width of the status section
        details_section_width = 150  # Width of the details section
        content_section_width = rect.width() - status_section_width - details_section_width
        
        # Get status color from database
        status_color = self.get_status_color(status)
        
        # Draw pill background with category color for better visibility
        painter.setPen(QPen(QColor("#cccccc"), 1))
        painter.setBrush(QBrush(transparent_category_color))
        painter.drawPath(path)
        
        # Draw status section (left section)
        status_rect = QRectF(
            rect.left(),
            rect.top(),
            status_section_width,
            rect.height()
        )
        status_path = QPainterPath()
        status_path.addRoundedRect(status_rect, self.pill_radius, self.pill_radius)
        
        # Clip to left part of the pill
        painter.setClipRect(QRectF(rect.left(), rect.top(), status_section_width + self.pill_radius, rect.height()))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(status_color))
        painter.drawPath(status_path)
        painter.setClipping(False)
        
        # Draw first vertical divider
        painter.setPen(QPen(QColor("#cccccc"), 1))
        painter.drawLine(
            rect.left() + status_section_width,
            rect.top(),
            rect.left() + status_section_width,
            rect.bottom()
        )
        
        # Draw details section (right section)
        details_rect = QRectF(
            rect.right() - details_section_width,
            rect.top(),
            details_section_width,
            rect.height()
        )
        details_path = QPainterPath()
        details_path.addRoundedRect(details_rect, self.pill_radius, self.pill_radius)
        
        # Clip to right part of the pill
        painter.setClipRect(QRectF(rect.right() - details_section_width - self.pill_radius, rect.top(), details_section_width + self.pill_radius, rect.height()))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#f5f5f5")))  # Light gray background
        painter.drawPath(details_path)
        painter.setClipping(False)
        
        # Draw second vertical divider
        painter.setPen(QPen(QColor("#cccccc"), 1))
        painter.drawLine(
            rect.right() - details_section_width,
            rect.top(),
            rect.right() - details_section_width,
            rect.bottom()
        )
        
        # Draw status text in status section
        status_font = QFont(option.font)
        status_font.setPointSize(10)
        painter.setFont(status_font)
        painter.setPen(QColor("white"))  # White text on colored background
        
        status_text_rect = QRectF(
            rect.left(),
            rect.top(),
            status_section_width,
            rect.height()
        )
        painter.drawText(status_text_rect, Qt.AlignmentFlag.AlignCenter, status or "Not Started")
        
        # Draw task content in the middle section
        # Title - bold
        title_font = QFont(option.font)
        title_font.setBold(True)
        title_font.setPointSize(10)
        painter.setFont(title_font)
        painter.setPen(QColor(0, 0, 0))  # Black text
        
        title_rect = QRectF(
            rect.left() + status_section_width + self.text_padding,
            rect.top() + 5,
            content_section_width - self.text_padding * 2,
            20  # Height for title
        )
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title or "")
        
        # Description - smaller gray text
        if description:
            desc_font = QFont(option.font)
            desc_font.setPointSize(8)
            painter.setFont(desc_font)
            painter.setPen(QColor(100, 100, 100))  # Gray text
            
            desc_rect = QRectF(
                rect.left() + status_section_width + self.text_padding,
                rect.top() + 25,
                content_section_width - self.text_padding * 2,
                20  # Height for description
            )
            # Truncate description if too long
            elidedText = painter.fontMetrics().elidedText(
                description, Qt.TextElideMode.ElideRight, int(desc_rect.width()))
            painter.drawText(desc_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elidedText)
        
        # Draw priority text
        if priority:
            priority_font = QFont(option.font)
            priority_font.setPointSize(8)
            painter.setFont(priority_font)
            
            # Use the priority color for the text
            priority_color = self.get_priority_color(priority)
            painter.setPen(priority_color)
            
            priority_text_rect = QRectF(
                rect.left() + status_section_width + self.text_padding,
                rect.top() + rect.height() - 18,
                content_section_width,
                15
            )
            painter.drawText(priority_text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"Priority: {priority}")
        
        # Draw details section (URL or attached files)
        if link:
            link_font = QFont(option.font)
            link_font.setPointSize(8)
            painter.setFont(link_font)
            painter.setPen(QColor(0, 0, 255))  # Blue text for link
            
            # Draw link icon
            link_icon_rect = QRectF(
                rect.right() - details_section_width + 10,
                rect.top() + (rect.height() - 16) / 2,
                16, 16
            )
            # You could draw a custom icon here, but for simplicity we'll just use a colored circle
            painter.setBrush(QBrush(QColor(0, 0, 255, 50)))  # Transparent blue
            painter.setPen(QPen(QColor(0, 0, 255), 1))
            painter.drawEllipse(link_icon_rect)
            
            # Draw link text
            link_text_rect = QRectF(
                rect.right() - details_section_width + 30,
                rect.top(),
                details_section_width - 40,
                rect.height()
            )
            
            # Truncate link if too long
            display_link = link
            if len(display_link) > 25:
                if display_link.startswith("http://"):
                    display_link = display_link[7:]
                elif display_link.startswith("https://"):
                    display_link = display_link[8:]
                
                # Further truncate if still too long
                if len(display_link) > 25:
                    display_link = display_link[:22] + "..."
                    
            painter.drawText(link_text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, display_link)
        else:
            # Draw "No details" text
            font = QFont(option.font)
            font.setPointSize(8)
            painter.setFont(font)
            painter.setPen(QColor(150, 150, 150))  # Light gray text
            painter.drawText(
                QRectF(rect.right() - details_section_width, rect.top(), details_section_width, rect.height()),
                Qt.AlignmentFlag.AlignCenter,
                "No details"
            )
        
        # Restore painter
        painter.restore()
    
    def sizeHint(self, option, index):
        # Return a size that accounts for our custom drawing
        return QSize(option.rect.width(), self.pill_height + self.item_margin * 2)