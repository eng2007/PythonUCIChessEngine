//! OpusChess - Move Generator Module
//!
//! This module handles the generation of legal chess moves, including
//! all special moves (castling, en passant, pawn promotion).

use crate::types::*;
use crate::board::{Board, Move};

/// Direction offsets for sliding pieces
const ROOK_DIRECTIONS: [i32; 4] = [8, -8, -1, 1];
const BISHOP_DIRECTIONS: [i32; 4] = [7, 9, -7, -9];
const QUEEN_DIRECTIONS: [i32; 8] = [8, -8, -1, 1, 7, 9, -7, -9];
const KING_DIRECTIONS: [i32; 8] = [8, -8, -1, 1, 7, 9, -7, -9];
const KNIGHT_OFFSETS: [i32; 8] = [17, 15, 10, 6, -6, -10, -15, -17];

/// Move generator for chess positions
pub struct MoveGenerator;

impl MoveGenerator {
    /// Create a new move generator
    pub fn new() -> Self {
        MoveGenerator
    }

    /// Generate all legal moves for the current position
    pub fn generate_legal_moves(&self, board: &Board) -> Vec<Move> {
        let pseudo_legal = self.generate_pseudo_legal_moves(board);
        let mut legal_moves = Vec::with_capacity(pseudo_legal.len());

        for mv in pseudo_legal {
            if self.is_legal(board, &mv) {
                legal_moves.push(mv);
            }
        }

        legal_moves
    }

    /// Generate all pseudo-legal moves (may leave king in check)
    pub fn generate_pseudo_legal_moves(&self, board: &Board) -> Vec<Move> {
        let mut moves = Vec::with_capacity(64);
        let color = if board.white_to_move { WHITE } else { BLACK };

        for sq in 0..64 {
            let piece = board.squares[sq];
            if piece == EMPTY || get_piece_color(piece) != color {
                continue;
            }

            let piece_type = get_piece_type(piece);

            match piece_type {
                PAWN => self.generate_pawn_moves(board, sq, &mut moves),
                KNIGHT => self.generate_knight_moves(board, sq, &mut moves),
                BISHOP => self.generate_sliding_moves(board, sq, &BISHOP_DIRECTIONS, &mut moves),
                ROOK => self.generate_sliding_moves(board, sq, &ROOK_DIRECTIONS, &mut moves),
                QUEEN => self.generate_sliding_moves(board, sq, &QUEEN_DIRECTIONS, &mut moves),
                KING => self.generate_king_moves(board, sq, &mut moves),
                _ => {}
            }
        }

        moves
    }

    /// Generate pawn moves from the given square
    fn generate_pawn_moves(&self, board: &Board, sq: usize, moves: &mut Vec<Move>) {
        let color = get_piece_color(board.squares[sq]);
        let is_white_pawn = color == WHITE;

        let direction: i32 = if is_white_pawn { 8 } else { -8 };
        let start_rank = if is_white_pawn { 1 } else { 6 };
        let promo_rank = if is_white_pawn { 7 } else { 0 };

        let file = sq % 8;
        let rank = sq / 8;

        // Single push
        let to_sq = (sq as i32 + direction) as usize;
        if to_sq < 64 && board.squares[to_sq] == EMPTY {
            if to_sq / 8 == promo_rank {
                // Promotion
                for promo in [QUEEN, ROOK, BISHOP, KNIGHT] {
                    moves.push(Move::with_promotion(sq, to_sq, promo));
                }
            } else {
                moves.push(Move::new(sq, to_sq));

                // Double push from starting rank
                if rank == start_rank {
                    let to_sq2 = (sq as i32 + 2 * direction) as usize;
                    if to_sq2 < 64 && board.squares[to_sq2] == EMPTY {
                        moves.push(Move::new(sq, to_sq2));
                    }
                }
            }
        }

        // Captures
        let capture_offsets = [direction - 1, direction + 1];
        for offset in capture_offsets {
            let to_sq_i32 = sq as i32 + offset;
            if to_sq_i32 < 0 || to_sq_i32 >= 64 {
                continue;
            }
            let to_sq = to_sq_i32 as usize;
            let to_file = to_sq % 8;

            // Check if move wraps around the board
            if (to_file as i32 - file as i32).abs() != 1 {
                continue;
            }

            let target = board.squares[to_sq];

            // Regular capture
            if target != EMPTY && get_piece_color(target) != color {
                if to_sq / 8 == promo_rank {
                    for promo in [QUEEN, ROOK, BISHOP, KNIGHT] {
                        moves.push(Move::with_promotion(sq, to_sq, promo));
                    }
                } else {
                    moves.push(Move::new(sq, to_sq));
                }
            }

            // En passant capture
            if board.en_passant_square >= 0 && to_sq == board.en_passant_square as usize {
                moves.push(Move::en_passant(sq, to_sq));
            }
        }
    }

