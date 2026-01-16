//! OpusChess - Search Engine Module
//!
//! This module implements the chess search algorithm using:
//! - Minimax with alpha-beta pruning
//! - Transposition table with Zobrist hashing
//! - Null Move Pruning (NMP)
//! - Late Move Reductions (LMR)
//! - Aspiration Windows
//! - Futility Pruning
//! - Check Extensions
//! - Killer/History heuristics

use crate::types::*;
use crate::board::{Board, Move};
use crate::move_generator::MoveGenerator;
use crate::evaluation::{evaluate, evaluate_move, PIECE_VALUES};
use rand::prelude::*;
use std::collections::HashMap;

// Constants for search
pub const INFINITY: i32 = 100000;
pub const MATE_SCORE: i32 = 50000;
const MAX_DEPTH: usize = 100;

// Transposition table entry types
const TT_EXACT: u8 = 0;
const TT_ALPHA: u8 = 1;
const TT_BETA: u8 = 2;

// Null Move Pruning
const NULL_MOVE_REDUCTION: i32 = 2;

// Late Move Reductions
const LMR_FULL_DEPTH_MOVES: usize = 4;
const LMR_REDUCTION_LIMIT: i32 = 3;

// Aspiration Windows
const ASPIRATION_WINDOW: i32 = 50;

// Futility Pruning margins
const FUTILITY_MARGIN: [i32; 4] = [0, 200, 300, 500];

// Check Extension
const CHECK_EXTENSION: i32 = 1;

// Contempt - penalty for accepting draws
const CONTEMPT: i32 = 25;

// ============================================================================
// ZOBRIST HASHING
// ============================================================================

pub struct ZobristHash {
    piece_keys: [[u64; 64]; 32],
    side_key: u64,
    castling_keys: [u64; 16],
    ep_keys: [u64; 9],
}

impl ZobristHash {
    pub fn new() -> Self {
        let mut rng = StdRng::seed_from_u64(12345);
        
        let mut piece_keys = [[0u64; 64]; 32];
        for piece in 0..32 {
            for sq in 0..64 {
                piece_keys[piece][sq] = rng.gen();
            }
        }
        
        let side_key = rng.gen();
        
        let mut castling_keys = [0u64; 16];
        for i in 0..16 {
            castling_keys[i] = rng.gen();
        }
        
        let mut ep_keys = [0u64; 9];
        for i in 0..9 {
            ep_keys[i] = rng.gen();
        }
        
        ZobristHash { piece_keys, side_key, castling_keys, ep_keys }
    }
    
    pub fn hash_position(&self, board: &Board) -> u64 {
        let mut h = 0u64;
        
        for sq in 0..64 {
            let piece = board.squares[sq];
            if piece != EMPTY {
                h ^= self.piece_keys[piece as usize][sq];
            }
        }
        
        if !board.white_to_move {
            h ^= self.side_key;
        }
        
        h ^= self.castling_keys[board.castling_rights as usize];
        
        let ep_idx = if board.en_passant_square >= 0 {
            (board.en_passant_square as usize) % 8
        } else {
            8
        };
        h ^= self.ep_keys[ep_idx];
        
        h
    }
}

impl Default for ZobristHash {
    fn default() -> Self {
        ZobristHash::new()
    }
}

// ============================================================================
// TRANSPOSITION TABLE
// ============================================================================

#[derive(Clone)]
struct TTEntry {
    hash_key: u64,
    depth: i32,
    score: i32,
    flag: u8,
    best_move: Option<Move>,
}

pub struct TranspositionTable {
    table: HashMap<u64, TTEntry>,
    size: usize,
    mask: u64,
    pub hits: u64,
    pub writes: u64,
}

impl TranspositionTable {
    pub fn new(size_mb: usize) -> Self {
        let num_entries = (size_mb * 1024 * 1024) / 50;
        let mut size = 1usize;
        while size * 2 <= num_entries {
            size *= 2;
        }
        let mask = (size - 1) as u64;
        
        TranspositionTable {
            table: HashMap::with_capacity(size),
            size,
            mask,
            hits: 0,
            writes: 0,
        }
    }
    
