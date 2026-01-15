"""
OpusChess - Position Evaluation Module (Enhanced)

This module provides static evaluation of chess positions.
The evaluation considers:
- Material balance
- Piece positioning (piece-square tables)
- Pawn structure (doubled, isolated, passed pawns)
- King safety
- Piece mobility
- Bishop pair bonus
- Rook on open/semi-open files
- Control of center
"""

from board import (
    Board, EMPTY, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    WHITE, BLACK, get_piece_type, get_piece_color,
    WHITE_PAWN, BLACK_PAWN, WHITE_ROOK, BLACK_ROOK,
    WHITE_BISHOP, BLACK_BISHOP, WHITE_QUEEN, BLACK_QUEEN
)

# ============================================================================
# PIECE VALUES
# ============================================================================

PIECE_VALUES = {
    PAWN: 100,
    KNIGHT: 320,
    BISHOP: 330,
    ROOK: 500,
    QUEEN: 900,
    KING: 20000
}

# ============================================================================
# PIECE-SQUARE TABLES
# ============================================================================

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

# Rook PST - encourages 7th rank and central files
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

PIECE_SQUARE_TABLES = {
    PAWN: PAWN_PST,
    KNIGHT: KNIGHT_PST,
    BISHOP: BISHOP_PST,
    ROOK: ROOK_PST,
    QUEEN: QUEEN_PST,
    KING: KING_MIDDLEGAME_PST,
}

# ============================================================================
# EVALUATION BONUSES/PENALTIES (in centipawns)
# ============================================================================

# Pawn structure
DOUBLED_PAWN_PENALTY = -15
ISOLATED_PAWN_PENALTY = -20
PASSED_PAWN_BONUS = [0, 10, 20, 35, 60, 100, 150, 0]  # By rank for white
BACKWARD_PAWN_PENALTY = -10
PAWN_CHAIN_BONUS = 5  # Per pawn in chain

# King safety
KING_PAWN_SHIELD_BONUS = 10  # Per pawn in front of king
OPEN_FILE_NEAR_KING_PENALTY = -25  # Per open file near king
SEMI_OPEN_FILE_NEAR_KING_PENALTY = -15

# Piece bonuses
BISHOP_PAIR_BONUS = 50
ROOK_ON_OPEN_FILE_BONUS = 25
ROOK_ON_SEMI_OPEN_FILE_BONUS = 15
ROOK_ON_7TH_RANK_BONUS = 30
CONNECTED_ROOKS_BONUS = 15

# Mobility (bonus per available square)
KNIGHT_MOBILITY_BONUS = 4
BISHOP_MOBILITY_BONUS = 5
ROOK_MOBILITY_BONUS = 3
QUEEN_MOBILITY_BONUS = 2

# Center control
CENTER_SQUARES = [27, 28, 35, 36]  # d4, e4, d5, e5
EXTENDED_CENTER = [18, 19, 20, 21, 26, 29, 34, 37, 42, 43, 44, 45]
CENTER_PAWN_BONUS = 15
EXTENDED_CENTER_PAWN_BONUS = 8


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_pst_value(piece_type: int, sq: int, is_white: bool, is_endgame: bool = False) -> int:
    """Get piece-square table value for a piece."""
    if piece_type == KING and is_endgame:
        pst = KING_ENDGAME_PST
    else:
        pst = PIECE_SQUARE_TABLES.get(piece_type)
    
    if pst is None:
        return 0
    
    if is_white:
        index = sq
    else:
        rank = sq // 8
        file = sq % 8
        mirrored_rank = 7 - rank
        index = mirrored_rank * 8 + file
    
    return pst[index]


def count_material(board: Board) -> tuple:
    """Count material for both sides (excluding kings)."""
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
    """Determine if the position is an endgame."""
    white_material, black_material = count_material(board)
    return white_material <= 1300 and black_material <= 1300


def get_pawn_files(board: Board) -> tuple:
    """
    Get lists of files containing pawns for each side.
    Returns (white_pawn_files, black_pawn_files) as sets of file indices (0-7).
    Also returns pawn positions for each color.
    """
    white_pawns = []  # List of squares with white pawns
    black_pawns = []  # List of squares with black pawns
    
    for sq in range(64):
        piece = board.squares[sq]
        if piece == WHITE_PAWN:
            white_pawns.append(sq)
        elif piece == BLACK_PAWN:
            black_pawns.append(sq)
    
    return white_pawns, black_pawns


