"""
OpusChess - Search Engine Module (Fully Optimized)

This module implements the chess search algorithm using:
- Minimax with alpha-beta pruning
- Transposition table with Zobrist hashing
- Null Move Pruning (NMP)
- Late Move Reductions (LMR)
- Aspiration Windows
- Static Exchange Evaluation (SEE)
- Futility Pruning
- Check Extensions
- Killer/History heuristics
- Principal Variation Search (PVS)
"""

from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
import random

from board import (
    Board, Move, EMPTY, get_piece_type, get_piece_color, WHITE, BLACK,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING
)
from move_generator import MoveGenerator
from evaluation import evaluate, evaluate_move, PIECE_VALUES

# Constants for search
INFINITY = 100000
MATE_SCORE = 50000
MAX_DEPTH = 100

# Transposition table entry types
TT_EXACT = 0    # Exact score
TT_ALPHA = 1    # Upper bound (failed low)
TT_BETA = 2     # Lower bound (failed high)

# Null Move Pruning
NULL_MOVE_REDUCTION = 2

# Late Move Reductions
LMR_FULL_DEPTH_MOVES = 4
LMR_REDUCTION_LIMIT = 3

# Aspiration Windows
ASPIRATION_WINDOW = 50  # Initial window size in centipawns

# Futility Pruning margins (by depth)
FUTILITY_MARGIN = [0, 200, 300, 500]  # depth 0, 1, 2, 3

# Check Extension
CHECK_EXTENSION = 1  # Extend search by 1 ply when in check

# Internal Iterative Deepening
IID_DEPTH_LIMIT = 4  # Minimum depth to apply IID
IID_REDUCTION = 2    # Depth reduction for IID search

# Contempt - penalty for accepting draws when winning
CONTEMPT = 25  # centipawns

# Razoring margins (by depth)
RAZORING_MARGIN = [0, 125, 250, 375]  # depth 0, 1, 2, 3

# Reverse Futility Pruning margins (by depth)
REVERSE_FUTILITY_MARGIN = [0, 100, 200, 300]  # depth 0, 1, 2, 3

# Late Move Pruning (LMP) - max quiet moves to search at each depth
LMP_MOVE_COUNTS = [0, 5, 8, 12, 16]  # depth 0, 1, 2, 3, 4

# Probcut
PROBCUT_DEPTH = 5    # Minimum depth to apply Probcut
PROBCUT_MARGIN = 200  # Margin for Probcut

# Singular Extensions
SINGULAR_DEPTH = 6    # Minimum depth for singular extensions
SINGULAR_MARGIN = 50  # Margin to consider a move singular

# SEE piece values (for fast lookup)
SEE_VALUES = {
    PAWN: 100,
    KNIGHT: 320,
    BISHOP: 330,
    ROOK: 500,
    QUEEN: 900,
    KING: 20000,
    EMPTY: 0
}


# ============================================================================
# ZOBRIST HASHING
# ============================================================================

