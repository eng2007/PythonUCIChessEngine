//! OpusChess - Parallel Search Module (Lazy SMP)
//!
//! This module implements multi-threaded search using the Lazy SMP algorithm.
//! Each thread searches the same position independently with slightly different
//! parameters, sharing the transposition table.

use std::sync::{Arc, Mutex, atomic::{AtomicBool, AtomicU64, Ordering}};
use std::thread;
use std::collections::HashMap;

use crate::types::*;
use crate::board::{Board, Move};
use crate::move_generator::MoveGenerator;
use crate::evaluation::{evaluate, evaluate_move, PIECE_VALUES};
use crate::search::{INFINITY, MATE_SCORE, ZobristHash};

const MAX_DEPTH: usize = 100;
const TT_EXACT: u8 = 0;
const TT_ALPHA: u8 = 1;
const TT_BETA: u8 = 2;
const NULL_MOVE_REDUCTION: i32 = 2;
const LMR_FULL_DEPTH_MOVES: usize = 4;
const LMR_REDUCTION_LIMIT: i32 = 3;
const ASPIRATION_WINDOW: i32 = 50;
const FUTILITY_MARGIN: [i32; 4] = [0, 200, 300, 500];
const CHECK_EXTENSION: i32 = 1;
const CONTEMPT: i32 = 25;

/// Shared transposition table entry
#[derive(Clone)]
struct SharedTTEntry {
    hash_key: u64,
    depth: i32,
    score: i32,
    flag: u8,
    best_move: Option<Move>,
}

/// Thread-safe transposition table
pub struct SharedTranspositionTable {
    table: Mutex<HashMap<u64, SharedTTEntry>>,
    size: usize,
    mask: u64,
    hits: AtomicU64,
    writes: AtomicU64,
}

impl SharedTranspositionTable {
    pub fn new(size_mb: usize) -> Self {
        let num_entries = (size_mb * 1024 * 1024) / 50;
        let mut size = 1usize;
        while size * 2 <= num_entries {
            size *= 2;
        }
        let mask = (size - 1) as u64;

        SharedTranspositionTable {
            table: Mutex::new(HashMap::with_capacity(size)),
            size,
            mask,
            hits: AtomicU64::new(0),
            writes: AtomicU64::new(0),
        }
    }

    fn probe(&self, hash_key: u64) -> Option<SharedTTEntry> {
        let table = self.table.lock().unwrap();
        if let Some(entry) = table.get(&(hash_key & self.mask)) {
            if entry.hash_key == hash_key {
                self.hits.fetch_add(1, Ordering::Relaxed);
                return Some(entry.clone());
            }
        }
        None
    }

    fn store(&self, hash_key: u64, depth: i32, score: i32, flag: u8, best_move: Option<Move>) {
        let index = hash_key & self.mask;
        let mut table = self.table.lock().unwrap();
        
        let should_replace = match table.get(&index) {
            None => true,
            Some(existing) => depth >= existing.depth || hash_key == existing.hash_key,
        };

        if should_replace {
            table.insert(index, SharedTTEntry { hash_key, depth, score, flag, best_move });
            self.writes.fetch_add(1, Ordering::Relaxed);
        }
    }

    pub fn clear(&self) {
        self.table.lock().unwrap().clear();
        self.hits.store(0, Ordering::Relaxed);
        self.writes.store(0, Ordering::Relaxed);
    }

    pub fn hashfull(&self) -> usize {
        if self.size == 0 { return 0; }
        ((self.writes.load(Ordering::Relaxed) as usize * 1000) / self.size).min(1000)
    }
}

/// Worker thread search state
struct WorkerSearch {
    move_generator: MoveGenerator,
    zobrist: ZobristHash,
    nodes_searched: u64,
    best_move: Option<Move>,
    stop_search: Arc<AtomicBool>,
    tt: Arc<SharedTranspositionTable>,
    killer_moves: [[Option<Move>; 2]; MAX_DEPTH],
    history: [[i32; 64]; 32],
    use_tt: bool,
    use_null_move: bool,
    use_lmr: bool,
    thread_id: usize,
}