    /// Generate knight moves from the given square
    fn generate_knight_moves(&self, board: &Board, sq: usize, moves: &mut Vec<Move>) {
        let color = get_piece_color(board.squares[sq]);
        let file = sq % 8;
        let rank = sq / 8;

        for &offset in &KNIGHT_OFFSETS {
            let to_sq_i32 = sq as i32 + offset;
            if to_sq_i32 < 0 || to_sq_i32 >= 64 {
                continue;
            }
            let to_sq = to_sq_i32 as usize;
            let to_file = to_sq % 8;
            let to_rank = to_sq / 8;

            // Check for wraparound
            if (to_file as i32 - file as i32).abs() > 2 
               || (to_rank as i32 - rank as i32).abs() > 2 {
                continue;
            }

            let target = board.squares[to_sq];
            if target == EMPTY || get_piece_color(target) != color {
                moves.push(Move::new(sq, to_sq));
            }
        }
    }

    /// Generate moves for sliding pieces (bishop, rook, queen)
    fn generate_sliding_moves(&self, board: &Board, sq: usize, directions: &[i32], moves: &mut Vec<Move>) {
        let color = get_piece_color(board.squares[sq]);

        for &direction in directions {
            let mut current_sq = sq;
            loop {
                let current_file = current_sq % 8;
                let next_sq_i32 = current_sq as i32 + direction;

                if next_sq_i32 < 0 || next_sq_i32 >= 64 {
                    break;
                }
                let next_sq = next_sq_i32 as usize;
                let next_file = next_sq % 8;

                // Check for wraparound
                let file_diff = (next_file as i32 - current_file as i32).abs();
                if direction == -1 || direction == 1 {
                    if file_diff != 1 {
                        break;
                    }
                } else if direction == 7 || direction == -9 {
                    if next_file as i32 != current_file as i32 - 1 {
                        break;
                    }
                } else if direction == 9 || direction == -7 {
                    if next_file as i32 != current_file as i32 + 1 {
                        break;
                    }
                }

                let target = board.squares[next_sq];

                if target == EMPTY {
                    moves.push(Move::new(sq, next_sq));
                } else if get_piece_color(target) != color {
                    moves.push(Move::new(sq, next_sq));
                    break;
                } else {
                    break;
                }

                current_sq = next_sq;
            }
        }
    }

