//! OpusChess - UCI Chess Engine
//!
//! A chess engine written in Rust with support for:
//! - Full FIDE chess rules
//! - UCI protocol
//! - Minimax search with alpha-beta pruning
//! - Transposition table with Zobrist hashing
//! - Advanced pruning techniques (NMP, LMR, etc.)
//! - Multi-threaded search (Lazy SMP)
//! - Bitboard representation for fast move generation

pub mod types;
pub mod bitboard;
pub mod board;
pub mod move_generator;
pub mod evaluation;
pub mod search;
pub mod parallel_search;
pub mod uci;

