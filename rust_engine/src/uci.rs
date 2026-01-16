//! OpusChess - UCI Protocol Module
//!
//! This module implements the Universal Chess Interface (UCI) protocol,
//! allowing the engine to communicate with chess GUIs.

use std::io::{self, BufRead, Write};
use crate::types::*;
use crate::board::{Board, Move};
use crate::move_generator::MoveGenerator;
use crate::parallel_search::ParallelSearchEngine;

// Engine identification
const ENGINE_NAME: &str = "OpusChess";
const ENGINE_AUTHOR: &str = "AI Assistant";
const ENGINE_VERSION: &str = "2.1";

/// UCI option representation
#[derive(Clone)]
pub struct UCIOption {
    pub name: String,
    pub opt_type: String,
    pub default: String,
    pub value: String,
    pub min: Option<i32>,
    pub max: Option<i32>,
}

impl UCIOption {
    pub fn spin(name: &str, default: i32, min: i32, max: i32) -> Self {
        UCIOption {
            name: name.to_string(),
            opt_type: "spin".to_string(),
            default: default.to_string(),
            value: default.to_string(),
            min: Some(min),
            max: Some(max),
        }
    }

    pub fn check(name: &str, default: bool) -> Self {
        UCIOption {
            name: name.to_string(),
            opt_type: "check".to_string(),
            default: if default { "true".to_string() } else { "false".to_string() },
            value: if default { "true".to_string() } else { "false".to_string() },
            min: None,
            max: None,
        }
    }

    pub fn button(name: &str) -> Self {
        UCIOption {
            name: name.to_string(),
            opt_type: "button".to_string(),
            default: String::new(),
            value: String::new(),
            min: None,
            max: None,
        }
    }

    pub fn to_uci_string(&self) -> String {
        let mut s = format!("option name {} type {}", self.name, self.opt_type);
        
        match self.opt_type.as_str() {
            "spin" => {
                s.push_str(&format!(" default {} min {} max {}", 
                    self.default, 
                    self.min.unwrap_or(0), 
                    self.max.unwrap_or(1000)));
            }
            "check" => {
                s.push_str(&format!(" default {}", self.default));
            }
            _ => {}
        }
        
        s
    }

    pub fn set_value(&mut self, value_str: &str) -> bool {
        match self.opt_type.as_str() {
            "spin" => {
                if let Ok(val) = value_str.parse::<i32>() {
                    if let (Some(min), Some(max)) = (self.min, self.max) {
                        if val >= min && val <= max {
                            self.value = val.to_string();
                            return true;
                        }
                    }
                }
            }
            "check" => {
                self.value = if value_str.to_lowercase() == "true" { 
                    "true".to_string() 
                } else { 
                    "false".to_string() 
                };
                return true;
            }
            _ => {}
        }
        false
    }

    pub fn get_int(&self) -> i32 {
        self.value.parse().unwrap_or(0)
    }

    pub fn get_bool(&self) -> bool {
        self.value.to_lowercase() == "true"
    }
}

/// UCI protocol handler
pub struct UCIProtocol {
    board: Board,
    move_generator: MoveGenerator,
    search_engine: ParallelSearchEngine,
    running: bool,
    debug_mode: bool,
    options: Vec<UCIOption>,
}

impl UCIProtocol {
    pub fn new() -> Self {
        let num_threads = num_cpus::get();
        let mut protocol = UCIProtocol {
            board: Board::new(),
            move_generator: MoveGenerator::new(),
            search_engine: ParallelSearchEngine::new(64, num_threads),
            running: true,
            debug_mode: false,
            options: Vec::new(),
        };
        
        protocol.init_options();
        protocol
    }

