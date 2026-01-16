//! OpusChess - Board Representation Module
//!
//! This module provides the core data structures for representing a chess board,
//! pieces, and moves. It includes FEN parsing and generation, move execution,
//! and position history tracking.

use crate::types::*;
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

/// Starting position FEN
pub const STARTING_FEN: &str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

/// Represents a chess move
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct Move {
    pub from_sq: usize,
    pub to_sq: usize,
    pub promotion: u8,
    pub is_castling: bool,
    pub is_en_passant: bool,
}

impl Move {
    /// Create a new move
    pub fn new(from_sq: usize, to_sq: usize) -> Self {
        Move {
            from_sq,
            to_sq,
            promotion: 0,
            is_castling: false,
            is_en_passant: false,
        }
    }

    /// Create a promotion move
    pub fn with_promotion(from_sq: usize, to_sq: usize, promotion: u8) -> Self {
        Move {
            from_sq,
            to_sq,
            promotion,
            is_castling: false,
            is_en_passant: false,
        }
    }

    /// Create a castling move
    pub fn castling(from_sq: usize, to_sq: usize) -> Self {
        Move {
            from_sq,
            to_sq,
            promotion: 0,
            is_castling: true,
            is_en_passant: false,
        }
    }

    /// Create an en passant move
    pub fn en_passant(from_sq: usize, to_sq: usize) -> Self {
        Move {
            from_sq,
            to_sq,
            promotion: 0,
            is_castling: false,
            is_en_passant: true,
        }
    }

    /// Convert move to UCI notation (e.g., "e2e4", "e7e8q")
    pub fn to_uci(&self) -> String {
        let mut uci = format!("{}{}", square_name(self.from_sq), square_name(self.to_sq));
        if self.promotion != 0 {
            let promo_char = match self.promotion {
                QUEEN => 'q',
                ROOK => 'r',
                BISHOP => 'b',
                KNIGHT => 'n',
                _ => return uci,
            };
            uci.push(promo_char);
        }
        uci
    }

    /// Null move constant
    pub fn null() -> Self {
        Move::new(0, 0)
    }

    /// Check if this is a null move
    pub fn is_null(&self) -> bool {
        self.from_sq == 0 && self.to_sq == 0 && self.promotion == 0
    }
}

impl Default for Move {
    fn default() -> Self {
        Move::null()
    }
}

/// Information needed to undo a move
#[derive(Clone, Copy, Debug)]
pub struct UndoInfo {
    pub captured_piece: u8,
    pub castling_rights: u8,
    pub en_passant_square: i8,
    pub halfmove_clock: u16,
    pub moved_piece: u8,
}

/// Chess board representation
#[derive(Clone)]
pub struct Board {
    /// 64-element array representing the board (0=a1, 1=b1, ..., 63=h8)
    pub squares: [u8; 64],
    /// True if it's white's turn
    pub white_to_move: bool,
    /// Bitmask for castling rights (1=K, 2=Q, 4=k, 8=q)
    pub castling_rights: u8,
    /// Target square for en passant (-1 if none)
    pub en_passant_square: i8,
    /// Moves since last pawn move or capture (for 50-move rule)
    pub halfmove_clock: u16,
    /// Full move counter
    pub fullmove_number: u16,
    /// Position history for repetition detection
    pub position_history: Vec<u64>,
}

impl Board {
    /// Create a new board with the starting position
    pub fn new() -> Self {
        Board::from_fen(STARTING_FEN).unwrap()
    }

