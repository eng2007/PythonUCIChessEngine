"""
OpusChess - Board Representation Module

This module provides the core data structures for representing a chess board,
pieces, and moves. It includes FEN parsing and generation, move execution,
and position history tracking.
"""

from typing import Optional, List, Tuple
from dataclasses import dataclass
from copy import deepcopy

# Piece type constants (lower 3 bits)
EMPTY = 0
PAWN = 1
KNIGHT = 2
BISHOP = 3
ROOK = 4
QUEEN = 5
KING = 6

# Color constants (bits 3-4)
WHITE = 8
BLACK = 16

# Piece masks
PIECE_MASK = 7  # 0b111 - extracts piece type
COLOR_MASK = 24  # 0b11000 - extracts color

# Complete piece values for convenience
WHITE_PAWN = WHITE | PAWN
WHITE_KNIGHT = WHITE | KNIGHT
WHITE_BISHOP = WHITE | BISHOP
WHITE_ROOK = WHITE | ROOK
WHITE_QUEEN = WHITE | QUEEN
WHITE_KING = WHITE | KING

BLACK_PAWN = BLACK | PAWN
BLACK_KNIGHT = BLACK | KNIGHT
BLACK_BISHOP = BLACK | BISHOP
BLACK_ROOK = BLACK | ROOK
BLACK_QUEEN = BLACK | QUEEN
BLACK_KING = BLACK | KING

# FEN piece mapping
FEN_TO_PIECE = {
    'P': WHITE_PAWN, 'N': WHITE_KNIGHT, 'B': WHITE_BISHOP,
    'R': WHITE_ROOK, 'Q': WHITE_QUEEN, 'K': WHITE_KING,
    'p': BLACK_PAWN, 'n': BLACK_KNIGHT, 'b': BLACK_BISHOP,
    'r': BLACK_ROOK, 'q': BLACK_QUEEN, 'k': BLACK_KING
}

PIECE_TO_FEN = {v: k for k, v in FEN_TO_PIECE.items()}

# Square names for UCI notation
FILE_NAMES = 'abcdefgh'
RANK_NAMES = '12345678'