def get_pawn_count_per_file(pawns: list) -> dict:
    """Count pawns per file."""
    counts = {}
    for sq in pawns:
        file = sq % 8
        counts[file] = counts.get(file, 0) + 1
    return counts


# ============================================================================
# PAWN STRUCTURE EVALUATION
# ============================================================================

def evaluate_pawn_structure(board: Board, white_pawns: list, black_pawns: list) -> int:
    """
    Evaluate pawn structure for both sides.
    
    Considers:
    - Doubled pawns
    - Isolated pawns
    - Passed pawns
    - Pawn chains
    """
    score = 0
    
    white_files = get_pawn_count_per_file(white_pawns)
    black_files = get_pawn_count_per_file(black_pawns)
    
    # Evaluate white pawns
    for sq in white_pawns:
        file = sq % 8
        rank = sq // 8
        
        # Doubled pawns
        if white_files.get(file, 0) > 1:
            score += DOUBLED_PAWN_PENALTY
        
        # Isolated pawns (no friendly pawns on adjacent files)
        has_neighbor = False
        for adj_file in [file - 1, file + 1]:
            if 0 <= adj_file <= 7 and adj_file in white_files:
                has_neighbor = True
                break
        if not has_neighbor:
            score += ISOLATED_PAWN_PENALTY
        
        # Passed pawns (no enemy pawns in front or on adjacent files)
        is_passed = True
        for check_file in [file - 1, file, file + 1]:
            if check_file < 0 or check_file > 7:
                continue
            for check_rank in range(rank + 1, 8):
                check_sq = check_rank * 8 + check_file
                if board.squares[check_sq] == BLACK_PAWN:
                    is_passed = False
                    break
            if not is_passed:
                break
        if is_passed:
            score += PASSED_PAWN_BONUS[rank]
        
        # Pawn chain (protected by another pawn)
        for defender_sq in [sq - 9, sq - 7]:
            if 0 <= defender_sq < 64:
                def_file = defender_sq % 8
                if abs(def_file - file) == 1:
                    if board.squares[defender_sq] == WHITE_PAWN:
                        score += PAWN_CHAIN_BONUS
                        break
    
    # Evaluate black pawns (mirror the logic)
    for sq in black_pawns:
        file = sq % 8
        rank = sq // 8
        
        # Doubled pawns
        if black_files.get(file, 0) > 1:
            score -= DOUBLED_PAWN_PENALTY
        
        # Isolated pawns
        has_neighbor = False
        for adj_file in [file - 1, file + 1]:
            if 0 <= adj_file <= 7 and adj_file in black_files:
                has_neighbor = True
                break
        if not has_neighbor:
            score -= ISOLATED_PAWN_PENALTY
        
        # Passed pawns
        is_passed = True
        for check_file in [file - 1, file, file + 1]:
            if check_file < 0 or check_file > 7:
                continue
            for check_rank in range(0, rank):
                check_sq = check_rank * 8 + check_file
                if board.squares[check_sq] == WHITE_PAWN:
                    is_passed = False
                    break
            if not is_passed:
                break
        if is_passed:
            score -= PASSED_PAWN_BONUS[7 - rank]
        
        # Pawn chain
        for defender_sq in [sq + 9, sq + 7]:
            if 0 <= defender_sq < 64:
                def_file = defender_sq % 8
                if abs(def_file - file) == 1:
                    if board.squares[defender_sq] == BLACK_PAWN:
                        score -= PAWN_CHAIN_BONUS
                        break
    
    return score


# ============================================================================
# KING SAFETY EVALUATION
# ============================================================================

