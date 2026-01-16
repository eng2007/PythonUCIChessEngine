//! OpusChess - Position Evaluation Module
//!
//! This module provides static evaluation of chess positions considering:
//! - Material balance
//! - Piece positioning (piece-square tables)
//! - Pawn structure (doubled, isolated, passed pawns)
//! - King safety
//! - Piece mobility
//! - Bishop pair bonus

use crate::types::*;
use crate::board::Board;

// ============================================================================
// PIECE VALUES
// ============================================================================

pub const PIECE_VALUES: [i32; 7] = [
    0,      // EMPTY
    100,    // PAWN
    320,    // KNIGHT
    330,    // BISHOP
    500,    // ROOK
    900,    // QUEEN
    20000,  // KING
];

// ============================================================================
// PIECE-SQUARE TABLES
// ============================================================================

// Pawn PST - encourages central control and advancement
const PAWN_PST: [i32; 64] = [
    0,   0,   0,   0,   0,   0,   0,   0,   // Rank 1
    5,  10,  10, -20, -20,  10,  10,   5,   // Rank 2
    5,  -5, -10,   0,   0, -10,  -5,   5,   // Rank 3
    0,   0,   0,  20,  20,   0,   0,   0,   // Rank 4
    5,   5,  10,  25,  25,  10,   5,   5,   // Rank 5
   10,  10,  20,  30,  30,  20,  10,  10,   // Rank 6
   50,  50,  50,  50,  50,  50,  50,  50,   // Rank 7
    0,   0,   0,   0,   0,   0,   0,   0,   // Rank 8
];

// Knight PST - encourages central positioning
const KNIGHT_PST: [i32; 64] = [
   -50, -40, -30, -30, -30, -30, -40, -50,
   -40, -20,   0,   5,   5,   0, -20, -40,
   -30,   5,  10,  15,  15,  10,   5, -30,
   -30,   0,  15,  20,  20,  15,   0, -30,
   -30,   5,  15,  20,  20,  15,   5, -30,
   -30,   0,  10,  15,  15,  10,   0, -30,
   -40, -20,   0,   0,   0,   0, -20, -40,
   -50, -40, -30, -30, -30, -30, -40, -50,
];

// Bishop PST
const BISHOP_PST: [i32; 64] = [
   -20, -10, -10, -10, -10, -10, -10, -20,
   -10,   5,   0,   0,   0,   0,   5, -10,
   -10,  10,  10,  10,  10,  10,  10, -10,
   -10,   0,  10,  10,  10,  10,   0, -10,
   -10,   5,   5,  10,  10,   5,   5, -10,
   -10,   0,   5,  10,  10,   5,   0, -10,
   -10,   0,   0,   0,   0,   0,   0, -10,
   -20, -10, -10, -10, -10, -10, -10, -20,
];

// Rook PST
const ROOK_PST: [i32; 64] = [
    0,   0,   0,   5,   5,   0,   0,   0,
   -5,   0,   0,   0,   0,   0,   0,  -5,
   -5,   0,   0,   0,   0,   0,   0,  -5,
   -5,   0,   0,   0,   0,   0,   0,  -5,
   -5,   0,   0,   0,   0,   0,   0,  -5,
   -5,   0,   0,   0,   0,   0,   0,  -5,
    5,  10,  10,  10,  10,  10,  10,   5,
    0,   0,   0,   0,   0,   0,   0,   0,
];

// Queen PST
const QUEEN_PST: [i32; 64] = [
   -20, -10, -10,  -5,  -5, -10, -10, -20,
   -10,   0,   5,   0,   0,   0,   0, -10,
   -10,   5,   5,   5,   5,   5,   0, -10,
     0,   0,   5,   5,   5,   5,   0,  -5,
    -5,   0,   5,   5,   5,   5,   0,  -5,
   -10,   0,   5,   5,   5,   5,   0, -10,
   -10,   0,   0,   0,   0,   0,   0, -10,
   -20, -10, -10,  -5,  -5, -10, -10, -20,
];