class ZobristHash:
    """Zobrist hashing for chess positions."""
    
    def __init__(self, seed: int = 12345):
        random.seed(seed)
        
        self.piece_keys: List[List[int]] = []
        for piece in range(32):
            squares = [random.getrandbits(64) for _ in range(64)]
            self.piece_keys.append(squares)
        
        self.side_key: int = random.getrandbits(64)
        self.castling_keys: List[int] = [random.getrandbits(64) for _ in range(16)]
        self.ep_keys: List[int] = [random.getrandbits(64) for _ in range(9)]
    
    def hash_position(self, board: Board) -> int:
        h = 0
        for sq in range(64):
            piece = board.squares[sq]
            if piece != EMPTY:
                h ^= self.piece_keys[piece][sq]
        
        if not board.white_to_move:
            h ^= self.side_key
        
        h ^= self.castling_keys[board.castling_rights]
        
        if board.en_passant_square >= 0:
            h ^= self.ep_keys[board.en_passant_square % 8]
        else:
            h ^= self.ep_keys[8]
        
        return h
    
    def update_hash(self, current_hash: int, board: Board, move: Move, 
                    old_castling: int, old_ep: int, captured_piece: int) -> int:
        h = current_hash
        piece = board.squares[move.to_sq]
        original_piece = piece
        
        if move.promotion:
            original_piece = get_piece_color(piece) | PAWN
        
        h ^= self.piece_keys[original_piece][move.from_sq]
        h ^= self.piece_keys[piece][move.to_sq]
        
        if captured_piece != EMPTY:
            if move.is_en_passant:
                cap_sq = move.to_sq - 8 if get_piece_color(piece) == WHITE else move.to_sq + 8
                h ^= self.piece_keys[captured_piece][cap_sq]
            else:
                h ^= self.piece_keys[captured_piece][move.to_sq]
        
        if move.is_castling:
            from board import WHITE_ROOK, BLACK_ROOK
            rook_moves = {
                6: (7, 5, WHITE_ROOK), 2: (0, 3, WHITE_ROOK),
                62: (63, 61, BLACK_ROOK), 58: (56, 59, BLACK_ROOK)
            }
            if move.to_sq in rook_moves:
                from_r, to_r, rook = rook_moves[move.to_sq]
                h ^= self.piece_keys[rook][from_r]
                h ^= self.piece_keys[rook][to_r]
        
        h ^= self.castling_keys[old_castling]
        h ^= self.castling_keys[board.castling_rights]
        
        old_ep_idx = old_ep % 8 if old_ep >= 0 else 8
        new_ep_idx = board.en_passant_square % 8 if board.en_passant_square >= 0 else 8
        h ^= self.ep_keys[old_ep_idx]
        h ^= self.ep_keys[new_ep_idx]
        
        h ^= self.side_key
        return h


# ============================================================================
# TRANSPOSITION TABLE
# ============================================================================

@dataclass
class TTEntry:
    hash_key: int
    depth: int
    score: int
    flag: int
    best_move: Optional[Move]


class TranspositionTable:
    def __init__(self, size_mb: int = 64):
        num_entries = (size_mb * 1024 * 1024) // 50
        self.size = 1
        while self.size * 2 <= num_entries:
            self.size *= 2
        self.mask = self.size - 1
        self.table: Dict[int, TTEntry] = {}
        self.hits = 0
        self.writes = 0
    
    def probe(self, hash_key: int) -> Optional[TTEntry]:
        entry = self.table.get(hash_key & self.mask)
        if entry and entry.hash_key == hash_key:
            self.hits += 1
            return entry
        return None
    
    def store(self, hash_key: int, depth: int, score: int, flag: int, 
              best_move: Optional[Move]) -> None:
        index = hash_key & self.mask
        existing = self.table.get(index)
        if existing is None or depth >= existing.depth or hash_key == existing.hash_key:
            self.table[index] = TTEntry(hash_key, depth, score, flag, best_move)
            self.writes += 1
    
    def clear(self) -> None:
        self.table.clear()
        self.hits = 0
        self.writes = 0


# ============================================================================
# STATIC EXCHANGE EVALUATION (SEE)
# ============================================================================