def evaluate_king_safety(board: Board, white_pawns: list, black_pawns: list, 
                         endgame: bool) -> int:
    """
    Evaluate king safety for both sides.
    
    Considers:
    - Pawn shield in front of king
    - Open files near king
    """
    if endgame:
        return 0  # King safety less important in endgame
    
    score = 0
    
    white_king_sq = board.find_king(True)
    black_king_sq = board.find_king(False)
    
    white_pawn_set = set(white_pawns)
    black_pawn_set = set(black_pawns)
    
    # White king safety
    wk_file = white_king_sq % 8
    wk_rank = white_king_sq // 8
    
    # Pawn shield (pawns on ranks 2-3 in front of king)
    for file_offset in [-1, 0, 1]:
        shield_file = wk_file + file_offset
        if shield_file < 0 or shield_file > 7:
            continue
        
        for rank in [1, 2]:  # Ranks 2-3 (0-indexed: 1, 2)
            sq = rank * 8 + shield_file
            if sq in white_pawn_set:
                score += KING_PAWN_SHIELD_BONUS
                break
    
    # Open/semi-open files near king
    for file_offset in [-1, 0, 1]:
        check_file = wk_file + file_offset
        if check_file < 0 or check_file > 7:
            continue
        
        white_pawn_on_file = any(p % 8 == check_file for p in white_pawns)
        black_pawn_on_file = any(p % 8 == check_file for p in black_pawns)
        
        if not white_pawn_on_file and not black_pawn_on_file:
            score += OPEN_FILE_NEAR_KING_PENALTY
        elif not white_pawn_on_file:
            score += SEMI_OPEN_FILE_NEAR_KING_PENALTY
    
    # Black king safety (mirror)
    bk_file = black_king_sq % 8
    bk_rank = black_king_sq // 8
    
    for file_offset in [-1, 0, 1]:
        shield_file = bk_file + file_offset
        if shield_file < 0 or shield_file > 7:
            continue
        
        for rank in [6, 5]:  # Ranks 7-6 (0-indexed: 6, 5)
            sq = rank * 8 + shield_file
            if sq in black_pawn_set:
                score -= KING_PAWN_SHIELD_BONUS
                break
    
    for file_offset in [-1, 0, 1]:
        check_file = bk_file + file_offset
        if check_file < 0 or check_file > 7:
            continue
        
        white_pawn_on_file = any(p % 8 == check_file for p in white_pawns)
        black_pawn_on_file = any(p % 8 == check_file for p in black_pawns)
        
        if not white_pawn_on_file and not black_pawn_on_file:
            score -= OPEN_FILE_NEAR_KING_PENALTY
        elif not black_pawn_on_file:
            score -= SEMI_OPEN_FILE_NEAR_KING_PENALTY
    
    return score


# ============================================================================
# PIECE ACTIVITY EVALUATION
# ============================================================================

def evaluate_pieces(board: Board, white_pawns: list, black_pawns: list) -> int:
    """
    Evaluate piece activity and positioning.
    
    Considers:
    - Bishop pair
    - Rooks on open/semi-open files
    - Rooks on 7th rank
    - Connected rooks
    """
    score = 0
    
    white_bishops = 0
    black_bishops = 0
    white_rooks = []
    black_rooks = []
    
    white_pawn_files = set(p % 8 for p in white_pawns)
    black_pawn_files = set(p % 8 for p in black_pawns)
    
    for sq in range(64):
        piece = board.squares[sq]
        if piece == EMPTY:
            continue
        
        piece_type = get_piece_type(piece)
        is_white = get_piece_color(piece) == WHITE
        file = sq % 8
        rank = sq // 8
        
        if piece_type == BISHOP:
            if is_white:
                white_bishops += 1
            else:
                black_bishops += 1
        
        elif piece_type == ROOK:
            if is_white:
                white_rooks.append(sq)
                
                # Rook on open file
                if file not in white_pawn_files and file not in black_pawn_files:
                    score += ROOK_ON_OPEN_FILE_BONUS
                elif file not in white_pawn_files:
                    score += ROOK_ON_SEMI_OPEN_FILE_BONUS
                
                # Rook on 7th rank
                if rank == 6:
                    score += ROOK_ON_7TH_RANK_BONUS
            else:
                black_rooks.append(sq)
                
                # Rook on open file
                if file not in white_pawn_files and file not in black_pawn_files:
                    score -= ROOK_ON_OPEN_FILE_BONUS
                elif file not in black_pawn_files:
                    score -= ROOK_ON_SEMI_OPEN_FILE_BONUS
                
                # Rook on 2nd rank (7th from black's perspective)
                if rank == 1:
                    score -= ROOK_ON_7TH_RANK_BONUS
    
    # Bishop pair
    if white_bishops >= 2:
        score += BISHOP_PAIR_BONUS
    if black_bishops >= 2:
        score -= BISHOP_PAIR_BONUS
    
    # Connected rooks (on same rank with no pieces between)
    if len(white_rooks) == 2:
        r1, r2 = white_rooks
        if r1 // 8 == r2 // 8:  # Same rank
            rank = r1 // 8
            f1, f2 = min(r1 % 8, r2 % 8), max(r1 % 8, r2 % 8)
            connected = True
            for f in range(f1 + 1, f2):
                if board.squares[rank * 8 + f] != EMPTY:
                    connected = False
                    break
            if connected:
                score += CONNECTED_ROOKS_BONUS
    
    if len(black_rooks) == 2:
        r1, r2 = black_rooks
        if r1 // 8 == r2 // 8:
            rank = r1 // 8
            f1, f2 = min(r1 % 8, r2 % 8), max(r1 % 8, r2 % 8)
            connected = True
            for f in range(f1 + 1, f2):
                if board.squares[rank * 8 + f] != EMPTY:
                    connected = False
                    break
            if connected:
                score -= CONNECTED_ROOKS_BONUS
    
    return score