// King middlegame PST
const KING_MIDDLEGAME_PST: [i32; 64] = [
    20,  30,  10,   0,   0,  10,  30,  20,
    20,  20,   0,   0,   0,   0,  20,  20,
   -10, -20, -20, -20, -20, -20, -20, -10,
   -20, -30, -30, -40, -40, -30, -30, -20,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
];

// King endgame PST
const KING_ENDGAME_PST: [i32; 64] = [
   -50, -30, -30, -30, -30, -30, -30, -50,
   -30, -30,   0,   0,   0,   0, -30, -30,
   -30, -10,  20,  30,  30,  20, -10, -30,
   -30, -10,  30,  40,  40,  30, -10, -30,
   -30, -10,  30,  40,  40,  30, -10, -30,
   -30, -10,  20,  30,  30,  20, -10, -30,
   -30, -20, -10,   0,   0, -10, -20, -30,
   -50, -40, -30, -20, -20, -30, -40, -50,
];

// ============================================================================
// EVALUATION BONUSES/PENALTIES
// ============================================================================

const DOUBLED_PAWN_PENALTY: i32 = -15;
const ISOLATED_PAWN_PENALTY: i32 = -20;
const PASSED_PAWN_BONUS: [i32; 8] = [0, 10, 20, 35, 60, 100, 150, 0];
const PAWN_CHAIN_BONUS: i32 = 5;

const BISHOP_PAIR_BONUS: i32 = 50;
const ROOK_ON_OPEN_FILE_BONUS: i32 = 25;
const ROOK_ON_SEMI_OPEN_FILE_BONUS: i32 = 15;
const ROOK_ON_7TH_RANK_BONUS: i32 = 30;

const KNIGHT_MOBILITY_BONUS: i32 = 4;
const BISHOP_MOBILITY_BONUS: i32 = 5;
const ROOK_MOBILITY_BONUS: i32 = 3;
const QUEEN_MOBILITY_BONUS: i32 = 2;

const CENTER_SQUARES: [usize; 4] = [27, 28, 35, 36];
const CENTER_PAWN_BONUS: i32 = 15;

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/// Get piece-square table value for a piece
fn get_pst_value(piece_type: u8, sq: usize, is_white: bool, is_endgame: bool) -> i32 {
    let pst = match piece_type {
        PAWN => &PAWN_PST,
        KNIGHT => &KNIGHT_PST,
        BISHOP => &BISHOP_PST,
        ROOK => &ROOK_PST,
        QUEEN => &QUEEN_PST,
        KING => if is_endgame { &KING_ENDGAME_PST } else { &KING_MIDDLEGAME_PST },
        _ => return 0,
    };

    let index = if is_white {
        sq
    } else {
        let rank = sq / 8;
        let file = sq % 8;
        (7 - rank) * 8 + file
    };

    pst[index]
}

/// Count material for both sides (excluding kings)
fn count_material(board: &Board) -> (i32, i32) {
    let mut white_material = 0;
    let mut black_material = 0;

    for sq in 0..64 {
        let piece = board.squares[sq];
        if piece == EMPTY {
            continue;
        }

        let piece_type = get_piece_type(piece);
        if piece_type == KING {
            continue;
        }

        let value = PIECE_VALUES[piece_type as usize];

        if get_piece_color(piece) == WHITE {
            white_material += value;
        } else {
            black_material += value;
        }
    }

    (white_material, black_material)
}

/// Determine if the position is an endgame
fn is_endgame(board: &Board) -> bool {
    let (white_material, black_material) = count_material(board);
    white_material <= 1300 && black_material <= 1300
}

/// Get pawn positions for each color
fn get_pawn_positions(board: &Board) -> (Vec<usize>, Vec<usize>) {
    let mut white_pawns = Vec::new();
    let mut black_pawns = Vec::new();

    for sq in 0..64 {
        let piece = board.squares[sq];
        if piece == WHITE_PAWN {
            white_pawns.push(sq);
        } else if piece == BLACK_PAWN {
            black_pawns.push(sq);
        }
    }

    (white_pawns, black_pawns)
}