class SEE:
    """
    Static Exchange Evaluation.
    
    Calculates the likely outcome of a series of captures on a single square,
    without actually making the moves. Used for move ordering and pruning.
    """
    
    # Directions for sliding pieces
    ROOK_DIRS = [8, -8, 1, -1]
    BISHOP_DIRS = [9, 7, -9, -7]
    
    @staticmethod
    def get_least_valuable_attacker(board: Board, sq: int, by_white: bool) -> Tuple[int, int]:
        """
        Find the least valuable attacker of a square.
        Returns (attacker_square, piece_value) or (-1, 0) if no attacker.
        """
        color = WHITE if by_white else BLACK
        
        # Check pawns first (least valuable)
        pawn_dir = -8 if by_white else 8
        pawn_attacks = []
        file = sq % 8
        for offset in [pawn_dir - 1, pawn_dir + 1]:
            att_sq = sq + offset
            if 0 <= att_sq < 64:
                att_file = att_sq % 8
                if abs(att_file - file) == 1:
                    piece = board.squares[att_sq]
                    if get_piece_type(piece) == PAWN and get_piece_color(piece) == color:
                        return (att_sq, SEE_VALUES[PAWN])
        
        # Check knights
        knight_offsets = [17, 15, 10, 6, -6, -10, -15, -17]
        for offset in knight_offsets:
            att_sq = sq + offset
            if 0 <= att_sq < 64:
                if abs((att_sq % 8) - file) <= 2:
                    piece = board.squares[att_sq]
                    if get_piece_type(piece) == KNIGHT and get_piece_color(piece) == color:
                        return (att_sq, SEE_VALUES[KNIGHT])
        
        # Check bishops and diagonal queens
        for d in SEE.BISHOP_DIRS:
            for dist in range(1, 8):
                att_sq = sq + d * dist
                if not (0 <= att_sq < 64):
                    break
                att_file = att_sq % 8
                orig_file = (sq + d * (dist - 1)) % 8 if dist > 1 else file
                if abs(att_file - orig_file) != 1:
                    break
                piece = board.squares[att_sq]
                if piece != EMPTY:
                    pt = get_piece_type(piece)
                    if get_piece_color(piece) == color and pt in (BISHOP, QUEEN):
                        return (att_sq, SEE_VALUES[pt])
                    break
        
        # Check rooks and orthogonal queens
        for d in SEE.ROOK_DIRS:
            for dist in range(1, 8):
                att_sq = sq + d * dist
                if not (0 <= att_sq < 64):
                    break
                if d in [1, -1]:  # Horizontal
                    if abs((att_sq % 8) - ((att_sq - d) % 8)) != 1:
                        break
                piece = board.squares[att_sq]
                if piece != EMPTY:
                    pt = get_piece_type(piece)
                    if get_piece_color(piece) == color and pt in (ROOK, QUEEN):
                        return (att_sq, SEE_VALUES[pt])
                    break
        
        # Check king
        for d in SEE.ROOK_DIRS + SEE.BISHOP_DIRS:
            att_sq = sq + d
            if 0 <= att_sq < 64:
                if abs((att_sq % 8) - file) <= 1:
                    piece = board.squares[att_sq]
                    if get_piece_type(piece) == KING and get_piece_color(piece) == color:
                        return (att_sq, SEE_VALUES[KING])
        
        return (-1, 0)
    
    @staticmethod
    def evaluate(board: Board, move: Move) -> int:
        """
        Evaluate a capture using SEE.
        
        Returns the expected material gain/loss from the capture sequence.
        Positive = good for the moving side.
        """
        from_sq = move.from_sq
        to_sq = move.to_sq
        
        attacker = board.squares[from_sq]
        victim = board.squares[to_sq]
        
        if victim == EMPTY and not move.is_en_passant:
            return 0  # Not a capture
        
        attacker_value = SEE_VALUES.get(get_piece_type(attacker), 0)
        victim_value = SEE_VALUES.get(get_piece_type(victim), 0) if victim != EMPTY else SEE_VALUES[PAWN]
        
        # Simple SEE approximation
        # Full SEE would simulate the entire capture sequence
        # For now, use MVV-LVA style evaluation
        gain = victim_value - attacker_value
        
        # If we win material even if we lose the attacker, it's good
        if gain >= 0:
            return gain
        
        # Check if the square is defended
        is_white = get_piece_color(attacker) == WHITE
        defender_sq, defender_value = SEE.get_least_valuable_attacker(board, to_sq, not is_white)
        
        if defender_sq < 0:
            return victim_value  # No defender, we win the piece
        
        # Defended - we might lose the attacker
        if defender_value < attacker_value:
            return victim_value - attacker_value  # We lose material
        
        return victim_value  # Trade is even or in our favor


# ============================================================================
# SEARCH ENGINE
# ============================================================================

