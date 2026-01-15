"""
OpusChess - UCI Protocol Module

This module implements the Universal Chess Interface (UCI) protocol,
allowing the engine to communicate with chess GUIs.
"""

import sys
from typing import Optional, List, Dict, Any
from board import Board, Move, parse_square, QUEEN, ROOK, BISHOP, KNIGHT
from move_generator import MoveGenerator
from search import SearchEngine

# Engine identification
ENGINE_NAME = "OpusChess"
ENGINE_AUTHOR = "AI Assistant"
ENGINE_VERSION = "2.0"


class UCIOption:
    """Represents a UCI option."""
    
    def __init__(self, name: str, opt_type: str, default: Any, 
                 min_val: Any = None, max_val: Any = None, var: List[str] = None):
        self.name = name
        self.type = opt_type
        self.default = default
        self.value = default
        self.min = min_val
        self.max = max_val
        self.var = var or []
    
    def to_uci_string(self) -> str:
        """Convert option to UCI string format."""
        s = f"option name {self.name} type {self.type}"
        
        if self.type == "spin":
            s += f" default {self.default} min {self.min} max {self.max}"
        elif self.type == "check":
            s += f" default {'true' if self.default else 'false'}"
        elif self.type == "string":
            s += f" default {self.default}" if self.default else " default"
        elif self.type == "combo":
            s += f" default {self.default}"
            for v in self.var:
                s += f" var {v}"
        
        return s
    
    def set_value(self, value_str: str) -> bool:
        """Set option value from string. Returns True if successful."""
        try:
            if self.type == "spin":
                val = int(value_str)
                if self.min <= val <= self.max:
                    self.value = val
                    return True
            elif self.type == "check":
                self.value = value_str.lower() == "true"
                return True
            elif self.type == "string":
                self.value = value_str
                return True
            elif self.type == "combo":
                if value_str in self.var:
                    self.value = value_str
                    return True
            elif self.type == "button":
                return True
        except ValueError:
            pass
        return False


