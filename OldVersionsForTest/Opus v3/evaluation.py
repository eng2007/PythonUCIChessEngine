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