    /// Create a board from a FEN string
    pub fn from_fen(fen: &str) -> Option<Self> {
        let parts: Vec<&str> = fen.split_whitespace().collect();
        if parts.is_empty() {
            return None;
        }

        let mut board = Board {
            squares: [EMPTY; 64],
            white_to_move: true,
            castling_rights: 0,
            en_passant_square: -1,
            halfmove_clock: 0,
            fullmove_number: 1,
            position_history: Vec::new(),
        };

        // Parse piece placement
        let mut rank = 7i8;
        let mut file = 0i8;
        
        for c in parts[0].chars() {
            if c == '/' {
                rank -= 1;
                file = 0;
            } else if c.is_ascii_digit() {
                file += c.to_digit(10).unwrap() as i8;
            } else if let Some(piece) = fen_to_piece(c) {
                let sq = (rank * 8 + file) as usize;
                if sq < 64 {
                    board.squares[sq] = piece;
                }
                file += 1;
            }
        }

        // Parse active color
        if parts.len() > 1 {
            board.white_to_move = parts[1] != "b";
        }

        // Parse castling rights
        if parts.len() > 2 && parts[2] != "-" {
            for c in parts[2].chars() {
                match c {
                    'K' => board.castling_rights |= CASTLE_WK,
                    'Q' => board.castling_rights |= CASTLE_WQ,
                    'k' => board.castling_rights |= CASTLE_BK,
                    'q' => board.castling_rights |= CASTLE_BQ,
                    _ => {}
                }
            }
        }

        // Parse en passant square
        if parts.len() > 3 && parts[3] != "-" {
            if let Some(sq) = parse_square(parts[3]) {
                board.en_passant_square = sq as i8;
            }
        }

        // Parse halfmove clock
        if parts.len() > 4 {
            board.halfmove_clock = parts[4].parse().unwrap_or(0);
        }

        // Parse fullmove number
        if parts.len() > 5 {
            board.fullmove_number = parts[5].parse().unwrap_or(1);
        }

        // Initialize position history
        board.position_history.push(board.compute_hash());

        Some(board)
    }

    /// Generate FEN string from current board state
    pub fn to_fen(&self) -> String {
        let mut fen = String::new();

        // Piece placement
        for rank in (0..8).rev() {
            let mut empty_count = 0;
            for file in 0..8 {
                let piece = self.squares[rank * 8 + file];
                if piece == EMPTY {
                    empty_count += 1;
                } else {
                    if empty_count > 0 {
                        fen.push_str(&empty_count.to_string());
                        empty_count = 0;
                    }
                    if let Some(c) = piece_to_fen(piece) {
                        fen.push(c);
                    }
                }
            }
            if empty_count > 0 {
                fen.push_str(&empty_count.to_string());
            }
            if rank > 0 {
                fen.push('/');
            }
        }

        // Active color
        fen.push(' ');
        fen.push(if self.white_to_move { 'w' } else { 'b' });

        // Castling rights
        fen.push(' ');
        if self.castling_rights == 0 {
            fen.push('-');
        } else {
            if self.castling_rights & CASTLE_WK != 0 { fen.push('K'); }
            if self.castling_rights & CASTLE_WQ != 0 { fen.push('Q'); }
            if self.castling_rights & CASTLE_BK != 0 { fen.push('k'); }
            if self.castling_rights & CASTLE_BQ != 0 { fen.push('q'); }
        }

        // En passant
        fen.push(' ');
        if self.en_passant_square >= 0 {
            fen.push_str(&square_name(self.en_passant_square as usize));
        } else {
            fen.push('-');
        }

        // Halfmove clock and fullmove number
        fen.push_str(&format!(" {} {}", self.halfmove_clock, self.fullmove_number));

        fen
    }

    /// Compute a hash of the current position for repetition detection
    fn compute_hash(&self) -> u64 {
        let mut hasher = DefaultHasher::new();
        self.squares.hash(&mut hasher);
        self.white_to_move.hash(&mut hasher);
        self.castling_rights.hash(&mut hasher);
        self.en_passant_square.hash(&mut hasher);
        hasher.finish()
    }