class SearchEngine:
    """
    Chess search engine with full optimization suite:
    - Alpha-Beta + PVS
    - Transposition Table
    - Null Move Pruning
    - Late Move Reductions
    - Aspiration Windows
    - Futility Pruning
    - Check Extensions
    - SEE for move ordering
    - Killer/History heuristics
    """
    
    def __init__(self, tt_size_mb: int = 64):
        self.move_generator = MoveGenerator()
        self.nodes_searched = 0
        self.best_move: Optional[Move] = None
        self.max_depth = 4
        self.stop_search = False
        
        # Transposition table
        self.tt = TranspositionTable(tt_size_mb)
        self.zobrist = ZobristHash()
        
        # Killer moves (2 per ply)
        self.killer_moves: List[List[Optional[Move]]] = [[None, None] for _ in range(MAX_DEPTH)]
        
        # History heuristic
        self.history: List[List[int]] = [[0] * 64 for _ in range(32)]
        
        # Countermove table: (piece, to_square) -> best response move
        self.countermove: Dict[Tuple[int, int], Move] = {}
        self.last_move: Optional[Tuple[int, int]] = None  # (piece, to_sq) of last move
        
        # Configurable options (can be set via UCI)
        self.use_tt = True
        self.use_null_move = True
        self.use_lmr = True
        self.use_iid = True
        self.use_razoring = True
        self.use_reverse_futility = True
        self.use_lmp = True
        self.use_probcut = True
        self.use_singular_extensions = True
        self.use_countermove = True
        
        # Statistics
        self.tt_cutoffs = 0
        self.null_move_cutoffs = 0
        self.lmr_reductions = 0
        self.futility_prunes = 0
        self.check_extensions = 0
        self.iid_searches = 0
        self.razoring_prunes = 0
        self.reverse_futility_prunes = 0
        self.lmp_prunes = 0
        self.probcut_prunes = 0
        self.singular_extensions = 0
        
        # Timing and PV
        self.search_start_time = 0.0
        self.pv: List[Move] = []  # Principal variation
        self.info_callback = None  # Callback for reporting info per depth
    
    def search(self, board: Board, depth: int = 4, info_callback=None) -> Tuple[Optional[Move], int]:
        """
        Search with aspiration windows.
        
        Args:
            board: Current board position
            depth: Maximum search depth
            info_callback: Optional callback function(depth, score, nodes, time_ms, pv, hashfull)
                          Called after each iteration with search statistics
        """
        import time
        
        self.nodes_searched = 0
        self.best_move = None
        self.max_depth = depth
        self.stop_search = False
        self.tt_cutoffs = 0
        self.null_move_cutoffs = 0
        self.lmr_reductions = 0
        self.futility_prunes = 0
        self.check_extensions = 0
        self.iid_searches = 0
        self.pv = []
        self.info_callback = info_callback
        self.search_start_time = time.time()
        
        self.killer_moves = [[None, None] for _ in range(MAX_DEPTH)]
        
        position_hash = self.zobrist.hash_position(board)
        
        best_move = None
        best_score = -INFINITY
        
        # Initial search at depth 1 to get a starting score
        score = self._alphabeta(board, 1, -INFINITY, INFINITY, 0, True, position_hash, True)
        if self.best_move:
            best_move = self.best_move
            best_score = score
            self._extract_pv(board, position_hash, 1)
            self._report_info(1, score, board)
        
        # Iterative deepening with aspiration windows
        for current_depth in range(2, depth + 1):
            if self.stop_search:
                break
            
            # Set up aspiration window around previous score
            alpha = best_score - ASPIRATION_WINDOW
            beta = best_score + ASPIRATION_WINDOW
            
            while True:
                score = self._alphabeta(board, current_depth, alpha, beta, 
                                       0, True, position_hash, True)
                
                if self.stop_search:
                    break
                
                # Check if we failed low or high
                if score <= alpha:
                    # Failed low - widen window downward
                    alpha = -INFINITY
                elif score >= beta:
                    # Failed high - widen window upward
                    beta = INFINITY
                else:
                    # Score is within window
                    break
            
            if not self.stop_search and self.best_move is not None:
                best_move = self.best_move
                best_score = score
                self._extract_pv(board, position_hash, current_depth)
                self._report_info(current_depth, score, board)
        
        return best_move, best_score
    
    def _extract_pv(self, board: Board, position_hash: int, depth: int) -> None:
        """
        Extract the principal variation from the transposition table.
        """
        self.pv = []
        
        if not self.use_tt:
            if self.best_move:
                self.pv.append(self.best_move)
            return
        
        seen_hashes = set()
        current_hash = position_hash
        undos = []  # Store undo info to restore board
        
        for _ in range(min(depth, 20)):  # Limit PV length
            if current_hash in seen_hashes:
                break
            seen_hashes.add(current_hash)
            
            entry = self.tt.probe(current_hash)
            if entry is None or entry.best_move is None:
                break
            
            move = entry.best_move
            self.pv.append(move)
            
            # Make the move and store undo info
            old_castling = board.castling_rights
            old_ep = board.en_passant_square
            undo = board.make_move(move)
            
            # Update hash for next position
            current_hash = self.zobrist.update_hash(
                current_hash, board, move, old_castling, old_ep, undo.captured_piece
            )
            undos.append((move, undo))
        
        # Restore board state by unmaking all moves in reverse order
        for move, undo in reversed(undos):
            board.unmake_move(move, undo)
    
    def _report_info(self, depth: int, score: int, board: Board) -> None:
        """
        Report search information via callback.
        """
        import time
        
        if self.info_callback is None:
            return
        
        elapsed = time.time() - self.search_start_time
        time_ms = int(elapsed * 1000)
        
        # Calculate hash usage (permille)
        if self.tt.size > 0:
            hashfull = int((self.tt.writes / self.tt.size) * 1000)
            hashfull = min(hashfull, 1000)
        else:
            hashfull = 0
        
        # Get PV string
        pv_str = " ".join(move.to_uci() for move in self.pv) if self.pv else ""
        if not pv_str and self.best_move:
            pv_str = self.best_move.to_uci()
        
        # Calculate NPS
        nps = int(self.nodes_searched / elapsed) if elapsed > 0 else 0
        
        self.info_callback(
            depth=depth,
            score=score,
            nodes=self.nodes_searched,
            time_ms=time_ms,
            pv=pv_str,
            hashfull=hashfull,
            nps=nps
        )
    
    def _alphabeta(self, board: Board, depth: int, alpha: int, beta: int,
                   ply: int, is_root: bool, position_hash: int, 
                   allow_null: bool) -> int:
        """Alpha-beta with all optimizations."""
        if self.stop_search:
            return 0
        
        self.nodes_searched += 1
        original_alpha = alpha
        
        # Draw detection with contempt
        if not is_root:
            if board.is_fifty_moves() or board.is_repetition():
                # Apply contempt: in winning position, avoid draw
                return -CONTEMPT
            if board.has_insufficient_material():
                return -CONTEMPT
            # Penalty for approaching repetition (2nd occurrence)
            rep_count = board.repetition_count()
            if rep_count >= 2:
                # Position repeated - strong penalty to avoid 3rd repetition
                return -CONTEMPT * 2
        
        # Probe TT
        tt_move = None
        tt_entry = None
        
        if self.use_tt:
            tt_entry = self.tt.probe(position_hash)
            
            if tt_entry is not None and not is_root:
                if tt_entry.depth >= depth:
                    if tt_entry.flag == TT_EXACT:
                        self.tt_cutoffs += 1
                        return tt_entry.score
                    elif tt_entry.flag == TT_ALPHA and tt_entry.score <= alpha:
                        self.tt_cutoffs += 1
                        return alpha
                    elif tt_entry.flag == TT_BETA and tt_entry.score >= beta:
                        self.tt_cutoffs += 1
                        return beta
                tt_move = tt_entry.best_move
        
        # Check detection
        in_check = self.move_generator.is_in_check(board)
        
        # Check extension
        extended_depth = depth
        if in_check:
            extended_depth += CHECK_EXTENSION
            self.check_extensions += 1
        
        # Generate moves
        moves = self.move_generator.generate_legal_moves(board)
        
        # Checkmate / Stalemate
        if len(moves) == 0:
            if in_check:
                return -MATE_SCORE + ply
            return 0
        
        # Quiescence at leaf
        if extended_depth <= 0:
            return self._quiescence(board, alpha, beta)
        
        # Static evaluation for pruning decisions
        static_eval = None
        
        # ================================================================
        # INTERNAL ITERATIVE DEEPENING (IID)
        # ================================================================
        # If we don't have a TT move and depth is high enough, do a
        # reduced depth search to find a good move to search first
        if (self.use_iid and 
            tt_move is None and 
            extended_depth >= IID_DEPTH_LIMIT and 
            not in_check):
            
            self.iid_searches += 1
            # Search at reduced depth
            self._alphabeta(board, extended_depth - IID_REDUCTION, alpha, beta,
                           ply, False, position_hash, False)
            
            # Try to get the best move from TT now
            if self.use_tt:
                tt_entry = self.tt.probe(position_hash)
                if tt_entry is not None:
                    tt_move = tt_entry.best_move
        
        # Null Move Pruning
        if (self.use_null_move and allow_null and not is_root and not in_check and 
            extended_depth >= 3 and self._has_big_pieces(board)):
            
            board.white_to_move = not board.white_to_move
            null_hash = position_hash ^ self.zobrist.side_key
            
            null_score = -self._alphabeta(
                board, extended_depth - 1 - NULL_MOVE_REDUCTION, 
                -beta, -beta + 1, ply + 1, False, null_hash, False
            )
            
            board.white_to_move = not board.white_to_move
            
            if null_score >= beta:
                self.null_move_cutoffs += 1
                return beta
        
        # Get static evaluation for pruning decisions
        static_eval = None
        if extended_depth <= 4 and not in_check and abs(alpha) < MATE_SCORE - 100:
            static_eval = evaluate(board)
        
        # ================================================================
        # RAZORING
        # ================================================================
        # If static eval is very low, drop into quiescence
        if (self.use_razoring and 
            static_eval is not None and
            extended_depth <= 3 and
            not is_root and
            not in_check):
            
            razor_margin = RAZORING_MARGIN[extended_depth]
            if static_eval + razor_margin < alpha:
                razor_score = self._quiescence(board, alpha, beta)
                if razor_score < alpha:
                    self.razoring_prunes += 1
                    return razor_score
        
        # ================================================================
        # REVERSE FUTILITY PRUNING (Static Null Move Pruning)
        # ================================================================
        # If static eval is very high, return beta
        if (self.use_reverse_futility and
            static_eval is not None and
            extended_depth <= 3 and
            not is_root and
            not in_check):
            
            reverse_margin = REVERSE_FUTILITY_MARGIN[extended_depth]
            if static_eval - reverse_margin >= beta:
                self.reverse_futility_prunes += 1
                return beta
        
        # ================================================================
        # PROBCUT
        # ================================================================
        # If a shallow search finds a very high score, likely full search will too
        if (self.use_probcut and
            extended_depth >= PROBCUT_DEPTH and
            not is_root and
            not in_check and
            abs(beta) < MATE_SCORE - 100):
            
            probcut_beta = beta + PROBCUT_MARGIN
            probcut_depth = extended_depth - 4
            
            # Do a reduced depth search
            probcut_score = self._alphabeta(
                board, probcut_depth, probcut_beta - 1, probcut_beta,
                ply, False, position_hash, False
            )
            
            if probcut_score >= probcut_beta:
                self.probcut_prunes += 1
                return beta
        
        # Order moves
        moves = self._order_moves(board, moves, tt_move, ply)
        
        best_score = -INFINITY
        best_move_at_node = None
        moves_searched = 0
        quiet_moves_searched = 0
        
        for move in moves:
            if self.stop_search:
                break
            
            is_capture = board.squares[move.to_sq] != EMPTY or move.is_en_passant
            is_quiet = not is_capture and not move.promotion
            
            # ================================================================
            # LATE MOVE PRUNING (LMP)
            # ================================================================
            # Skip late quiet moves at low depths
            if (self.use_lmp and
                is_quiet and
                extended_depth <= 4 and
                not in_check and
                not is_root and
                moves_searched > 0):
                
                lmp_limit = LMP_MOVE_COUNTS[min(extended_depth, 4)]
                if quiet_moves_searched >= lmp_limit:
                    self.lmp_prunes += 1
                    moves_searched += 1
                    quiet_moves_searched += 1
                    continue
            
            # ================================================================
            # FUTILITY PRUNING
            # ================================================================
            # Skip quiet moves that have no chance of raising alpha
            if (static_eval is not None and 
                moves_searched > 0 and
                extended_depth <= 3 and
                not in_check and
                is_quiet):
                
                futility_value = static_eval + FUTILITY_MARGIN[extended_depth]
                if futility_value <= alpha:
                    self.futility_prunes += 1
                    moves_searched += 1
                    quiet_moves_searched += 1
                    continue
            
            if is_quiet:
                quiet_moves_searched += 1
            
            # Save state
            old_castling = board.castling_rights
            old_ep = board.en_passant_square
            
            # Make move
            undo = board.make_move(move)
            
            # Track last move for countermove heuristic
            old_last_move = self.last_move
            moved_piece = undo.moved_piece
            self.last_move = (moved_piece, move.to_sq)
            
            # Check if this move gives check (for LMR decision)
            gives_check = self.move_generator.is_in_check(board)
            
            # Update hash
            new_hash = self.zobrist.update_hash(
                position_hash, board, move, old_castling, old_ep, undo.captured_piece
            )
            
            # ================================================================
            # LATE MOVE REDUCTIONS
            # ================================================================
            do_full_search = True
            
            if (self.use_lmr and
                moves_searched >= LMR_FULL_DEPTH_MOVES and 
                extended_depth >= LMR_REDUCTION_LIMIT and
                not in_check and
                not gives_check and
                not move.promotion and
                undo.captured_piece == EMPTY and
                not self._is_killer(move, ply)):
                
                reduction = 1 + (moves_searched >= 6)
                
                score = -self._alphabeta(
                    board, extended_depth - 1 - reduction, -alpha - 1, -alpha,
                    ply + 1, False, new_hash, True
                )
                
                self.lmr_reductions += 1
                do_full_search = score > alpha
            
            # Full search
            if do_full_search:
                if moves_searched == 0:
                    score = -self._alphabeta(
                        board, extended_depth - 1, -beta, -alpha,
                        ply + 1, False, new_hash, True
                    )
                else:
                    # PVS
                    score = -self._alphabeta(
                        board, extended_depth - 1, -alpha - 1, -alpha,
                        ply + 1, False, new_hash, True
                    )
                    
                    if score > alpha and score < beta:
                        score = -self._alphabeta(
                            board, extended_depth - 1, -beta, -alpha,
                            ply + 1, False, new_hash, True
                        )
            
            board.unmake_move(move, undo)
            self.last_move = old_last_move  # Restore for countermove heuristic
            moves_searched += 1
            
            if score > best_score:
                best_score = score
                best_move_at_node = move
                if is_root:
                    self.best_move = move
            
            if score > alpha:
                alpha = score
                if undo.captured_piece == EMPTY and not move.promotion:
                    piece = board.squares[move.from_sq]
                    self.history[piece][move.to_sq] += extended_depth * extended_depth
            
            if alpha >= beta:
                if undo.captured_piece == EMPTY and not move.promotion:
                    self._update_killers(move, ply)
                    # Countermove heuristic - remember this as a good response
                    if self.use_countermove and self.last_move is not None:
                        self.countermove[self.last_move] = move
                break
        
        # Store in TT
        if not self.stop_search and self.use_tt:
            if best_score <= original_alpha:
                flag = TT_ALPHA
            elif best_score >= beta:
                flag = TT_BETA
            else:
                flag = TT_EXACT
            self.tt.store(position_hash, depth, best_score, flag, best_move_at_node)
        
        return best_score
    
    def _quiescence(self, board: Board, alpha: int, beta: int, depth: int = 0) -> int:
        """Quiescence search with SEE."""
        if self.stop_search:
            return 0
        
        self.nodes_searched += 1
        stand_pat = evaluate(board)
        
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat
        if depth >= 4:
            return stand_pat
        
        moves = self.move_generator.generate_legal_moves(board)
        captures = [m for m in moves 
                   if board.squares[m.to_sq] != EMPTY or m.is_en_passant or m.promotion]
        
        # Order by SEE
        scored = []
        for m in captures:
            see_score = SEE.evaluate(board, m)
            scored.append((see_score, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        
        for see_score, move in scored:
            if self.stop_search:
                break
            
            # Skip losing captures
            if see_score < 0 and depth >= 2:
                continue
            
            undo = board.make_move(move)
            score = -self._quiescence(board, -beta, -alpha, depth + 1)
            board.unmake_move(move, undo)
            
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        
        return alpha
    
    def _order_moves(self, board: Board, moves: List[Move], 
                     tt_move: Optional[Move], ply: int) -> List[Move]:
        """Order moves with SEE for captures."""
        scored = []
        
        for move in moves:
            if tt_move and move == tt_move:
                score = 3000000
            elif board.squares[move.to_sq] != EMPTY or move.is_en_passant:
                # Capture - use SEE
                see = SEE.evaluate(board, move)
                score = 2000000 + see
            elif move.promotion:
                score = 1900000 + PIECE_VALUES.get(move.promotion, 0)
            elif self._is_killer(move, ply):
                score = 1000000
            elif self.use_countermove and self.last_move is not None:
                # Countermove bonus
                cm = self.countermove.get(self.last_move)
                if cm and move == cm:
                    score = 900000
                else:
                    piece = board.squares[move.from_sq]
                    score = self.history[piece][move.to_sq]
            else:
                piece = board.squares[move.from_sq]
                score = self.history[piece][move.to_sq]
            
            scored.append((score, move))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]
    
    def _is_killer(self, move: Move, ply: int) -> bool:
        if ply >= MAX_DEPTH:
            return False
        k = self.killer_moves[ply]
        return (k[0] and move == k[0]) or (k[1] and move == k[1])
    
    def _update_killers(self, move: Move, ply: int) -> None:
        if ply >= MAX_DEPTH:
            return
        k = self.killer_moves[ply]
        if k[0] and move == k[0]:
            return
        k[1] = k[0]
        k[0] = move
    
    def _has_big_pieces(self, board: Board) -> bool:
        color = WHITE if board.white_to_move else BLACK
        for sq in range(64):
            piece = board.squares[sq]
            if piece != EMPTY and get_piece_color(piece) == color:
                pt = get_piece_type(piece)
                if pt in (KNIGHT, BISHOP, ROOK, QUEEN):
                    return True
        return False
    
    def stop(self):
        self.stop_search = True
    
    def clear_tt(self):
        self.tt.clear()
    
    def get_info(self) -> dict:
        import time
        elapsed = time.time() - self.search_start_time if self.search_start_time > 0 else 0
        nps = int(self.nodes_searched / elapsed) if elapsed > 0 else 0
        hashfull = int((self.tt.writes / self.tt.size) * 1000) if self.tt.size > 0 else 0
        
        return {
            'nodes': self.nodes_searched,
            'depth': self.max_depth,
            'time_ms': int(elapsed * 1000),
            'nps': nps,
            'hashfull': min(hashfull, 1000),
            'tt_hits': self.tt.hits,
            'tt_cutoffs': self.tt_cutoffs,
            'null_cutoffs': self.null_move_cutoffs,
            'lmr_reductions': self.lmr_reductions,
            'futility_prunes': self.futility_prunes,
            'check_extensions': self.check_extensions,
            'iid_searches': self.iid_searches,
            'pv': " ".join(m.to_uci() for m in self.pv) if self.pv else "",
        }
