"""
OpusChess - Search Engine Module (Optimized)

This module implements the chess search algorithm using:
- Minimax with alpha-beta pruning
- Transposition table with Zobrist hashing
- Null Move Pruning (NMP)
- Late Move Reductions (LMR)
- Killer move heuristic
"""

from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
import random

from board import Board, Move, EMPTY, get_piece_type, get_piece_color, WHITE, PAWN
from move_generator import MoveGenerator
from evaluation import evaluate, evaluate_move, PIECE_VALUES, KING

# Constants for search
INFINITY = 100000
MATE_SCORE = 50000
MAX_DEPTH = 100

# Transposition table entry types
TT_EXACT = 0    # Exact score
TT_ALPHA = 1    # Upper bound (failed low)
TT_BETA = 2     # Lower bound (failed high)

# Null Move Pruning constants
NULL_MOVE_REDUCTION = 2  # Depth reduction for null move search

# Late Move Reductions constants
LMR_FULL_DEPTH_MOVES = 4   # Search this many moves at full depth
LMR_REDUCTION_LIMIT = 3    # Minimum depth to apply LMR


# ============================================================================
# ZOBRIST HASHING
# ============================================================================

class ZobristHash:
    """
    Zobrist hashing for chess positions.
    
    Uses random 64-bit numbers XORed together to create a unique hash
    for each position. This allows efficient hashing of positions for
    the transposition table.
    """
    
    def __init__(self, seed: int = 12345):
        """Initialize Zobrist hash tables with random numbers."""
        random.seed(seed)
        
        # Random numbers for each piece on each square
        self.piece_keys: List[List[int]] = []
        for piece in range(32):
            squares = []
            for sq in range(64):
                squares.append(random.getrandbits(64))
            self.piece_keys.append(squares)
        
        # Random number for side to move
        self.side_key: int = random.getrandbits(64)
        
        # Random numbers for castling rights
        self.castling_keys: List[int] = [random.getrandbits(64) for _ in range(16)]
        
        # Random numbers for en passant file
        self.ep_keys: List[int] = [random.getrandbits(64) for _ in range(9)]
    
    def hash_position(self, board: Board) -> int:
        """Compute the Zobrist hash for a board position."""
        h = 0
        
        for sq in range(64):
            piece = board.squares[sq]
            if piece != EMPTY:
                h ^= self.piece_keys[piece][sq]
        
        if not board.white_to_move:
            h ^= self.side_key
        
        h ^= self.castling_keys[board.castling_rights]
        
        if board.en_passant_square >= 0:
            ep_file = board.en_passant_square % 8
            h ^= self.ep_keys[ep_file]
        else:
            h ^= self.ep_keys[8]
        
        return h
    
    def update_hash(self, current_hash: int, board: Board, move: Move, 
                    old_castling: int, old_ep: int, captured_piece: int) -> int:
        """Incrementally update the hash after a move."""
        h = current_hash
        
        piece = board.squares[move.to_sq]
        original_piece = piece
        
        if move.promotion:
            original_piece = (get_piece_color(piece)) | PAWN
        
        h ^= self.piece_keys[original_piece][move.from_sq]
        h ^= self.piece_keys[piece][move.to_sq]
        
        if captured_piece != EMPTY:
            if move.is_en_passant:
                if get_piece_color(piece) == WHITE:
                    cap_sq = move.to_sq - 8
                else:
                    cap_sq = move.to_sq + 8
                h ^= self.piece_keys[captured_piece][cap_sq]
            else:
                h ^= self.piece_keys[captured_piece][move.to_sq]
        
        if move.is_castling:
            from board import WHITE_ROOK, BLACK_ROOK
            if move.to_sq == 6:
                h ^= self.piece_keys[WHITE_ROOK][7]
                h ^= self.piece_keys[WHITE_ROOK][5]
            elif move.to_sq == 2:
                h ^= self.piece_keys[WHITE_ROOK][0]
                h ^= self.piece_keys[WHITE_ROOK][3]
            elif move.to_sq == 62:
                h ^= self.piece_keys[BLACK_ROOK][63]
                h ^= self.piece_keys[BLACK_ROOK][61]
            elif move.to_sq == 58:
                h ^= self.piece_keys[BLACK_ROOK][56]
                h ^= self.piece_keys[BLACK_ROOK][59]
        
        h ^= self.castling_keys[old_castling]
        h ^= self.castling_keys[board.castling_rights]
        
        if old_ep >= 0:
            h ^= self.ep_keys[old_ep % 8]
        else:
            h ^= self.ep_keys[8]
        
        if board.en_passant_square >= 0:
            h ^= self.ep_keys[board.en_passant_square % 8]
        else:
            h ^= self.ep_keys[8]
        
        h ^= self.side_key
        
        return h