# ============================================================================
# MOBILITY EVALUATION
# ============================================================================

def count_mobility(board: Board, sq: int, piece_type: int, is_white: bool) -> int:
    """Count the number of squares a piece can move to (simplified)."""
    moves = 0
    file = sq % 8
    rank = sq // 8
    color = WHITE if is_white else BLACK
    
    if piece_type == KNIGHT:
        offsets = [17, 15, 10, 6, -6, -10, -15, -17]
        for offset in offsets:
            to_sq = sq + offset
            if to_sq < 0 or to_sq >= 64:
                continue
            to_file = to_sq % 8
            if abs(to_file - file) > 2:
                continue
            target = board.squares[to_sq]
            if target == EMPTY or get_piece_color(target) != color:
                moves += 1
    
    elif piece_type == BISHOP:
        directions = [7, 9, -7, -9]
        for d in directions:
            current = sq
            while True:
                curr_file = current % 8
                next_sq = current + d
                if next_sq < 0 or next_sq >= 64:
                    break
                next_file = next_sq % 8
                if abs(next_file - curr_file) != 1:
                    break
                target = board.squares[next_sq]
                if target == EMPTY:
                    moves += 1
                    current = next_sq
                else:
                    if get_piece_color(target) != color:
                        moves += 1
                    break
    
    elif piece_type == ROOK:
        directions = [8, -8, 1, -1]
        for d in directions:
            current = sq
            while True:
                curr_file = current % 8
                next_sq = current + d
                if next_sq < 0 or next_sq >= 64:
                    break
                next_file = next_sq % 8
                if d in [1, -1] and abs(next_file - curr_file) != 1:
                    break
                target = board.squares[next_sq]
                if target == EMPTY:
                    moves += 1
                    current = next_sq
                else:
                    if get_piece_color(target) != color:
                        moves += 1
                    break
    
    elif piece_type == QUEEN:
        directions = [8, -8, 1, -1, 7, 9, -7, -9]
        for d in directions:
            current = sq
            while True:
                curr_file = current % 8
                next_sq = current + d
                if next_sq < 0 or next_sq >= 64:
                    break
                next_file = next_sq % 8
                if d in [1, -1, 7, -9, 9, -7]:
                    if abs(next_file - curr_file) != 1:
                        break
                target = board.squares[next_sq]
                if target == EMPTY:
                    moves += 1
                    current = next_sq
                else:
                    if get_piece_color(target) != color:
                        moves += 1
                    break
    
    return moves


def evaluate_mobility(board: Board) -> int:
    """Evaluate piece mobility for both sides."""
    score = 0
    
    mobility_bonus = {
        KNIGHT: KNIGHT_MOBILITY_BONUS,
        BISHOP: BISHOP_MOBILITY_BONUS,
        ROOK: ROOK_MOBILITY_BONUS,
        QUEEN: QUEEN_MOBILITY_BONUS,
    }
    
    for sq in range(64):
        piece = board.squares[sq]
        if piece == EMPTY:
            continue
        
        piece_type = get_piece_type(piece)
        if piece_type not in mobility_bonus:
            continue
        
        is_white = get_piece_color(piece) == WHITE
        moves = count_mobility(board, sq, piece_type, is_white)
        bonus = moves * mobility_bonus[piece_type]
        
        if is_white:
            score += bonus
        else:
            score -= bonus
    
    return score


