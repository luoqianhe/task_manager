# src/test_tree.py

from PyQt6.QtWidgets import QMainWindow, QApplication, QWidget, QVBoxLayout, QPushButton
from ui.chat_tree import ChatTreeWidget

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chat Tree Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Create layout for central widget
        layout = QVBoxLayout()
        central.setLayout(layout)
        
        # Add tree
        self.tree = ChatTreeWidget()
        layout.addWidget(self.tree)
        
        # Add button
        add_button = QPushButton("Add New Chat")
        add_button.setFixedHeight(30)
        add_button.clicked.connect(self.show_add_dialog)
        layout.addWidget(add_button)
    
    def show_add_dialog(self):
        from ui.chat_dialogs import AddChatDialog
        dialog = AddChatDialog(self)
        if dialog.exec():
            self.tree.add_new_chat(dialog.get_data())

def main():
    import sys
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()