# ============================================================================
# TRANSPOSITION TABLE
# ============================================================================

@dataclass
class TTEntry:
    """Entry in the transposition table."""
    hash_key: int
    depth: int
    score: int
    flag: int
    best_move: Optional[Move]


class TranspositionTable:
    """Hash table for storing previously evaluated positions."""
    
    def __init__(self, size_mb: int = 64):
        entry_size = 50
        num_entries = (size_mb * 1024 * 1024) // entry_size
        
        self.size = 1
        while self.size * 2 <= num_entries:
            self.size *= 2
        
        self.mask = self.size - 1
        self.table: Dict[int, TTEntry] = {}
        
        self.hits = 0
        self.writes = 0
    
    def probe(self, hash_key: int) -> Optional[TTEntry]:
        index = hash_key & self.mask
        entry = self.table.get(index)
        
        if entry is not None and entry.hash_key == hash_key:
            self.hits += 1
            return entry
        
        return None
    
    def store(self, hash_key: int, depth: int, score: int, flag: int, 
              best_move: Optional[Move]) -> None:
        index = hash_key & self.mask
        existing = self.table.get(index)
        
        if (existing is None or 
            depth >= existing.depth or 
            hash_key == existing.hash_key):
            
            self.table[index] = TTEntry(
                hash_key=hash_key,
                depth=depth,
                score=score,
                flag=flag,
                best_move=best_move
            )
            self.writes += 1
    
    def clear(self) -> None:
        self.table.clear()
        self.hits = 0
        self.writes = 0


# ============================================================================
# SEARCH ENGINE
# ============================================================================

