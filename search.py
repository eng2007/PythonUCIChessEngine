"""
OpusChess - Search Engine Module (with Transposition Table)

This module implements the chess search algorithm using minimax
with alpha-beta pruning and transposition table for caching positions.
"""

from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
import random

from board import Board, Move, EMPTY, get_piece_type, get_piece_color, WHITE
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
        # Indexed as: piece_keys[piece_value][square]
        # piece_value ranges from 0-31 (enough for all piece types and colors)
        self.piece_keys: List[List[int]] = []
        for piece in range(32):
            squares = []
            for sq in range(64):
                squares.append(random.getrandbits(64))
            self.piece_keys.append(squares)
        
        # Random number for side to move (XOR when black to move)
        self.side_key: int = random.getrandbits(64)
        
        # Random numbers for castling rights (4 bits = 16 combinations)
        self.castling_keys: List[int] = [random.getrandbits(64) for _ in range(16)]
        
        # Random numbers for en passant file (0-7, plus one for no EP)
        self.ep_keys: List[int] = [random.getrandbits(64) for _ in range(9)]
    
    def hash_position(self, board: Board) -> int:
        """
        Compute the Zobrist hash for a board position.
        
        Args:
            board: Current board state
            
        Returns:
            64-bit hash value
        """
        h = 0
        
        # Hash pieces
        for sq in range(64):
            piece = board.squares[sq]
            if piece != EMPTY:
                h ^= self.piece_keys[piece][sq]
        
        # Hash side to move
        if not board.white_to_move:
            h ^= self.side_key
        
        # Hash castling rights
        h ^= self.castling_keys[board.castling_rights]
        
        # Hash en passant
        if board.en_passant_square >= 0:
            ep_file = board.en_passant_square % 8
            h ^= self.ep_keys[ep_file]
        else:
            h ^= self.ep_keys[8]  # No EP
        
        return h
    
    def update_hash(self, current_hash: int, board: Board, move: Move, 
                    old_castling: int, old_ep: int, captured_piece: int) -> int:
        """
        Incrementally update the hash after a move.
        
        This is more efficient than recomputing the full hash.
        """
        h = current_hash
        
        piece = board.squares[move.to_sq]  # The piece that moved (now at to_sq)
        original_piece = piece
        
        # If there was a promotion, we need the original pawn
        if move.promotion:
            from board import PAWN
            original_piece = (get_piece_color(piece)) | PAWN
        
        # Remove piece from original square
        h ^= self.piece_keys[original_piece][move.from_sq]
        
        # Add piece to new square
        h ^= self.piece_keys[piece][move.to_sq]
        
        # Handle capture
        if captured_piece != EMPTY:
            if move.is_en_passant:
                # EP capture - pawn was on different square
                if get_piece_color(piece) == WHITE:
                    cap_sq = move.to_sq - 8
                else:
                    cap_sq = move.to_sq + 8
                h ^= self.piece_keys[captured_piece][cap_sq]
            else:
                h ^= self.piece_keys[captured_piece][move.to_sq]
        
        # Handle castling (rook moves)
        if move.is_castling:
            from board import WHITE_ROOK, BLACK_ROOK
            if move.to_sq == 6:  # White kingside
                h ^= self.piece_keys[WHITE_ROOK][7]
                h ^= self.piece_keys[WHITE_ROOK][5]
            elif move.to_sq == 2:  # White queenside
                h ^= self.piece_keys[WHITE_ROOK][0]
                h ^= self.piece_keys[WHITE_ROOK][3]
            elif move.to_sq == 62:  # Black kingside
                h ^= self.piece_keys[BLACK_ROOK][63]
                h ^= self.piece_keys[BLACK_ROOK][61]
            elif move.to_sq == 58:  # Black queenside
                h ^= self.piece_keys[BLACK_ROOK][56]
                h ^= self.piece_keys[BLACK_ROOK][59]
        
        # Update castling rights
        h ^= self.castling_keys[old_castling]
        h ^= self.castling_keys[board.castling_rights]
        
        # Update en passant
        if old_ep >= 0:
            h ^= self.ep_keys[old_ep % 8]
        else:
            h ^= self.ep_keys[8]
        
        if board.en_passant_square >= 0:
            h ^= self.ep_keys[board.en_passant_square % 8]
        else:
            h ^= self.ep_keys[8]
        
        # Flip side to move
        h ^= self.side_key
        
        return h


# ============================================================================
# TRANSPOSITION TABLE
# ============================================================================

@dataclass
class TTEntry:
    """Entry in the transposition table."""
    hash_key: int       # Full hash for verification
    depth: int          # Search depth
    score: int          # Evaluation score
    flag: int           # TT_EXACT, TT_ALPHA, or TT_BETA
    best_move: Optional[Move]  # Best move found


