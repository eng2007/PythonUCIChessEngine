"""
OpusChess - Position Evaluation Module (Basic Version)

This module provides static evaluation of chess positions.
The evaluation considers material balance and piece positioning
using piece-square tables.
"""

from board import (
    Board, EMPTY, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    WHITE, BLACK, get_piece_type, get_piece_color
)

# Piece values in centipawns
PIECE_VALUES = {
    PAWN: 100,
    KNIGHT: 320,
    BISHOP: 330,
    ROOK: 500,
    QUEEN: 900,
    KING: 20000
}

# Piece-Square Tables (PST)
# Values are from White's perspective, for ranks 1-8 (index 0-7)
# Positive values are good for the piece

# Pawn PST - encourages central control and advancement
PAWN_PST = [
    0,   0,   0,   0,   0,   0,   0,   0,   # Rank 1 (never used)
    5,  10,  10, -20, -20,  10,  10,   5,   # Rank 2
   5,  -5, -10,   0,   0, -10,  -5,   5,   # Rank 3
    0,   0,   0,  20,  20,   0,   0,   0,   # Rank 4
    5,   5,  10,  25,  25,  10,   5,   5,   # Rank 5
   10,  10,  20,  30,  30,  20,  10,  10,   # Rank 6
   50,  50,  50,  50,  50,  50,  50,  50,   # Rank 7
    0,   0,   0,   0,   0,   0,   0,   0,   # Rank 8 (promotion)
]

# Knight PST - encourages central positioning
KNIGHT_PST = [
   -50, -40, -30, -30, -30, -30, -40, -50,
   -40, -20,   0,   5,   5,   0, -20, -40,
   -30,   5,  10,  15,  15,  10,   5, -30,
   -30,   0,  15,  20,  20,  15,   0, -30,
   -30,   5,  15,  20,  20,  15,   5, -30,
   -30,   0,  10,  15,  15,  10,   0, -30,
   -40, -20,   0,   0,   0,   0, -20, -40,
   -50, -40, -30, -30, -30, -30, -40, -50,
]

# Bishop PST - encourages diagonals and avoiding corners
BISHOP_PST = [
   -20, -10, -10, -10, -10, -10, -10, -20,
   -10,   5,   0,   0,   0,   0,   5, -10,
   -10,  10,  10,  10,  10,  10,  10, -10,
   -10,   0,  10,  10,  10,  10,   0, -10,
   -10,   5,   5,  10,  10,   5,   5, -10,
   -10,   0,   5,  10,  10,   5,   0, -10,
   -10,   0,   0,   0,   0,   0,   0, -10,
   -20, -10, -10, -10, -10, -10, -10, -20,
]

# Rook PST - encourages 7th rank and open files
ROOK_PST = [
    0,   0,   0,   5,   5,   0,   0,   0,
   -5,   0,   0,   0,   0,   0,   0,  -5,
   -5,   0,   0,   0,   0,   0,   0,  -5,
   -5,   0,   0,   0,   0,   0,   0,  -5,
   -5,   0,   0,   0,   0,   0,   0,  -5,
   -5,   0,   0,   0,   0,   0,   0,  -5,
    5,  10,  10,  10,  10,  10,  10,   5,
    0,   0,   0,   0,   0,   0,   0,   0,
]

# Queen PST - encourages central control, but not too early
QUEEN_PST = [
   -20, -10, -10,  -5,  -5, -10, -10, -20,
   -10,   0,   5,   0,   0,   0,   0, -10,
   -10,   5,   5,   5,   5,   5,   0, -10,
    0,   0,   5,   5,   5,   5,   0,  -5,
   -5,   0,   5,   5,   5,   5,   0,  -5,
   -10,   0,   5,   5,   5,   5,   0, -10,
   -10,   0,   0,   0,   0,   0,   0, -10,
   -20, -10, -10,  -5,  -5, -10, -10, -20,
]

# King PST for middlegame - encourages castled position
KING_MIDDLEGAME_PST = [
    20,  30,  10,   0,   0,  10,  30,  20,
    20,  20,   0,   0,   0,   0,  20,  20,
   -10, -20, -20, -20, -20, -20, -20, -10,
   -20, -30, -30, -40, -40, -30, -30, -20,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
]

# King PST for endgame - encourages central king
KING_ENDGAME_PST = [
   -50, -30, -30, -30, -30, -30, -30, -50,
   -30, -30,   0,   0,   0,   0, -30, -30,
   -30, -10,  20,  30,  30,  20, -10, -30,
   -30, -10,  30,  40,  40,  30, -10, -30,
   -30, -10,  30,  40,  40,  30, -10, -30,
   -30, -10,  20,  30,  30,  20, -10, -30,
   -30, -20, -10,   0,   0, -10, -20, -30,
   -50, -40, -30, -20, -20, -30, -40, -50,
]