    /// Execute a move on the board. Returns UndoInfo for undoing the move later.
    pub fn make_move(&mut self, mv: &Move) -> UndoInfo {
        let from_sq = mv.from_sq;
        let to_sq = mv.to_sq;
        let piece = self.squares[from_sq];
        let captured = self.squares[to_sq];

        // Save undo information
        let undo = UndoInfo {
            captured_piece: if mv.is_en_passant {
                if self.white_to_move { BLACK_PAWN } else { WHITE_PAWN }
            } else {
                captured
            },
            castling_rights: self.castling_rights,
            en_passant_square: self.en_passant_square,
            halfmove_clock: self.halfmove_clock,
            moved_piece: piece,
        };

        // Update halfmove clock
        let piece_type = get_piece_type(piece);
        if piece_type == PAWN || captured != EMPTY {
            self.halfmove_clock = 0;
        } else {
            self.halfmove_clock += 1;
        }

        // Handle en passant capture
        if mv.is_en_passant {
            if self.white_to_move {
                self.squares[to_sq - 8] = EMPTY;
            } else {
                self.squares[to_sq + 8] = EMPTY;
            }
        }

        // Handle castling
        if mv.is_castling {
            match to_sq {
                6 => {  // White kingside (g1)
                    self.squares[7] = EMPTY;
                    self.squares[5] = WHITE_ROOK;
                }
                2 => {  // White queenside (c1)
                    self.squares[0] = EMPTY;
                    self.squares[3] = WHITE_ROOK;
                }
                62 => { // Black kingside (g8)
                    self.squares[63] = EMPTY;
                    self.squares[61] = BLACK_ROOK;
                }
                58 => { // Black queenside (c8)
                    self.squares[56] = EMPTY;
                    self.squares[59] = BLACK_ROOK;
                }
                _ => {}
            }
        }

        // Move the piece
        self.squares[to_sq] = piece;
        self.squares[from_sq] = EMPTY;

        // Handle promotion
        if mv.promotion != 0 {
            self.squares[to_sq] = (if self.white_to_move { WHITE } else { BLACK }) | mv.promotion;
        }

        // Update castling rights
        if piece_type == KING {
            if self.white_to_move {
                self.castling_rights &= !(CASTLE_WK | CASTLE_WQ);
            } else {
                self.castling_rights &= !(CASTLE_BK | CASTLE_BQ);
            }
        }

        // If rook moves or is captured
        if from_sq == 0 || to_sq == 0 { self.castling_rights &= !CASTLE_WQ; }
        if from_sq == 7 || to_sq == 7 { self.castling_rights &= !CASTLE_WK; }
        if from_sq == 56 || to_sq == 56 { self.castling_rights &= !CASTLE_BQ; }
        if from_sq == 63 || to_sq == 63 { self.castling_rights &= !CASTLE_BK; }

        // Update en passant square
        self.en_passant_square = -1;
        if piece_type == PAWN {
            let diff = (to_sq as i32) - (from_sq as i32);
            if diff.abs() == 16 {
                self.en_passant_square = ((from_sq as i32 + to_sq as i32) / 2) as i8;
            }
        }

        // Update fullmove number
        if !self.white_to_move {
            self.fullmove_number += 1;
        }

        // Switch side to move
        self.white_to_move = !self.white_to_move;

        // Update position history
        self.position_history.push(self.compute_hash());

        undo
    }

    /// Undo a move using saved UndoInfo
    pub fn unmake_move(&mut self, mv: &Move, undo: &UndoInfo) {
        // Switch side back
        self.white_to_move = !self.white_to_move;

        let from_sq = mv.from_sq;
        let to_sq = mv.to_sq;

        // Restore the moved piece
        self.squares[from_sq] = undo.moved_piece;

        // Restore captured piece
        if mv.is_en_passant {
            self.squares[to_sq] = EMPTY;
            if self.white_to_move {
                self.squares[to_sq - 8] = BLACK_PAWN;
            } else {
                self.squares[to_sq + 8] = WHITE_PAWN;
            }
        } else {
            self.squares[to_sq] = undo.captured_piece;
        }

        // Handle castling - move rook back
        if mv.is_castling {
            match to_sq {
                6 => {  // White kingside
                    self.squares[5] = EMPTY;
                    self.squares[7] = WHITE_ROOK;
                }
                2 => {  // White queenside
                    self.squares[3] = EMPTY;
                    self.squares[0] = WHITE_ROOK;
                }
                62 => { // Black kingside
                    self.squares[61] = EMPTY;
                    self.squares[63] = BLACK_ROOK;
                }
                58 => { // Black queenside
                    self.squares[59] = EMPTY;
                    self.squares[56] = BLACK_ROOK;
                }
                _ => {}
            }
        }

        // Restore game state
        self.castling_rights = undo.castling_rights;
        self.en_passant_square = undo.en_passant_square;
        self.halfmove_clock = undo.halfmove_clock;

        // Update fullmove number
        if !self.white_to_move {
            self.fullmove_number -= 1;
        }

        // Remove last position from history
        self.position_history.pop();
    }

