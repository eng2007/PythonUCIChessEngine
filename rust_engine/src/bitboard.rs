//! OpusChess - Bitboard Module
//!
//! This module provides bitboard utilities for fast move generation.
//! A bitboard is a 64-bit integer where each bit represents a square on the board.

// ============================================================================
// CONSTANTS - Files and Ranks
// ============================================================================

pub const FILE_A: u64 = 0x0101010101010101;
pub const FILE_B: u64 = 0x0202020202020202;
pub const FILE_C: u64 = 0x0404040404040404;
pub const FILE_D: u64 = 0x0808080808080808;
pub const FILE_E: u64 = 0x1010101010101010;
pub const FILE_F: u64 = 0x2020202020202020;
pub const FILE_G: u64 = 0x4040404040404040;
pub const FILE_H: u64 = 0x8080808080808080;

pub const RANK_1: u64 = 0x00000000000000FF;
pub const RANK_2: u64 = 0x000000000000FF00;
pub const RANK_3: u64 = 0x0000000000FF0000;
pub const RANK_4: u64 = 0x00000000FF000000;
pub const RANK_5: u64 = 0x000000FF00000000;
pub const RANK_6: u64 = 0x0000FF0000000000;
pub const RANK_7: u64 = 0x00FF000000000000;
pub const RANK_8: u64 = 0xFF00000000000000;

pub const NOT_FILE_A: u64 = !FILE_A;
pub const NOT_FILE_H: u64 = !FILE_H;
pub const NOT_FILE_AB: u64 = !(FILE_A | FILE_B);
pub const NOT_FILE_GH: u64 = !(FILE_G | FILE_H);

// ============================================================================
// PRECOMPUTED ATTACK TABLES
// ============================================================================

/// Knight attack table - attacks from each square
pub static KNIGHT_ATTACKS: [u64; 64] = init_knight_attacks();

/// King attack table - attacks from each square  
pub static KING_ATTACKS: [u64; 64] = init_king_attacks();

/// Pawn attack table - [color][square] where 0=white, 1=black
pub static PAWN_ATTACKS: [[u64; 64]; 2] = init_pawn_attacks();

// ============================================================================
// INITIALIZATION FUNCTIONS (const)
// ============================================================================

const fn init_knight_attacks() -> [u64; 64] {
    let mut attacks = [0u64; 64];
    let mut sq = 0usize;
    
    while sq < 64 {
        let bb = 1u64 << sq;
        let mut attack = 0u64;
        
        // NNE: +17 (up 2, right 1)
        if bb & NOT_FILE_H != 0 {
            attack |= bb << 17;
        }
        // NNW: +15 (up 2, left 1)
        if bb & NOT_FILE_A != 0 {
            attack |= bb << 15;
        }
        // NEE: +10 (up 1, right 2)
        if bb & NOT_FILE_GH != 0 {
            attack |= bb << 10;
        }
        // NWW: +6 (up 1, left 2)
        if bb & NOT_FILE_AB != 0 {
            attack |= bb << 6;
        }
        // SSE: -15 (down 2, right 1)
        if bb & NOT_FILE_H != 0 && sq >= 15 {
            attack |= bb >> 15;
        }
        // SSW: -17 (down 2, left 1)
        if bb & NOT_FILE_A != 0 && sq >= 17 {
            attack |= bb >> 17;
        }
        // SEE: -6 (down 1, right 2)
        if bb & NOT_FILE_GH != 0 && sq >= 6 {
            attack |= bb >> 6;
        }
        // SWW: -10 (down 1, left 2)
        if bb & NOT_FILE_AB != 0 && sq >= 10 {
            attack |= bb >> 10;
        }
        
        attacks[sq] = attack;
        sq += 1;
    }
    
    attacks
}

const fn init_king_attacks() -> [u64; 64] {
    let mut attacks = [0u64; 64];
    let mut sq = 0usize;
    
    while sq < 64 {
        let bb = 1u64 << sq;
        let mut attack = 0u64;
        
        // North
        attack |= bb << 8;
        // South
        if sq >= 8 {
            attack |= bb >> 8;
        }
        // East
        if bb & NOT_FILE_H != 0 {
            attack |= bb << 1;
        }
        // West
        if bb & NOT_FILE_A != 0 {
            attack |= bb >> 1;
        }
        // Northeast
        if bb & NOT_FILE_H != 0 {
            attack |= bb << 9;
        }
        // Northwest
        if bb & NOT_FILE_A != 0 {
            attack |= bb << 7;
        }
        // Southeast
        if bb & NOT_FILE_H != 0 && sq >= 7 {
            attack |= bb >> 7;
        }
        // Southwest
        if bb & NOT_FILE_A != 0 && sq >= 9 {
            attack |= bb >> 9;
        }
        
        attacks[sq] = attack;
        sq += 1;
    }
    
    attacks
}