    fn probe(&mut self, hash_key: u64) -> Option<&TTEntry> {
        let entry = self.table.get(&(hash_key & self.mask));
        if let Some(e) = entry {
            if e.hash_key == hash_key {
                self.hits += 1;
                return Some(e);
            }
        }
        None
    }
    
    fn store(&mut self, hash_key: u64, depth: i32, score: i32, flag: u8, best_move: Option<Move>) {
        let index = hash_key & self.mask;
        let should_replace = match self.table.get(&index) {
            None => true,
            Some(existing) => depth >= existing.depth || hash_key == existing.hash_key,
        };
        
        if should_replace {
            self.table.insert(index, TTEntry { hash_key, depth, score, flag, best_move });
            self.writes += 1;
        }
    }
    
    pub fn clear(&mut self) {
        self.table.clear();
        self.hits = 0;
        self.writes = 0;
    }
    
    pub fn hashfull(&self) -> usize {
        if self.size == 0 { return 0; }
        ((self.writes as usize * 1000) / self.size).min(1000)
    }
}

// ============================================================================
// SEARCH ENGINE
// ============================================================================

pub struct SearchEngine {
    move_generator: MoveGenerator,
    pub nodes_searched: u64,
    pub best_move: Option<Move>,
    max_depth: i32,
    pub stop_search: bool,
    
    // Transposition table
    tt: TranspositionTable,
    zobrist: ZobristHash,
    
    // Killer moves (2 per ply)
    killer_moves: [[Option<Move>; 2]; MAX_DEPTH],
    
    // History heuristic
    history: [[i32; 64]; 32],
    
    // Configurable options
    pub use_tt: bool,
    pub use_null_move: bool,
    pub use_lmr: bool,
    
    // Statistics
    tt_cutoffs: u64,
    null_move_cutoffs: u64,
    futility_prunes: u64,
    
    // PV
    pub pv: Vec<Move>,
    search_start_time: std::time::Instant,
}

impl SearchEngine {
    pub fn new(tt_size_mb: usize) -> Self {
        SearchEngine {
            move_generator: MoveGenerator::new(),
            nodes_searched: 0,
            best_move: None,
            max_depth: 4,
            stop_search: false,
            tt: TranspositionTable::new(tt_size_mb),
            zobrist: ZobristHash::new(),
            killer_moves: [[None; 2]; MAX_DEPTH],
            history: [[0; 64]; 32],
            use_tt: true,
            use_null_move: true,
            use_lmr: true,
            tt_cutoffs: 0,
            null_move_cutoffs: 0,
            futility_prunes: 0,
            pv: Vec::new(),
            search_start_time: std::time::Instant::now(),
        }
    }
    
    /// Search with aspiration windows
    pub fn search<F>(&mut self, board: &Board, depth: i32, mut info_callback: Option<F>) 
        -> (Option<Move>, i32)
    where F: FnMut(i32, i32, u64, u64, &str, usize, u64)
    {
        self.nodes_searched = 0;
        self.best_move = None;
        self.max_depth = depth;
        self.stop_search = false;
        self.tt_cutoffs = 0;
        self.null_move_cutoffs = 0;
        self.futility_prunes = 0;
        self.pv.clear();
        self.search_start_time = std::time::Instant::now();
        self.killer_moves = [[None; 2]; MAX_DEPTH];
        
        let position_hash = self.zobrist.hash_position(board);
        
        let mut best_move = None;
        let mut best_score = -INFINITY;
        
        // Initial search at depth 1
        let mut temp_board = board.clone();
        let score = self.alphabeta(&mut temp_board, 1, -INFINITY, INFINITY, 0, true, position_hash, true);
        if self.best_move.is_some() {
            best_move = self.best_move;
            best_score = score;
            self.extract_pv(board, position_hash, 1);
            if let Some(ref mut cb) = info_callback {
                self.report_info(1, score, cb);
            }
        }
        
        // Iterative deepening with aspiration windows
        for current_depth in 2..=depth {
            if self.stop_search {
                break;
            }
            
            let mut alpha = best_score - ASPIRATION_WINDOW;
            let mut beta = best_score + ASPIRATION_WINDOW;
            
            loop {
                let mut temp_board = board.clone();
                let score = self.alphabeta(&mut temp_board, current_depth, alpha, beta, 
                                          0, true, position_hash, true);
                
                if self.stop_search {
                    break;
                }
                
                if score <= alpha {
                    alpha = -INFINITY;
                } else if score >= beta {
                    beta = INFINITY;
                } else {
                    break;
                }
            }
            
            if !self.stop_search && self.best_move.is_some() {
                best_move = self.best_move;
                best_score = self.alphabeta(&mut board.clone(), current_depth, -INFINITY, INFINITY, 
                                           0, true, position_hash, true);
                self.extract_pv(board, position_hash, current_depth);
                if let Some(ref mut cb) = info_callback {
                    self.report_info(current_depth, best_score, cb);
                }
            }
        }
        
        (best_move, best_score)
    }
    