class SearchEngine:
    """
    Chess search engine with:
    - Minimax + Alpha-Beta pruning
    - Transposition Table
    - Null Move Pruning
    - Late Move Reductions
    - Killer Move Heuristic
    """
    
    def __init__(self, tt_size_mb: int = 64):
        """Initialize the search engine."""
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
        
        # History heuristic (piece-to-square scores)
        self.history: List[List[int]] = [[0] * 64 for _ in range(32)]
        
        # Statistics
        self.tt_cutoffs = 0
        self.null_move_cutoffs = 0
        self.lmr_reductions = 0
    
    def search(self, board: Board, depth: int = 4) -> Tuple[Optional[Move], int]:
        """Search for the best move in the position."""
        self.nodes_searched = 0
        self.best_move = None
        self.max_depth = depth
        self.stop_search = False
        self.tt_cutoffs = 0
        self.null_move_cutoffs = 0
        self.lmr_reductions = 0
        
        # Clear killer moves for new search
        self.killer_moves = [[None, None] for _ in range(MAX_DEPTH)]
        
        # Compute initial hash
        position_hash = self.zobrist.hash_position(board)
        
        # Iterative deepening
        best_move = None
        best_score = -INFINITY
        
        for current_depth in range(1, depth + 1):
            if self.stop_search:
                break
            
            score = self._alphabeta(board, current_depth, -INFINITY, INFINITY, 
                                   0, True, position_hash, True)
            
            if not self.stop_search and self.best_move is not None:
                best_move = self.best_move
                best_score = score
        
        return best_move, best_score
    
    def _alphabeta(self, board: Board, depth: int, alpha: int, beta: int,
                   ply: int, is_root: bool, position_hash: int, 
                   allow_null: bool) -> int:
        """
        Alpha-beta search with NMP and LMR.
        
        Args:
            board: Current board state
            depth: Remaining depth to search
            alpha, beta: Search window
            ply: Current ply from root
            is_root: True if this is the root node
            position_hash: Zobrist hash of current position
            allow_null: True if null move pruning is allowed
        """
        if self.stop_search:
            return 0
        
        self.nodes_searched += 1
        original_alpha = alpha
        
        # Check for draws
        if not is_root:
            if board.is_fifty_moves() or board.is_repetition():
                return 0
            if board.has_insufficient_material():
                return 0
        
        # Probe transposition table
        tt_move = None
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
        
        # Check if in check (needed for NMP and extensions)
        in_check = self.move_generator.is_in_check(board)
        
        # Generate legal moves
        moves = self.move_generator.generate_legal_moves(board)
        
        # Check for checkmate or stalemate
        if len(moves) == 0:
            if in_check:
                return -MATE_SCORE + ply
            else:
                return 0
        
        # Leaf node - quiescence search
        if depth <= 0:
            return self._quiescence(board, alpha, beta)
        
        # ================================================================
        # NULL MOVE PRUNING
        # ================================================================
        # Skip if:
        # - In check (illegal to pass when in check)
        # - At root
        # - Previous move was null (avoid double null)
        # - Low material (zugzwang risk)
        # ================================================================
        if (allow_null and 
            not is_root and 
            not in_check and 
            depth >= 3 and
            self._has_big_pieces(board)):
            
            # Make null move (just switch side)
            board.white_to_move = not board.white_to_move
            null_hash = position_hash ^ self.zobrist.side_key
            
            # Search with reduced depth
            null_score = -self._alphabeta(
                board, depth - 1 - NULL_MOVE_REDUCTION, 
                -beta, -beta + 1,
                ply + 1, False, null_hash, False  # Don't allow consecutive null moves
            )
            
            # Unmake null move
            board.white_to_move = not board.white_to_move
            
            if null_score >= beta:
                self.null_move_cutoffs += 1
                return beta
        
        # Order moves
        moves = self._order_moves(board, moves, tt_move, ply)
        
        best_score = -INFINITY
        best_move_at_node = None
        moves_searched = 0
        
        for move in moves:
            if self.stop_search:
                break
            
            # Save state for hash update
            old_castling = board.castling_rights
            old_ep = board.en_passant_square
            
            # Make the move
            undo = board.make_move(move)
            
            # Update hash incrementally
            new_hash = self.zobrist.update_hash(
                position_hash, board, move, 
                old_castling, old_ep, undo.captured_piece
            )
            
            # ================================================================
            # LATE MOVE REDUCTIONS (LMR)
            # ================================================================
            # For moves searched after the first few, search with reduced depth
            # Conditions for reduction:
            # - Not the first few moves
            # - Sufficient depth
            # - Not in check
            # - Not a capture or promotion
            # - Not a killer move
            # ================================================================
            do_full_search = True
            
            if (moves_searched >= LMR_FULL_DEPTH_MOVES and 
                depth >= LMR_REDUCTION_LIMIT and
                not in_check and
                not move.promotion and
                undo.captured_piece == EMPTY and
                not self._is_killer(move, ply)):
                
                # Calculate reduction (more reduction for later moves)
                reduction = 1
                if moves_searched >= 6:
                    reduction = 2
                
                # Reduced depth search
                score = -self._alphabeta(
                    board, depth - 1 - reduction, -alpha - 1, -alpha,
                    ply + 1, False, new_hash, True
                )
                
                self.lmr_reductions += 1
                
                # If reduced search beats alpha, need to re-search at full depth
                do_full_search = score > alpha
            
            # Full depth search (or re-search after LMR)
            if do_full_search:
                if moves_searched == 0:
                    # First move - full window search
                    score = -self._alphabeta(
                        board, depth - 1, -beta, -alpha,
                        ply + 1, False, new_hash, True
                    )
                else:
                    # PVS: null window search first
                    score = -self._alphabeta(
                        board, depth - 1, -alpha - 1, -alpha,
                        ply + 1, False, new_hash, True
                    )
                    
                    # If it beats alpha, re-search with full window
                    if score > alpha and score < beta:
                        score = -self._alphabeta(
                            board, depth - 1, -beta, -alpha,
                            ply + 1, False, new_hash, True
                        )
            
            # Unmake the move
            board.unmake_move(move, undo)
            
            moves_searched += 1
            
            if score > best_score:
                best_score = score
                best_move_at_node = move
                
                if is_root:
                    self.best_move = move
            
            if score > alpha:
                alpha = score
                
                # Update history heuristic for quiet moves that improve alpha
                if undo.captured_piece == EMPTY and not move.promotion:
                    piece = board.squares[move.from_sq]
                    self.history[piece][move.to_sq] += depth * depth
            
            # Beta cutoff
            if alpha >= beta:
                # Update killer moves for quiet moves that cause cutoff
                if undo.captured_piece == EMPTY and not move.promotion:
                    self._update_killers(move, ply)
                break
        
        # Store in transposition table
        if not self.stop_search:
            if best_score <= original_alpha:
                flag = TT_ALPHA
            elif best_score >= beta:
                flag = TT_BETA
            else:
                flag = TT_EXACT
            
            self.tt.store(position_hash, depth, best_score, flag, best_move_at_node)
        
        return best_score
    
    def _quiescence(self, board: Board, alpha: int, beta: int, depth: int = 0) -> int:
        """Quiescence search - only captures."""
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
        captures = [m for m in moves if board.squares[m.to_sq] != 0 or m.is_en_passant or m.promotion]
        
        captures = self._order_moves(board, captures, None, 0)
        
        for move in captures:
            if self.stop_search:
                break
            
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
        """Order moves for better pruning."""
        scored_moves = []
        
        for move in moves:
            # TT move gets highest priority
            if tt_move is not None and move == tt_move:
                score = 2000000
            # Captures by MVV-LVA
            elif board.squares[move.to_sq] != EMPTY:
                score = 1000000 + evaluate_move(board, move)
            # Killer moves
            elif self._is_killer(move, ply):
                score = 900000
            # History heuristic
            else:
                piece = board.squares[move.from_sq]
                score = self.history[piece][move.to_sq]
            
            scored_moves.append((score, move))
        
        scored_moves.sort(key=lambda x: x[0], reverse=True)
        
        return [move for _, move in scored_moves]
    
    def _is_killer(self, move: Move, ply: int) -> bool:
        """Check if move is a killer move at this ply."""
        if ply >= MAX_DEPTH:
            return False
        killers = self.killer_moves[ply]
        return (killers[0] is not None and move == killers[0]) or \
               (killers[1] is not None and move == killers[1])
    
    def _update_killers(self, move: Move, ply: int) -> None:
        """Update killer moves for this ply."""
        if ply >= MAX_DEPTH:
            return
        killers = self.killer_moves[ply]
        # Don't add duplicate
        if killers[0] is not None and move == killers[0]:
            return
        # Shift and add new killer
        killers[1] = killers[0]
        killers[0] = move
    
    def _has_big_pieces(self, board: Board) -> bool:
        """Check if side to move has pieces other than pawns and king."""
        from board import KNIGHT, BISHOP, ROOK, QUEEN
        color = WHITE if board.white_to_move else 16  # BLACK
        
        for sq in range(64):
            piece = board.squares[sq]
            if piece == EMPTY:
                continue
            if get_piece_color(piece) != color:
                continue
            pt = get_piece_type(piece)
            if pt in (KNIGHT, BISHOP, ROOK, QUEEN):
                return True
        return False
    
    def stop(self):
        """Signal the search to stop."""
        self.stop_search = True
    
    def clear_tt(self):
        """Clear the transposition table."""
        self.tt.clear()
    
    def get_info(self) -> dict:
        """Get information about the last search."""
        return {
            'nodes': self.nodes_searched,
            'depth': self.max_depth,
            'tt_hits': self.tt.hits,
            'tt_cutoffs': self.tt_cutoffs,
            'null_cutoffs': self.null_move_cutoffs,
            'lmr_reductions': self.lmr_reductions,
        }
