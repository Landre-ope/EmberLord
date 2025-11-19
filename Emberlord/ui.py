import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QStackedWidget, QLabel, QVBoxLayout, QGraphicsBlurEffect, QFileDialog, QInputDialog
)
from PyQt6.QtGui import QPainter, QColor, QPixmap, QIcon, QMovie
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QTimer, QSize, QUrl
from PyQt6.QtMultimedia import QSoundEffect
import logic
import random

WINDOW_SIZE = 720
BOARD_SIZE = 8
Y_OFFSET = 50
BOARD_PIX = WINDOW_SIZE - 2 * Y_OFFSET
SQUARE_SIZE = BOARD_PIX // BOARD_SIZE

# Colors
LIGHT_COLOR = QColor(245, 230, 200)
DARK_COLOR = QColor(130, 50, 30)
HIGHLIGHT_COLOR = QColor(0, 255, 0, 100)


class Board(QWidget):
    # Initialize board widget: load graphics, timers and game state
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Emberlord")
        self.setFixedSize(1024, WINDOW_SIZE)
        self.top_offset = 20

        self.board_x = 200
        self.board_y = 100
        self.board_width = 512  # For example, 8 squares * 64px each
        self.board_height = 512

        # Board graphics
        self.board_bg = QPixmap(r'images/bg.png').scaled(1024, WINDOW_SIZE)
        self.red_piece = QPixmap(r'images/red piece.png').scaled(SQUARE_SIZE, SQUARE_SIZE, Qt.AspectRatioMode.KeepAspectRatio)
        self.blue_piece = QPixmap(r'images/blue piece.png').scaled(SQUARE_SIZE, SQUARE_SIZE, Qt.AspectRatioMode.KeepAspectRatio)
        self.red_king = QPixmap(r'images/red king.png').scaled(SQUARE_SIZE, SQUARE_SIZE, Qt.AspectRatioMode.KeepAspectRatio)
        self.blue_king = QPixmap(r'images/blue king.png').scaled(SQUARE_SIZE, SQUARE_SIZE, Qt.AspectRatioMode.KeepAspectRatio)

        self.pieces = []
        self.highlight_moves = []
        self.recently_captured = []
        self.random_burn_pos = None
        self.active_burn_column = None
        self.awaiting_burn = False

        # Game logic
        self.logic = logic.GameLogic()
        self.logic.reset_board()
        self.selected_piece = None

        # Timers
        self.turn_time = 15
        self.timer_begin = True
        self.timer_active = False
        self.turn_timer = QTimer(self)
        self.turn_timer.timeout.connect(self.update_turn_timer)

        self.highlight_timer = QTimer(self)
        self.highlight_timer.setSingleShot(True)
        self.highlight_timer.timeout.connect(self.clear_highlight)

        self.burn_movie = QMovie(r'images/lava tile.gif')
        self.burn_movie.frameChanged.connect(self.update)
        self.burn_animation_start = False
        # Forced-capture UI helpers
        self.forced_capture_positions = []
        self.forced_flash_state = False
        self.forced_flash_timer = QTimer(self)
        self.forced_flash_timer.setInterval(500)
        self.forced_flash_timer.timeout.connect(lambda: (setattr(self, 'forced_flash_state', not self.forced_flash_state), self.update()))

        # UI Elements
        self.paused = False
        self.setup_ui()
        self.piece_placement()

        # Lava GIF timer for smooth animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_lava_visuals)
        self.timer.start(100)

    # Create and arrange UI controls (buttons, labels, counters)
    def setup_ui(self):
        # Pause button and label
        self.pause_btn = QPushButton("", self)
        pause_icon = QPixmap(r'images/pause.png').scaled(100, 50, Qt.AspectRatioMode.KeepAspectRatio)
        btn_width = pause_icon.width()
        btn_height = pause_icon.height()
        self.pause_btn.setIcon(QIcon(pause_icon))
        self.pause_btn.setIconSize(pause_icon.size())
        self.pause_btn.setGeometry(950, 10, pause_icon.width(), pause_icon.height())
        self.pause_btn.setStyleSheet("QPushButton{border:none;background:transparent;}"
                                     "QPushButton:hover{background-color:rgba(255,255,255,30);}"
                                     "QPushButton:pressed{background-color:rgba(255,255,255,60);}")
        self.pause_btn.clicked.connect(self.toggle_pause)

        self.pause_label = QLabel("PAUSED", self)
        self.pause_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pause_label.setStyleSheet("color:white;font-size:48px;font-family:raleway;font-weight:bold;background-color:rgba(0,0,0,180);")
        self.pause_label.setGeometry(0, 0, self.width(), self.height())
        self.pause_label.hide()

        # Turn icons
        self.red_turn_label = QLabel(self)
        self.red_turn_label.setGeometry(800, 70, 150, 150)
        self.red_turn_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.blue_turn_label = QLabel(self)
        self.blue_turn_label.setGeometry(800, 510, 150, 150)
        self.blue_turn_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.red_active = QPixmap(r"images/player2 turn.png").scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio)
        self.red_inactive = QPixmap(r"images/player2.png").scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio)
        self.blue_active = QPixmap(r"images/player1 turn.png").scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio)
        self.blue_inactive = QPixmap(r"images/player1.png").scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio)

        # Turn timer label
        self.timer_label = QLabel("Time: 0s", self)
        self.timer_label.setGeometry(800, 360, 150, 40)
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("color:white;font-size:20px;font-weight:bold;font-family:raleway")

        # Burn buttons
        self.red_burn_btn = QPushButton(self)
        self.red_burn_btn.setIcon(QIcon(r"images/lava wave.png"))
        self.red_burn_btn.setIconSize(QSize(btn_width, btn_height))
        self.red_burn_btn.setFixedSize(btn_width, btn_height)
        self.red_burn_btn.setFlat(True)
        self.red_burn_btn.setStyleSheet("background-color: transparent; border: none;")
        self.red_burn_btn.clicked.connect(lambda: self.prepare_burn("red"))
        self.red_burn_btn.hide()

        self.blue_burn_btn = QPushButton(self)
        self.blue_burn_btn.setIcon(QIcon(r"images/lava wave.png"))
        self.blue_burn_btn.setIconSize(QSize(btn_width, btn_height))
        self.blue_burn_btn.setFixedSize(btn_width, btn_height)
        self.blue_burn_btn.setFlat(True)
        self.blue_burn_btn.setStyleSheet("background-color: transparent; border: none;")
        self.blue_burn_btn.clicked.connect(lambda: self.prepare_burn("blue"))
        self.blue_burn_btn.hide()

        timer_geo = self.timer_label.geometry()
        timer_center_x = timer_geo.x() + (timer_geo.width() // 2)
        red_btn_x = timer_center_x - (btn_width // 2)
        blue_btn_x = red_btn_x
        red_btn_y = timer_geo.y() - btn_height - 10
        blue_btn_y = timer_geo.y() + timer_geo.height() + 10
        self.red_burn_btn.setGeometry(red_btn_x, red_btn_y, btn_width, btn_height)
        self.blue_burn_btn.setGeometry(blue_btn_x, blue_btn_y, btn_width, btn_height)

        # Captured counters
        self.frame_label = QLabel(self)
        self.frame_label.setGeometry(800, 130, 150, 150)
        self.frame_img = QPixmap(r'images/blank frame.png')
        self.frame_label.setPixmap(self.frame_img.scaled(self.frame_label.width(),self.frame_label.height(),
                                                         Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))

        self.red_counter_label = QLabel("Captured: 0", self)
        self.red_counter_label.setGeometry(800, 130, 150, 150)
        self.red_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.red_counter_label.setStyleSheet("color:white;font-size:20px;font-weight:bold;font-family:raleway;")

        self.frame_label = QLabel(self)
        self.frame_label.setGeometry(800, 450, 150, 150)
        self.frame_img = QPixmap(r'images/blank frame.png')
        self.frame_label.setPixmap(self.frame_img.scaled(self.frame_label.width(), self.frame_label.height(),
                                                         Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

        self.blue_counter_label = QLabel("Captured: 0", self)
        self.blue_counter_label.setGeometry(800, 450, 150, 150)
        self.blue_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.blue_counter_label.setStyleSheet("color:white;font-size:20px;font-weight:bold;font-family:raleway;")

        # Winner overlay
        self.winner_label = QLabel("", self)
        self.winner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.winner_label.setStyleSheet("color:yellow;font-size:48px;background-color:rgba(0,0,0,180);")
        self.winner_label.setGeometry(0, 0, self.width(), self.height())
        self.winner_label.hide()

        # Restart button
        self.restart_btn = QPushButton("Restart", self)
        self.restart_btn.setGeometry(850, 180, 150, 50)
        self.restart_btn.setStyleSheet("color:white;font-size:18px;background-color:rgba(50,50,50,180);")
        self.restart_btn.clicked.connect(self.restart_game)
        self.restart_btn.hide()

        # Player info dict placeholders
        self.player_info = {"red":{"name":"Red","img":None},"blue":{"name":"Blue","img":None}}
        self.player_labels, self.player_images, self.player_counters = {}, {}, {}

        self.winner_image = QLabel(self)
        self.winner_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.winner_image.setGeometry(0, 0, self.width(), self.height())
        self.winner_image.setPixmap(QPixmap(r'images/player1 wins.png').scaled(self.width(), self.height(),
                                                Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation))
        self.winner_image.hide()

    # Reset and place pieces on the board, then refresh visuals
    def piece_placement(self):
        self.logic.reset_board()
        self.update_board_piece()

    # Update the turn indicator icons according to current player
    def update_turn_icons(self):
        if self.logic.current_turn == "red":
            self.red_turn_label.setPixmap(self.red_active)
            self.blue_turn_label.setPixmap(self.blue_inactive)
        else:
            self.red_turn_label.setPixmap(self.red_inactive)
            self.blue_turn_label.setPixmap(self.blue_active)

    # Show or hide burn buttons depending on king power-up availability
    def update_burn_button_visibility(self):
        self.red_burn_btn.hide()
        self.blue_burn_btn.hide()
        kings_with_power = [p for p in self.logic.pieces if p.color==self.logic.current_turn and getattr(p,"king",False) and getattr(p,"power_up",False)]
        if kings_with_power and not self.logic.multi_capture_piece and not self.awaiting_burn:
            if self.logic.current_turn=="red": self.red_burn_btn.show()
            else: self.blue_burn_btn.show()

    # Set display names and avatars for players in the UI
    def set_player_info(self, info):
        self.player_info = info
        padding = 10

        for color in ["red", "blue"]:
            if color == "red":
                x = self.board_x - 180
                y_lbl = self.board_y
                y_img = y_lbl + 45
            else:
                x = self.board_x - 180
                y_img = self.board_y + self.board_height - 100
                y_lbl = y_img - 45

            lbl = QLabel(info[color]["name"], self)
            lbl.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: bold; font-family: raleway;"
                              f"background-color: rgba(255, 255, 255, 1); padding: 10px; border-radius: 5px;")
            lbl.setGeometry(x, y_lbl, 120, 40)
            lbl.show()
            self.player_labels[color] = lbl

            img_lbl = QLabel(self)
            pix = info[color]["img"]
            if pix:
                img_lbl.setPixmap(pix.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            img_lbl.setGeometry(x, y_img, 100, 100)
            img_lbl.setStyleSheet("border: 2px solid white;")
            img_lbl.show()
            self.player_images[color] = img_lbl

            """counter_lbl = QLabel(f"{color.capitalize()} Captured: 0",self)
            counter_lbl.setGeometry(20,y_offsets[2],150,40)
            counter_lbl.setStyleSheet(f"color:{color};font-size:16px;")
            counter_lbl.show()
            self.player_counters[color]=counter_lbl"""

    # Handle board clicks: select/move pieces and enforce captures
    def click_handle(self, row, col):
        clicked_piece = self.logic.get_piece(row, col)
        # Prevent any pending highlight-clear from removing new highlights
        try:
            self.highlight_timer.stop()
        except Exception:
            pass

        # Start turn timer if first action
        if not self.timer_active and clicked_piece and clicked_piece.color == self.logic.current_turn:
            self.timer_active = True
            self.turn_timer.start(1000)

        # Enforce multi-capture: ignore attempts to select a different piece
        # Allow clicks on empty squares so the continuing capture move can be made
        if self.logic.multi_capture_piece is not None:
            # if the user clicked on a (different) piece, ignore it
            if clicked_piece and clicked_piece is not self.logic.multi_capture_piece:
                self.highlight_timer.stop()
                self.highlight_moves.clear()
                self.update()
                return
            # If no selection is active, auto-select the multi-capture piece
            if self.selected_piece is None:
                cap = self.logic.multi_capture_piece
                self.selected_piece = (cap.row, cap.col)
                # highlight only capture moves for this piece
                self.highlight_timer.stop()
                self.highlight_moves = self.logic.get_valid_moves(cap, capture=True)

        if self.selected_piece is None:
            # Select piece if it's the current player's turn
            if clicked_piece and clicked_piece.color == self.logic.current_turn:
                self.selected_piece = (row, col)
                self.highlight_timer.stop()
                self.highlight_moves = self.logic.get_valid_moves(clicked_piece)
        else:
            s_row, s_col = self.selected_piece
            moved = self.logic.move_piece(s_row, s_col, row, col)

            if moved:
                # Stop any pending clear and update highlights for the continued capture or clear
                self.highlight_timer.stop()
                self.highlight_moves.clear()
                # If the logic says the same piece must continue capturing, keep it selected
                if self.logic.multi_capture_piece is not None:
                    piece = self.logic.multi_capture_piece
                    self.selected_piece = (piece.row, piece.col)
                    # highlight only capture moves for this piece
                    self.highlight_timer.stop()
                    self.highlight_moves = self.logic.get_valid_moves(piece, capture=True)
                else:
                    # No further captures, end turn
                    self.selected_piece = None
                    self.highlight_timer.start(1000)
                    self.turn_time = 15
                self.update_board_piece()
            else:
                # Invalid move, deselect
                self.selected_piece = None
                self.highlight_timer.stop()
                self.highlight_moves.clear()

        self.update()

    # Per-turn timer tick: update, handle timeout and burns
    def update_turn_timer(self):
        if not self.timer_active or self.paused or self.winner_label.isVisible():
            return
        self.turn_time -= 1
        if self.turn_time <= 0:
            self.automatic_burn()
        self.timer_label.setText(f"Time: {self.turn_time}s")
        self.update_turn_icons()
        self.update_burn_button_visibility()
        # Compute forced-capture highlights (pieces of current player that have captures)
        try:
            forced = [p for p in self.logic.pieces if p.color == self.logic.current_turn and self.logic.piece_has_capture(p)]
            self.forced_capture_positions = [(p.row, p.col) for p in forced]
        except Exception:
            self.forced_capture_positions = []
        # Start/stop forced highlight pulsing
        if self.forced_capture_positions:
            if not self.forced_flash_timer.isActive():
                self.forced_flash_timer.start()
        else:
            if self.forced_flash_timer.isActive():
                self.forced_flash_timer.stop()

    # Activate the king-column burn power for `color` (targets king's column)
    def prepare_burn(self, color):
        if color != self.logic.current_turn:
            return

        # Prefer the currently selected piece if it's a king with power_up
        col = None
        if self.selected_piece is not None:
            s_row, s_col = self.selected_piece
            sel_piece = self.logic.get_piece(s_row, s_col)
            if sel_piece and sel_piece.color == color and getattr(sel_piece, 'king', False) and getattr(sel_piece, 'power_up', False):
                col = sel_piece.col

        # Otherwise pick any king with a power_up belonging to the current player
        if col is None:
            kings = [p for p in self.logic.pieces if p.color == color and getattr(p, 'king', False) and getattr(p, 'power_up', False)]
            if not kings:
                return
            col = kings[0].col

        # Perform burn in the king's column (logic.burn_column will end the turn)
        if self.logic.burn_column(col):
            # Start burn animation and schedule finish
            self.active_burn_column = col
            self.burn_animation_start = True
            self.burn_movie.jumpToFrame(0)
            self.burn_movie.start()

            frame_count = self.burn_movie.frameCount()
            frame_delay = self.burn_movie.nextFrameDelay() or 100
            total_duration = frame_count * frame_delay

            QTimer.singleShot(total_duration, lambda: self.finish_burn_column(col))

            # Clear selection and UI state while animation plays
            self.selected_piece = None
            self.highlight_moves = []
            self.update_burn_button_visibility()
            return
    # Finish burn animation for a column and start next player's timer
    def finish_burn_column(self, col):
        self.active_burn_column = None
        self.burn_animation_start = False
        self.burn_movie.stop()
        # burn_column already ended the turn; just clear temporary state
        self.logic.multi_capture_piece = None
        self.turn_time = 15
        self.update_board_piece()
        if not self.winner_label.isVisible():
            self.turn_timer.start(1000)

    # Perform an automatic random burn (used when the timer runs out)
    def automatic_burn(self):
        self.turn_timer.stop()
        current_color = self.logic.current_turn
        player_pieces = [p for p in self.logic.pieces if p.color==current_color]
        if not player_pieces:
            self.logic.end_turn()
            self.turn_time = 15
            self.update_board_piece()
            return
        piece_to_burn = random.choice(player_pieces)
        self.random_burn_pos = (piece_to_burn.row,piece_to_burn.col)
        self.burn_animation_start=True
        self.burn_movie.jumpToFrame(0)
        self.burn_movie.start()
        frame_count = self.burn_movie.frameCount()
        frame_delay = self.burn_movie.nextFrameDelay() or 100
        total_duration = frame_count*frame_delay
        QTimer.singleShot(total_duration,lambda:self.finish_random_burn(piece_to_burn))

    # Finish a burn animation for `piece`, remove it and hand the turn
    def finish_random_burn(self,piece):
        self.logic.pieces=[p for p in self.logic.pieces if not(p.row==piece.row and p.col==piece.col)]
        if piece.color=="red": self.logic.red_captured+=1
        else: self.logic.blue_captured+=1
        self.random_burn_pos=None
        self.burn_animation_start=False
        self.burn_movie.stop()
        self.logic.multi_capture_piece = None
        self.logic.end_turn()
        self.turn_time=15
        if not self.winner_label.isVisible(): self.turn_timer.start(1000)
        self.update_board_piece()

    # Paint the board, pieces, highlights and animations
    def paintEvent(self,event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        offset_x = (self.width()-WINDOW_SIZE)//2
        offset_y = Y_OFFSET

        painter.drawPixmap(0,0,self.width(),self.height(),self.board_bg)

        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                color = LIGHT_COLOR if (row+col)%2==0 else DARK_COLOR
                painter.fillRect(offset_x+col*SQUARE_SIZE,offset_y+row*SQUARE_SIZE,SQUARE_SIZE,SQUARE_SIZE,color)

        # Highlight
        for row,col in self.highlight_moves:
            painter.fillRect(offset_x+col*SQUARE_SIZE,offset_y+row*SQUARE_SIZE,SQUARE_SIZE,SQUARE_SIZE,HIGHLIGHT_COLOR)

        # Forced-capture pulsing highlight
        if getattr(self, 'forced_capture_positions', None):
            alpha = 220 if getattr(self, 'forced_flash_state', False) else 100
            overlay = QColor(0, 200, 0)
            overlay.setAlpha(alpha)
            thickness = 6
            for row, col in self.forced_capture_positions:
                x = offset_x + col * SQUARE_SIZE
                y = offset_y + row * SQUARE_SIZE
                painter.fillRect(x, y, SQUARE_SIZE, thickness, overlay)
                painter.fillRect(x, y + SQUARE_SIZE - thickness, SQUARE_SIZE, thickness, overlay)
                painter.fillRect(x, y + thickness, thickness, SQUARE_SIZE - 2 * thickness, overlay)
                painter.fillRect(x + SQUARE_SIZE - thickness, y + thickness, thickness, SQUARE_SIZE - 2 * thickness, overlay)

        # Burn animations
        if self.random_burn_pos:
            row,col = self.random_burn_pos
            frame = self.burn_movie.currentPixmap()
            scaled_frame = frame.scaled(SQUARE_SIZE,SQUARE_SIZE,Qt.AspectRatioMode.KeepAspectRatioByExpanding)
            painter.drawPixmap(offset_x+col*SQUARE_SIZE,offset_y+row*SQUARE_SIZE,SQUARE_SIZE,SQUARE_SIZE,scaled_frame)
        elif self.burn_animation_start and self.active_burn_column is not None:
            col = self.active_burn_column
            frame = self.burn_movie.currentPixmap()
            scaled_frame = frame.scaled(SQUARE_SIZE,BOARD_PIX,Qt.AspectRatioMode.KeepAspectRatioByExpanding)
            painter.drawPixmap(offset_x+col*SQUARE_SIZE,offset_y,SQUARE_SIZE,BOARD_PIX,scaled_frame)

        # Pieces
        for piece in self.logic.pieces:
            pixmap = self.red_king if getattr(piece,"king",False) and piece.color=="red" else \
                     self.blue_king if getattr(piece,"king",False) and piece.color=="blue" else \
                     self.red_piece if piece.color=="red" else self.blue_piece
            painter.drawPixmap(offset_x+piece.col*SQUARE_SIZE,offset_y+piece.row*SQUARE_SIZE,SQUARE_SIZE,SQUARE_SIZE,pixmap)

    # Refresh board UI and optionally restart the per-turn timer
    def update_board_piece(self):
        self.pieces.clear()
        self.timer_label.setText(f"Time: {self.turn_time}s")
        self.red_counter_label.setText(f"Captured: {self.logic.blue_captured}")
        self.blue_counter_label.setText(f"Captured: {self.logic.red_captured}")
        winner = self.logic.winner_check()
        if winner:
            self.winner_label.setText(winner)
            self.winner_label.show()
            self.restart_btn.show()
            self.paused=True
        self.update_turn_icons()
        self.update_burn_button_visibility()
        self.update()

    # Clear temporary move highlights
    def clear_highlight(self):
        self.highlight_moves.clear()
        self.update()

    # Toggle pause state, hiding/showing UI and timers
    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.pause_label.show()
            self.pause_btn.hide()
            self.blue_burn_btn.hide()
            self.red_burn_btn.hide()
            self.timer_label.hide()
        else:
            self.pause_label.hide()
            self.pause_btn.show()
            self.timer_label.show()
            self.update_burn_button_visibility()
        self.update()

    # Handle key presses (Escape toggles pause)
    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Escape: self.toggle_pause()
        super().keyPressEvent(event)

    # Map mouse clicks to board coordinates and delegate to click handler
    def mousePressEvent(self, event):
        offset_x = (self.width() - WINDOW_SIZE) // 2
        offset_y = Y_OFFSET
        pos = event.position()
        x_click = int(pos.x() - offset_x)
        y_click = int(pos.y() - offset_y)
        col = x_click // SQUARE_SIZE
        row = y_click // SQUARE_SIZE

        if self.paused:
            self.toggle_pause()
            return

        # ---------------- King Burn Handling ----------------
        if self.awaiting_burn and 0 <= col < BOARD_SIZE:
            # Attempt burn
            if self.logic.burn_column(col):
                # Start burn animation
                self.active_burn_column = col
                self.burn_animation_start = True
                self.burn_movie.jumpToFrame(0)
                self.burn_movie.start()

                # Calculate total animation duration
                frame_count = self.burn_movie.frameCount()
                frame_delay = self.burn_movie.nextFrameDelay() or 100
                total_duration = frame_count * frame_delay

                # Finish burn after animation
                QTimer.singleShot(total_duration, lambda: self.finish_burn_column(col))

            self.awaiting_burn = False
            self.update_burn_button_visibility()
            self.update_board_piece()
            return

        # ---------------- Regular Piece Handling ----------------
        if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
            self.click_handle(row, col)

    # Trigger periodic visual updates for burn animations
    def update_lava_visuals(self):
        if self.burn_animation_start: self.update()

    # Reset game state and restart from the initial position
    def restart_game(self):
        self.logic.reset_board()
        self.turn_time = 15
        self.paused = False
        self.selected_piece = None
        self.highlight_moves.clear()
        self.winner_label.hide()
        self.restart_btn.hide()
        self.random_burn_pos=None
        self.burn_animation_start=False
        self.burn_movie.stop()
        self.update_board_piece()


class MenuWidget(QWidget):
    # Main menu widget: background and navigation buttons
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(1024, WINDOW_SIZE)

        # Background and button images
        self.bg = QPixmap(r'images/menu bg.png').scaled(1024, WINDOW_SIZE)
        self.play_ui = QPixmap(r'images/start.png')
        self.setup_ui = QPixmap(r'images/edit profile.png')
        self.quit_ui = QPixmap(r'images/quit.png')

        # Buttons
        self.play_btn = QPushButton("", self)
        self.setup_btn = QPushButton("", self)
        self.quit_btn = QPushButton("", self)

        # Button style
        button_style = """
            QPushButton {
                border: none; 
                background: transparent; 
                color: white; 
                font-size: 24px;
            }
            QPushButton:hover { 
                background-color: rgba(255, 255, 255, 40); 
            }
            QPushButton:pressed { 
                background-color: rgba(255, 255, 255, 80); 
            }"""
        self.play_btn.setStyleSheet(button_style)
        self.setup_btn.setStyleSheet(button_style)
        self.quit_btn.setStyleSheet(button_style)

        # Button sizes and positions
        btn_width = 600
        btn_height = 110
        btn_spacing = 15
        start_y = 320
        center_x = (1024 - btn_width) // 2

        self.play_btn.setGeometry(center_x, start_y, btn_width, btn_height)
        self.setup_btn.setGeometry(center_x, start_y + btn_height + btn_spacing, btn_width, btn_height)
        self.quit_btn.setGeometry(center_x, start_y + 2 * (btn_height + btn_spacing), btn_width, btn_height)

        # Scale icons for start and quit buttons
        scaled_play = self.play_ui.scaled(self.play_btn.size(),
                                          Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                          Qt.TransformationMode.SmoothTransformation)
        scaled_setup = self.setup_ui.scaled(self.setup_btn.size(),
                                          Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                          Qt.TransformationMode.SmoothTransformation)
        scaled_quit = self.quit_ui.scaled(self.quit_btn.size(),
                                          Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                          Qt.TransformationMode.SmoothTransformation)
        self.play_btn.setIcon(QIcon(scaled_play))
        self.play_btn.setIconSize(self.play_btn.size())
        self.setup_btn.setIcon(QIcon(scaled_setup))
        self.setup_btn.setIconSize(self.setup_btn.size())
        self.quit_btn.setIcon(QIcon(scaled_quit))
        self.quit_btn.setIconSize(self.quit_btn.size())

        # Connections
        self.play_btn.clicked.connect(self.start_game)
        self.quit_btn.clicked.connect(QApplication.quit)
        self.setup_btn.clicked.connect(self.open_player_setup)

        # Default player info
        self.player_info = {
            "blue": {"name": "Blue", "img": None},
            "red": {"name": "Red", "img": None}
        }

    # Open dialogs to configure player names and avatars
    def open_player_setup(self):
        # Blue player
        blue_img, _ = QFileDialog.getOpenFileName(self, "Select Blue Player Image", "", "Images (*.png *.jpg *.bmp)")
        if blue_img:
            blue_name, ok = QInputDialog.getText(self, "Blue Player Name", "Enter Blue Player Name:")
            if ok and blue_name.strip() != "":
                self.player_info["blue"]["name"] = blue_name
                self.player_info["blue"]["img"] = QPixmap(blue_img)
        # Red player
            red_img, _ = QFileDialog.getOpenFileName(self, "Select Red Player Image", "", "Images (*.png *.jpg *.bmp)")
            if red_img:
                red_name, ok = QInputDialog.getText(self, "Red Player Name", "Enter Red Player Name:")
                if ok and red_name.strip() != "":
                    self.player_info["red"]["name"] = red_name
                    self.player_info["red"]["img"] = QPixmap(red_img)

    # Start a new game by switching to the play view and applying player info
    def start_game(self):
        self.main_window.board.set_player_info(self.player_info)
        self.main_window.transition_to("play")

    # Paint menu background and UI
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawPixmap(0, 0, self.bg)



class EmberLord(QWidget):
    # Top-level application window and view stack manager
    def __init__(self):
        super().__init__()
        self.icon_image = QPixmap(r'images/emberlord_icon.png').scaled(
            32, 13, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.icon = QIcon(self.icon_image)
        self.setWindowIcon(self.icon)
        self.setWindowTitle("Emberlord")
        self.setFixedSize(1024, WINDOW_SIZE)

        self.stack = QStackedWidget(self)
        self.menu = MenuWidget(self)
        self.menu.main_window = self
        self.board = Board()

        self.stack.addWidget(self.menu)
        self.stack.addWidget(self.board)

        layout = QVBoxLayout()
        layout.addWidget(self.stack)
        self.setLayout(layout)

        self._overlay = QLabel(self)
        self._overlay.setGeometry(0, 0, 1024, WINDOW_SIZE)
        self._overlay.setStyleSheet("background-color: black;")
        self._overlay.setVisible(False)

        self.show()

    # Play a blur transition and switch to the requested view
    def transition_to(self, new_state):
        current_pixmap = self.grab()
        self._overlay.setPixmap(current_pixmap)
        self._overlay.setScaledContents(True)
        self._overlay.setVisible(True)
        self._overlay.raise_()

        # The blur effect needs to be applied to the overlay QLabel
        blur = QGraphicsBlurEffect()
        self._overlay.setGraphicsEffect(blur)

        self.blur_anim = QPropertyAnimation(blur, b"blurRadius")
        self.blur_anim.setDuration(600)
        self.blur_anim.setStartValue(0.0)
        self.blur_anim.setEndValue(25.0)
        self.blur_anim.finished.connect(lambda: self._finish_transition(new_state))
        self.blur_anim.start()

    # Complete the blur transition and set the correct stack widget
    def _finish_transition(self, new_state):
        if new_state == "play":
            self.stack.setCurrentWidget(self.board)
            # board.restart_game is called in MenuWidget.start_game
            # self.board.logic.reset_board() # redundant if restart_game is called
            # self.board.update_board_piece() # redundant if restart_game is called

        self._overlay.setVisible(False)
        self._overlay.setGraphicsEffect(None)

    # These properties were only needed if animating the opacity directly, which is not being done.
    # Leaving them in as they don't harm but the opacity animation in _finish_transition is removed.
    @pyqtProperty(float)
    # Property getter for overlay opacity (used by animations)
    def overlay_opacity(self):
        return self._overlay.windowOpacity()

    @overlay_opacity.setter
    # Property setter for overlay opacity (used by animations)
    def overlay_opacity(self, value):
        self._overlay.setWindowOpacity(value)