class TranspositionTable:
    """
    Hash table for storing previously evaluated positions.
    
    Uses a fixed-size table with replacement based on depth.
    """
    
    def __init__(self, size_mb: int = 64):
        """
        Initialize transposition table.
        
        Args:
            size_mb: Approximate size in megabytes
        """
        # Estimate entries based on size (each entry ~50 bytes)
        entry_size = 50
        num_entries = (size_mb * 1024 * 1024) // entry_size
        
        # Use power of 2 for efficient indexing
        self.size = 1
        while self.size * 2 <= num_entries:
            self.size *= 2
        
        self.mask = self.size - 1
        self.table: Dict[int, TTEntry] = {}
        
        # Statistics
        self.hits = 0
        self.writes = 0
    
    def probe(self, hash_key: int) -> Optional[TTEntry]:
        """
        Look up a position in the table.
        
        Args:
            hash_key: Zobrist hash of position
            
        Returns:
            TTEntry if found, None otherwise
        """
        index = hash_key & self.mask
        entry = self.table.get(index)
        
        if entry is not None and entry.hash_key == hash_key:
            self.hits += 1
            return entry
        
        return None
    
    def store(self, hash_key: int, depth: int, score: int, flag: int, 
              best_move: Optional[Move]) -> None:
        """
        Store a position in the table.
        
        Uses replacement strategy based on depth - deeper searches
        are more valuable to keep.
        """
        index = hash_key & self.mask
        existing = self.table.get(index)
        
        # Always replace if:
        # - Slot is empty
        # - New entry has greater or equal depth
        # - Hash matches (same position, update)
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
        """Clear the transposition table."""
        self.table.clear()
        self.hits = 0
        self.writes = 0


# ============================================================================
# SEARCH ENGINE
# ============================================================================

class SearchEngine:
    """
    Chess search engine using minimax with alpha-beta pruning
    and transposition table.
    
    Attributes:
        move_generator: MoveGenerator instance
        nodes_searched: Counter for nodes visited during search
        best_move: Best move found during search
        max_depth: Maximum search depth
        stop_search: Flag to stop search early
        tt: Transposition table
        zobrist: Zobrist hashing
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
        
        # Statistics
        self.tt_cutoffs = 0
    
    def search(self, board: Board, depth: int = 4) -> Tuple[Optional[Move], int]:
        """
        Search for the best move in the position.
        
        Args:
            board: Current board state
            depth: Search depth (half-moves)
            
        Returns:
            Tuple of (best_move, score)
        """
        self.nodes_searched = 0
        self.best_move = None
        self.max_depth = depth
        self.stop_search = False
        self.tt_cutoffs = 0
        
        # Compute initial hash
        position_hash = self.zobrist.hash_position(board)
        
        # Iterative deepening
        best_move = None
        best_score = -INFINITY
        
        for current_depth in range(1, depth + 1):
            if self.stop_search:
                break
            
            score = self._alphabeta(board, current_depth, -INFINITY, INFINITY, 
                                   True, position_hash)
            
            if not self.stop_search and self.best_move is not None:
                best_move = self.best_move
                best_score = score
        
        return best_move, best_score
    
    def _alphabeta(self, board: Board, depth: int, alpha: int, beta: int,
                   is_root: bool, position_hash: int) -> int:
        """
        Alpha-beta pruning search with transposition table.
        """
        if self.stop_search:
            return 0
        
        self.nodes_searched += 1
        original_alpha = alpha
        
        # Check for draws (not at root)
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
            
            # Use TT move for move ordering
            tt_move = tt_entry.best_move
        
        # Generate legal moves
        moves = self.move_generator.generate_legal_moves(board)
        
        # Check for checkmate or stalemate
        if len(moves) == 0:
            if self.move_generator.is_in_check(board):
                return -MATE_SCORE + (self.max_depth - depth)
            else:
                return 0
        
        # Leaf node - quiescence search
        if depth <= 0:
            return self._quiescence(board, alpha, beta)
        
        # Order moves (TT move first, then by heuristic)
        moves = self._order_moves(board, moves, tt_move)
        
        best_score = -INFINITY
        best_move_at_node = None
        
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
            
            # Recursively search
            score = -self._alphabeta(board, depth - 1, -beta, -alpha, False, new_hash)
            
            # Unmake the move
            board.unmake_move(move, undo)
            
            if score > best_score:
                best_score = score
                best_move_at_node = move
                
                if is_root:
                    self.best_move = move
            
            alpha = max(alpha, score)
            
            # Beta cutoff
            if alpha >= beta:
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
        """
        Quiescence search to handle tactical positions.
        """
        if self.stop_search:
            return 0
        
        self.nodes_searched += 1
        
        # Stand-pat score
        stand_pat = evaluate(board)
        
        if stand_pat >= beta:
            return beta
        
        if alpha < stand_pat:
            alpha = stand_pat
        
        # Limit quiescence depth
        if depth >= 4:
            return stand_pat
        
        # Generate and search only captures
        moves = self.move_generator.generate_legal_moves(board)
        captures = [m for m in moves if board.squares[m.to_sq] != 0 or m.is_en_passant]
        
        # Order captures by MVV-LVA
        captures = self._order_moves(board, captures, None)
        
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
                     tt_move: Optional[Move]) -> List[Move]:
        """
        Order moves for better alpha-beta pruning.
        
        Priority:
        1. TT move (if available)
        2. Captures (by MVV-LVA)
        3. Promotions
        4. Other moves
        """
        scored_moves = []
        
        for move in moves:
            # TT move gets highest priority
            if tt_move is not None and move == tt_move:
                score = 1000000
            else:
                score = evaluate_move(board, move)
            scored_moves.append((score, move))
        
        # Sort by score descending
        scored_moves.sort(key=lambda x: x[0], reverse=True)
        
        return [move for _, move in scored_moves]
    
    def stop(self):
        """Signal the search to stop."""
        self.stop_search = True
    
    def clear_tt(self):
        """Clear the transposition table."""
        self.tt.clear()
    
    def get_info(self) -> dict:
        """
        Get information about the last search.
        """
        return {
            'nodes': self.nodes_searched,
            'depth': self.max_depth,
            'tt_hits': self.tt.hits,
            'tt_cutoffs': self.tt_cutoffs,
        }
