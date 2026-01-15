"""
OpusChess - Search Engine Module

This module implements the chess search algorithm using minimax
with alpha-beta pruning. It finds the best move for the current position.
"""

from typing import Optional, Tuple, List
from board import Board, Move
from move_generator import MoveGenerator
from evaluation import evaluate, evaluate_move, PIECE_VALUES, KING

# Constants for search
INFINITY = 100000
MATE_SCORE = 50000
MAX_DEPTH = 100


class SearchEngine:
    """
    Chess search engine using minimax with alpha-beta pruning.
    
    Attributes:
        move_generator: MoveGenerator instance
        nodes_searched: Counter for nodes visited during search
        best_move: Best move found during search
        max_depth: Maximum search depth
        stop_search: Flag to stop search early
    """
    
    def __init__(self):
        """Initialize the search engine."""
        self.move_generator = MoveGenerator()
        self.nodes_searched = 0
        self.best_move: Optional[Move] = None
        self.max_depth = 4
        self.stop_search = False
    
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
        
        # Iterative deepening
        best_move = None
        best_score = -INFINITY
        
        for current_depth in range(1, depth + 1):
            if self.stop_search:
                break
            
            score = self._alphabeta(board, current_depth, -INFINITY, INFINITY, True)
            
            if not self.stop_search and self.best_move is not None:
                best_move = self.best_move
                best_score = score
        
        return best_move, best_score
    
    def _alphabeta(self, board: Board, depth: int, alpha: int, beta: int,
                   is_root: bool = False) -> int:
        """
        Alpha-beta pruning search.
        
        Args:
            board: Current board state
            depth: Remaining depth to search
            alpha: Alpha value for pruning
            beta: Beta value for pruning
            is_root: True if this is the root node
            
        Returns:
            Best score for the current position
        """
        if self.stop_search:
            return 0
        
        self.nodes_searched += 1
        
        # Check for draws
        if not is_root:
            if board.is_fifty_moves() or board.is_repetition():
                return 0
            if board.has_insufficient_material():
                return 0
        
        # Generate legal moves
        moves = self.move_generator.generate_legal_moves(board)
        
        # Check for checkmate or stalemate
        if len(moves) == 0:
            if self.move_generator.is_in_check(board):
                # Checkmate - return negative score (bad for us)
                return -MATE_SCORE + (self.max_depth - depth)
            else:
                # Stalemate
                return 0
        
        # Leaf node - return static evaluation
        if depth <= 0:
            return self._quiescence(board, alpha, beta)
        
        # Order moves for better pruning
        moves = self._order_moves(board, moves)
        
        best_score = -INFINITY
        best_move_at_node = None
        
        for move in moves:
            if self.stop_search:
                break
            
            # Make the move
            undo = board.make_move(move)
            
            # Recursively search
            score = -self._alphabeta(board, depth - 1, -beta, -alpha, False)
            
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
        
        return best_score
    
    def _quiescence(self, board: Board, alpha: int, beta: int, depth: int = 0) -> int:
        """
        Quiescence search to handle tactical positions.
        
        Only searches captures to avoid horizon effect.
        
        Args:
            board: Current board state
            alpha: Alpha value
            beta: Beta value
            depth: Current quiescence depth (for limiting)
            
        Returns:
            Evaluation score
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
        captures = self._order_moves(board, captures)
        
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
    
    def _order_moves(self, board: Board, moves: List[Move]) -> List[Move]:
        """
        Order moves for better alpha-beta pruning.
        
        Ordering priority:
        1. Captures (by MVV-LVA)
        2. Promotions
        3. Other moves
        
        Args:
            board: Current board state
            moves: List of moves to order
            
        Returns:
            Ordered list of moves
        """
        scored_moves = []
        
        for move in moves:
            score = evaluate_move(board, move)
            scored_moves.append((score, move))
        
        # Sort by score descending
        scored_moves.sort(key=lambda x: x[0], reverse=True)
        
        return [move for _, move in scored_moves]
    
    def stop(self):
        """Signal the search to stop."""
        self.stop_search = True
    
    def get_info(self) -> dict:
        """
        Get information about the last search.
        
        Returns:
            Dictionary with search statistics
        """
        return {
            'nodes': self.nodes_searched,
            'depth': self.max_depth,
        }
