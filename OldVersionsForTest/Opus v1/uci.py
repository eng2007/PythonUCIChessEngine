"""
OpusChess - UCI Protocol Module

This module implements the Universal Chess Interface (UCI) protocol,
allowing the engine to communicate with chess GUIs.
"""

import sys
from typing import Optional, List
from board import Board, Move, parse_square, QUEEN, ROOK, BISHOP, KNIGHT
from move_generator import MoveGenerator
from search import SearchEngine

# Engine identification
ENGINE_NAME = "OpusChess"
ENGINE_AUTHOR = "AI Assistant"
ENGINE_VERSION = "1.0"


class UCIProtocol:
    """
    UCI protocol handler.
    
    Parses UCI commands from stdin and sends responses to stdout.
    """
    
    def __init__(self):
        """Initialize the UCI protocol handler."""
        self.board = Board()
        self.move_generator = MoveGenerator()
        self.search_engine = SearchEngine()
        self.running = True
        self.debug_mode = False
    
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
        elif command == "ucinewgame":
            self._cmd_ucinewgame()
        elif command == "position":
            self._cmd_position(args)
        elif command == "go":
            self._cmd_go(args)
        elif command == "stop":
            self._cmd_stop()
        elif command == "quit":
            self._cmd_quit()
        elif command == "debug":
            self._cmd_debug(args)
        elif command == "d":
            self._cmd_display()
        elif command == "perft":
            self._cmd_perft(args)
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
        # Options would be listed here
        self._send("option name Depth type spin default 4 min 1 max 20")
        self._send("uciok")
    
    def _cmd_isready(self):
        """Handle 'isready' command - check if engine is ready."""
        self._send("readyok")
    
    def _cmd_ucinewgame(self):
        """Handle 'ucinewgame' command - reset for new game."""
        self.board = Board()
        self.search_engine = SearchEngine()
    
    def _cmd_position(self, args: List[str]):
        """
        Handle 'position' command - set up a position.
        
        Format: position [startpos | fen <fen_string>] [moves <move1> <move2> ...]
        """
        if not args:
            return
        
        moves_index = -1
        
        if args[0] == "startpos":
            self.board = Board()
            if len(args) > 1 and args[1] == "moves":
                moves_index = 2
        elif args[0] == "fen":
            # Find where FEN ends (at "moves" or end of args)
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
        
        # Apply moves if specified
        if moves_index >= 0:
            for move_str in args[moves_index:]:
                move = self._parse_move(move_str)
                if move:
                    self.board.make_move(move)
    
    def _parse_move(self, move_str: str) -> Optional[Move]:
        """
        Parse a move string in UCI format (e.g., 'e2e4', 'e7e8q').
        
        Returns:
            Move object or None if invalid
        """
        if len(move_str) < 4:
            return None
        
        try:
            from_sq = parse_square(move_str[0:2])
            to_sq = parse_square(move_str[2:4])
        except (ValueError, IndexError):
            return None
        
        # Check for promotion
        promotion = 0
        if len(move_str) == 5:
            promo_char = move_str[4].lower()
            promo_map = {'q': QUEEN, 'r': ROOK, 'b': BISHOP, 'n': KNIGHT}
            promotion = promo_map.get(promo_char, 0)
        
        # Generate legal moves to find the matching one
        legal_moves = self.move_generator.generate_legal_moves(self.board)
        
        for move in legal_moves:
            if move.from_sq == from_sq and move.to_sq == to_sq:
                if promotion:
                    if move.promotion == promotion:
                        return move
                else:
                    if move.promotion == 0:
                        return move
        
        # If no exact match found, create the move (for promotions without specifying piece)
        for move in legal_moves:
            if move.from_sq == from_sq and move.to_sq == to_sq:
                return move
        
        return None
    
    def _cmd_go(self, args: List[str]):
        """
        Handle 'go' command - start searching.
        
        Supported options:
        - depth <n>: Search to depth n
        - movetime <ms>: Search for ms milliseconds
        - infinite: Search until 'stop' command
        """
        depth = 4  # Default depth
        
        i = 0
        while i < len(args):
            if args[i] == "depth" and i + 1 < len(args):
                try:
                    depth = int(args[i + 1])
                except ValueError:
                    pass
                i += 2
            elif args[i] == "movetime" and i + 1 < len(args):
                # For now, ignore time and use depth
                # TODO: Implement time management
                i += 2
            elif args[i] == "infinite":
                depth = 20  # Use high depth for infinite
                i += 1
            elif args[i] in ("wtime", "btime", "winc", "binc", "movestogo"):
                # Time control - skip for now
                i += 2
            else:
                i += 1
        
        # Limit depth
        depth = min(depth, 20)
        
        # Search for best move
        best_move, score = self.search_engine.search(self.board, depth)
        
        # Send search info
        info = self.search_engine.get_info()
        self._send(f"info depth {info['depth']} nodes {info['nodes']} score cp {score}")
        
        # Send best move
        if best_move:
            self._send(f"bestmove {best_move.to_uci()}")
        else:
            # No legal moves - shouldn't happen in valid position
            legal_moves = self.move_generator.generate_legal_moves(self.board)
            if legal_moves:
                self._send(f"bestmove {legal_moves[0].to_uci()}")
            else:
                self._send("bestmove 0000")  # No legal moves
    
    def _cmd_stop(self):
        """Handle 'stop' command - stop searching."""
        self.search_engine.stop()
    
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
        """Handle 'd' command - display the board (non-standard, for debugging)."""
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
    
    def _cmd_perft(self, args: List[str]):
        """
        Handle 'perft' command - count nodes at given depth (for testing).
        
        Format: perft <depth>
        """
        depth = 1
        if args:
            try:
                depth = int(args[0])
            except ValueError:
                pass
        
        nodes = self._perft(self.board, depth)
        self._send(f"Nodes: {nodes}")
    
    def _perft(self, board: Board, depth: int) -> int:
        """
        Perft (performance test) - count leaf nodes at given depth.
        
        Args:
            board: Current board state
            depth: Depth to search
            
        Returns:
            Number of leaf nodes
        """
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