/// Evaluate pawn structure
fn evaluate_pawn_structure(board: &Board, white_pawns: &[usize], black_pawns: &[usize]) -> i32 {
    let mut score = 0;

    // Count pawns per file for each side
    let mut white_files = [0u8; 8];
    let mut black_files = [0u8; 8];

    for &sq in white_pawns {
        white_files[sq % 8] += 1;
    }
    for &sq in black_pawns {
        black_files[sq % 8] += 1;
    }

    // Evaluate white pawns
    for &sq in white_pawns {
        let file = sq % 8;
        let rank = sq / 8;

        // Doubled pawns
        if white_files[file] > 1 {
            score += DOUBLED_PAWN_PENALTY;
        }

        // Isolated pawns
        let has_neighbor = (file > 0 && white_files[file - 1] > 0) 
                        || (file < 7 && white_files[file + 1] > 0);
        if !has_neighbor {
            score += ISOLATED_PAWN_PENALTY;
        }

        // Passed pawns
        let mut is_passed = true;
        for check_file in file.saturating_sub(1)..=(file + 1).min(7) {
            for check_rank in (rank + 1)..8 {
                let check_sq = check_rank * 8 + check_file;
                if board.squares[check_sq] == BLACK_PAWN {
                    is_passed = false;
                    break;
                }
            }
            if !is_passed { break; }
        }
        if is_passed {
            score += PASSED_PAWN_BONUS[rank];
        }

        // Pawn chain
        if sq >= 9 {
            let defender1 = sq - 9;
            let defender2 = sq - 7;
            if (file > 0 && board.squares[defender1] == WHITE_PAWN) 
               || (file < 7 && board.squares[defender2] == WHITE_PAWN) {
                score += PAWN_CHAIN_BONUS;
            }
        }
    }

    // Evaluate black pawns (mirror the logic)
    for &sq in black_pawns {
        let file = sq % 8;
        let rank = sq / 8;

        // Doubled pawns
        if black_files[file] > 1 {
            score -= DOUBLED_PAWN_PENALTY;
        }

        // Isolated pawns
        let has_neighbor = (file > 0 && black_files[file - 1] > 0) 
                        || (file < 7 && black_files[file + 1] > 0);
        if !has_neighbor {
            score -= ISOLATED_PAWN_PENALTY;
        }

        // Passed pawns
        let mut is_passed = true;
        for check_file in file.saturating_sub(1)..=(file + 1).min(7) {
            for check_rank in 0..rank {
                let check_sq = check_rank * 8 + check_file;
                if board.squares[check_sq] == WHITE_PAWN {
                    is_passed = false;
                    break;
                }
            }
            if !is_passed { break; }
        }
        if is_passed {
            score -= PASSED_PAWN_BONUS[7 - rank];
        }

        // Pawn chain
        if sq <= 54 {
            let defender1 = sq + 9;
            let defender2 = sq + 7;
            if (file < 7 && defender1 < 64 && board.squares[defender1] == BLACK_PAWN) 
               || (file > 0 && board.squares[defender2] == BLACK_PAWN) {
                score -= PAWN_CHAIN_BONUS;
            }
        }
    }

    score
}