# ============================================================================
# CENTER CONTROL EVALUATION
# ============================================================================

def evaluate_center_control(board: Board) -> int:
    """Evaluate control of the center squares."""
    score = 0
    
    for sq in CENTER_SQUARES:
        piece = board.squares[sq]
        if piece != EMPTY and get_piece_type(piece) == PAWN:
            if get_piece_color(piece) == WHITE:
                score += CENTER_PAWN_BONUS
            else:
                score -= CENTER_PAWN_BONUS
    
    for sq in EXTENDED_CENTER:
        piece = board.squares[sq]
        if piece != EMPTY and get_piece_type(piece) == PAWN:
            if get_piece_color(piece) == WHITE:
                score += EXTENDED_CENTER_PAWN_BONUS
            else:
                score -= EXTENDED_CENTER_PAWN_BONUS
    
    return score


# ============================================================================
# ENDGAME KNOWLEDGE
# ============================================================================

# Distance from edge of board (for driving king to corner/edge)
def distance_from_edge(sq: int) -> int:
    """Calculate minimum distance from square to board edge."""
    file = sq % 8
    rank = sq // 8
    return min(file, 7 - file, rank, 7 - rank)


def distance_from_corner(sq: int) -> int:
    """Calculate minimum distance from square to nearest corner."""
    file = sq % 8
    rank = sq // 8
    # Distance to each corner
    corners = [
        file + rank,           # a1
        (7 - file) + rank,     # h1
        file + (7 - rank),     # a8
        (7 - file) + (7 - rank) # h8
    ]
    return min(corners)


def king_distance(sq1: int, sq2: int) -> int:
    """Calculate Chebyshev distance between two squares (king moves)."""
    file1, rank1 = sq1 % 8, sq1 // 8
    file2, rank2 = sq2 % 8, sq2 // 8
    return max(abs(file1 - file2), abs(rank1 - rank2))


def get_piece_positions(board: Board) -> dict:
    """
    Get positions of all pieces on the board.
    Returns dict with piece type -> list of (square, color) pairs.
    """
    pieces = {
        PAWN: [], KNIGHT: [], BISHOP: [], ROOK: [], QUEEN: [], KING: []
    }
    
    for sq in range(64):
        piece = board.squares[sq]
        if piece != EMPTY:
            pt = get_piece_type(piece)
            color = get_piece_color(piece)
            pieces[pt].append((sq, color))
    
    return pieces