    fn extract_pv(&mut self, board: &Board, position_hash: u64, depth: i32) {
        self.pv.clear();
        
        if !self.use_tt {
            if let Some(mv) = self.best_move {
                self.pv.push(mv);
            }
            return;
        }
        
        let mut seen_hashes = std::collections::HashSet::new();
        let mut current_hash = position_hash;
        let mut temp_board = board.clone();
        
        for _ in 0..depth.min(20) {
            if seen_hashes.contains(&current_hash) {
                break;
            }
            seen_hashes.insert(current_hash);
            
            let entry = self.tt.table.get(&(current_hash & self.tt.mask)).cloned();
            if let Some(e) = entry {
                if e.hash_key == current_hash {
                    if let Some(mv) = e.best_move {
                        self.pv.push(mv);
                        temp_board.make_move(&mv);
                        current_hash = self.zobrist.hash_position(&temp_board);
                    } else {
                        break;
                    }
                } else {
                    break;
                }
            } else {
                break;
            }
        }
    }
    
    fn report_info<F>(&self, depth: i32, score: i32, callback: &mut F)
    where F: FnMut(i32, i32, u64, u64, &str, usize, u64)
    {
        let elapsed = self.search_start_time.elapsed();
        let time_ms = elapsed.as_millis() as u64;
        let nps = if time_ms > 0 { (self.nodes_searched * 1000) / time_ms } else { 0 };
        let hashfull = self.tt.hashfull();
        
        let pv_str: String = self.pv.iter()
            .map(|m| m.to_uci())
            .collect::<Vec<_>>()
            .join(" ");
        
        callback(depth, score, self.nodes_searched, time_ms, &pv_str, hashfull, nps);
    }
    
