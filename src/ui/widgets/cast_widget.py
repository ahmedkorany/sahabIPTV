from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QSizePolicy
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt
from src.utils.helpers import load_image_async

class CastWidget(QWidget):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.grid_layout.setHorizontalSpacing(10)
        self.grid_layout.setVerticalSpacing(10)

    def clear(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout is not None:
                    self._clear_layout(sub_layout)

    def set_cast(self, cast_data):
        """Set the cast data and populate the widget."""
        print(f"[CastWidget] set_cast called with {len(cast_data) if cast_data else 0} cast members")
        print(f"[CastWidget] Widget visible: {self.isVisible()}, parent visible: {self.parent().isVisible() if self.parent() else 'No parent'}")
        
        # Ensure widget is visible
        self.setVisible(True)
        if self.parent():
            self.parent().setVisible(True)
            print(f"[CastWidget] Parent type: {type(self.parent()).__name__}")
            
        # Force update and repaint
        self.update()
        self.repaint()
        if self.parent():
            self.parent().update()
            self.parent().repaint()
            
        print(f"[CastWidget] After visibility fix - Widget visible: {self.isVisible()}, parent visible: {self.parent().isVisible() if self.parent() else 'No parent'}")
        print(f"[CastWidget] Widget size: {self.size()}, parent size: {self.parent().size() if self.parent() else 'No parent'}")
        print(f"[CastWidget] Widget geometry: {self.geometry()}")
        
        # Check if widget is actually shown
        print(f"[CastWidget] Widget isHidden: {self.isHidden()}, isVisible: {self.isVisible()}, isVisibleTo parent: {self.isVisibleTo(self.parent()) if self.parent() else 'No parent'}")
        self.clear()
        MAX_CAST_MEMBERS = 24
        MAX_CAST_COLUMNS = 7
        row, col = 0, 0
        placeholder_pixmap = QPixmap('assets/person.png')
        if placeholder_pixmap.isNull():
            placeholder_pixmap = QPixmap(125, 188)
            placeholder_pixmap.fill(Qt.lightGray)
        loading_counter = {'count': 0}
        for i, member in enumerate(cast_data):
            if i >= MAX_CAST_MEMBERS:
                break
            member_name = member.get('name', 'N/A')
            character_name = member.get('character', '')
            profile_path = member.get('profile_path')
            gender = member.get('gender', 0)
            if gender == 2:
                gender_placeholder = QPixmap('assets/actor.png')
            elif gender == 1:
                gender_placeholder = QPixmap('assets/actress.png')
            else:
                gender_placeholder = QPixmap('assets/person.png')
            if gender_placeholder.isNull():
                gender_placeholder = QPixmap(125, 188)
                gender_placeholder.fill(Qt.lightGray)
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 5, 5, 5)
            item_layout.setSpacing(2)
            poster_with_overlay_container = QWidget()
            poster_with_overlay_container.setFixedSize(125, 188)
            poster_label = QLabel(poster_with_overlay_container)
            poster_label.setGeometry(0, 0, 125, 188)
            poster_label.setAlignment(Qt.AlignCenter)
            if profile_path:
                full_image_url = f"https://image.tmdb.org/t/p/w185{profile_path}"
                load_image_async(full_image_url, poster_label, gender_placeholder.scaled(125, 188, Qt.KeepAspectRatio, Qt.SmoothTransformation), update_size=(125,188), main_window=self.main_window, loading_counter=loading_counter)
            else:
                poster_label.setPixmap(gender_placeholder.scaled(125, 188, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            overlay_height = 35
            name_overlay_widget = QWidget(poster_with_overlay_container)
            name_overlay_widget.setGeometry(0, 188 - overlay_height, 125, overlay_height)
            name_overlay_widget.setStyleSheet("background-color: rgba(0, 0, 0, 180);")
            name_overlay_layout = QVBoxLayout()
            name_overlay_layout.setContentsMargins(2, 2, 2, 2)
            name_overlay_layout.setAlignment(Qt.AlignCenter)
            actor_name_label = QLabel(member_name)
            actor_name_label.setAlignment(Qt.AlignCenter)
            actor_name_label.setWordWrap(True)
            actor_name_label.setFont(QFont('Arial', 14))
            actor_name_label.setStyleSheet("color: white; background-color: transparent;")
            name_overlay_layout.addWidget(actor_name_label)
            name_overlay_widget.setLayout(name_overlay_layout)
            item_layout.addWidget(poster_with_overlay_container)
            if character_name:
                character_label = QLabel(f"as {character_name}")
                character_label.setFixedWidth(125)
                character_label.setAlignment(Qt.AlignCenter)
                character_label.setWordWrap(True)
                character_label.setFont(QFont('Arial', 10, italic=True))
                character_label.setStyleSheet("color: lightgray;")
                item_layout.addWidget(character_label)
            item_layout.addStretch(1)
            item_widget.setMinimumWidth(135)
            item_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            self.grid_layout.addWidget(item_widget, row, col)
            col += 1
            if col >= MAX_CAST_COLUMNS:
                col = 0
                row += 1
        if col > 0:
            for c_idx in range(col, MAX_CAST_COLUMNS):
                self.grid_layout.setColumnStretch(c_idx, 1)
        self.grid_layout.setRowStretch(row + 1, 1)
