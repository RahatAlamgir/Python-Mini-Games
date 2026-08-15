import copy

class Move:
    def __init__(self, start_sq, end_sq, board, is_enpassant=False, is_castle=False):
        self.start_row, self.start_col = start_sq
        self.end_row, self.end_col = end_sq
        self.piece_moved = board[self.start_row][self.start_col]
        self.piece_captured = board[self.end_row][self.end_col]
        
        self.is_pawn_promotion = (self.piece_moved == "P" and self.end_row == 0) or \
                                 (self.piece_moved == "p" and self.end_row == 7)
        self.is_enpassant_move = is_enpassant
        if self.is_enpassant_move:
            self.piece_captured = "p" if self.piece_moved == "P" else "P"
            
        self.is_castle_move = is_castle
        self.move_id = self.start_row * 1000 + self.start_col * 100 + self.end_row * 10 + self.end_col

    def __eq__(self, other):
        if isinstance(other, Move):
            return self.move_id == other.move_id
        return False

class CastleRights:
    def __init__(self, wks, wqs, bks, bqs):
        self.wks = wks
        self.wqs = wqs
        self.bks = bks
        self.bqs = bqs

class GameState:
    def __init__(self):
        self.board = [
            ["r", "n", "b", "q", "k", "b", "n", "r"],
            ["p", "p", "p", "p", "p", "p", "p", "p"],
            [" ", " ", " ", " ", " ", " ", " ", " "],
            [" ", " ", " ", " ", " ", " ", " ", " "],
            [" ", " ", " ", " ", " ", " ", " ", " "],
            [" ", " ", " ", " ", " ", " ", " ", " "],
            ["P", "P", "P", "P", "P", "P", "P", "P"],
            ["R", "N", "B", "Q", "K", "B", "N", "R"],
        ]
        self.white_to_move = True
        self.move_log = []
        self.white_king_location = (7, 4)
        self.black_king_location = (0, 4)
        self.in_check = False
        self.checkmate = False
        self.stalemate = False
        self.enpassant_possible = ()
        self.enpassant_possible_log = [self.enpassant_possible]
        
        self.current_castling_right = CastleRights(True, True, True, True)
        self.castle_rights_log = [CastleRights(self.current_castling_right.wks, self.current_castling_right.wqs,
                                               self.current_castling_right.bks, self.current_castling_right.bqs)]

    def make_move(self, move):
        self.board[move.start_row][move.start_col] = " "
        self.board[move.end_row][move.end_col] = move.piece_moved
        self.move_log.append(move)
        self.white_to_move = not self.white_to_move

        # King Location Tracking
        if move.piece_moved == "K":
            self.white_king_location = (move.end_row, move.end_col)
        elif move.piece_moved == "k":
            self.black_king_location = (move.end_row, move.end_col)

        # Pawn Promotion (Default to Queen)
        if move.is_pawn_promotion:
            self.board[move.end_row][move.end_col] = "Q" if move.piece_moved.isupper() else "q"

        # En Passant
        if move.is_enpassant_move:
            self.board[move.start_row][move.end_col] = " "

        if move.piece_moved.lower() == "p" and abs(move.start_row - move.end_row) == 2:
            self.enpassant_possible = ((move.start_row + move.end_row) // 2, move.start_col)
        else:
            self.enpassant_possible = ()
        self.enpassant_possible_log.append(self.enpassant_possible)

        # Castling
        if move.is_castle_move:
            if move.end_col - move.start_col == 2: # Kingside
                self.board[move.end_row][move.end_col - 1] = self.board[move.end_row][move.end_col + 1]
                self.board[move.end_row][move.end_col + 1] = " "
            else: # Queenside
                self.board[move.end_row][move.end_col + 1] = self.board[move.end_row][move.end_col - 2]
                self.board[move.end_row][move.end_col - 2] = " "

        # Update Castle Rights
        self.update_castle_rights(move)
        self.castle_rights_log.append(CastleRights(self.current_castling_right.wks, self.current_castling_right.wqs,
                                                   self.current_castling_right.bks, self.current_castling_right.bqs))

    def undo_move(self):
        if len(self.move_log) != 0:
            move = self.move_log.pop()
            self.board[move.start_row][move.start_col] = move.piece_moved
            self.board[move.end_row][move.end_col] = move.piece_captured
            self.white_to_move = not self.white_to_move

            if move.piece_moved == "K":
                self.white_king_location = (move.start_row, move.start_col)
            elif move.piece_moved == "k":
                self.black_king_location = (move.start_row, move.start_col)

            if move.is_enpassant_move:
                self.board[move.end_row][move.end_col] = " "
                self.board[move.start_row][move.end_col] = move.piece_captured

            self.enpassant_possible_log.pop()
            self.enpassant_possible = self.enpassant_possible_log[-1]

            self.castle_rights_log.pop()
            new_rights = copy.deepcopy(self.castle_rights_log[-1])
            self.current_castling_right = new_rights

            if move.is_castle_move:
                if move.end_col - move.start_col == 2:
                    self.board[move.end_row][move.end_col + 1] = self.board[move.end_row][move.end_col - 1]
                    self.board[move.end_row][move.end_col - 1] = " "
                else:
                    self.board[move.end_row][move.end_col - 2] = self.board[move.end_row][move.end_col + 1]
                    self.board[move.end_row][move.end_col + 1] = " "

            self.checkmate = False
            self.stalemate = False

    def update_castle_rights(self, move):
        if move.piece_moved == "K":
            self.current_castling_right.wks = False
            self.current_castling_right.wqs = False
        elif move.piece_moved == "k":
            self.current_castling_right.bks = False
            self.current_castling_right.bqs = False
        elif move.piece_moved == "R":
            if move.start_row == 7:
                if move.start_col == 0:
                    self.current_castling_right.wqs = False
                elif move.start_col == 7:
                    self.current_castling_right.wks = False
        elif move.piece_moved == "r":
            if move.start_row == 0:
                if move.start_col == 0:
                    self.current_castling_right.bqs = False
                elif move.start_col == 7:
                    self.current_castling_right.bks = False

    def get_valid_moves(self):
        temp_enpassant_possible = self.enpassant_possible
        temp_castle_rights = CastleRights(self.current_castling_right.wks, self.current_castling_right.wqs,
                                          self.current_castling_right.bks, self.current_castling_right.bqs)
        
        # 1. Generate all possible moves
        moves = self.get_all_possible_moves()
        if self.white_to_move:
            self.get_castle_moves(self.white_king_location[0], self.white_king_location[1], moves)
        else:
            self.get_castle_moves(self.black_king_location[0], self.black_king_location[1], moves)

        # 2. Filter moves that leave king in check
        for i in range(len(moves) - 1, -1, -1):
            self.make_move(moves[i])
            self.white_to_move = not self.white_to_move
            if self.in_check_state():
                moves.pop(i)
            self.white_to_move = not self.white_to_move
            self.undo_move()

        # Checkmate or Stalemate determination
        if len(moves) == 0:
            if self.in_check_state():
                self.checkmate = True
            else:
                self.stalemate = True
        else:
            self.checkmate = False
            self.stalemate = False

        self.enpassant_possible = temp_enpassant_possible
        self.current_castling_right = temp_castle_rights
        return moves

    def in_check_state(self):
        if self.white_to_move:
            return self.square_under_attack(self.white_king_location[0], self.white_king_location[1])
        else:
            return self.square_under_attack(self.black_king_location[0], self.black_king_location[1])

    def square_under_attack(self, r, c):
        self.white_to_move = not self.white_to_move
        opp_moves = self.get_all_possible_moves()
        self.white_to_move = not self.white_to_move
        for move in opp_moves:
            if move.end_row == r and move.end_col == c:
                return True
        return False

    def get_all_possible_moves(self):
        moves = []
        for r in range(8):
            for c in range(8):
                turn = self.board[r][c]
                if (turn.isupper() and self.white_to_move) or (turn.islower() and not self.white_to_move):
                    piece = turn.lower()
                    if piece == 'p':
                        self.get_pawn_moves(r, c, moves)
                    elif piece == 'r':
                        self.get_rook_moves(r, c, moves)
                    elif piece == 'n':
                        self.get_knight_moves(r, c, moves)
                    elif piece == 'b':
                        self.get_bishop_moves(r, c, moves)
                    elif piece == 'q':
                        self.get_queen_moves(r, c, moves)
                    elif piece == 'k':
                        self.get_king_moves(r, c, moves)
        return moves

    def get_pawn_moves(self, r, c, moves):
        piece_sign = 1 if not self.white_to_move else -1
        start_row = 1 if not self.white_to_move else 6
        enemy = "white" if not self.white_to_move else "black"

        if self.board[r + piece_sign][c] == " ":
            moves.append(Move((r, c), (r + piece_sign, c), self.board))
            if r == start_row and self.board[r + 2 * piece_sign][c] == " ":
                moves.append(Move((r, c), (r + 2 * piece_sign, c), self.board))

        if c - 1 >= 0:
            if self.is_enemy(self.board[r + piece_sign][c - 1], enemy):
                moves.append(Move((r, c), (r + piece_sign, c - 1), self.board))
            elif (r + piece_sign, c - 1) == self.enpassant_possible:
                moves.append(Move((r, c), (r + piece_sign, c - 1), self.board, is_enpassant=True))

        if c + 1 <= 7:
            if self.is_enemy(self.board[r + piece_sign][c + 1], enemy):
                moves.append(Move((r, c), (r + piece_sign, c + 1), self.board))
            elif (r + piece_sign, c + 1) == self.enpassant_possible:
                moves.append(Move((r, c), (r + piece_sign, c + 1), self.board, is_enpassant=True))

    def get_rook_moves(self, r, c, moves):
        directions = ((-1, 0), (0, -1), (1, 0), (0, 1))
        enemy = "black" if self.white_to_move else "white"
        for d in directions:
            for i in range(1, 8):
                end_r, end_c = r + d[0] * i, c + d[1] * i
                if 0 <= end_r < 8 and 0 <= end_c < 8:
                    end_piece = self.board[end_r][end_c]
                    if end_piece == " ":
                        moves.append(Move((r, c), (end_r, end_c), self.board))
                    elif self.is_enemy(end_piece, enemy):
                        moves.append(Move((r, c), (end_r, end_c), self.board))
                        break
                    else:
                        break
                else:
                    break

    def get_knight_moves(self, r, c, moves):
        knight_moves = ((-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1))
        enemy = "black" if self.white_to_move else "white"
        for m in knight_moves:
            end_r, end_c = r + m[0], c + m[1]
            if 0 <= end_r < 8 and 0 <= end_c < 8:
                end_piece = self.board[end_r][end_c]
                if end_piece == " " or self.is_enemy(end_piece, enemy):
                    moves.append(Move((r, c), (end_r, end_c), self.board))

    def get_bishop_moves(self, r, c, moves):
        directions = ((-1, -1), (-1, 1), (1, -1), (1, 1))
        enemy = "black" if self.white_to_move else "white"
        for d in directions:
            for i in range(1, 8):
                end_r, end_c = r + d[0] * i, c + d[1] * i
                if 0 <= end_r < 8 and 0 <= end_c < 8:
                    end_piece = self.board[end_r][end_c]
                    if end_piece == " ":
                        moves.append(Move((r, c), (end_r, end_c), self.board))
                    elif self.is_enemy(end_piece, enemy):
                        moves.append(Move((r, c), (end_r, end_c), self.board))
                        break
                    else:
                        break
                else:
                    break

    def get_queen_moves(self, r, c, moves):
        self.get_rook_moves(r, c, moves)
        self.get_bishop_moves(r, c, moves)

    def get_king_moves(self, r, c, moves):
        king_moves = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
        enemy = "black" if self.white_to_move else "white"
        for i in range(8):
            end_r, end_c = r + king_moves[i][0], c + king_moves[i][1]
            if 0 <= end_r < 8 and 0 <= end_c < 8:
                end_piece = self.board[end_r][end_c]
                if end_piece == " " or self.is_enemy(end_piece, enemy):
                    moves.append(Move((r, c), (end_r, end_c), self.board))

    def get_castle_moves(self, r, c, moves):
        if self.square_under_attack(r, c):
            return
        if (self.white_to_move and self.current_castling_right.wks) or (not self.white_to_move and self.current_castling_right.bks):
            self.get_kingside_castle_moves(r, c, moves)
        if (self.white_to_move and self.current_castling_right.wqs) or (not self.white_to_move and self.current_castling_right.bqs):
            self.get_queenside_castle_moves(r, c, moves)

    def get_kingside_castle_moves(self, r, c, moves):
        if self.board[r][c + 1] == ' ' and self.board[r][c + 2] == ' ':
            if not self.square_under_attack(r, c + 1) and not self.square_under_attack(r, c + 2):
                moves.append(Move((r, c), (r, c + 2), self.board, is_castle=True))

    def get_queenside_castle_moves(self, r, c, moves):
        if self.board[r][c - 1] == ' ' and self.board[r][c - 2] == ' ' and self.board[r][c - 3] == ' ':
            if not self.square_under_attack(r, c - 1) and not self.square_under_attack(r, c - 2):
                moves.append(Move((r, c), (r, c - 2), self.board, is_castle=True))

    def is_enemy(self, piece, player_color):
        return (player_color == "white" and piece.isupper()) or (player_color == "black" and piece.islower())