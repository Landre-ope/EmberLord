import time

class Piece:
    # Simple game piece model: stores position, color and king/power-up state
    def __init__(self, row, col, color):
        self.row = row
        self.col = col
        self.color = color
        self.king = False
        self.power_up = False 

    # Promote this piece to king and grant its power-up
    def make_king(self):
        self.king = True
        self.power_up = True


class GameLogic:
    # Core game rules and state: pieces, turns, capture tracking
    # Initialize game state and counters
    def __init__(self):
        self.pieces = []
        self.current_turn = 'blue'
        self.start_time = None
        self.elapsed = 0
        self.red_captured = 0
        self.blue_captured = 0
        self.must_continue_capture_piece = None
        self.last_burn_col = None
        self.multi_capture_piece = None
    # Reset the board to the initial starting position and clear counters
    def reset_board(self):
        self.red_captured = 0
        self.blue_captured = 0
        self.pieces.clear()
        for row in range(3):
            for col in range(8):
                if (row + col) % 2 != 0:
                    self.pieces.append(Piece(row, col, 'red'))
        for row in range(5, 8):
            for col in range(8):
                if (row + col) % 2 != 0:
                    self.pieces.append(Piece(row, col, 'blue'))
        self.current_turn = 'blue'
        self.start_time = None
        self.elapsed = 0
        self.must_continue_capture = None

    # Return the Piece at (row,col) or None if empty
    def get_piece(self, row, col):
        for piece in self.pieces:
            if piece.row == row and piece.col == col:
                return piece
        return None
    
    # Return True if `player_color` has any capturing move available
    def player_has_capture(self, player_color):
        for p in self.pieces:
            if p.color == player_color:
                if self.piece_has_capture(p):
                    return True
        return False

    # Return True if the square at (row,col) has no piece
    def is_empty(self, row, col):
        return self.get_piece(row, col) is None

    # End the current player's turn and clear mandatory-capture state
    def end_turn(self):
        self.current_turn = 'red' if self.current_turn == 'blue' else 'blue'
        self.must_continue_capture = None

    # Return elapsed game time (seconds)
    def get_time(self):
        if self.start_time:
            return int(time.time() - self.start_time + self.elapsed)
        return int(self.elapsed)

    # Start time tracking for the game
    def time_start(self):
        self.start_time = time.time()
        self.elapsed = 0
        
    # Move a piece from start to end if the move is valid; handle captures and promotions
    def move_piece(self, start_row, start_col, end_row, end_col):
        piece = self.get_piece(start_row, start_col)
        if not piece or piece.color != self.current_turn:
            return False

        if self.multi_capture_piece is not None:
            if piece is not self.multi_capture_piece:
                return False

        must_capture = self.player_has_capture(self.current_turn)

        # KING MOVES (flying king): allow long-range diagonal moves and captures
        if piece.king:
            # Ensure move is along a diagonal
            drow = end_row - start_row
            dcol = end_col - start_col
            if abs(drow) != abs(dcol) or drow == 0:
                return False

            step_r = 1 if drow > 0 else -1
            step_c = 1 if dcol > 0 else -1

            encountered = []
            r, c = start_row + step_r, start_col + step_c
            while (r != end_row + step_r) and (c != end_col + step_c):
                p = self.get_piece(r, c)
                if p:
                    encountered.append(p)
                r += step_r
                c += step_c

            # Destination must be empty
            if not self.is_empty(end_row, end_col):
                return False

            # Simple long move (no pieces in between)
            if len(encountered) == 0:
                if must_capture:
                    return False
                # Move king to destination
                piece.row = end_row
                piece.col = end_col
                # Promotion already present
                self.multi_capture_piece = None
                self.end_turn()
                return True

            # Capture move: must encounter exactly one enemy piece and it must belong to opponent
            if len(encountered) == 1 and encountered[0].color != piece.color:
                mid_piece = encountered[0]
                try:
                    self.pieces.remove(mid_piece)
                except ValueError:
                    pass
                if mid_piece.color == 'red':
                    self.red_captured += 1
                else:
                    self.blue_captured += 1

                piece.row = end_row
                piece.col = end_col

                # After capture, check for additional captures for this king
                if self.piece_has_capture(piece):
                    self.multi_capture_piece = piece
                    return True
                else:
                    self.multi_capture_piece = None
                    self.end_turn()
                    return True

            # Any other pattern is invalid
            return False

        # Non-king (regular) move logic (unchanged)
        is_simple_move = abs(end_row - start_row) == 1 and abs(end_col - start_col) == 1
        is_capture_move = abs(end_row - start_row) == 2 and abs(end_col - start_col) == 2

        if is_simple_move:
            if must_capture:
                return False
            if self.is_empty(end_row, end_col):
                if piece.king or (piece.color == 'red' and end_row > start_row) or (piece.color == 'blue' and end_row < start_row):
                    piece.row = end_row
                    piece.col = end_col
                    if piece.color == 'red' and piece.row == 7:
                        piece.make_king()
                    if piece.color == 'blue' and piece.row == 0:
                        piece.make_king()
                    self.multi_capture_piece = None
                    self.end_turn()
                    return True
            return False

        if is_capture_move:
            mid_row = (start_row + end_row) // 2
            mid_col = (start_col + end_col) // 2
            mid_piece = self.get_piece(mid_row, mid_col)
            if mid_piece and mid_piece.color != piece.color and self.is_empty(end_row, end_col):
                try:
                    self.pieces.remove(mid_piece)
                except ValueError:
                    pass
                if mid_piece.color == 'red':
                    self.red_captured += 1
                else:
                    self.blue_captured += 1
                piece.row = end_row
                piece.col = end_col
                if piece.color == 'red' and piece.row == 7:
                    piece.make_king()
                if piece.color == 'blue' and piece.row == 0:
                    piece.make_king()
                if self.piece_has_capture(piece):
                    self.multi_capture_piece = piece
                    return True
                else:
                    self.multi_capture_piece = None
                    self.end_turn()
                    return True

        return False

    # Return True if any piece of the current turn has a mandatory capture
    def has_mandatory_capture(self):
        if self.must_continue_capture_piece:
            return bool(self.piece_has_capture(self.must_continue_capture_piece))
        current_pieces = [p for p in self.pieces if p.color == self.current_turn]
        for piece in current_pieces:
            if self.piece_has_capture(piece):
                return True
        return False

    # Check whether a specific piece has at least one capture move available
    def piece_has_capture(self, piece):
        # King captures: flying king can jump over a single enemy anywhere along diagonal
        if getattr(piece, 'king', False):
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            for dr, dc in directions:
                r, c = piece.row + dr, piece.col + dc
                encountered = []
                while 0 <= r < 8 and 0 <= c < 8:
                    p = self.get_piece(r, c)
                    if p:
                        encountered.append(p)
                        break
                    r += dr
                    c += dc
                if len(encountered) == 1 and encountered[0].color != piece.color:
                    # After the enemy, at least one empty square must exist to land
                    rr, cc = encountered[0].row + dr, encountered[0].col + dc
                    while 0 <= rr < 8 and 0 <= cc < 8:
                        if self.is_empty(rr, cc):
                            return True
                        # blocked by another piece
                        break
                        rr += dr
                        cc += dc
            # no capture found for king
            return False

        # Normal piece single-jump captures
        for drow in (-2, 2):
            for dcol in (-2, 2):
                new_row = piece.row + drow
                new_col = piece.col + dcol
                mid_row = piece.row + drow // 2
                mid_col = piece.col + dcol // 2
                if 0 <= new_row < 8 and 0 <= new_col < 8 and self.is_empty(new_row, new_col):
                    mid_piece = self.get_piece(mid_row, mid_col)
                    if mid_piece and mid_piece.color != piece.color:
                        return True
        return False



   
    # Return list of valid moves for a piece; if capture=True, prefer capture destinations
    def get_valid_moves(self, piece, capture=False):
        moves = []
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]

        if piece.king:
            for dr, dc in directions:
                r, c = piece.row + dr, piece.col + dc
                jumped = None
                while 0 <= r < 8 and 0 <= c < 8:
                    target = self.get_piece(r, c)
                    if target:
                        if target.color == piece.color:
                            break
                        if jumped is None:
                            jumped = target
                        else:
                            break
                    elif jumped:
                        moves.append((r, c))
                    elif not capture:
                        moves.append((r, c))
                    r += dr
                    c += dc
        else:
            fwd_dirs = [1] if piece.color == 'red' else [-1]
            for dr in fwd_dirs:
                for dc in [-1, 1]:
                    r, c = piece.row + dr, piece.col + dc
                    if 0 <= r < 8 and 0 <= c < 8 and self.is_empty(r, c) and not capture:
                        moves.append((r, c))
            for dr, dc in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
                r, c = piece.row + dr, piece.col + dc
                mid_r, mid_c = piece.row + dr // 2, piece.col + dc // 2
                if 0 <= r < 8 and 0 <= c < 8 and self.is_empty(r, c):
                    mid_piece = self.get_piece(mid_r, mid_c)
                    if mid_piece and mid_piece.color != piece.color:
                        moves.append((r, c))
        return moves

                
    # Remove all opponent pieces in a column when a king uses its burn power
    def burn_column(self, col):
        kings = [p for p in self.pieces if p.color == self.current_turn and p.king and p.power_up]
        if self.must_continue_capture:
            return False
        if not kings:
            return False
        king = kings[0]
        king.power_up = False 
        to_remove = [p for p in self.pieces if p.col == col and p.color != self.current_turn]
        for p in to_remove:
            self.pieces.remove(p)
            if p.color == 'red':
                self.red_captured += 1
            else:
                self.blue_captured += 1
        self.must_continue_capture = None
        self.end_turn()
        self.last_burn_col = col
        return True
    
    # Check for a winner or if current player is stuck (no valid moves)
    def winner_check(self):
        red_pieces = [p for p in self.pieces if p.color == 'red']
        blue_pieces = [p for p in self.pieces if p.color == 'blue']
        if not red_pieces:
            return "Blue Wins!"
        if not blue_pieces:
            return "Red Wins!"
        current_pieces = red_pieces if self.current_turn == 'red' else blue_pieces
        has_moves = any(self.get_valid_moves(piece) for piece in current_pieces)
        if not has_moves:
             return f"{self.current_turn.capitalize()} is stuck! Opponent Wins!"
        return None

    # Remove a piece as a penalty (e.g., timeout), update counters, clear capture state and end turn
    def penalize_piece(self, piece):
        removed = False
        new_pieces = []
        for p in self.pieces:
            if p.row == piece.row and p.col == piece.col and p.color == piece.color:
                removed = True
                if p.color == 'red':
                    self.red_captured += 1
                else:
                    self.blue_captured += 1
                continue
            new_pieces.append(p)
        self.pieces = new_pieces
        self.multi_capture_piece = None
        self.must_continue_capture = None
        self.must_continue_capture_piece = None
        self.end_turn()
        return removed