const fn init_pawn_attacks() -> [[u64; 64]; 2] {
    let mut attacks = [[0u64; 64]; 2];
    let mut sq = 0usize;
    
    while sq < 64 {
        let bb = 1u64 << sq;
        
        // White pawn attacks (moving up)
        let mut white_attack = 0u64;
        if bb & NOT_FILE_A != 0 {
            white_attack |= bb << 7;  // Capture left
        }
        if bb & NOT_FILE_H != 0 {
            white_attack |= bb << 9;  // Capture right
        }
        attacks[0][sq] = white_attack;
        
        // Black pawn attacks (moving down)
        let mut black_attack = 0u64;
        if bb & NOT_FILE_H != 0 && sq >= 7 {
            black_attack |= bb >> 7;  // Capture right (from black's perspective)
        }
        if bb & NOT_FILE_A != 0 && sq >= 9 {
            black_attack |= bb >> 9;  // Capture left
        }
        attacks[1][sq] = black_attack;
        
        sq += 1;
    }
    
    attacks
}

// ============================================================================
// SLIDING PIECE ATTACKS (Runtime computation for now)
// ============================================================================

/// Get rook attacks from a square given occupied squares
#[inline]
pub fn rook_attacks(sq: usize, occupied: u64) -> u64 {
    let mut attacks = 0u64;
    
    // North
    let mut current = sq;
    while current < 56 {
        current += 8;
        attacks |= 1u64 << current;
        if (1u64 << current) & occupied != 0 {
            break;
        }
    }
    
    // South
    current = sq;
    while current >= 8 {
        current -= 8;
        attacks |= 1u64 << current;
        if (1u64 << current) & occupied != 0 {
            break;
        }
    }
    
    // East
    current = sq;
    while current % 8 < 7 {
        current += 1;
        attacks |= 1u64 << current;
        if (1u64 << current) & occupied != 0 {
            break;
        }
    }
    
    // West
    current = sq;
    while current % 8 > 0 {
        current -= 1;
        attacks |= 1u64 << current;
        if (1u64 << current) & occupied != 0 {
            break;
        }
    }
    
    attacks
}

/// Get bishop attacks from a square given occupied squares
#[inline]
pub fn bishop_attacks(sq: usize, occupied: u64) -> u64 {
    let mut attacks = 0u64;
    let file = sq % 8;
    let rank = sq / 8;
    
    // Northeast
    let mut f = file;
    let mut r = rank;
    while f < 7 && r < 7 {
        f += 1;
        r += 1;
        let target = r * 8 + f;
        attacks |= 1u64 << target;
        if (1u64 << target) & occupied != 0 {
            break;
        }
    }
    
    // Northwest
    f = file;
    r = rank;
    while f > 0 && r < 7 {
        f -= 1;
        r += 1;
        let target = r * 8 + f;
        attacks |= 1u64 << target;
        if (1u64 << target) & occupied != 0 {
            break;
        }
    }
    
    // Southeast
    f = file;
    r = rank;
    while f < 7 && r > 0 {
        f += 1;
        r -= 1;
        let target = r * 8 + f;
        attacks |= 1u64 << target;
        if (1u64 << target) & occupied != 0 {
            break;
        }
    }
    
    // Southwest
    f = file;
    r = rank;
    while f > 0 && r > 0 {
        f -= 1;
        r -= 1;
        let target = r * 8 + f;
        attacks |= 1u64 << target;
        if (1u64 << target) & occupied != 0 {
            break;
        }
    }
    
    attacks
}

/// Get queen attacks (combination of rook and bishop)
#[inline]
pub fn queen_attacks(sq: usize, occupied: u64) -> u64 {
    rook_attacks(sq, occupied) | bishop_attacks(sq, occupied)
}

// ============================================================================
// BITBOARD UTILITIES
// ============================================================================

/// Extract and clear the least significant bit, returning its index
#[inline]
pub fn pop_lsb(bb: &mut u64) -> usize {
    let idx = bb.trailing_zeros() as usize;
    *bb &= *bb - 1;
    idx
}

/// Count the number of set bits in a bitboard
#[inline]
pub fn popcount(bb: u64) -> u32 {
    bb.count_ones()
}

/// Get the index of the least significant bit
#[inline]
pub fn lsb(bb: u64) -> usize {
    bb.trailing_zeros() as usize
}