    /// Find the king's square for the specified color
    pub fn find_king(&self, white: bool) -> Option<usize> {
        let king = if white { WHITE_KING } else { BLACK_KING };
        for sq in 0..64 {
            if self.squares[sq] == king {
                return Some(sq);
            }
        }
        None
    }

    /// Count how many times the current position has occurred
    pub fn repetition_count(&self) -> usize {
        if self.position_history.is_empty() {
            return 1;
        }
        let current_hash = *self.position_history.last().unwrap();
        self.position_history.iter().filter(|&&h| h == current_hash).count()
    }

    /// Check if current position has occurred 3 times (draw by repetition)
    pub fn is_repetition(&self) -> bool {
        if self.position_history.len() < 5 {
            return false;
        }
        self.repetition_count() >= 3
    }

    /// Check if 50-move rule applies (draw)
    pub fn is_fifty_moves(&self) -> bool {
        self.halfmove_clock >= 100
    }

    /// Check for insufficient material to checkmate
    pub fn has_insufficient_material(&self) -> bool {
        let mut pieces: Vec<(u8, u8, usize)> = Vec::new();
        
        for sq in 0..64 {
            let piece = self.squares[sq];
            if piece != EMPTY {
                pieces.push((get_piece_type(piece), get_piece_color(piece), sq));
            }
        }

        // Only kings left
        if pieces.len() == 2 {
            return true;
        }

        // King and minor piece vs King
        if pieces.len() == 3 {
            for (ptype, _, _) in &pieces {
                if *ptype == KNIGHT || *ptype == BISHOP {
                    return true;
                }
            }
        }

        // King + Bishop vs King + Bishop (same color squares)
        if pieces.len() == 4 {
            let bishops: Vec<(usize, u8)> = pieces.iter()
                .filter(|(pt, _, _)| *pt == BISHOP)
                .map(|(_, c, sq)| (*sq, *c))
                .collect();
            
            if bishops.len() == 2 {
                let (sq1, c1) = bishops[0];
                let (sq2, c2) = bishops[1];
                let sq1_color = (sq1 / 8 + sq1 % 8) % 2;
                let sq2_color = (sq2 / 8 + sq2 % 8) % 2;
                if sq1_color == sq2_color && c1 != c2 {
                    return true;
                }
            }
        }

        false
    }

    /// Create a copy of the board
    pub fn copy(&self) -> Self {
        self.clone()
    }

    /// Display the board as a string
    pub fn display(&self) -> String {
        let mut lines = Vec::new();
        lines.push("  +---+---+---+---+---+---+---+---+".to_string());
        
        for rank in (0..8).rev() {
            let mut row = format!("{} |", rank + 1);
            for file in 0..8 {
                let piece = self.squares[rank * 8 + file];
                if piece == EMPTY {
                    row.push_str("   |");
                } else if let Some(c) = piece_to_fen(piece) {
                    row.push_str(&format!(" {} |", c));
                } else {
                    row.push_str(" ? |");
                }
            }
            lines.push(row);
            lines.push("  +---+---+---+---+---+---+---+---+".to_string());
        }
        lines.push("    a   b   c   d   e   f   g   h".to_string());
        
        lines.join("\n")
    }
}

impl Default for Board {
    fn default() -> Self {
        Board::new()
    }
}

impl std::fmt::Display for Board {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.display())
    }
}