impl WorkerSearch {
    fn new(
        thread_id: usize,
        stop_search: Arc<AtomicBool>,
        tt: Arc<SharedTranspositionTable>,
        use_tt: bool,
        use_null_move: bool,
        use_lmr: bool,
    ) -> Self {
        WorkerSearch {
            move_generator: MoveGenerator::new(),
            zobrist: ZobristHash::new(),
            nodes_searched: 0,
            best_move: None,
            stop_search,
            tt,
            killer_moves: [[None; 2]; MAX_DEPTH],
            history: [[0; 64]; 32],
            use_tt,
            use_null_move,
            use_lmr,
            thread_id,
        }
    }

    fn search(&mut self, board: &Board, depth: i32) -> (Option<Move>, i32) {
        self.nodes_searched = 0;
        self.best_move = None;
        self.killer_moves = [[None; 2]; MAX_DEPTH];

        let position_hash = self.zobrist.hash_position(board);
        let mut best_move = None;
        let mut best_score = -INFINITY;

        // Add thread-specific depth variation for Lazy SMP
        let thread_depth_offset = if self.thread_id % 2 == 1 { 1 } else { 0 };

        // Initial search at depth 1
        let mut temp_board = board.clone();
        let score = self.alphabeta(&mut temp_board, 1, -INFINITY, INFINITY, 0, true, position_hash, true);
        if self.best_move.is_some() {
            best_move = self.best_move;
            best_score = score;
        }

        // Iterative deepening with aspiration windows
        for current_depth in 2..=depth {
            if self.stop_search.load(Ordering::Relaxed) {
                break;
            }

            // Lazy SMP: threads search with slightly different depths
            let effective_depth = current_depth + thread_depth_offset;

            let mut alpha = best_score - ASPIRATION_WINDOW;
            let mut beta = best_score + ASPIRATION_WINDOW;

            loop {
                let mut temp_board = board.clone();
                let score = self.alphabeta(
                    &mut temp_board, effective_depth, alpha, beta,
                    0, true, position_hash, true
                );

                if self.stop_search.load(Ordering::Relaxed) {
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

            if !self.stop_search.load(Ordering::Relaxed) && self.best_move.is_some() {
                best_move = self.best_move;
                best_score = self.alphabeta(
                    &mut board.clone(), effective_depth, -INFINITY, INFINITY,
                    0, true, position_hash, true
                );
            }
        }

        (best_move, best_score)
    }

    fn alphabeta(
        &mut self, board: &mut Board, depth: i32, mut alpha: i32, beta: i32,
        ply: usize, is_root: bool, position_hash: u64, allow_null: bool
    ) -> i32 {
        if self.stop_search.load(Ordering::Relaxed) {
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
                        TT_EXACT => return entry.score,
                        TT_ALPHA if entry.score <= alpha => return alpha,
                        TT_BETA if entry.score >= beta => return beta,
                        _ => {}
                    }
                }
                tt_move = entry.best_move;
            }
        }