    fn alphabeta(&mut self, board: &mut Board, depth: i32, mut alpha: i32, beta: i32,
                 ply: usize, is_root: bool, position_hash: u64, allow_null: bool) -> i32 {
        if self.stop_search {
            return 0;
        }
        
        self.nodes_searched += 1;
        let original_alpha = alpha;
        
        // Draw detection
        if !is_root {
            if board.is_fifty_moves() || board.is_repetition() {
                return -CONTEMPT;
            }
            if board.has_insufficient_material() {
                return -CONTEMPT;
            }
            if board.repetition_count() >= 2 {
                return -CONTEMPT * 2;
            }
        }
        
        // Probe TT
        let mut tt_move: Option<Move> = None;
        
        if self.use_tt {
            if let Some(entry) = self.tt.probe(position_hash) {
                if !is_root && entry.depth >= depth {
                    match entry.flag {
                        TT_EXACT => {
                            self.tt_cutoffs += 1;
                            return entry.score;
                        }
                        TT_ALPHA if entry.score <= alpha => {
                            self.tt_cutoffs += 1;
                            return alpha;
                        }
                        TT_BETA if entry.score >= beta => {
                            self.tt_cutoffs += 1;
                            return beta;
                        }
                        _ => {}
                    }
                }
                tt_move = entry.best_move;
            }
        }
        
        // Check detection
        let in_check = self.move_generator.is_in_check(board);
        
        // Check extension
        let extended_depth = if in_check { depth + CHECK_EXTENSION } else { depth };
        
        // Generate moves
        let moves = self.move_generator.generate_legal_moves(board);
        
        // Checkmate / Stalemate
        if moves.is_empty() {
            return if in_check { -MATE_SCORE + ply as i32 } else { 0 };
        }
        
        // Quiescence at leaf
        if extended_depth <= 0 {
            return self.quiescence(board, alpha, beta);
        }
        
        // Static evaluation for pruning
        let static_eval = if extended_depth <= 4 && !in_check && alpha.abs() < MATE_SCORE - 100 {
            Some(evaluate(board))
        } else {
            None
        };
        
        // Null Move Pruning
        if self.use_null_move && allow_null && !is_root && !in_check 
           && extended_depth >= 3 && self.has_big_pieces(board) {
            
            board.white_to_move = !board.white_to_move;
            let null_hash = position_hash ^ self.zobrist.side_key;
            
            let null_score = -self.alphabeta(
                board, extended_depth - 1 - NULL_MOVE_REDUCTION,
                -beta, -beta + 1, ply + 1, false, null_hash, false
            );
            
            board.white_to_move = !board.white_to_move;
            
            if null_score >= beta {
                self.null_move_cutoffs += 1;
                return beta;
            }
        }
        
        // Order moves
        let ordered_moves = self.order_moves(board, moves, tt_move, ply);
        
        let mut best_score = -INFINITY;
        let mut best_move_at_node: Option<Move> = None;
        let mut moves_searched = 0;
        
        for mv in ordered_moves {
            if self.stop_search {
                break;
            }
            
            let is_capture = board.squares[mv.to_sq] != EMPTY || mv.is_en_passant;
            let is_quiet = !is_capture && mv.promotion == 0;
            
            // Futility Pruning
            if let Some(se) = static_eval {
                if moves_searched > 0 && extended_depth <= 3 && !in_check && is_quiet {
                    let futility_value = se + FUTILITY_MARGIN[extended_depth as usize];
                    if futility_value <= alpha {
                        self.futility_prunes += 1;
                        moves_searched += 1;
                        continue;
                    }
                }
            }
            
            // Make move
            let undo = board.make_move(&mv);
            
            let new_hash = self.zobrist.hash_position(board);
            
            // Late Move Reductions
            let mut score;
            if self.use_lmr && moves_searched >= LMR_FULL_DEPTH_MOVES 
               && extended_depth >= LMR_REDUCTION_LIMIT && is_quiet && !in_check {
                
                // Reduced depth search
                let reduction = 1 + (moves_searched as i32 / 6);
                let reduced_depth = (extended_depth - 1 - reduction).max(1);
                
                score = -self.alphabeta(board, reduced_depth, -alpha - 1, -alpha, 
                                        ply + 1, false, new_hash, true);
                
                // Re-search at full depth if it looks promising
                if score > alpha {
                    score = -self.alphabeta(board, extended_depth - 1, -beta, -alpha, 
                                           ply + 1, false, new_hash, true);
                }
            } else if moves_searched > 0 {
                // PVS: Search with null window first
                score = -self.alphabeta(board, extended_depth - 1, -alpha - 1, -alpha, 
                                        ply + 1, false, new_hash, true);
                
                if score > alpha && score < beta {
                    score = -self.alphabeta(board, extended_depth - 1, -beta, -alpha, 
                                           ply + 1, false, new_hash, true);
                }
            } else {
                // Full window search for first move
                score = -self.alphabeta(board, extended_depth - 1, -beta, -alpha, 
                                        ply + 1, false, new_hash, true);
            }
            
            // Unmake move
            board.unmake_move(&mv, &undo);
            
            if score > best_score {
                best_score = score;
                best_move_at_node = Some(mv);
                
                if is_root {
                    self.best_move = Some(mv);
                }
            }
            
            if score > alpha {
                alpha = score;
            }
            
            if alpha >= beta {
                // Store killer move
                if is_quiet && ply < MAX_DEPTH {
                    self.killer_moves[ply][1] = self.killer_moves[ply][0];
                    self.killer_moves[ply][0] = Some(mv);
                    
                    // Update history
                    let piece = undo.moved_piece as usize;
                    self.history[piece][mv.to_sq] += extended_depth * extended_depth;
                }
                break;
            }
            
            moves_searched += 1;
        }
        
        // Store in TT
        if self.use_tt && !self.stop_search {
            let flag = if best_score <= original_alpha {
                TT_ALPHA
            } else if best_score >= beta {
                TT_BETA
            } else {
                TT_EXACT
            };
            
            self.tt.store(position_hash, extended_depth, best_score, flag, best_move_at_node);
        }
        
        best_score
    }
    