/// Evaluate piece activity
fn evaluate_pieces(board: &Board, white_pawns: &[usize], black_pawns: &[usize]) -> i32 {
    let mut score = 0;
    let mut white_bishops = 0;
    let mut black_bishops = 0;

    let white_pawn_files: Vec<usize> = white_pawns.iter().map(|&sq| sq % 8).collect();
    let black_pawn_files: Vec<usize> = black_pawns.iter().map(|&sq| sq % 8).collect();

    for sq in 0..64 {
        let piece = board.squares[sq];
        if piece == EMPTY {
            continue;
        }

        let piece_type = get_piece_type(piece);
        let is_white = get_piece_color(piece) == WHITE;
        let file = sq % 8;
        let rank = sq / 8;

        if piece_type == BISHOP {
            if is_white { white_bishops += 1; } else { black_bishops += 1; }
        } else if piece_type == ROOK {
            if is_white {
                // Rook on open file
                if !white_pawn_files.contains(&file) && !black_pawn_files.contains(&file) {
                    score += ROOK_ON_OPEN_FILE_BONUS;
                } else if !white_pawn_files.contains(&file) {
                    score += ROOK_ON_SEMI_OPEN_FILE_BONUS;
                }
                // Rook on 7th rank
                if rank == 6 {
                    score += ROOK_ON_7TH_RANK_BONUS;
                }
            } else {
                if !white_pawn_files.contains(&file) && !black_pawn_files.contains(&file) {
                    score -= ROOK_ON_OPEN_FILE_BONUS;
                } else if !black_pawn_files.contains(&file) {
                    score -= ROOK_ON_SEMI_OPEN_FILE_BONUS;
                }
                if rank == 1 {
                    score -= ROOK_ON_7TH_RANK_BONUS;
                }
            }
        }
    }

    // Bishop pair
    if white_bishops >= 2 { score += BISHOP_PAIR_BONUS; }
    if black_bishops >= 2 { score -= BISHOP_PAIR_BONUS; }

    score
}

/// Count mobility for a piece (simplified)
fn count_mobility(board: &Board, sq: usize, piece_type: u8, is_white: bool) -> i32 {
    let mut moves = 0i32;
    let file = sq % 8;
    let color = if is_white { WHITE } else { BLACK };

    const KNIGHT_OFFSETS: [i32; 8] = [17, 15, 10, 6, -6, -10, -15, -17];
    const BISHOP_DIRS: [i32; 4] = [7, 9, -7, -9];
    const ROOK_DIRS: [i32; 4] = [8, -8, 1, -1];
    const QUEEN_DIRS: [i32; 8] = [8, -8, 1, -1, 7, 9, -7, -9];

    match piece_type {
        KNIGHT => {
            for &offset in &KNIGHT_OFFSETS {
                let to_sq_i32 = sq as i32 + offset;
                if to_sq_i32 < 0 || to_sq_i32 >= 64 { continue; }
                let to_sq = to_sq_i32 as usize;
                if (to_sq % 8).abs_diff(file) > 2 { continue; }
                let target = board.squares[to_sq];
                if target == EMPTY || get_piece_color(target) != color {
                    moves += 1;
                }
            }
        }
        BISHOP => {
            for &d in &BISHOP_DIRS {
                let mut current = sq;
                loop {
                    let curr_file = current % 8;
                    let next_sq_i32 = current as i32 + d;
                    if next_sq_i32 < 0 || next_sq_i32 >= 64 { break; }
                    let next_sq = next_sq_i32 as usize;
                    if (next_sq % 8).abs_diff(curr_file) != 1 { break; }
                    let target = board.squares[next_sq];
                    if target == EMPTY {
                        moves += 1;
                        current = next_sq;
                    } else {
                        if get_piece_color(target) != color { moves += 1; }
                        break;
                    }
                }
            }
        }
        ROOK => {
            for &d in &ROOK_DIRS {
                let mut current = sq;
                loop {
                    let curr_file = current % 8;
                    let next_sq_i32 = current as i32 + d;
                    if next_sq_i32 < 0 || next_sq_i32 >= 64 { break; }
                    let next_sq = next_sq_i32 as usize;
                    if (d == 1 || d == -1) && (next_sq % 8).abs_diff(curr_file) != 1 { break; }
                    let target = board.squares[next_sq];
                    if target == EMPTY {
                        moves += 1;
                        current = next_sq;
                    } else {
                        if get_piece_color(target) != color { moves += 1; }
                        break;
                    }
                }
            }
        }
        QUEEN => {
            for &d in &QUEEN_DIRS {
                let mut current = sq;
                loop {
                    let curr_file = current % 8;
                    let next_sq_i32 = current as i32 + d;
                    if next_sq_i32 < 0 || next_sq_i32 >= 64 { break; }
                    let next_sq = next_sq_i32 as usize;
                    if (d == 1 || d == -1 || d == 7 || d == -9 || d == 9 || d == -7) 
                       && (next_sq % 8).abs_diff(curr_file) != 1 { break; }
                    let target = board.squares[next_sq];
                    if target == EMPTY {
                        moves += 1;
                        current = next_sq;
                    } else {
                        if get_piece_color(target) != color { moves += 1; }
                        break;
                    }
                }
            }
        }
        _ => {}
    }

    moves
}