/// Get the index of the most significant bit
#[inline]
pub fn msb(bb: u64) -> usize {
    63 - bb.leading_zeros() as usize
}

/// Create a bitboard with a single bit set at the given square
#[inline]
pub const fn square_bb(sq: usize) -> u64 {
    1u64 << sq
}

/// Check if a bitboard has any bits set
#[inline]
pub const fn any(bb: u64) -> bool {
    bb != 0
}

/// Check if a bitboard is empty
#[inline]
pub const fn empty(bb: u64) -> bool {
    bb == 0
}

/// Get the file (0-7) of a square
#[inline]
pub const fn file_of(sq: usize) -> usize {
    sq & 7
}

/// Get the rank (0-7) of a square
#[inline]
pub const fn rank_of(sq: usize) -> usize {
    sq >> 3
}

/// Get the bitboard for a file (0-7)
#[inline]
pub const fn file_bb(file: usize) -> u64 {
    FILE_A << file
}

/// Get the bitboard for a rank (0-7)
#[inline]
pub const fn rank_bb(rank: usize) -> u64 {
    RANK_1 << (rank * 8)
}

/// Shift a bitboard north (up) by one rank
#[inline]
pub const fn shift_north(bb: u64) -> u64 {
    bb << 8
}

/// Shift a bitboard south (down) by one rank
#[inline]
pub const fn shift_south(bb: u64) -> u64 {
    bb >> 8
}

/// Shift a bitboard east (right) by one file
#[inline]
pub const fn shift_east(bb: u64) -> u64 {
    (bb << 1) & NOT_FILE_A
}

/// Shift a bitboard west (left) by one file
#[inline]
pub const fn shift_west(bb: u64) -> u64 {
    (bb >> 1) & NOT_FILE_H
}

// ============================================================================
// ATTACK DETECTION
// ============================================================================

/// Check if a square is attacked by any piece of the given color
pub fn is_square_attacked_bb(
    sq: usize,
    by_white: bool,
    pawns: u64,
    knights: u64,
    bishops: u64,
    rooks: u64,
    queens: u64,
    kings: u64,
    occupied: u64,
) -> bool {
    
    // Pawn attacks (check from attacker's perspective)
    let pawn_attack_mask = if by_white {
        PAWN_ATTACKS[1][sq]  // Black pawn attacks to find white attackers
    } else {
        PAWN_ATTACKS[0][sq]  // White pawn attacks to find black attackers
    };
    if pawn_attack_mask & pawns != 0 {
        return true;
    }
    
    // Knight attacks
    if KNIGHT_ATTACKS[sq] & knights != 0 {
        return true;
    }
    
    // King attacks
    if KING_ATTACKS[sq] & kings != 0 {
        return true;
    }
    
    // Bishop/Queen diagonal attacks
    let bishop_attacks = bishop_attacks(sq, occupied);
    if bishop_attacks & (bishops | queens) != 0 {
        return true;
    }
    
    // Rook/Queen straight attacks
    let rook_attacks = rook_attacks(sq, occupied);
    if rook_attacks & (rooks | queens) != 0 {
        return true;
    }
    
    false
}

/// Get all attackers to a square
pub fn attackers_to(sq: usize, occupied: u64, white_pieces: u64, black_pieces: u64,
                   pawns: u64, knights: u64, bishops: u64, rooks: u64, queens: u64, kings: u64) -> u64 {
    let mut attackers = 0u64;
    
    // Pawn attackers
    attackers |= PAWN_ATTACKS[1][sq] & pawns & white_pieces;  // White pawns
    attackers |= PAWN_ATTACKS[0][sq] & pawns & black_pieces;  // Black pawns
    
    // Knight attackers
    attackers |= KNIGHT_ATTACKS[sq] & knights;
    
    // King attackers
    attackers |= KING_ATTACKS[sq] & kings;
    
    // Sliding piece attackers
    attackers |= bishop_attacks(sq, occupied) & (bishops | queens);
    attackers |= rook_attacks(sq, occupied) & (rooks | queens);
    
    attackers
}

// ============================================================================
// DEBUG / DISPLAY
// ============================================================================

/// Print a bitboard in a human-readable format
pub fn print_bitboard(bb: u64) {
    println!();
    for rank in (0..8).rev() {
        print!("{}  ", rank + 1);
        for file in 0..8 {
            let sq = rank * 8 + file;
            if bb & (1u64 << sq) != 0 {
                print!("1 ");
            } else {
                print!(". ");
            }
        }
        println!();
    }
    println!("   a b c d e f g h");
    println!("   Bitboard: 0x{:016X}", bb);
}