def detect_endgame_type(board: Board) -> str:
    """
    Detect the type of endgame for specialized evaluation.
    Returns a string identifier or None for normal evaluation.
    """
    pieces = get_piece_positions(board)
    
    white_pawns = sum(1 for sq, c in pieces[PAWN] if c == WHITE)
    black_pawns = sum(1 for sq, c in pieces[PAWN] if c == BLACK)
    white_knights = sum(1 for sq, c in pieces[KNIGHT] if c == WHITE)
    black_knights = sum(1 for sq, c in pieces[KNIGHT] if c == BLACK)
    white_bishops = sum(1 for sq, c in pieces[BISHOP] if c == WHITE)
    black_bishops = sum(1 for sq, c in pieces[BISHOP] if c == BLACK)
    white_rooks = sum(1 for sq, c in pieces[ROOK] if c == WHITE)
    black_rooks = sum(1 for sq, c in pieces[ROOK] if c == BLACK)
    white_queens = sum(1 for sq, c in pieces[QUEEN] if c == WHITE)
    black_queens = sum(1 for sq, c in pieces[QUEEN] if c == BLACK)
    
    total_pawns = white_pawns + black_pawns
    white_pieces = white_knights + white_bishops + white_rooks + white_queens
    black_pieces = black_knights + black_bishops + black_rooks + black_queens
    
    # K vs K - draw
    if total_pawns == 0 and white_pieces == 0 and black_pieces == 0:
        return "KK"
    
    # KQ vs K
    if white_queens == 1 and black_pieces == 0 and total_pawns == 0 and white_pieces == 1:
        return "KQK_WHITE"
    if black_queens == 1 and white_pieces == 0 and total_pawns == 0 and black_pieces == 1:
        return "KQK_BLACK"
    
    # KR vs K
    if white_rooks == 1 and black_pieces == 0 and total_pawns == 0 and white_pieces == 1:
        return "KRK_WHITE"
    if black_rooks == 1 and white_pieces == 0 and total_pawns == 0 and black_pieces == 1:
        return "KRK_BLACK"
    
    # KBB vs K (same color bishops are draw, opposite color is mate)
    if white_bishops == 2 and white_pieces == 2 and black_pieces == 0 and total_pawns == 0:
        return "KBBK_WHITE"
    if black_bishops == 2 and black_pieces == 2 and white_pieces == 0 and total_pawns == 0:
        return "KBBK_BLACK"
    
    # KBN vs K
    if (white_bishops == 1 and white_knights == 1 and white_pieces == 2 and 
        black_pieces == 0 and total_pawns == 0):
        return "KBNK_WHITE"
    if (black_bishops == 1 and black_knights == 1 and black_pieces == 2 and 
        white_pieces == 0 and total_pawns == 0):
        return "KBNK_BLACK"
    
    # KP vs K
    if white_pawns == 1 and black_pawns == 0 and white_pieces == 0 and black_pieces == 0:
        return "KPK_WHITE"
    if black_pawns == 1 and white_pawns == 0 and white_pieces == 0 and black_pieces == 0:
        return "KPK_BLACK"
    
    # KR vs KP
    if (white_rooks == 1 and white_pieces == 1 and black_pawns == 1 and 
        black_pieces == 0 and white_pawns == 0):
        return "KRKP_WHITE"
    if (black_rooks == 1 and black_pieces == 1 and white_pawns == 1 and 
        white_pieces == 0 and black_pawns == 0):
        return "KRKP_BLACK"
    
    return None


def evaluate_kqk(board: Board, strong_side_white: bool) -> int:
    """
    Evaluate KQ vs K endgame.
    Drive the weak king to the edge/corner.
    """
    pieces = get_piece_positions(board)
    
    # Find kings
    strong_king = None
    weak_king = None
    
    for sq, color in pieces[KING]:
        if (color == WHITE) == strong_side_white:
            strong_king = sq
        else:
            weak_king = sq
    
    if weak_king is None or strong_king is None:
        return 0
    
    # Base score: Queen value
    score = PIECE_VALUES[QUEEN]
    
    # Bonus for driving weak king to edge
    edge_dist = distance_from_edge(weak_king)
    score += (3 - edge_dist) * 20
    
    # Bonus for strong king close to weak king (for final mate)
    k_dist = king_distance(strong_king, weak_king)
    score += (7 - k_dist) * 10
    
    return score if strong_side_white else -score


def evaluate_krk(board: Board, strong_side_white: bool) -> int:
    """
    Evaluate KR vs K endgame.
    Drive the weak king to the edge.
    """
    pieces = get_piece_positions(board)
    
    strong_king = None
    weak_king = None
    
    for sq, color in pieces[KING]:
        if (color == WHITE) == strong_side_white:
            strong_king = sq
        else:
            weak_king = sq
    
    if weak_king is None or strong_king is None:
        return 0
    
    score = PIECE_VALUES[ROOK]
    
    # Drive weak king to edge
    edge_dist = distance_from_edge(weak_king)
    score += (3 - edge_dist) * 25
    
    # Strong king should be close to weak king
    k_dist = king_distance(strong_king, weak_king)
    score += (7 - k_dist) * 15
    
    return score if strong_side_white else -score


