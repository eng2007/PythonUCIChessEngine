//! OpusChess - UCI Chess Engine
//!
//! A chess engine written in Rust with support for:
//! - Full FIDE chess rules
//! - UCI protocol
//! - Minimax search with alpha-beta pruning
//! - Transposition table with Zobrist hashing
//! - Advanced pruning techniques (NMP, LMR, etc.)
//!
//! Usage:
//!     opus_chess
//!
//! The engine reads UCI commands from stdin and writes responses to stdout.
//! Compatible with any UCI chess GUI (Arena, CuteChess, etc.)

use opus_chess::uci::UCIProtocol;

fn main() {
    let mut uci = UCIProtocol::new();
    uci.run();
}