/// Evaluate piece mobility
fn evaluate_mobility(board: &Board) -> i32 {
    let mut score = 0;

    for sq in 0..64 {
        let piece = board.squares[sq];
        if piece == EMPTY { continue; }

        let piece_type = get_piece_type(piece);
        let is_white = get_piece_color(piece) == WHITE;

        let bonus_per_move = match piece_type {
            KNIGHT => KNIGHT_MOBILITY_BONUS,
            BISHOP => BISHOP_MOBILITY_BONUS,
            ROOK => ROOK_MOBILITY_BONUS,
            QUEEN => QUEEN_MOBILITY_BONUS,
            _ => continue,
        };

        let moves = count_mobility(board, sq, piece_type, is_white);
        let bonus = moves * bonus_per_move;

        if is_white { score += bonus; } else { score -= bonus; }
    }

    score
}

/// Evaluate center control
fn evaluate_center_control(board: &Board) -> i32 {
    let mut score = 0;

    for &sq in &CENTER_SQUARES {
        let piece = board.squares[sq];
        if piece != EMPTY && get_piece_type(piece) == PAWN {
            if get_piece_color(piece) == WHITE {
                score += CENTER_PAWN_BONUS;
            } else {
                score -= CENTER_PAWN_BONUS;
            }
        }
    }

    score
}

// ============================================================================
// MAIN EVALUATION FUNCTION
// ============================================================================

/// Evaluate the position from white's perspective (positive = white is better)
pub fn evaluate(board: &Board) -> i32 {
    let mut score = 0;
    let endgame = is_endgame(board);
    let (white_pawns, black_pawns) = get_pawn_positions(board);

    // Material and piece-square tables
    for sq in 0..64 {
        let piece = board.squares[sq];
        if piece == EMPTY { continue; }

        let piece_type = get_piece_type(piece);
        let is_white = get_piece_color(piece) == WHITE;

        let material_value = PIECE_VALUES[piece_type as usize];
        let pst_value = get_pst_value(piece_type, sq, is_white, endgame);

        if is_white {
            score += material_value + pst_value;
        } else {
            score -= material_value + pst_value;
        }
    }

    // Pawn structure
    score += evaluate_pawn_structure(board, &white_pawns, &black_pawns);

    // Piece activity
    score += evaluate_pieces(board, &white_pawns, &black_pawns);

    // Mobility
    score += evaluate_mobility(board);

    // Center control
    score += evaluate_center_control(board);

    // Return score from the perspective of the side to move
    if board.white_to_move { score } else { -score }
}

/// Evaluate a move for move ordering (captures, promotions)
pub fn evaluate_move(board: &Board, mv: &crate::board::Move) -> i32 {
    let mut score = 0;

    // Captures - MVV-LVA (Most Valuable Victim - Least Valuable Attacker)
    let victim = board.squares[mv.to_sq];
    if victim != EMPTY {
        let victim_value = PIECE_VALUES[get_piece_type(victim) as usize];
        let attacker = board.squares[mv.from_sq];
        let attacker_value = PIECE_VALUES[get_piece_type(attacker) as usize];
        score += 10 * victim_value - attacker_value;
    }

    // Promotions
    if mv.promotion != 0 {
        score += PIECE_VALUES[mv.promotion as usize];
    }

    score
}