def evaluate_kbnk(board: Board, strong_side_white: bool) -> int:
    """
    Evaluate KBN vs K endgame.
    Drive the weak king to the corner matching bishop color.
    This is a difficult but theoretically won endgame.
    """
    pieces = get_piece_positions(board)
    
    strong_king = None
    weak_king = None
    bishop_sq = None
    
    for sq, color in pieces[KING]:
        if (color == WHITE) == strong_side_white:
            strong_king = sq
        else:
            weak_king = sq
    
    for sq, color in pieces[BISHOP]:
        if (color == WHITE) == strong_side_white:
            bishop_sq = sq
    
    if weak_king is None or strong_king is None or bishop_sq is None:
        return 0
    
    score = PIECE_VALUES[BISHOP] + PIECE_VALUES[KNIGHT]
    
    # Determine bishop color (light or dark square)
    bishop_file = bishop_sq % 8
    bishop_rank = bishop_sq // 8
    is_light_bishop = (bishop_file + bishop_rank) % 2 == 1
    
    # Target corners: a1/h8 for light bishop, a8/h1 for dark bishop
    if is_light_bishop:
        corner_distances = [
            distance_from_corner(weak_king),  # General corner distance
        ]
    else:
        corner_distances = [
            distance_from_corner(weak_king),
        ]
    
    # Drive weak king to corner
    corner_dist = min(corner_distances)
    score += (7 - corner_dist) * 20
    
    # Strong king should be close
    k_dist = king_distance(strong_king, weak_king)
    score += (7 - k_dist) * 10
    
    return score if strong_side_white else -score


def evaluate_kpk(board: Board, strong_side_white: bool) -> int:
    """
    Evaluate KP vs K endgame.
    
    Uses the rule of the square and opposition concepts:
    - Pawn can promote if the defending king can't reach the queening square
    - Key squares (opposition) determine if pawn can promote with king support
    """
    pieces = get_piece_positions(board)
    
    strong_king = None
    weak_king = None
    pawn_sq = None
    
    for sq, color in pieces[KING]:
        if (color == WHITE) == strong_side_white:
            strong_king = sq
        else:
            weak_king = sq
    
    for sq, color in pieces[PAWN]:
        if (color == WHITE) == strong_side_white:
            pawn_sq = sq
    
    if pawn_sq is None or strong_king is None or weak_king is None:
        return 0
    
    pawn_file = pawn_sq % 8
    pawn_rank = pawn_sq // 8
    
    # Promotion square
    if strong_side_white:
        promo_sq = 56 + pawn_file  # 8th rank
        promo_rank = 7
        pawn_advance = promo_rank - pawn_rank
    else:
        promo_sq = pawn_file  # 1st rank
        promo_rank = 0
        pawn_advance = pawn_rank - promo_rank
    
    # Rule of the square: can defending king reach queening square?
    weak_king_file = weak_king % 8
    weak_king_rank = weak_king // 8
    
    if strong_side_white:
        # White pawn advancing up
        square_rank = pawn_rank
        square_left = max(0, pawn_file - pawn_advance)
        square_right = min(7, pawn_file + pawn_advance)
        in_square = (weak_king_rank >= square_rank and 
                    square_left <= weak_king_file <= square_right)
    else:
        # Black pawn advancing down
        square_rank = pawn_rank
        square_left = max(0, pawn_file - pawn_advance)
        square_right = min(7, pawn_file + pawn_advance)
        in_square = (weak_king_rank <= square_rank and 
                    square_left <= weak_king_file <= square_right)
    
    score = PIECE_VALUES[PAWN]
    
    # Bonus for pawn advancement
    if strong_side_white:
        score += pawn_rank * 30
    else:
        score += (7 - pawn_rank) * 30
    
    # If defending king not in square, it's likely winning
    if not in_square:
        score += 200
    
    # Strong king should support the pawn
    k_pawn_dist = king_distance(strong_king, pawn_sq)
    score += (7 - k_pawn_dist) * 10
    
    # Penalty for rook pawn (a or h file) - often drawn
    if pawn_file == 0 or pawn_file == 7:
        score -= 50
    
    return score if strong_side_white else -score


def evaluate_krkp(board: Board, rook_side_white: bool) -> int:
    """
    Evaluate KR vs KP endgame.
    Rook is usually winning unless pawn is far advanced.
    """
    pieces = get_piece_positions(board)
    
    rook_king = None
    pawn_king = None
    rook_sq = None
    pawn_sq = None
    
    for sq, color in pieces[KING]:
        if (color == WHITE) == rook_side_white:
            rook_king = sq
        else:
            pawn_king = sq
    
    for sq, color in pieces[ROOK]:
        if (color == WHITE) == rook_side_white:
            rook_sq = sq
    
    for sq, color in pieces[PAWN]:
        if (color == WHITE) != rook_side_white:
            pawn_sq = sq
    
    if pawn_sq is None or rook_sq is None:
        return 0
    
    score = PIECE_VALUES[ROOK] - PIECE_VALUES[PAWN]
    
    pawn_rank = pawn_sq // 8
    
    # Penalty if pawn is very advanced (7th rank)
    if (not rook_side_white and pawn_rank >= 6) or (rook_side_white and pawn_rank <= 1):
        # Pawn is dangerous
        score -= 150
    
    # Rook king should be close to pawn
    k_pawn_dist = king_distance(rook_king, pawn_sq)
    score += (7 - k_pawn_dist) * 10
    
    return score if rook_side_white else -score