    fn quiescence(&mut self, board: &mut Board, mut alpha: i32, beta: i32) -> i32 {
        self.nodes_searched += 1;
        
        let stand_pat = evaluate(board);
        
        if stand_pat >= beta {
            return beta;
        }
        
        if stand_pat > alpha {
            alpha = stand_pat;
        }
        
        let moves = self.move_generator.generate_legal_moves(board);
        
        // Only search captures
        let mut captures: Vec<Move> = moves.into_iter()
            .filter(|m| board.squares[m.to_sq] != EMPTY || m.is_en_passant || m.promotion != 0)
            .collect();
        
        // Order captures by MVV-LVA
        captures.sort_by_key(|m| -evaluate_move(board, m));
        
        for mv in captures {
            if self.stop_search {
                break;
            }
            
            let undo = board.make_move(&mv);
            let score = -self.quiescence(board, -beta, -alpha);
            board.unmake_move(&mv, &undo);
            
            if score >= beta {
                return beta;
            }
            if score > alpha {
                alpha = score;
            }
        }
        
        alpha
    }
    
    fn order_moves(&self, board: &Board, moves: Vec<Move>, tt_move: Option<Move>, ply: usize) -> Vec<Move> {
        let mut scored_moves: Vec<(Move, i32)> = moves.into_iter().map(|m| {
            let mut score = 0i32;
            
            // TT move gets highest priority
            if Some(m) == tt_move {
                score += 10000000;
            }
            
            // Captures
            let victim = board.squares[m.to_sq];
            if victim != EMPTY {
                let victim_value = PIECE_VALUES[get_piece_type(victim) as usize];
                let attacker = board.squares[m.from_sq];
                let attacker_value = PIECE_VALUES[get_piece_type(attacker) as usize];
                score += 1000000 + 10 * victim_value - attacker_value;
            }
            
            // Promotions
            if m.promotion != 0 {
                score += 900000 + PIECE_VALUES[m.promotion as usize];
            }
            
            // Killer moves
            if ply < MAX_DEPTH {
                if Some(m) == self.killer_moves[ply][0] {
                    score += 800000;
                } else if Some(m) == self.killer_moves[ply][1] {
                    score += 700000;
                }
            }
            
            // History heuristic
            let piece = board.squares[m.from_sq] as usize;
            if piece < 32 {
                score += self.history[piece][m.to_sq];
            }
            
            (m, score)
        }).collect();
        
        scored_moves.sort_by(|a, b| b.1.cmp(&a.1));
        scored_moves.into_iter().map(|(m, _)| m).collect()
    }
    
    fn has_big_pieces(&self, board: &Board) -> bool {
        let color = if board.white_to_move { WHITE } else { BLACK };
        
        for sq in 0..64 {
            let piece = board.squares[sq];
            if piece != EMPTY && get_piece_color(piece) == color {
                let pt = get_piece_type(piece);
                if pt == KNIGHT || pt == BISHOP || pt == ROOK || pt == QUEEN {
                    return true;
                }
            }
        }
        false
    }
    
    pub fn stop(&mut self) {
        self.stop_search = true;
    }
    
    pub fn clear_tt(&mut self) {
        self.tt.clear();
    }
}

impl Default for SearchEngine {
    fn default() -> Self {
        SearchEngine::new(64)
    }
}
