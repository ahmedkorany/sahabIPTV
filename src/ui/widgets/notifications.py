from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QApplication, QSizePolicy
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRect, QPoint
from PyQt5.QtGui import QPixmap, QIcon, QFont, QColor, QPainter, QBrush

class NotificationPopup(QWidget):
    closed = pyqtSignal()

    def __init__(self, title, message, type='info', parent=None, timeout=7000, action_callback=None):
        super().__init__(parent)

        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose) # Important for cleanup

        self.action_callback = action_callback
        self.timeout = timeout
        self.type = type

        self._init_ui(title, message)

        if self.timeout > 0:
            QTimer.singleShot(self.timeout, self.close)

    def _init_ui(self, title, message):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10) # Add some margins for shadow/border effect

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(32, 32)
        self.icon_label.setScaledContents(True)
        main_layout.addWidget(self.icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        self.title_label = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        self.title_label.setFont(title_font)
        text_layout.addWidget(self.title_label)

        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        message_font = QFont()
        message_font.setPointSize(10)
        self.message_label.setFont(message_font)
        self.message_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        text_layout.addWidget(self.message_label)

        main_layout.addLayout(text_layout)
        main_layout.addStretch() # Push close button to the right if needed, or keep it tight

        self.close_button = QPushButton("✕") # Using a more common 'X'
        self.close_button.setFixedSize(24, 24)
        font = QFont()
        font.setPointSize(10)
        self.close_button.setFont(font)
        self.close_button.setStyleSheet("background: transparent; border: none; color: #aaa;")
        self.close_button.clicked.connect(self.close)

        # Add close button to a VBox to align it top-right if main_layout is QHBoxLayout
        close_btn_layout = QVBoxLayout()
        close_btn_layout.addWidget(self.close_button, 0, Qt.AlignTop)
        main_layout.addLayout(close_btn_layout)


        self.set_type_styling()
        self.setMinimumWidth(300) # Ensure a minimum width
        self.setMaximumWidth(400) # And a maximum width
        self.adjustSize() # Adjust size to content

    def set_type_styling(self):
        icon_size = 32  # For QStyle icons
        if self.type == 'success':
            icon = QApplication.style().standardIcon(QApplication.style().SP_MessageBoxInformation) # Using Info as success
            self.bg_color = QColor(220, 255, 220, 230) # Light green, slightly transparent
            self.border_color = QColor(0, 128, 0, 200)   # Darker green
            self.title_color = QColor(0, 100, 0)
            self.message_color = QColor(0, 0, 0)
        elif self.type == 'error':
            icon = QApplication.style().standardIcon(QApplication.style().SP_MessageBoxCritical)
            self.bg_color = QColor(255, 220, 220, 230) # Light red
            self.border_color = QColor(128, 0, 0, 200)    # Darker red
            self.title_color = QColor(100, 0, 0)
            self.message_color = QColor(0, 0, 0)
        else: # info
            icon = QApplication.style().standardIcon(QApplication.style().SP_MessageBoxInformation)
            self.bg_color = QColor(220, 230, 255, 230) # Light blue
            self.border_color = QColor(0, 0, 128, 200)    # Darker blue
            self.title_color = QColor(0, 0, 100)
            self.message_color = QColor(0, 0, 0)

        self.icon_label.setPixmap(icon.pixmap(icon_size, icon_size))
        self.title_label.setStyleSheet(f"color: {self.title_color.name()};")
        self.message_label.setStyleSheet(f"color: {self.message_color.name()};")
        # Close button color can be adjusted too if needed
        self.close_button.setStyleSheet(f"background: transparent; border: none; color: {self.message_color.name()};")


    def paintEvent(self, event):
        # Custom paint event to draw rounded rect background
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(0, 0, -1, -1) # Adjust for border

        painter.setBrush(QBrush(self.bg_color))
        painter.setPen(self.border_color) # Border color
        painter.drawRoundedRect(rect, 5, 5) # 5px radius for rounded corners

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.action_callback:
                self.action_callback()
            self.close() # Close on click
        super().mousePressEvent(event)

    def show_popup(self, position_index=0):
        if not self.parentWidget():
            print("NotificationPopup: No parent widget, cannot position.")
            # Fallback: show at screen corner
            screen_geo = QApplication.desktop().availableGeometry(self)
            self.move(screen_geo.right() - self.width() - 10, screen_geo.bottom() - self.height() - 10 - (position_index * (self.height() + 5)))
            self.show()
            return

        parent_geo = self.parentWidget().geometry()
        # Position at bottom-right of parent
        x = parent_geo.width() - self.width() - 10

        # Stacking: position_index determines vertical offset from bottom
        # Each notification is (self.height() + 5px margin) tall
        y = parent_geo.height() - self.height() - 10 - (position_index * (self.height() + 5))

        # Ensure it's relative to parent's top-left for `move`
        self.move(self.parentWidget().mapToGlobal(QPoint(x, y)))
        self.show()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

if __name__ == '__main__':
    # Example Usage
    app = QApplication([])
    main_window = QWidget() # Dummy main window
    main_window.setGeometry(100, 100, 800, 600)
    main_window.show()

    def example_action():
        print("Notification action triggered!")

    # Test different types
    pop1 = NotificationPopup("Success!", "Your download has completed successfully.", type='success', parent=main_window, action_callback=example_action)
    pop1.show_popup(position_index=0)

    pop2 = NotificationPopup("Error Occurred", "Failed to download the file. Please try again later.", type='error', parent=main_window, timeout=10000)
    # Show this one slightly above the first one
    QTimer.singleShot(1000, lambda: pop2.show_popup(position_index=1))


    pop3 = NotificationPopup("Information", "A new update is available for the application.", type='info', parent=main_window, timeout=0) # No auto-timeout
    QTimer.singleShot(2000, lambda: pop3.show_popup(position_index=2))

    app.exec_()