    /// Generate king moves from the given square, including castling
    fn generate_king_moves(&self, board: &Board, sq: usize, moves: &mut Vec<Move>) {
        let color = get_piece_color(board.squares[sq]);
        let file = sq % 8;

        // Normal king moves
        for &direction in &KING_DIRECTIONS {
            let to_sq_i32 = sq as i32 + direction;
            if to_sq_i32 < 0 || to_sq_i32 >= 64 {
                continue;
            }
            let to_sq = to_sq_i32 as usize;
            let to_file = to_sq % 8;

            // Check for wraparound
            if (to_file as i32 - file as i32).abs() > 1 {
                continue;
            }

            let target = board.squares[to_sq];
            if target == EMPTY || get_piece_color(target) != color {
                moves.push(Move::new(sq, to_sq));
            }
        }

        // Castling
        let is_white_king = color == WHITE;
        let enemy_is_white = !is_white_king;

        if !self.is_square_attacked(board, sq, enemy_is_white) {
            if is_white_king {
                // Kingside castling (O-O) - white
                if (board.castling_rights & CASTLE_WK) != 0
                    && board.squares[5] == EMPTY
                    && board.squares[6] == EMPTY
                    && !self.is_square_attacked(board, 5, false)
                    && !self.is_square_attacked(board, 6, false)
                {
                    moves.push(Move::castling(sq, 6));
                }

                // Queenside castling (O-O-O) - white
                if (board.castling_rights & CASTLE_WQ) != 0
                    && board.squares[1] == EMPTY
                    && board.squares[2] == EMPTY
                    && board.squares[3] == EMPTY
                    && !self.is_square_attacked(board, 2, false)
                    && !self.is_square_attacked(board, 3, false)
                {
                    moves.push(Move::castling(sq, 2));
                }
            } else {
                // Kingside castling (O-O) - black
                if (board.castling_rights & CASTLE_BK) != 0
                    && board.squares[61] == EMPTY
                    && board.squares[62] == EMPTY
                    && !self.is_square_attacked(board, 61, true)
                    && !self.is_square_attacked(board, 62, true)
                {
                    moves.push(Move::castling(sq, 62));
                }

                // Queenside castling (O-O-O) - black
                if (board.castling_rights & CASTLE_BQ) != 0
                    && board.squares[57] == EMPTY
                    && board.squares[58] == EMPTY
                    && board.squares[59] == EMPTY
                    && !self.is_square_attacked(board, 58, true)
                    && !self.is_square_attacked(board, 59, true)
                {
                    moves.push(Move::castling(sq, 58));
                }
            }
        }
    }

    /// Check if a square is attacked by the specified color
    pub fn is_square_attacked(&self, board: &Board, sq: usize, by_white: bool) -> bool {
        let attacker_color = if by_white { WHITE } else { BLACK };
        let file = sq % 8;
        let rank = sq / 8;

        // Check pawn attacks
        let pawn_direction: i32 = if by_white { -8 } else { 8 };
        let pawn_attackers = [sq as i32 + pawn_direction - 1, sq as i32 + pawn_direction + 1];
        for attacker_sq_i32 in pawn_attackers {
            if attacker_sq_i32 < 0 || attacker_sq_i32 >= 64 {
                continue;
            }
            let attacker_sq = attacker_sq_i32 as usize;
            let att_file = attacker_sq % 8;
            if (att_file as i32 - file as i32).abs() != 1 {
                continue;
            }
            let piece = board.squares[attacker_sq];
            if piece != EMPTY && get_piece_type(piece) == PAWN && get_piece_color(piece) == attacker_color {
                return true;
            }
        }

        // Check knight attacks
        for &offset in &KNIGHT_OFFSETS {
            let attacker_sq_i32 = sq as i32 + offset;
            if attacker_sq_i32 < 0 || attacker_sq_i32 >= 64 {
                continue;
            }
            let attacker_sq = attacker_sq_i32 as usize;
            let att_file = attacker_sq % 8;
            let att_rank = attacker_sq / 8;
            if (att_file as i32 - file as i32).abs() > 2 
               || (att_rank as i32 - rank as i32).abs() > 2 {
                continue;
            }
            let piece = board.squares[attacker_sq];
            if piece != EMPTY && get_piece_type(piece) == KNIGHT && get_piece_color(piece) == attacker_color {
                return true;
            }
        }

        // Check king attacks
        for &direction in &KING_DIRECTIONS {
            let attacker_sq_i32 = sq as i32 + direction;
            if attacker_sq_i32 < 0 || attacker_sq_i32 >= 64 {
                continue;
            }
            let attacker_sq = attacker_sq_i32 as usize;
            let att_file = attacker_sq % 8;
            if (att_file as i32 - file as i32).abs() > 1 {
                continue;
            }
            let piece = board.squares[attacker_sq];
            if piece != EMPTY && get_piece_type(piece) == KING && get_piece_color(piece) == attacker_color {
                return true;
            }
        }

        // Check sliding piece attacks (rook, queen)
        for &direction in &ROOK_DIRECTIONS {
            if self.check_sliding_attack(board, sq, direction, attacker_color, &[ROOK, QUEEN]) {
                return true;
            }
        }

        // Check sliding piece attacks (bishop, queen)
        for &direction in &BISHOP_DIRECTIONS {
            if self.check_sliding_attack(board, sq, direction, attacker_color, &[BISHOP, QUEEN]) {
                return true;
            }
        }

        false
    }