def square_name(sq: int) -> str:
    """Convert square index (0-63) to algebraic notation (e.g., 'e4')."""
    return FILE_NAMES[sq % 8] + RANK_NAMES[sq // 8]


def parse_square(name: str) -> int:
    """Convert algebraic notation to square index."""
    file_idx = FILE_NAMES.index(name[0])
    rank_idx = RANK_NAMES.index(name[1])
    return rank_idx * 8 + file_idx


def get_piece_type(piece: int) -> int:
    """Extract piece type from piece value."""
    return piece & PIECE_MASK


def get_piece_color(piece: int) -> int:
    """Extract color from piece value."""
    return piece & COLOR_MASK


def is_white(piece: int) -> bool:
    """Check if piece is white."""
    return (piece & COLOR_MASK) == WHITE


def is_black(piece: int) -> bool:
    """Check if piece is black."""
    return (piece & COLOR_MASK) == BLACK


@dataclass
class Move:
    """
    Represents a chess move.
    
    Attributes:
        from_sq: Source square (0-63)
        to_sq: Destination square (0-63)
        promotion: Piece type for pawn promotion (QUEEN, ROOK, BISHOP, KNIGHT) or 0
        is_castling: True if this is a castling move
        is_en_passant: True if this is an en passant capture
    """
    from_sq: int
    to_sq: int
    promotion: int = 0
    is_castling: bool = False
    is_en_passant: bool = False
    
    def to_uci(self) -> str:
        """Convert move to UCI notation (e.g., 'e2e4', 'e7e8q')."""
        uci = square_name(self.from_sq) + square_name(self.to_sq)
        if self.promotion:
            promo_chars = {QUEEN: 'q', ROOK: 'r', BISHOP: 'b', KNIGHT: 'n'}
            uci += promo_chars.get(self.promotion, '')
        return uci
    
    def __eq__(self, other):
        if not isinstance(other, Move):
            return False
        return (self.from_sq == other.from_sq and 
                self.to_sq == other.to_sq and 
                self.promotion == other.promotion)
    
    def __hash__(self):
        return hash((self.from_sq, self.to_sq, self.promotion))
    
    def __repr__(self):
        return f"Move({self.to_uci()})"


@dataclass
class UndoInfo:
    """Information needed to undo a move."""
    captured_piece: int
    castling_rights: int
    en_passant_square: int
    halfmove_clock: int
    moved_piece: int


class Board:
    """
    Chess board representation.
    
    The board is represented as a flat array of 64 squares, indexed 0-63
    where 0 = a1, 1 = b1, ..., 63 = h8.
    
    Attributes:
        squares: 64-element list representing the board
        white_to_move: True if it's white's turn
        castling_rights: Bitmask for castling (1=K, 2=Q, 4=k, 8=q)
        en_passant_square: Target square for en passant (-1 if none)
        halfmove_clock: Moves since last pawn move or capture (for 50-move rule)
        fullmove_number: Full move counter
        position_history: List of position hashes for repetition detection
    """
    
    # Castling rights bitmasks
    CASTLE_WK = 1  # White kingside
    CASTLE_WQ = 2  # White queenside
    CASTLE_BK = 4  # Black kingside
    CASTLE_BQ = 8  # Black queenside
    
    STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    
    def __init__(self, fen: Optional[str] = None):
        """Initialize board from FEN string or starting position."""
        self.squares = [EMPTY] * 64
        self.white_to_move = True
        self.castling_rights = 0
        self.en_passant_square = -1
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.position_history: List[int] = []
        
        if fen is None:
            fen = self.STARTING_FEN
        self._parse_fen(fen)
    
    def _parse_fen(self, fen: str) -> None:
        """Parse a FEN string and set up the board."""
        parts = fen.split()
        
        # Parse piece placement
        rank = 7
        file = 0
        for char in parts[0]:
            if char == '/':
                rank -= 1
                file = 0
            elif char.isdigit():
                file += int(char)
            else:
                sq = rank * 8 + file
                self.squares[sq] = FEN_TO_PIECE.get(char, EMPTY)
                file += 1
        
        # Parse active color
        self.white_to_move = parts[1] == 'w' if len(parts) > 1 else True
        
        # Parse castling rights
        self.castling_rights = 0
        if len(parts) > 2 and parts[2] != '-':
            if 'K' in parts[2]: self.castling_rights |= self.CASTLE_WK
            if 'Q' in parts[2]: self.castling_rights |= self.CASTLE_WQ
            if 'k' in parts[2]: self.castling_rights |= self.CASTLE_BK
            if 'q' in parts[2]: self.castling_rights |= self.CASTLE_BQ
        
        # Parse en passant square
        self.en_passant_square = -1
        if len(parts) > 3 and parts[3] != '-':
            self.en_passant_square = parse_square(parts[3])
        
        # Parse halfmove clock
        self.halfmove_clock = int(parts[4]) if len(parts) > 4 else 0
        
        # Parse fullmove number
        self.fullmove_number = int(parts[5]) if len(parts) > 5 else 1
        
        # Initialize position history
        self.position_history = [self._compute_hash()]
    
    def to_fen(self) -> str:
        """Generate FEN string from current board state."""
        fen_parts = []
        
        # Piece placement
        rows = []
        for rank in range(7, -1, -1):
            row = ""
            empty_count = 0
            for file in range(8):
                piece = self.squares[rank * 8 + file]
                if piece == EMPTY:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        row += str(empty_count)
                        empty_count = 0
                    row += PIECE_TO_FEN.get(piece, '?')
            if empty_count > 0:
                row += str(empty_count)
            rows.append(row)
        fen_parts.append('/'.join(rows))
        
        # Active color
        fen_parts.append('w' if self.white_to_move else 'b')
        
        # Castling rights
        castling = ""
        if self.castling_rights & self.CASTLE_WK: castling += 'K'
        if self.castling_rights & self.CASTLE_WQ: castling += 'Q'
        if self.castling_rights & self.CASTLE_BK: castling += 'k'
        if self.castling_rights & self.CASTLE_BQ: castling += 'q'
        fen_parts.append(castling if castling else '-')
        
        # En passant
        if self.en_passant_square >= 0:
            fen_parts.append(square_name(self.en_passant_square))
        else:
            fen_parts.append('-')
        
        # Halfmove clock and fullmove number
        fen_parts.append(str(self.halfmove_clock))
        fen_parts.append(str(self.fullmove_number))
        
        return ' '.join(fen_parts)
    
    def _compute_hash(self) -> int:
        """Compute a hash of the current position for repetition detection."""
        # Simple hash based on board state and game state
        h = hash(tuple(self.squares))
        h ^= hash((self.white_to_move, self.castling_rights, self.en_passant_square))
        return h
    
    def make_move(self, move: Move) -> UndoInfo:
        """
        Execute a move on the board.
        
        Returns UndoInfo for undoing the move later.
        """
        from_sq = move.from_sq
        to_sq = move.to_sq
        piece = self.squares[from_sq]
        captured = self.squares[to_sq]
        
        # Save undo information
        undo = UndoInfo(
            captured_piece=captured if not move.is_en_passant else (BLACK_PAWN if self.white_to_move else WHITE_PAWN),
            castling_rights=self.castling_rights,
            en_passant_square=self.en_passant_square,
            halfmove_clock=self.halfmove_clock,
            moved_piece=piece
        )
        
        # Update halfmove clock
        piece_type = get_piece_type(piece)
        if piece_type == PAWN or captured != EMPTY:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        
        # Handle en passant capture
        if move.is_en_passant:
            # Remove the captured pawn
            if self.white_to_move:
                self.squares[to_sq - 8] = EMPTY
            else:
                self.squares[to_sq + 8] = EMPTY
        
        # Handle castling
        if move.is_castling:
            # Move the rook
            if to_sq == 6:  # White kingside (g1)
                self.squares[7] = EMPTY  # h1
                self.squares[5] = WHITE_ROOK  # f1
            elif to_sq == 2:  # White queenside (c1)
                self.squares[0] = EMPTY  # a1
                self.squares[3] = WHITE_ROOK  # d1
            elif to_sq == 62:  # Black kingside (g8)
                self.squares[63] = EMPTY  # h8
                self.squares[61] = BLACK_ROOK  # f8
            elif to_sq == 58:  # Black queenside (c8)
                self.squares[56] = EMPTY  # a8
                self.squares[59] = BLACK_ROOK  # d8
        
        # Move the piece
        self.squares[to_sq] = piece
        self.squares[from_sq] = EMPTY
        
        # Handle promotion
        if move.promotion:
            self.squares[to_sq] = (WHITE if self.white_to_move else BLACK) | move.promotion
        
        # Update castling rights
        # If king moves, remove both castling rights for that side
        if piece_type == KING:
            if self.white_to_move:
                self.castling_rights &= ~(self.CASTLE_WK | self.CASTLE_WQ)
            else:
                self.castling_rights &= ~(self.CASTLE_BK | self.CASTLE_BQ)
        
        # If rook moves or is captured, remove appropriate castling right
        if from_sq == 0 or to_sq == 0:  # a1
            self.castling_rights &= ~self.CASTLE_WQ
        if from_sq == 7 or to_sq == 7:  # h1
            self.castling_rights &= ~self.CASTLE_WK
        if from_sq == 56 or to_sq == 56:  # a8
            self.castling_rights &= ~self.CASTLE_BQ
        if from_sq == 63 or to_sq == 63:  # h8
            self.castling_rights &= ~self.CASTLE_BK
        
        # Update en passant square
        self.en_passant_square = -1
        if piece_type == PAWN:
            # Check for double pawn push
            if abs(to_sq - from_sq) == 16:
                self.en_passant_square = (from_sq + to_sq) // 2
        
        # Update fullmove number
        if not self.white_to_move:
            self.fullmove_number += 1
        
        # Switch side to move
        self.white_to_move = not self.white_to_move
        
        # Update position history
        self.position_history.append(self._compute_hash())
        
        return undo
    
    def unmake_move(self, move: Move, undo: UndoInfo) -> None:
        """Undo a move using saved UndoInfo."""
        # Switch side back
        self.white_to_move = not self.white_to_move
        
        from_sq = move.from_sq
        to_sq = move.to_sq
        
        # Restore the moved piece
        self.squares[from_sq] = undo.moved_piece
        
        # Restore captured piece (or empty square)
        if move.is_en_passant:
            self.squares[to_sq] = EMPTY
            # Restore the captured pawn
            if self.white_to_move:
                self.squares[to_sq - 8] = BLACK_PAWN
            else:
                self.squares[to_sq + 8] = WHITE_PAWN
        else:
            self.squares[to_sq] = undo.captured_piece
        
        # Handle castling - move rook back
        if move.is_castling:
            if to_sq == 6:  # White kingside
                self.squares[5] = EMPTY
                self.squares[7] = WHITE_ROOK
            elif to_sq == 2:  # White queenside
                self.squares[3] = EMPTY
                self.squares[0] = WHITE_ROOK
            elif to_sq == 62:  # Black kingside
                self.squares[61] = EMPTY
                self.squares[63] = BLACK_ROOK
            elif to_sq == 58:  # Black queenside
                self.squares[59] = EMPTY
                self.squares[56] = BLACK_ROOK
        
        # Restore game state
        self.castling_rights = undo.castling_rights
        self.en_passant_square = undo.en_passant_square
        self.halfmove_clock = undo.halfmove_clock
        
        # Update fullmove number
        if not self.white_to_move:
            self.fullmove_number -= 1
        
        # Remove last position from history
        if self.position_history:
            self.position_history.pop()
    
    def find_king(self, white: bool) -> int:
        """Find the king's square for the specified color."""
        king = WHITE_KING if white else BLACK_KING
        for sq in range(64):
            if self.squares[sq] == king:
                return sq
        return -1  # Should never happen in valid position
    
    def is_repetition(self) -> bool:
        """Check if current position has occurred 3 times (draw by repetition)."""
        if len(self.position_history) < 5:
            return False
        current_hash = self.position_history[-1]
        count = sum(1 for h in self.position_history if h == current_hash)
        return count >= 3
    
    def is_fifty_moves(self) -> bool:
        """Check if 50-move rule applies (draw)."""
        return self.halfmove_clock >= 100  # 100 half-moves = 50 full moves
    
    def has_insufficient_material(self) -> bool:
        """
        Check for insufficient material to checkmate.
        
        Draws: K vs K, K+B vs K, K+N vs K, K+B vs K+B (same color bishops)
        """
        pieces = []
        for sq in range(64):
            piece = self.squares[sq]
            if piece != EMPTY:
                pieces.append((get_piece_type(piece), get_piece_color(piece), sq))
        
        # Count pieces by type
        piece_counts = {}
        for ptype, color, sq in pieces:
            key = (ptype, color)
            piece_counts[key] = piece_counts.get(key, 0) + 1
        
        # Only kings left
        if len(pieces) == 2:
            return True
        
        # King and minor piece vs King
        if len(pieces) == 3:
            for ptype, color, sq in pieces:
                if ptype in (KNIGHT, BISHOP):
                    return True
        
        # King + Bishop vs King + Bishop (same color squares)
        if len(pieces) == 4:
            bishops = [(sq, color) for ptype, color, sq in pieces if ptype == BISHOP]
            if len(bishops) == 2:
                # Check if bishops are on same color squares
                sq1, c1 = bishops[0]
                sq2, c2 = bishops[1]
                sq1_color = (sq1 // 8 + sq1 % 8) % 2
                sq2_color = (sq2 // 8 + sq2 % 8) % 2
                if sq1_color == sq2_color and c1 != c2:
                    return True
        
        return False
    
    def copy(self) -> 'Board':
        """Create a deep copy of the board."""
        new_board = Board.__new__(Board)
        new_board.squares = self.squares.copy()
        new_board.white_to_move = self.white_to_move
        new_board.castling_rights = self.castling_rights
        new_board.en_passant_square = self.en_passant_square
        new_board.halfmove_clock = self.halfmove_clock
        new_board.fullmove_number = self.fullmove_number
        new_board.position_history = self.position_history.copy()
        return new_board
    
    def __str__(self) -> str:
        """Return a human-readable string representation of the board."""
        lines = []
        lines.append("  +---+---+---+---+---+---+---+---+")
        for rank in range(7, -1, -1):
            row = f"{rank + 1} |"
            for file in range(8):
                piece = self.squares[rank * 8 + file]
                if piece == EMPTY:
                    row += "   |"
                else:
                    symbol = PIECE_TO_FEN.get(piece, '?')
                    row += f" {symbol} |"
            lines.append(row)
            lines.append("  +---+---+---+---+---+---+---+---+")
        lines.append("    a   b   c   d   e   f   g   h")
        return '\n'.join(lines)