        // Check detection
        let in_check = self.move_generator.is_in_check(board);
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
                return beta;
            }
        }

        // Order moves
        let ordered_moves = self.order_moves(board, moves, tt_move, ply);

        let mut best_score = -INFINITY;
        let mut best_move_at_node: Option<Move> = None;
        let mut moves_searched = 0;

        for mv in ordered_moves {
            if self.stop_search.load(Ordering::Relaxed) {
                break;
            }

            let is_capture = board.squares[mv.to_sq] != EMPTY || mv.is_en_passant;
            let is_quiet = !is_capture && mv.promotion == 0;

            // Futility Pruning
            if let Some(se) = static_eval {
                if moves_searched > 0 && extended_depth <= 3 && !in_check && is_quiet {
                    let futility_value = se + FUTILITY_MARGIN[extended_depth as usize];
                    if futility_value <= alpha {
                        moves_searched += 1;
                        continue;
                    }
                }
            }

            // Make move
            let undo = board.make_move(&mv);
            let new_hash = self.zobrist.hash_position(board);

            // Late Move Reductions
            let score;
            if self.use_lmr && moves_searched >= LMR_FULL_DEPTH_MOVES
               && extended_depth >= LMR_REDUCTION_LIMIT && is_quiet && !in_check {

                let reduction = 1 + (moves_searched as i32 / 6);
                let reduced_depth = (extended_depth - 1 - reduction).max(1);

                let mut lmr_score = -self.alphabeta(
                    board, reduced_depth, -alpha - 1, -alpha,
                    ply + 1, false, new_hash, true
                );

                if lmr_score > alpha {
                    lmr_score = -self.alphabeta(
                        board, extended_depth - 1, -beta, -alpha,
                        ply + 1, false, new_hash, true
                    );
                }
                score = lmr_score;
            } else if moves_searched > 0 {
                // PVS
                let mut pvs_score = -self.alphabeta(
                    board, extended_depth - 1, -alpha - 1, -alpha,
                    ply + 1, false, new_hash, true
                );

                if pvs_score > alpha && pvs_score < beta {
                    pvs_score = -self.alphabeta(
                        board, extended_depth - 1, -beta, -alpha,
                        ply + 1, false, new_hash, true
                    );
                }
                score = pvs_score;
            } else {
                score = -self.alphabeta(
                    board, extended_depth - 1, -beta, -alpha,
                    ply + 1, false, new_hash, true
                );
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
                if is_quiet && ply < MAX_DEPTH {
                    self.killer_moves[ply][1] = self.killer_moves[ply][0];
                    self.killer_moves[ply][0] = Some(mv);

                    let piece = undo.moved_piece as usize;
                    self.history[piece][mv.to_sq] += extended_depth * extended_depth;
                }
                break;
            }

            moves_searched += 1;
        }

        // Store in TT
        if self.use_tt && !self.stop_search.load(Ordering::Relaxed) {
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

        let mut captures: Vec<Move> = moves.into_iter()
            .filter(|m| board.squares[m.to_sq] != EMPTY || m.is_en_passant || m.promotion != 0)
            .collect();

        captures.sort_by_key(|m| -evaluate_move(board, m));

        for mv in captures {
            if self.stop_search.load(Ordering::Relaxed) {
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

            if Some(m) == tt_move {
                score += 10000000;
            }

            let victim = board.squares[m.to_sq];
            if victim != EMPTY {
                let victim_value = PIECE_VALUES[get_piece_type(victim) as usize];
                let attacker = board.squares[m.from_sq];
                let attacker_value = PIECE_VALUES[get_piece_type(attacker) as usize];
                score += 1000000 + 10 * victim_value - attacker_value;
            }

            if m.promotion != 0 {
                score += 900000 + PIECE_VALUES[m.promotion as usize];
            }

            if ply < MAX_DEPTH {
                if Some(m) == self.killer_moves[ply][0] {
                    score += 800000;
                } else if Some(m) == self.killer_moves[ply][1] {
                    score += 700000;
                }
            }

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
}

/// Parallel search result
pub struct ParallelSearchResult {
    pub best_move: Option<Move>,
    pub score: i32,
    pub nodes: u64,
}

/// Parallel search engine using Lazy SMP
pub struct ParallelSearchEngine {
    pub num_threads: usize,
    tt: Arc<SharedTranspositionTable>,
    stop_search: Arc<AtomicBool>,
    pub use_tt: bool,
    pub use_null_move: bool,
    pub use_lmr: bool,
    pub nodes_searched: u64,
    pub best_move: Option<Move>,
    pub pv: Vec<Move>,
    search_start_time: std::time::Instant,
}

impl ParallelSearchEngine {
    pub fn new(tt_size_mb: usize, num_threads: usize) -> Self {
        let threads = if num_threads == 0 { num_cpus::get() } else { num_threads };
        
        ParallelSearchEngine {
            num_threads: threads.max(1),
            tt: Arc::new(SharedTranspositionTable::new(tt_size_mb)),
            stop_search: Arc::new(AtomicBool::new(false)),
            use_tt: true,
            use_null_move: true,
            use_lmr: true,
            nodes_searched: 0,
            best_move: None,
            pv: Vec::new(),
            search_start_time: std::time::Instant::now(),
        }
    }

    /// Search with multiple threads
    pub fn search<F>(&mut self, board: &Board, depth: i32, mut info_callback: Option<F>)
        -> (Option<Move>, i32)
    where F: FnMut(i32, i32, u64, u64, &str, usize, u64)
    {
        self.stop_search.store(false, Ordering::SeqCst);
        self.nodes_searched = 0;
        self.best_move = None;
        self.pv.clear();
        self.search_start_time = std::time::Instant::now();

        let tt = Arc::clone(&self.tt);
        let stop = Arc::clone(&self.stop_search);
        let use_tt = self.use_tt;
        let use_null_move = self.use_null_move;
        let use_lmr = self.use_lmr;
        let num_threads = self.num_threads;

        // Spawn helper threads (threads 1..N) - they run full search in background
        let board_clone = board.clone();
        let helper_handles: Vec<_> = (1..num_threads).map(|thread_id| {
            let board = board_clone.clone();
            let tt = Arc::clone(&tt);
            let stop = Arc::clone(&stop);

            thread::spawn(move || {
                let mut worker = WorkerSearch::new(
                    thread_id, stop, tt, use_tt, use_null_move, use_lmr
                );
                let result = worker.search(&board, depth);
                (result.0, result.1, worker.nodes_searched)
            })
        }).collect();

        // Main thread (thread 0) does iterative deepening with progress reports
        let mut main_worker = WorkerSearch::new(
            0, Arc::clone(&stop), Arc::clone(&tt), use_tt, use_null_move, use_lmr
        );

        let position_hash = main_worker.zobrist.hash_position(board);
        let mut best_move = None;
        let mut best_score = -INFINITY;

        // Initial search at depth 1
        let mut temp_board = board.clone();
        let score = main_worker.alphabeta(&mut temp_board, 1, -INFINITY, INFINITY, 0, true, position_hash, true);
        if main_worker.best_move.is_some() {
            best_move = main_worker.best_move;
            best_score = score;
            
            // Report depth 1
            if let Some(ref mut cb) = info_callback {
                let elapsed = self.search_start_time.elapsed();
                let time_ms = elapsed.as_millis() as u64;
                let nps = if time_ms > 0 { (main_worker.nodes_searched * 1000) / time_ms } else { 0 };
                let hashfull = self.tt.hashfull();
                let pv_str = best_move.map(|m| m.to_uci()).unwrap_or_default();
                cb(1, score, main_worker.nodes_searched, time_ms, &pv_str, hashfull, nps);
            }
        }

        // Iterative deepening with progress reports
        for current_depth in 2..=depth {
            if self.stop_search.load(Ordering::Relaxed) {
                break;
            }

            let mut alpha = best_score - ASPIRATION_WINDOW;
            let mut beta = best_score + ASPIRATION_WINDOW;

            loop {
                let mut temp_board = board.clone();
                let score = main_worker.alphabeta(
                    &mut temp_board, current_depth, alpha, beta,
                    0, true, position_hash, true
                );

                if self.stop_search.load(Ordering::Relaxed) {
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

            if !self.stop_search.load(Ordering::Relaxed) && main_worker.best_move.is_some() {
                best_move = main_worker.best_move;
                best_score = main_worker.alphabeta(
                    &mut board.clone(), current_depth, -INFINITY, INFINITY,
                    0, true, position_hash, true
                );

                // Report progress after each depth
                if let Some(ref mut cb) = info_callback {
                    let elapsed = self.search_start_time.elapsed();
                    let time_ms = elapsed.as_millis() as u64;
                    let nps = if time_ms > 0 { (main_worker.nodes_searched * 1000) / time_ms } else { 0 };
                    let hashfull = self.tt.hashfull();
                    let pv_str = best_move.map(|m| m.to_uci()).unwrap_or_default();
                    cb(current_depth, best_score, main_worker.nodes_searched, time_ms, &pv_str, hashfull, nps);
                }
            }
        }

        // Stop helper threads
        self.stop_search.store(true, Ordering::SeqCst);

        // Collect results from helper threads
        let mut total_nodes = main_worker.nodes_searched;
        for handle in helper_handles {
            if let Ok((mv, score, nodes)) = handle.join() {
                total_nodes += nodes;
                // If a helper found a better score, use it
                if score > best_score && mv.is_some() {
                    best_move = mv;
                    best_score = score;
                }
            }
        }

        self.nodes_searched = total_nodes;
        self.best_move = best_move;

        // Extract PV
        if let Some(mv) = best_move {
            self.pv.push(mv);
        }

        (best_move, best_score)
    }

    pub fn stop(&self) {
        self.stop_search.store(true, Ordering::SeqCst);
    }

    pub fn clear_tt(&self) {
        self.tt.clear();
    }

    pub fn set_threads(&mut self, threads: usize) {
        self.num_threads = if threads == 0 { num_cpus::get() } else { threads.max(1) };
    }
}

impl Default for ParallelSearchEngine {
    fn default() -> Self {
        ParallelSearchEngine::new(64, 0)
    }
}
