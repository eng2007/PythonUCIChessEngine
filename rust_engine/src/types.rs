//! OpusChess - Type definitions and constants
//!
//! This module provides the core type definitions and constants for
//! representing chess pieces, colors, and basic operations.

/// Piece type constants (lower 3 bits)
pub const EMPTY: u8 = 0;
pub const PAWN: u8 = 1;
pub const KNIGHT: u8 = 2;
pub const BISHOP: u8 = 3;
pub const ROOK: u8 = 4;
pub const QUEEN: u8 = 5;
pub const KING: u8 = 6;

/// Color constants (bits 3-4)
pub const WHITE: u8 = 8;
pub const BLACK: u8 = 16;

/// Piece masks
pub const PIECE_MASK: u8 = 0b111;
pub const COLOR_MASK: u8 = 0b11000;

/// Complete piece values for convenience
pub const WHITE_PAWN: u8 = WHITE | PAWN;
pub const WHITE_KNIGHT: u8 = WHITE | KNIGHT;
pub const WHITE_BISHOP: u8 = WHITE | BISHOP;
pub const WHITE_ROOK: u8 = WHITE | ROOK;
pub const WHITE_QUEEN: u8 = WHITE | QUEEN;
pub const WHITE_KING: u8 = WHITE | KING;

pub const BLACK_PAWN: u8 = BLACK | PAWN;
pub const BLACK_KNIGHT: u8 = BLACK | KNIGHT;
pub const BLACK_BISHOP: u8 = BLACK | BISHOP;
pub const BLACK_ROOK: u8 = BLACK | ROOK;
pub const BLACK_QUEEN: u8 = BLACK | QUEEN;
pub const BLACK_KING: u8 = BLACK | KING;

/// Castling rights bitmasks
pub const CASTLE_WK: u8 = 1;  // White kingside
pub const CASTLE_WQ: u8 = 2;  // White queenside  
pub const CASTLE_BK: u8 = 4;  // Black kingside
pub const CASTLE_BQ: u8 = 8;  // Black queenside

/// File and rank names for UCI notation
pub const FILE_NAMES: &[u8; 8] = b"abcdefgh";
pub const RANK_NAMES: &[u8; 8] = b"12345678";

/// Extract piece type from piece value
#[inline]
pub fn get_piece_type(piece: u8) -> u8 {
    piece & PIECE_MASK
}

/// Extract color from piece value
#[inline]
pub fn get_piece_color(piece: u8) -> u8 {
    piece & COLOR_MASK
}

/// Check if piece is white
#[inline]
pub fn is_white(piece: u8) -> bool {
    (piece & COLOR_MASK) == WHITE
}

/// Check if piece is black
#[inline]
pub fn is_black(piece: u8) -> bool {
    (piece & COLOR_MASK) == BLACK
}

/// Convert square index (0-63) to algebraic notation (e.g., "e4")
pub fn square_name(sq: usize) -> String {
    let file = (sq % 8) as u8;
    let rank = (sq / 8) as u8;
    format!("{}{}", FILE_NAMES[file as usize] as char, RANK_NAMES[rank as usize] as char)
}

/// Convert algebraic notation to square index
pub fn parse_square(name: &str) -> Option<usize> {
    let chars: Vec<char> = name.chars().collect();
    if chars.len() < 2 {
        return None;
    }
    
    let file = match chars[0] {
        'a'..='h' => (chars[0] as usize) - ('a' as usize),
        _ => return None,
    };
    
    let rank = match chars[1] {
        '1'..='8' => (chars[1] as usize) - ('1' as usize),
        _ => return None,
    };
    
    Some(rank * 8 + file)
}

/// FEN piece character to piece value
pub fn fen_to_piece(c: char) -> Option<u8> {
    match c {
        'P' => Some(WHITE_PAWN),
        'N' => Some(WHITE_KNIGHT),
        'B' => Some(WHITE_BISHOP),
        'R' => Some(WHITE_ROOK),
        'Q' => Some(WHITE_QUEEN),
        'K' => Some(WHITE_KING),
        'p' => Some(BLACK_PAWN),
        'n' => Some(BLACK_KNIGHT),
        'b' => Some(BLACK_BISHOP),
        'r' => Some(BLACK_ROOK),
        'q' => Some(BLACK_QUEEN),
        'k' => Some(BLACK_KING),
        _ => None,
    }
}

/// Piece value to FEN character
pub fn piece_to_fen(piece: u8) -> Option<char> {
    match piece {
        WHITE_PAWN => Some('P'),
        WHITE_KNIGHT => Some('N'),
        WHITE_BISHOP => Some('B'),
        WHITE_ROOK => Some('R'),
        WHITE_QUEEN => Some('Q'),
        WHITE_KING => Some('K'),
        BLACK_PAWN => Some('p'),
        BLACK_KNIGHT => Some('n'),
        BLACK_BISHOP => Some('b'),
        BLACK_ROOK => Some('r'),
        BLACK_QUEEN => Some('q'),
        BLACK_KING => Some('k'),
        _ => None,
    }
}