# Map piece types to their PST
PIECE_SQUARE_TABLES = {
    PAWN: PAWN_PST,
    KNIGHT: KNIGHT_PST,
    BISHOP: BISHOP_PST,
    ROOK: ROOK_PST,
    QUEEN: QUEEN_PST,
    KING: KING_MIDDLEGAME_PST,  # Default to middlegame
}


def get_pst_value(piece_type: int, sq: int, is_white: bool, is_endgame: bool = False) -> int:
    """
    Get piece-square table value for a piece.
    
    Args:
        piece_type: Type of piece (PAWN, KNIGHT, etc.)
        sq: Square index (0-63)
        is_white: True if the piece is white
        is_endgame: True if in endgame (affects king PST)
        
    Returns:
        PST bonus/penalty in centipawns
    """
    if piece_type == KING and is_endgame:
        pst = KING_ENDGAME_PST
    else:
        pst = PIECE_SQUARE_TABLES.get(piece_type)
    
    if pst is None:
        return 0
    
    # For white, use square directly
    # For black, mirror the square vertically
    if is_white:
        index = sq
    else:
        rank = sq // 8
        file = sq % 8
        mirrored_rank = 7 - rank
        index = mirrored_rank * 8 + file
    
    return pst[index]


def count_material(board: Board) -> tuple:
    """
    Count material for both sides.
    
    Returns:
        Tuple of (white_material, black_material) excluding kings
    """
    white_material = 0
    black_material = 0
    
    for sq in range(64):
        piece = board.squares[sq]
        if piece == EMPTY:
            continue
        
        piece_type = get_piece_type(piece)
        if piece_type == KING:
            continue
        
        value = PIECE_VALUES.get(piece_type, 0)
        
        if get_piece_color(piece) == WHITE:
            white_material += value
        else:
            black_material += value
    
    return white_material, black_material


def is_endgame(board: Board) -> bool:
    """
    Determine if the position is an endgame.
    
    Endgame is defined as: no queens, or each side has at most
    queen + minor piece worth of material.
    """
    white_material, black_material = count_material(board)
    
    # Simple heuristic: endgame if total material is low
    # Queen = 900, so if each side has <= 1300 (Q + minor), it's endgame
    return white_material <= 1300 and black_material <= 1300


def evaluate(board: Board) -> int:
    """
    Evaluate the current position.
    
    Returns:
        Score in centipawns from the perspective of the side to move.
        Positive = good for side to move, negative = bad.
    """
    if board.has_insufficient_material():
        return 0
    
    endgame = is_endgame(board)
    
    white_score = 0
    black_score = 0
    
    for sq in range(64):
        piece = board.squares[sq]
        if piece == EMPTY:
            continue
        
        piece_type = get_piece_type(piece)
        piece_color = get_piece_color(piece)
        
        # Material value
        material = PIECE_VALUES.get(piece_type, 0)
        
        # Position value
        is_white_piece = piece_color == WHITE
        position = get_pst_value(piece_type, sq, is_white_piece, endgame)
        
        if is_white_piece:
            white_score += material + position
        else:
            black_score += material + position
    
    # Calculate score relative to side to move
    score = white_score - black_score
    
    if not board.white_to_move:
        score = -score
    
    return score


def evaluate_move(board: Board, move) -> int:
    """
    Estimate the value of a move for move ordering.
    
    This is used to order moves before searching, without actually
    making the move. Higher values = likely better moves.
    
    Args:
        board: Current board state
        move: Move to evaluate
        
    Returns:
        Estimated move value (higher = better)
    """
    score = 0
    
    from_piece = board.squares[move.from_sq]
    to_piece = board.squares[move.to_sq]
    
    # Captures: MVV-LVA (Most Valuable Victim - Least Valuable Attacker)
    if to_piece != EMPTY:
        victim_value = PIECE_VALUES.get(get_piece_type(to_piece), 0)
        attacker_value = PIECE_VALUES.get(get_piece_type(from_piece), 0)
        score += 10000 + victim_value - attacker_value // 100
    
    # En passant capture
    if move.is_en_passant:
        score += 10000 + PIECE_VALUES[PAWN]
    
    # Promotions
    if move.promotion:
        score += 9000 + PIECE_VALUES.get(move.promotion, 0)
    
    # Castling is generally good
    if move.is_castling:
        score += 500
    
    # PST improvement (rough estimate)
    piece_type = get_piece_type(from_piece)
    is_white_piece = get_piece_color(from_piece) == WHITE
    
    from_pst = get_pst_value(piece_type, move.from_sq, is_white_piece)
    to_pst = get_pst_value(piece_type, move.to_sq, is_white_piece)
    score += to_pst - from_pst
    
    return score