    /// Check if there's a sliding piece attacking along a direction
    fn check_sliding_attack(&self, board: &Board, sq: usize, direction: i32, 
                           attacker_color: u8, piece_types: &[u8]) -> bool {
        let mut current_sq = sq;

        loop {
            let current_file = current_sq % 8;
            let next_sq_i32 = current_sq as i32 + direction;

            if next_sq_i32 < 0 || next_sq_i32 >= 64 {
                break;
            }
            let next_sq = next_sq_i32 as usize;
            let next_file = next_sq % 8;

            // Check for wraparound
            if direction == -1 || direction == 1 {
                if (next_file as i32 - current_file as i32).abs() != 1 {
                    break;
                }
            } else if direction == 7 || direction == -9 {
                if next_file as i32 != current_file as i32 - 1 {
                    break;
                }
            } else if direction == 9 || direction == -7 {
                if next_file as i32 != current_file as i32 + 1 {
                    break;
                }
            }

            let piece = board.squares[next_sq];

            if piece != EMPTY {
                if get_piece_color(piece) == attacker_color {
                    let piece_type = get_piece_type(piece);
                    if piece_types.contains(&piece_type) {
                        return true;
                    }
                }
                break;
            }

            current_sq = next_sq;
        }

        false
    }

    /// Check if a move is legal (doesn't leave own king in check)
    fn is_legal(&self, board: &Board, mv: &Move) -> bool {
        let mut temp_board = board.clone();
        let undo = temp_board.make_move(mv);

        // Check if own king is in check after the move
        let king_sq = temp_board.find_king(!temp_board.white_to_move);
        let in_check = match king_sq {
            Some(sq) => self.is_square_attacked(&temp_board, sq, temp_board.white_to_move),
            None => true,
        };

        temp_board.unmake_move(mv, &undo);

        !in_check
    }

    /// Check if the current side's king is in check
    pub fn is_in_check(&self, board: &Board) -> bool {
        match board.find_king(board.white_to_move) {
            Some(king_sq) => self.is_square_attacked(board, king_sq, !board.white_to_move),
            None => false,
        }
    }

    /// Check if the current position is checkmate
    pub fn is_checkmate(&self, board: &Board) -> bool {
        if !self.is_in_check(board) {
            return false;
        }
        self.generate_legal_moves(board).is_empty()
    }

    /// Check if the current position is stalemate
    pub fn is_stalemate(&self, board: &Board) -> bool {
        if self.is_in_check(board) {
            return false;
        }
        self.generate_legal_moves(board).is_empty()
    }

    /// Check if the position is a draw
    pub fn is_draw(&self, board: &Board) -> bool {
        if self.is_stalemate(board) {
            return true;
        }
        if board.is_fifty_moves() {
            return true;
        }
        if board.is_repetition() {
            return true;
        }
        if board.has_insufficient_material() {
            return true;
        }
        false
    }
}

impl Default for MoveGenerator {
    fn default() -> Self {
        MoveGenerator::new()
    }
}