    fn init_options(&mut self) {
        let default_threads = num_cpus::get() as i32;
        self.options = vec![
            UCIOption::spin("Threads", default_threads, 1, 256),
            UCIOption::spin("Hash", 64, 1, 1024),
            UCIOption::spin("Depth", 10, 1, 30),
            UCIOption::check("Ponder", true),
            UCIOption::check("UseTranspositionTable", true),
            UCIOption::check("UseNullMove", true),
            UCIOption::check("UseLMR", true),
            UCIOption::check("UseIID", true),
            UCIOption::check("UseRazoring", true),
            UCIOption::check("UseReverseFutility", true),
            UCIOption::check("UseLMP", true),
            UCIOption::check("UseProbcut", true),
            UCIOption::check("UseSingularExtensions", true),
            UCIOption::check("UseCountermove", true),
            UCIOption::button("Clear Hash"),
        ];
    }

    fn apply_options(&mut self) {
        for opt in &self.options {
            match opt.name.as_str() {
                "Threads" => {
                    let threads = opt.get_int() as usize;
                    self.search_engine.set_threads(threads);
                }
                "Hash" => {
                    let size = opt.get_int() as usize;
                    let threads = self.search_engine.num_threads;
                    self.search_engine = ParallelSearchEngine::new(size, threads);
                }
                "UseTranspositionTable" => {
                    self.search_engine.use_tt = opt.get_bool();
                }
                "UseNullMove" => {
                    self.search_engine.use_null_move = opt.get_bool();
                }
                "UseLMR" => {
                    self.search_engine.use_lmr = opt.get_bool();
                }
                _ => {}
            }
        }
    }

    pub fn run(&mut self) {
        let stdin = io::stdin();
        
        for line in stdin.lock().lines() {
            if let Ok(line) = line {
                let line = line.trim();
                if !line.is_empty() {
                    self.process_command(line);
                }
                if !self.running {
                    break;
                }
            }
        }
    }

    fn process_command(&mut self, line: &str) {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.is_empty() {
            return;
        }

        let command = parts[0];
        let args: Vec<&str> = parts[1..].to_vec();

        match command {
            "uci" => self.cmd_uci(),
            "isready" => self.cmd_isready(),
            "setoption" => self.cmd_setoption(&args),
            "ucinewgame" => self.cmd_ucinewgame(),
            "position" => self.cmd_position(&args),
            "go" => self.cmd_go(&args),
            "stop" => self.cmd_stop(),
            "quit" => self.cmd_quit(),
            "debug" => self.cmd_debug(&args),
            "d" => self.cmd_display(),
            "perft" => self.cmd_perft(&args),
            "bench" => self.cmd_bench(),
            _ => {
                if self.debug_mode {
                    self.send(&format!("info string Unknown command: {}", command));
                }
            }
        }
    }

    fn send(&self, message: &str) {
        println!("{}", message);
        io::stdout().flush().ok();
    }

    fn cmd_uci(&self) {
        self.send(&format!("id name {} {}", ENGINE_NAME, ENGINE_VERSION));
        self.send(&format!("id author {}", ENGINE_AUTHOR));
        
        for option in &self.options {
            self.send(&option.to_uci_string());
        }
        
        self.send("uciok");
    }

    fn cmd_setoption(&mut self, args: &[&str]) {
        if args.len() < 2 || args[0] != "name" {
            return;
        }

        // Parse option name and value
        let mut name_parts = Vec::new();
        let mut value_str = None;
        let mut i = 1;

        while i < args.len() {
            if args[i] == "value" {
                i += 1;
                if i < args.len() {
                    value_str = Some(args[i..].join(" "));
                }
                break;
            }
            name_parts.push(args[i]);
            i += 1;
        }

        let name = name_parts.join(" ");

        // Find and set the option
        let mut opt_set_msg: Option<String> = None;
        let mut clear_hash = false;
        for opt in &mut self.options {
            if opt.name == name {
                if opt.opt_type == "button" {
                    if name == "Clear Hash" {
                        clear_hash = true;
                    }
                } else if let Some(ref val) = value_str {
                    if opt.set_value(val) {
                        if self.debug_mode {
                            opt_set_msg = Some(format!("info string Option {} set to {}", name, opt.value));
                        }
                    }
                }
                break;
            }
        }
        if let Some(msg) = opt_set_msg {
            self.send(&msg);
        }
        if clear_hash {
            self.search_engine.clear_tt();
            if self.debug_mode {
                self.send("info string Hash table cleared");
            }
        }

        self.apply_options();
    }

