import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QStackedWidget, QLabel, QVBoxLayout
)
import ui

app = QApplication(sys.argv)
game = ui.EmberLord()
game.show()
sys.exit(app.exec())


