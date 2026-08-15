import random

PIECE_SCORE = {
    "K": 0, "Q": 900, "R": 500, "B": 330, "N": 320, "P": 100,
    "k": 0, "q": 900, "r": 500, "b": 330, "n": 320, "p": 100
}

pawn_table = [
    [0,  0,  0,  0,  0,  0,  0,  0],
    [50, 50, 50, 50, 50, 50, 50, 50],
    [10, 10, 20, 30, 30, 20, 10, 10],
    [5,  5, 10, 27, 27, 10,  5,  5],
    [0,  0,  0, 25, 25,  0,  0,  0],
    [5, -5,-10,  0,  0,-10, -5,  5],
    [5, 10, 10,-20,-20, 10, 10,  5],
    [0,  0,  0,  0,  0,  0,  0,  0]
]

knight_table = [
    [-50,-40,-30,-30,-30,-30,-40,-50],
    [-40,-20,  0,  0,  0,  0,-20,-40],
    [-30,  0, 10, 15, 15, 10,  0,-30],
    [-30,  5, 15, 20, 20, 15,  5,-30],
    [-30,  0, 15, 20, 20, 15,  0,-30],
    [-30,  5, 10, 15, 15, 10,  5,-30],
    [-40,-20,  0,  5,  5,  0,-20,-40],
    [-50,-40,-30,-30,-30,-30,-40,-50]
]

bishop_table = [
    [-20,-10,-10,-10,-10,-10,-10,-20],
    [-10,  0,  0,  0,  0,  0,  0,-10],
    [-10,  0,  5, 10, 10,  5,  0,-10],
    [-10,  5,  5, 10, 10,  5,  5,-10],
    [-10,  0, 10, 10, 10, 10,  0,-10],
    [-10, 10, 10, 10, 10, 10, 10,-10],
    [-10,  5,  0,  0,  0,  0,  5,-10],
    [-20,-10,-10,-10,-10,-10,-10,-20]
]

POSITION_BOARDS = {
    "P": pawn_table, "p": pawn_table[::-1],
    "N": knight_table, "n": knight_table,
    "B": bishop_table, "b": bishop_table
}

# Depth set to 2 for instant responsive UI without frame freeze
DEPTH = 2

def find_best_move(gs, valid_moves):
    global next_move
    next_move = None
    if not valid_moves:
        return None
        
    random.shuffle(valid_moves)
    find_move_minimax(gs, valid_moves, DEPTH, -100000, 100000, 1 if gs.white_to_move else -1)
    
    # Fallback to random legal move if tree search fails
    if next_move is None and valid_moves:
        return random.choice(valid_moves)
    return next_move

def find_move_minimax(gs, valid_moves, depth, alpha, beta, turn_multiplier):
    global next_move
    
    # Keep window responsive while AI computes
    import pygame
    pygame.event.pump()

    if depth == 0 or len(valid_moves) == 0:
        return turn_multiplier * evaluate_board(gs)

    max_score = -100000
    for move in valid_moves:
        gs.make_move(move)
        
        # Use simple move generator for deeper trees to avoid recursion lock
        next_moves = gs.get_all_possible_moves()
        score = -find_move_minimax(gs, next_moves, depth - 1, -beta, -alpha, -turn_multiplier)
        
        if score > max_score:
            max_score = score
            if depth == DEPTH:
                next_move = move
                
        gs.undo_move()
        
        if max_score > alpha:
            alpha = max_score
        if alpha >= beta:
            break
            
    return max_score

def evaluate_board(gs):
    if gs.checkmate:
        return -99999 if gs.white_to_move else 99999
    elif gs.stalemate:
        return 0

    score = 0
    for r in range(8):
        for c in range(8):
            piece = gs.board[r][c]
            if piece != " ":
                val = PIECE_SCORE[piece]
                if piece in POSITION_BOARDS:
                    val += POSITION_BOARDS[piece][r][c]
                if piece.isupper():
                    score += val
                else:
                    score -= val
    return score