class UCIProtocol:
    """
    UCI protocol handler.
    
    Parses UCI commands from stdin and sends responses to stdout.
    """
    
    # Default option values
    DEFAULT_HASH_SIZE = 64      # MB
    DEFAULT_DEPTH = 6
    DEFAULT_USE_TT = True
    DEFAULT_USE_NMP = True
    DEFAULT_USE_LMR = True
    DEFAULT_USE_IID = True
    
    def __init__(self):
        """Initialize the UCI protocol handler."""
        self.board = Board()
        self.move_generator = MoveGenerator()
        self.running = True
        self.debug_mode = False
        
        # Ponder state
        self.ponder_move = None  # Expected opponent's move
        self.pondering = False   # Currently pondering
        self.ponderhit_count = 0 # Stats: how often we predicted correctly
        self.ponder_total = 0    # Stats: total ponder attempts
        
        # Initialize options
        self.options: Dict[str, UCIOption] = {}
        self._init_options()
        
        # Create search engine with default options
        self._create_search_engine()
    
    def _init_options(self):
        """Initialize UCI options."""
        self.options = {
            "Hash": UCIOption("Hash", "spin", self.DEFAULT_HASH_SIZE, 1, 1024),
            "Depth": UCIOption("Depth", "spin", self.DEFAULT_DEPTH, 1, 30),
            "Ponder": UCIOption("Ponder", "check", True),
            "UseTranspositionTable": UCIOption("UseTranspositionTable", "check", self.DEFAULT_USE_TT),
            "UseNullMove": UCIOption("UseNullMove", "check", self.DEFAULT_USE_NMP),
            "UseLMR": UCIOption("UseLMR", "check", self.DEFAULT_USE_LMR),
            "UseIID": UCIOption("UseIID", "check", self.DEFAULT_USE_IID),
            "Clear Hash": UCIOption("Clear Hash", "button", None),
        }
    
    def _create_search_engine(self):
        """Create search engine with current options."""
        hash_size = self.options["Hash"].value
        self.search_engine = SearchEngine(tt_size_mb=hash_size)
        
        # Apply options to search engine
        self.search_engine.use_tt = self.options["UseTranspositionTable"].value
        self.search_engine.use_null_move = self.options["UseNullMove"].value
        self.search_engine.use_lmr = self.options["UseLMR"].value
        self.search_engine.use_iid = self.options["UseIID"].value
    
    def run(self):
        """Main loop - read commands from stdin and process them."""
        while self.running:
            try:
                line = input().strip()
                if line:
                    self._process_command(line)
            except EOFError:
                break
            except KeyboardInterrupt:
                break
    
    def _process_command(self, line: str):
        """Process a single UCI command."""
        parts = line.split()
        if not parts:
            return
        
        command = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        if command == "uci":
            self._cmd_uci()
        elif command == "isready":
            self._cmd_isready()
        elif command == "setoption":
            self._cmd_setoption(args)
        elif command == "ucinewgame":
            self._cmd_ucinewgame()
        elif command == "position":
            self._cmd_position(args)
        elif command == "go":
            self._cmd_go(args)
        elif command == "stop":
            self._cmd_stop()
        elif command == "ponderhit":
            self._cmd_ponderhit()
        elif command == "quit":
            self._cmd_quit()
        elif command == "debug":
            self._cmd_debug(args)
        elif command == "d":
            self._cmd_display()
        elif command == "perft":
            self._cmd_perft(args)
        elif command == "bench":
            self._cmd_bench()
        else:
            if self.debug_mode:
                self._send(f"info string Unknown command: {command}")
    
    def _send(self, message: str):
        """Send a message to stdout."""
        print(message, flush=True)
    
    def _cmd_uci(self):
        """Handle 'uci' command - identify the engine."""
        self._send(f"id name {ENGINE_NAME} {ENGINE_VERSION}")
        self._send(f"id author {ENGINE_AUTHOR}")
        
        # List all options
        for option in self.options.values():
            self._send(option.to_uci_string())
        
        self._send("uciok")
    
    def _cmd_setoption(self, args: List[str]):
        """
        Handle 'setoption' command.
        
        Format: setoption name <name> [value <value>]
        """
        if len(args) < 2 or args[0] != "name":
            return
        
        # Find the option name (may contain spaces)
        name_parts = []
        value_str = None
        i = 1
        
        while i < len(args):
            if args[i] == "value":
                i += 1
                if i < len(args):
                    value_str = " ".join(args[i:])
                break
            name_parts.append(args[i])
            i += 1
        
        name = " ".join(name_parts)
        
        # Find and set the option
        if name in self.options:
            option = self.options[name]
            
            if option.type == "button":
                # Handle button options
                if name == "Clear Hash":
                    self.search_engine.clear_tt()
                    if self.debug_mode:
                        self._send("info string Hash table cleared")
            elif value_str is not None:
                if option.set_value(value_str):
                    # Apply option changes
                    self._apply_option(name)
                    if self.debug_mode:
                        self._send(f"info string Option {name} set to {option.value}")
    
    def _apply_option(self, name: str):
        """Apply an option change to the engine."""
        if name == "Hash":
            # Need to recreate search engine with new hash size
            self._create_search_engine()
        elif name == "UseTranspositionTable":
            self.search_engine.use_tt = self.options[name].value
        elif name == "UseNullMove":
            self.search_engine.use_null_move = self.options[name].value
        elif name == "UseLMR":
            self.search_engine.use_lmr = self.options[name].value
        elif name == "UseIID":
            self.search_engine.use_iid = self.options[name].value
    
    def _cmd_isready(self):
        """Handle 'isready' command - check if engine is ready."""
        self._send("readyok")
    
    def _cmd_ucinewgame(self):
        """Handle 'ucinewgame' command - reset for new game."""
        self.board = Board()
        self.search_engine.clear_tt()
    
    def _cmd_position(self, args: List[str]):
        """Handle 'position' command - set up a position."""
        if not args:
            return
        
        moves_index = -1
        
        if args[0] == "startpos":
            self.board = Board()
            if len(args) > 1 and args[1] == "moves":
                moves_index = 2
        elif args[0] == "fen":
            fen_parts = []
            i = 1
            while i < len(args) and args[i] != "moves":
                fen_parts.append(args[i])
                i += 1
            
            if fen_parts:
                fen = " ".join(fen_parts)
                self.board = Board(fen)
            
            if i < len(args) and args[i] == "moves":
                moves_index = i + 1
        
        if moves_index >= 0:
            for move_str in args[moves_index:]:
                move = self._parse_move(move_str)
                if move:
                    self.board.make_move(move)
    
    def _parse_move(self, move_str: str) -> Optional[Move]:
        """Parse a move string in UCI format."""
        if len(move_str) < 4:
            return None
        
        try:
            from_sq = parse_square(move_str[0:2])
            to_sq = parse_square(move_str[2:4])
        except (ValueError, IndexError):
            return None
        
        promotion = 0
        if len(move_str) == 5:
            promo_char = move_str[4].lower()
            promo_map = {'q': QUEEN, 'r': ROOK, 'b': BISHOP, 'n': KNIGHT}
            promotion = promo_map.get(promo_char, 0)
        
        legal_moves = self.move_generator.generate_legal_moves(self.board)
        
        for move in legal_moves:
            if move.from_sq == from_sq and move.to_sq == to_sq:
                if promotion:
                    if move.promotion == promotion:
                        return move
                else:
                    if move.promotion == 0:
                        return move
        
        for move in legal_moves:
            if move.from_sq == from_sq and move.to_sq == to_sq:
                return move
        
        return None
    
    def _cmd_go(self, args: List[str]):
        """Handle 'go' command - start searching."""
        depth = self.options["Depth"].value
        
        i = 0
        while i < len(args):
            if args[i] == "depth" and i + 1 < len(args):
                try:
                    depth = int(args[i + 1])
                except ValueError:
                    pass
                i += 2
            elif args[i] == "movetime" and i + 1 < len(args):
                i += 2
            elif args[i] == "infinite":
                depth = 30
                i += 1
            elif args[i] in ("wtime", "btime", "winc", "binc", "movestogo"):
                i += 2
            else:
                i += 1
        
        depth = min(depth, 30)
        
        # Define callback for info output at each depth
        def info_callback(depth, score, nodes, time_ms, pv, hashfull, nps):
            # Format score (mate detection)
            if abs(score) > 40000:
                # Mate score
                mate_distance = (50000 - abs(score) + 1) // 2
                if score > 0:
                    score_str = f"mate {mate_distance}"
                else:
                    score_str = f"mate -{mate_distance}"
            else:
                score_str = f"cp {score}"
            
            # Build info string
            info_parts = [
                f"depth {depth}",
                f"score {score_str}",
                f"nodes {nodes}",
                f"time {time_ms}",
                f"nps {nps}",
                f"hashfull {hashfull}",
            ]
            
            if pv:
                info_parts.append(f"pv {pv}")
            
            self._send("info " + " ".join(info_parts))
        
        best_move, score = self.search_engine.search(self.board, depth, info_callback)
        
        # Get ponder move (expected opponent's reply) from PV
        ponder_move_str = ""
        if best_move and self.options["Ponder"].value:
            pv = self.search_engine.pv
            if len(pv) >= 2:
                # PV[0] is our move, PV[1] is expected opponent reply
                self.ponder_move = pv[1]
                ponder_move_str = f" ponder {pv[1].to_uci()}"
                self.ponder_total += 1
            else:
                self.ponder_move = None
        
        if best_move:
            self._send(f"bestmove {best_move.to_uci()}{ponder_move_str}")
        else:
            legal_moves = self.move_generator.generate_legal_moves(self.board)
            if legal_moves:
                self._send(f"bestmove {legal_moves[0].to_uci()}")
            else:
                self._send("bestmove 0000")
    
    def _cmd_stop(self):
        """Handle 'stop' command - stop searching."""
        self.search_engine.stop()
        self.pondering = False
    
    def _cmd_ponderhit(self):
        """
        Handle 'ponderhit' command.
        
        Called when the opponent played the move we predicted.
        This means our pondering was on the right track.
        """
        if self.ponder_move is not None:
            self.ponderhit_count += 1
            if self.debug_mode:
                hit_rate = (self.ponderhit_count / self.ponder_total * 100) if self.ponder_total > 0 else 0
                self._send(f"info string Ponderhit! Rate: {hit_rate:.1f}% ({self.ponderhit_count}/{self.ponder_total})")
        self.pondering = False
    
    def _cmd_quit(self):
        """Handle 'quit' command - exit the engine."""
        self.running = False
    
    def _cmd_debug(self, args: List[str]):
        """Handle 'debug' command - toggle debug mode."""
        if args and args[0] == "on":
            self.debug_mode = True
        elif args and args[0] == "off":
            self.debug_mode = False
    
    def _cmd_display(self):
        """Handle 'd' command - display the board."""
        self._send(str(self.board))
        self._send(f"FEN: {self.board.to_fen()}")
        
        in_check = self.move_generator.is_in_check(self.board)
        self._send(f"In check: {in_check}")
        
        legal_moves = self.move_generator.generate_legal_moves(self.board)
        self._send(f"Legal moves: {len(legal_moves)}")
        
        move_list = " ".join(m.to_uci() for m in legal_moves[:20])
        if len(legal_moves) > 20:
            move_list += " ..."
        self._send(f"Moves: {move_list}")
        
        # Show current options
        self._send("Options:")
        for name, opt in self.options.items():
            if opt.type != "button":
                self._send(f"  {name}: {opt.value}")
    
    def _cmd_perft(self, args: List[str]):
        """Handle 'perft' command."""
        depth = 1
        if args:
            try:
                depth = int(args[0])
            except ValueError:
                pass
        
        nodes = self._perft(self.board, depth)
        self._send(f"Nodes: {nodes}")
    
    def _perft(self, board: Board, depth: int) -> int:
        """Perft - count leaf nodes at given depth."""
        if depth == 0:
            return 1
        
        moves = self.move_generator.generate_legal_moves(board)
        
        if depth == 1:
            return len(moves)
        
        nodes = 0
        for move in moves:
            undo = board.make_move(move)
            nodes += self._perft(board, depth - 1)
            board.unmake_move(move, undo)
        
        return nodes
    
    def _cmd_bench(self):
        """Run a quick benchmark."""
        import time
        
        positions = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
            "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        ]
        
        total_nodes = 0
        start_time = time.time()
        
        for fen in positions:
            self.board = Board(fen)
            self.search_engine.clear_tt()
            move, score = self.search_engine.search(self.board, 5)
            total_nodes += self.search_engine.nodes_searched
        
        elapsed = time.time() - start_time
        nps = int(total_nodes / elapsed) if elapsed > 0 else 0
        
        self._send(f"info string Benchmark: {total_nodes} nodes in {elapsed:.2f}s ({nps} nps)")