    fn cmd_isready(&self) {
        self.send("readyok");
    }

    fn cmd_ucinewgame(&mut self) {
        self.board = Board::new();
        self.search_engine.clear_tt();
    }

    fn cmd_position(&mut self, args: &[&str]) {
        if args.is_empty() {
            return;
        }

        let mut moves_index: Option<usize> = None;

        if args[0] == "startpos" {
            self.board = Board::new();
            if args.len() > 1 && args[1] == "moves" {
                moves_index = Some(2);
            }
        } else if args[0] == "fen" {
            let mut fen_parts = Vec::new();
            let mut i = 1;
            while i < args.len() && args[i] != "moves" {
                fen_parts.push(args[i]);
                i += 1;
            }
            
            if !fen_parts.is_empty() {
                let fen = fen_parts.join(" ");
                if let Some(board) = Board::from_fen(&fen) {
                    self.board = board;
                }
            }
            
            if i < args.len() && args[i] == "moves" {
                moves_index = Some(i + 1);
            }
        }

        if let Some(idx) = moves_index {
            for move_str in &args[idx..] {
                if let Some(mv) = self.parse_move(move_str) {
                    self.board.make_move(&mv);
                }
            }
        }
    }

    fn parse_move(&self, move_str: &str) -> Option<Move> {
        if move_str.len() < 4 {
            return None;
        }

        let from_sq = parse_square(&move_str[0..2])?;
        let to_sq = parse_square(&move_str[2..4])?;

        let promotion = if move_str.len() == 5 {
            match move_str.chars().nth(4)? {
                'q' | 'Q' => QUEEN,
                'r' | 'R' => ROOK,
                'b' | 'B' => BISHOP,
                'n' | 'N' => KNIGHT,
                _ => 0,
            }
        } else {
            0
        };

        let legal_moves = self.move_generator.generate_legal_moves(&self.board);

        // Find matching legal move
        for mv in &legal_moves {
            if mv.from_sq == from_sq && mv.to_sq == to_sq {
                if promotion != 0 {
                    if mv.promotion == promotion {
                        return Some(*mv);
                    }
                } else if mv.promotion == 0 {
                    return Some(*mv);
                }
            }
        }

        // Fallback: return any matching move
        for mv in &legal_moves {
            if mv.from_sq == from_sq && mv.to_sq == to_sq {
                return Some(*mv);
            }
        }

        None
    }

    fn cmd_go(&mut self, args: &[&str]) {
        let mut depth = 6;
        
        // Parse depth option
        for opt in &self.options {
            if opt.name == "Depth" {
                depth = opt.get_int();
            }
        }

        let mut i = 0;
        while i < args.len() {
            match args[i] {
                "depth" if i + 1 < args.len() => {
                    if let Ok(d) = args[i + 1].parse::<i32>() {
                        depth = d;
                    }
                    i += 2;
                }
                "infinite" => {
                    depth = 30;
                    i += 1;
                }
                "wtime" | "btime" | "winc" | "binc" | "movestogo" | "movetime" => {
                    i += 2;
                }
                _ => {
                    i += 1;
                }
            }
        }

        depth = depth.min(30);

        // Search with info callback
        let (best_move, _score) = self.search_engine.search(&self.board, depth, Some(|d: i32, s: i32, n: u64, t: u64, pv: &str, hf: usize, nps: u64| {
            // Format score
            let score_str = if s.abs() > 40000 {
                let mate_distance = (50000 - s.abs() + 1) / 2;
                if s > 0 {
                    format!("mate {}", mate_distance)
                } else {
                    format!("mate -{}", mate_distance)
                }
            } else {
                format!("cp {}", s)
            };
            
            let info = format!(
                "info depth {} score {} nodes {} time {} nps {} hashfull {} pv {}",
                d, score_str, n, t, nps, hf, pv
            );
            println!("{}", info);
            io::stdout().flush().ok();
        }));

        // Get ponder move from PV
        let mut ponder_str = String::new();
        if self.search_engine.pv.len() >= 2 {
            ponder_str = format!(" ponder {}", self.search_engine.pv[1].to_uci());
        }

        if let Some(mv) = best_move {
            self.send(&format!("bestmove {}{}", mv.to_uci(), ponder_str));
        } else {
            let legal_moves = self.move_generator.generate_legal_moves(&self.board);
            if !legal_moves.is_empty() {
                self.send(&format!("bestmove {}", legal_moves[0].to_uci()));
            } else {
                self.send("bestmove 0000");
            }
        }
    }

