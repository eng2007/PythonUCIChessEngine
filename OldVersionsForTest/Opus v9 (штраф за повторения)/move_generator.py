"""
OpusChess - Move Generator Module

This module handles the generation of legal chess moves, including
all special moves (castling, en passant, pawn promotion).
"""

from typing import List, Tuple
from board import (
    Board, Move, EMPTY, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    WHITE, BLACK, get_piece_type, get_piece_color, is_white, is_black,
    WHITE_KING, BLACK_KING
)


class MoveGenerator:
    """
    Generates all legal moves for a given position.
    
    This class generates pseudo-legal moves first, then filters out
    moves that would leave the king in check.
    """
    
    # Direction offsets for sliding pieces
    # Rook directions: up, down, left, right
    ROOK_DIRECTIONS = [8, -8, -1, 1]
    # Bishop directions: diagonals
    BISHOP_DIRECTIONS = [7, 9, -7, -9]
    # Queen directions: combination of rook and bishop
    QUEEN_DIRECTIONS = [8, -8, -1, 1, 7, 9, -7, -9]
    # King directions: same as queen, but one square
    KING_DIRECTIONS = [8, -8, -1, 1, 7, 9, -7, -9]
    # Knight offsets
    KNIGHT_OFFSETS = [17, 15, 10, 6, -6, -10, -15, -17]
    
    def __init__(self):
        """Initialize the move generator."""
        pass
    
    def generate_legal_moves(self, board: Board) -> List[Move]:
        """
        Generate all legal moves for the current position.
        
        Args:
            board: Current board state
            
        Returns:
            List of legal Move objects
        """
        pseudo_legal = self._generate_pseudo_legal_moves(board)
        legal_moves = []
        
        for move in pseudo_legal:
            if self._is_legal(board, move):
                legal_moves.append(move)
        
        return legal_moves
    
    def _generate_pseudo_legal_moves(self, board: Board) -> List[Move]:
        """Generate all pseudo-legal moves (may leave king in check)."""
        moves = []
        color = WHITE if board.white_to_move else BLACK
        
        for sq in range(64):
            piece = board.squares[sq]
            if piece == EMPTY:
                continue
            if get_piece_color(piece) != color:
                continue
            
            piece_type = get_piece_type(piece)
            
            if piece_type == PAWN:
                moves.extend(self._generate_pawn_moves(board, sq))
            elif piece_type == KNIGHT:
                moves.extend(self._generate_knight_moves(board, sq))
            elif piece_type == BISHOP:
                moves.extend(self._generate_bishop_moves(board, sq))
            elif piece_type == ROOK:
                moves.extend(self._generate_rook_moves(board, sq))
            elif piece_type == QUEEN:
                moves.extend(self._generate_queen_moves(board, sq))
            elif piece_type == KING:
                moves.extend(self._generate_king_moves(board, sq))
        
        return moves
    
    def _generate_pawn_moves(self, board: Board, sq: int) -> List[Move]:
        """Generate pawn moves from the given square."""
        moves = []
        color = get_piece_color(board.squares[sq])
        is_white_pawn = color == WHITE
        
        # Direction of pawn movement
        direction = 8 if is_white_pawn else -8
        start_rank = 1 if is_white_pawn else 6
        promo_rank = 7 if is_white_pawn else 0
        
        file = sq % 8
        rank = sq // 8
        
        # Single push
        to_sq = sq + direction
        if 0 <= to_sq < 64 and board.squares[to_sq] == EMPTY:
            if to_sq // 8 == promo_rank:
                # Promotion
                for promo in [QUEEN, ROOK, BISHOP, KNIGHT]:
                    moves.append(Move(sq, to_sq, promotion=promo))
            else:
                moves.append(Move(sq, to_sq))
            
            # Double push from starting rank
            if rank == start_rank:
                to_sq2 = sq + 2 * direction
                if board.squares[to_sq2] == EMPTY:
                    moves.append(Move(sq, to_sq2))
        
        # Captures
        capture_offsets = [direction - 1, direction + 1]  # Left and right diagonals
        for offset in capture_offsets:
            to_sq = sq + offset
            to_file = to_sq % 8
            
            # Check if move wraps around the board
            if abs(to_file - file) != 1:
                continue
            if to_sq < 0 or to_sq >= 64:
                continue
            
            target = board.squares[to_sq]
            
            # Regular capture
            if target != EMPTY and get_piece_color(target) != color:
                if to_sq // 8 == promo_rank:
                    for promo in [QUEEN, ROOK, BISHOP, KNIGHT]:
                        moves.append(Move(sq, to_sq, promotion=promo))
                else:
                    moves.append(Move(sq, to_sq))
            
            # En passant capture
            if to_sq == board.en_passant_square:
                moves.append(Move(sq, to_sq, is_en_passant=True))
        
        return moves
    
    def _generate_knight_moves(self, board: Board, sq: int) -> List[Move]:
        """Generate knight moves from the given square."""
        moves = []
        color = get_piece_color(board.squares[sq])
        file = sq % 8
        rank = sq // 8
        
        for offset in self.KNIGHT_OFFSETS:
            to_sq = sq + offset
            if to_sq < 0 or to_sq >= 64:
                continue
            
            to_file = to_sq % 8
            to_rank = to_sq // 8
            
            # Check for wraparound (knight can't jump more than 2 files)
            if abs(to_file - file) > 2 or abs(to_rank - rank) > 2:
                continue
            
            target = board.squares[to_sq]
            if target == EMPTY or get_piece_color(target) != color:
                moves.append(Move(sq, to_sq))
        
        return moves
    
    def _generate_sliding_moves(self, board: Board, sq: int, 
                                 directions: List[int]) -> List[Move]:
        """Generate moves for sliding pieces (bishop, rook, queen)."""
        moves = []
        color = get_piece_color(board.squares[sq])
        file = sq % 8
        
        for direction in directions:
            current_sq = sq
            while True:
                current_file = current_sq % 8
                next_sq = current_sq + direction
                
                # Check bounds
                if next_sq < 0 or next_sq >= 64:
                    break
                
                next_file = next_sq % 8
                
                # Check for wraparound
                file_diff = abs(next_file - current_file)
                if direction in [-1, 1]:  # Horizontal
                    if file_diff != 1:
                        break
                elif direction in [7, -9]:  # Diagonal going left
                    if next_file != current_file - 1:
                        break
                elif direction in [9, -7]:  # Diagonal going right
                    if next_file != current_file + 1:
                        break
                
                target = board.squares[next_sq]
                
                if target == EMPTY:
                    moves.append(Move(sq, next_sq))
                elif get_piece_color(target) != color:
                    moves.append(Move(sq, next_sq))
                    break  # Can capture but not continue past
                else:
                    break  # Blocked by own piece
                
                current_sq = next_sq
        
        return moves
    
    def _generate_bishop_moves(self, board: Board, sq: int) -> List[Move]:
        """Generate bishop moves from the given square."""
        return self._generate_sliding_moves(board, sq, self.BISHOP_DIRECTIONS)
    
    def _generate_rook_moves(self, board: Board, sq: int) -> List[Move]:
        """Generate rook moves from the given square."""
        return self._generate_sliding_moves(board, sq, self.ROOK_DIRECTIONS)
    
    def _generate_queen_moves(self, board: Board, sq: int) -> List[Move]:
        """Generate queen moves from the given square."""
        return self._generate_sliding_moves(board, sq, self.QUEEN_DIRECTIONS)
    
    def _generate_king_moves(self, board: Board, sq: int) -> List[Move]:
        """Generate king moves from the given square, including castling."""
        moves = []
        color = get_piece_color(board.squares[sq])
        file = sq % 8
        
        # Normal king moves
        for direction in self.KING_DIRECTIONS:
            to_sq = sq + direction
            if to_sq < 0 or to_sq >= 64:
                continue
            
            to_file = to_sq % 8
            
            # Check for wraparound
            if abs(to_file - file) > 1:
                continue
            
            target = board.squares[to_sq]
            if target == EMPTY or get_piece_color(target) != color:
                moves.append(Move(sq, to_sq))
        
        # Castling - check if king is in check and squares are not attacked by enemy
        is_white_king = color == WHITE
        enemy_is_white = not is_white_king
        
        if not self.is_square_attacked(board, sq, enemy_is_white):
            if is_white_king:
                # Kingside castling (O-O) - white
                if (board.castling_rights & Board.CASTLE_WK and
                    board.squares[5] == EMPTY and
                    board.squares[6] == EMPTY and
                    not self.is_square_attacked(board, 5, False) and
                    not self.is_square_attacked(board, 6, False)):
                    moves.append(Move(sq, 6, is_castling=True))
                
                # Queenside castling (O-O-O) - white
                if (board.castling_rights & Board.CASTLE_WQ and
                    board.squares[1] == EMPTY and
                    board.squares[2] == EMPTY and
                    board.squares[3] == EMPTY and
                    not self.is_square_attacked(board, 2, False) and
                    not self.is_square_attacked(board, 3, False)):
                    moves.append(Move(sq, 2, is_castling=True))
            else:
                # Kingside castling (O-O) - black
                if (board.castling_rights & Board.CASTLE_BK and
                    board.squares[61] == EMPTY and
                    board.squares[62] == EMPTY and
                    not self.is_square_attacked(board, 61, True) and
                    not self.is_square_attacked(board, 62, True)):
                    moves.append(Move(sq, 62, is_castling=True))
                
                # Queenside castling (O-O-O) - black
                if (board.castling_rights & Board.CASTLE_BQ and
                    board.squares[57] == EMPTY and
                    board.squares[58] == EMPTY and
                    board.squares[59] == EMPTY and
                    not self.is_square_attacked(board, 58, True) and
                    not self.is_square_attacked(board, 59, True)):
                    moves.append(Move(sq, 58, is_castling=True))
        
        return moves
    
    def is_square_attacked(self, board: Board, sq: int, by_white: bool) -> bool:
        """
        Check if a square is attacked by the specified color.
        
        Args:
            board: Current board state
            sq: Square to check (0-63)
            by_white: True to check attacks by white, False for black
            
        Returns:
            True if the square is under attack
        """
        attacker_color = WHITE if by_white else BLACK
        file = sq % 8
        rank = sq // 8
        
        # Check pawn attacks
        pawn_direction = -8 if by_white else 8
        pawn_attackers = [sq + pawn_direction - 1, sq + pawn_direction + 1]
        for attacker_sq in pawn_attackers:
            if attacker_sq < 0 or attacker_sq >= 64:
                continue
            att_file = attacker_sq % 8
            if abs(att_file - file) != 1:
                continue
            piece = board.squares[attacker_sq]
            if piece != EMPTY and get_piece_type(piece) == PAWN and get_piece_color(piece) == attacker_color:
                return True
        
        # Check knight attacks
        for offset in self.KNIGHT_OFFSETS:
            attacker_sq = sq + offset
            if attacker_sq < 0 or attacker_sq >= 64:
                continue
            att_file = attacker_sq % 8
            att_rank = attacker_sq // 8
            if abs(att_file - file) > 2 or abs(att_rank - rank) > 2:
                continue
            piece = board.squares[attacker_sq]
            if piece != EMPTY and get_piece_type(piece) == KNIGHT and get_piece_color(piece) == attacker_color:
                return True
        
        # Check king attacks
        for direction in self.KING_DIRECTIONS:
            attacker_sq = sq + direction
            if attacker_sq < 0 or attacker_sq >= 64:
                continue
            att_file = attacker_sq % 8
            if abs(att_file - file) > 1:
                continue
            piece = board.squares[attacker_sq]
            if piece != EMPTY and get_piece_type(piece) == KING and get_piece_color(piece) == attacker_color:
                return True
        
        # Check sliding piece attacks (bishop, rook, queen)
        for direction in self.ROOK_DIRECTIONS:
            if self._check_sliding_attack(board, sq, direction, attacker_color, [ROOK, QUEEN]):
                return True
        
        for direction in self.BISHOP_DIRECTIONS:
            if self._check_sliding_attack(board, sq, direction, attacker_color, [BISHOP, QUEEN]):
                return True
        
        return False
    
    def _check_sliding_attack(self, board: Board, sq: int, direction: int,
                               attacker_color: int, piece_types: List[int]) -> bool:
        """Check if there's a sliding piece attacking along a direction."""
        current_sq = sq
        
        while True:
            current_file = current_sq % 8
            next_sq = current_sq + direction
            
            if next_sq < 0 or next_sq >= 64:
                break
            
            next_file = next_sq % 8
            
            # Check for wraparound
            if direction in [-1, 1]:
                if abs(next_file - current_file) != 1:
                    break
            elif direction in [7, -9]:
                if next_file != current_file - 1:
                    break
            elif direction in [9, -7]:
                if next_file != current_file + 1:
                    break
            
            piece = board.squares[next_sq]
            
            if piece != EMPTY:
                if get_piece_color(piece) == attacker_color:
                    if get_piece_type(piece) in piece_types:
                        return True
                break
            
            current_sq = next_sq
        
        return False
    
    def _is_legal(self, board: Board, move: Move) -> bool:
        """
        Check if a move is legal (doesn't leave own king in check).
        
        Args:
            board: Current board state
            move: Move to check
            
        Returns:
            True if the move is legal
        """
        # Make the move
        undo = board.make_move(move)
        
        # Check if own king is in check after the move
        # Note: side to move has switched, so we check the previous side's king
        king_sq = board.find_king(not board.white_to_move)
        in_check = self.is_square_attacked(board, king_sq, board.white_to_move)
        
        # Unmake the move
        board.unmake_move(move, undo)
        
        return not in_check
    
    def is_in_check(self, board: Board) -> bool:
        """Check if the current side's king is in check."""
        king_sq = board.find_king(board.white_to_move)
        return self.is_square_attacked(board, king_sq, not board.white_to_move)
    
    def is_checkmate(self, board: Board) -> bool:
        """Check if the current position is checkmate."""
        if not self.is_in_check(board):
            return False
        return len(self.generate_legal_moves(board)) == 0
    
    def is_stalemate(self, board: Board) -> bool:
        """Check if the current position is stalemate."""
        if self.is_in_check(board):
            return False
        return len(self.generate_legal_moves(board)) == 0
    
    def is_draw(self, board: Board) -> bool:
        """
        Check if the position is a draw.
        
        Considers: stalemate, 50-move rule, threefold repetition,
        insufficient material.
        """
        if self.is_stalemate(board):
            return True
        if board.is_fifty_moves():
            return True
        if board.is_repetition():
            return True
        if board.has_insufficient_material():
            return True
        return False