def evaluate_endgame_knowledge(board: Board) -> tuple:
    """
    Check for known endgames and return specialized evaluation.
    
    Returns:
        Tuple of (is_known_endgame, score)
        Score is from White's perspective (not side to move)
    """
    endgame_type = detect_endgame_type(board)
    
    if endgame_type is None:
        return False, 0
    
    if endgame_type == "KK":
        return True, 0
    
    elif endgame_type == "KQK_WHITE":
        return True, evaluate_kqk(board, True)
    elif endgame_type == "KQK_BLACK":
        return True, evaluate_kqk(board, False)
    
    elif endgame_type == "KRK_WHITE":
        return True, evaluate_krk(board, True)
    elif endgame_type == "KRK_BLACK":
        return True, evaluate_krk(board, False)
    
    elif endgame_type == "KBNK_WHITE":
        return True, evaluate_kbnk(board, True)
    elif endgame_type == "KBNK_BLACK":
        return True, evaluate_kbnk(board, False)
    
    elif endgame_type == "KPK_WHITE":
        return True, evaluate_kpk(board, True)
    elif endgame_type == "KPK_BLACK":
        return True, evaluate_kpk(board, False)
    
    elif endgame_type == "KRKP_WHITE":
        return True, evaluate_krkp(board, True)
    elif endgame_type == "KRKP_BLACK":
        return True, evaluate_krkp(board, False)
    
    return False, 0


# ============================================================================
# MAIN EVALUATION FUNCTION
# ============================================================================

def evaluate(board: Board) -> int:
    """
    Evaluate the current position.
    
    Returns:
        Score in centipawns from the perspective of the side to move.
        Positive = good for side to move, negative = bad.
    """
    if board.has_insufficient_material():
        return 0
    
    # Check for known endgame patterns first
    is_known, endgame_score = evaluate_endgame_knowledge(board)
    if is_known:
        # Convert from White's perspective to side-to-move perspective
        if not board.white_to_move:
            endgame_score = -endgame_score
        return endgame_score
    
    endgame = is_endgame(board)
    
    # Get pawn positions once for reuse
    white_pawns, black_pawns = get_pawn_files(board)
    
    white_score = 0
    black_score = 0
    
    # Material and PST evaluation
    for sq in range(64):
        piece = board.squares[sq]
        if piece == EMPTY:
            continue
        
        piece_type = get_piece_type(piece)
        piece_color = get_piece_color(piece)
        
        material = PIECE_VALUES.get(piece_type, 0)
        is_white_piece = piece_color == WHITE
        position = get_pst_value(piece_type, sq, is_white_piece, endgame)
        
        if is_white_piece:
            white_score += material + position
        else:
            black_score += material + position
    
    # Base material and position score
    score = white_score - black_score
    
    # Pawn structure
    score += evaluate_pawn_structure(board, white_pawns, black_pawns)
    
    # King safety
    score += evaluate_king_safety(board, white_pawns, black_pawns, endgame)
    
    # Piece activity
    score += evaluate_pieces(board, white_pawns, black_pawns)
    
    # Mobility (skip in endgame for speed)
    if not endgame:
        score += evaluate_mobility(board)
    
    # Center control
    score += evaluate_center_control(board)
    
    # Convert to side-to-move perspective
    if not board.white_to_move:
        score = -score
    
    return score


# ============================================================================
# MOVE ORDERING EVALUATION
# ============================================================================

def evaluate_move(board: Board, move) -> int:
    """
    Estimate the value of a move for move ordering.
    
    This is used to order moves before searching, without actually
    making the move. Higher values = likely better moves.
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