    fn cmd_stop(&mut self) {
        self.search_engine.stop();
    }

    fn cmd_quit(&mut self) {
        self.running = false;
    }

    fn cmd_debug(&mut self, args: &[&str]) {
        if !args.is_empty() {
            self.debug_mode = args[0] == "on";
        }
    }

    fn cmd_display(&self) {
        self.send(&self.board.display());
        self.send(&format!("FEN: {}", self.board.to_fen()));
        
        let in_check = self.move_generator.is_in_check(&self.board);
        self.send(&format!("In check: {}", in_check));
        
        let legal_moves = self.move_generator.generate_legal_moves(&self.board);
        self.send(&format!("Legal moves: {}", legal_moves.len()));
        
        let move_list: Vec<String> = legal_moves.iter().take(20).map(|m| m.to_uci()).collect();
        let mut moves_str = move_list.join(" ");
        if legal_moves.len() > 20 {
            moves_str.push_str(" ...");
        }
        self.send(&format!("Moves: {}", moves_str));
    }

    fn cmd_perft(&self, args: &[&str]) {
        let depth = args.first()
            .and_then(|s| s.parse::<usize>().ok())
            .unwrap_or(1);

        let mut board = self.board.clone();
        let nodes = self.perft(&mut board, depth);
        self.send(&format!("Nodes: {}", nodes));
    }

    fn perft(&self, board: &mut Board, depth: usize) -> u64 {
        if depth == 0 {
            return 1;
        }

        let moves = self.move_generator.generate_legal_moves(board);

        if depth == 1 {
            return moves.len() as u64;
        }

        let mut nodes = 0u64;
        for mv in moves {
            let undo = board.make_move(&mv);
            nodes += self.perft(board, depth - 1);
            board.unmake_move(&mv, &undo);
        }

        nodes
    }

    fn cmd_bench(&mut self) {
        use std::time::Instant;

        let positions = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
            "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        ];

        let mut total_nodes = 0u64;
        let start_time = Instant::now();

        for fen in &positions {
            if let Some(board) = Board::from_fen(fen) {
                self.board = board;
                self.search_engine.clear_tt();
                let (_, _) = self.search_engine.search::<fn(i32, i32, u64, u64, &str, usize, u64)>(
                    &self.board, 5, None
                );
                total_nodes += self.search_engine.nodes_searched;
            }
        }

        let elapsed = start_time.elapsed();
        let elapsed_secs = elapsed.as_secs_f64();
        let nps = if elapsed_secs > 0.0 { (total_nodes as f64 / elapsed_secs) as u64 } else { 0 };

        self.send(&format!(
            "info string Benchmark: {} nodes in {:.2}s ({} nps)",
            total_nodes, elapsed_secs, nps
        ));
    }
}

impl Default for UCIProtocol {
    fn default() -> Self {
        UCIProtocol::new()
    }
}
