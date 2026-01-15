"""
Модуль UCI (Universal Chess Interface) протокола.
"""

import sys
from typing import Optional
from chess_board import ChessBoard, Move
from move_generator import MoveGenerator
from search_engine import SearchEngine


class UCIInterface:
    """Класс для реализации UCI протокола."""
    
    def __init__(self):
        """Инициализация UCI интерфейса."""
        self.board = ChessBoard()
        self.engine = SearchEngine()
        self.running = True
        self.debug = False
    
    def run(self) -> None:
        """Главный цикл UCI интерфейса."""
        while self.running:
            try:
                command = input().strip()
                if command:
                    self._process_command(command)
            except EOFError:
                break
            except KeyboardInterrupt:
                break
    
    def _process_command(self, command: str) -> None:
        """
        Обрабатывает UCI команду.
        
        Args:
            command: Команда для обработки
        """
        parts = command.split()
        if not parts:
            return
        
        cmd = parts[0].lower()
        
        if cmd == 'uci':
            self._handle_uci()
        elif cmd == 'debug':
            self._handle_debug(parts)
        elif cmd == 'isready':
            self._handle_isready()
        elif cmd == 'setoption':
            self._handle_setoption(parts)
        elif cmd == 'ucinewgame':
            self._handle_ucinewgame()
        elif cmd == 'position':
            self._handle_position(parts)
        elif cmd == 'go':
            self._handle_go(parts)
        elif cmd == 'stop':
            self._handle_stop()
        elif cmd == 'quit':
            self._handle_quit()
        elif cmd == 'd':
            # Команда для отладки - показать доску
            self._print_debug(str(self.board))
            self._print_debug(f"FEN: {self.board.to_fen()}")
        else:
            self._print_debug(f"Unknown command: {command}")
    
    def _handle_uci(self) -> None:
        """Обрабатывает команду uci."""
        print("id name ChessEngine")
        print("id author AI Chess Developer")
        print("option name Hash type spin default 16 min 1 max 1024")
        print("option name Threads type spin default 1 min 1 max 8")
        print("uciok")
        sys.stdout.flush()
    
    def _handle_debug(self, parts: list) -> None:
        """Обрабатывает команду debug."""
        if len(parts) > 1:
            self.debug = parts[1].lower() == 'on'
    
    def _handle_isready(self) -> None:
        """Обрабатывает команду isready."""
        print("readyok")
        sys.stdout.flush()
    
    def _handle_setoption(self, parts: list) -> None:
        """Обрабатывает команду setoption."""
        # Базовая реализация - можно расширить для поддержки различных опций
        self._print_debug(f"Setting option: {' '.join(parts[1:])}")
    
    def _handle_ucinewgame(self) -> None:
        """Обрабатывает команду ucinewgame."""
        self.board = ChessBoard()
        self._print_debug("New game started")
    
    def _handle_position(self, parts: list) -> None:
        """
        Обрабатывает команду position.
        
        Args:
            parts: Части команды
        """
        if len(parts) < 2:
            return
        
        # position startpos или position fen <FEN>
        if parts[1] == 'startpos':
            self.board = ChessBoard()
            moves_index = 2
        elif parts[1] == 'fen':
            # Собираем FEN строку
            fen_parts = []
            moves_index = 2
            while moves_index < len(parts) and parts[moves_index] != 'moves':
                fen_parts.append(parts[moves_index])
                moves_index += 1
            
            fen = ' '.join(fen_parts)
            self.board = ChessBoard()
            self.board.load_fen(fen)
        else:
            return
        
        # Применяем ходы если есть
        if moves_index < len(parts) and parts[moves_index] == 'moves':
            for move_str in parts[moves_index + 1:]:
                move = self._parse_uci_move(move_str)
                if move:
                    self.board.make_move(move)
                else:
                    self._print_debug(f"Invalid move: {move_str}")
                    break
    
    def _parse_uci_move(self, move_str: str) -> Optional[Move]:
        """
        Парсит ход в UCI формате.
        
        Args:
            move_str: Ход в формате UCI (например, 'e2e4', 'e7e8q')
            
        Returns:
            Объект Move или None
        """
        if len(move_str) < 4:
            return None
        
        from_square = move_str[:2]
        to_square = move_str[2:4]
        
        from_pos = self.board.algebraic_to_coords(from_square)
        to_pos = self.board.algebraic_to_coords(to_square)
        
        # Проверка на превращение
        promotion_piece = None
        if len(move_str) == 5:
            promotion_char = move_str[4].lower()
            is_white = self.board.is_white_piece(self.board.get_piece(*from_pos))
            promotion_piece = promotion_char.upper() if is_white else promotion_char
        
        # Находим соответствующий легальный ход
        move_gen = MoveGenerator(self.board)
        legal_moves = move_gen.generate_legal_moves()
        
        for move in legal_moves:
            if move.from_pos == from_pos and move.to_pos == to_pos:
                if promotion_piece:
                    if move.is_promotion and move.promotion_piece == promotion_piece:
                        return move
                else:
                    return move
        
        return None
    
    def _handle_go(self, parts: list) -> None:
        """
        Обрабатывает команду go.
        
        Args:
            parts: Части команды
        """
        depth = 4  # Глубина по умолчанию
        max_time = None
        
        # Парсинг параметров
        i = 1
        while i < len(parts):
            if parts[i] == 'depth':
                if i + 1 < len(parts):
                    try:
                        depth = int(parts[i + 1])
                        i += 2
                    except ValueError:
                        i += 1
                else:
                    i += 1
            elif parts[i] == 'movetime':
                if i + 1 < len(parts):
                    try:
                        max_time = int(parts[i + 1]) / 1000.0  # Конвертируем мс в секунды
                        i += 2
                    except ValueError:
                        i += 1
                else:
                    i += 1
            elif parts[i] == 'wtime' and self.board.white_to_move:
                if i + 1 < len(parts):
                    try:
                        time_ms = int(parts[i + 1])
                        # Выделяем часть времени на ход
                        max_time = min(time_ms / 30000.0, 5.0)  # Максимум 5 секунд
                        i += 2
                    except ValueError:
                        i += 1
                else:
                    i += 1
            elif parts[i] == 'btime' and not self.board.white_to_move:
                if i + 1 < len(parts):
                    try:
                        time_ms = int(parts[i + 1])
                        max_time = min(time_ms / 30000.0, 5.0)
                        i += 2
                    except ValueError:
                        i += 1
                else:
                    i += 1
            elif parts[i] == 'infinite':
                max_time = None
                depth = 10
                i += 1
            else:
                i += 1
        
        # Поиск лучшего хода
        best_move = self.engine.search(self.board, depth, max_time)
        
        if best_move:
            move_str = best_move.to_uci(self.board)
            print(f"bestmove {move_str}")
            sys.stdout.flush()
            self._print_debug(f"Nodes searched: {self.engine.nodes_searched}")
        else:
            # Нет легальных ходов
            move_gen = MoveGenerator(self.board)
            if move_gen.is_checkmate():
                self._print_debug("Position is checkmate")
            elif move_gen.is_stalemate():
                self._print_debug("Position is stalemate")
            print("bestmove (none)")
            sys.stdout.flush()
    
    def _handle_stop(self) -> None:
        """Обрабатывает команду stop."""
        self.engine.stop()
    
    def _handle_quit(self) -> None:
        """Обрабатывает команду quit."""
        self.running = False
    
    def _print_debug(self, message: str) -> None:
        """
        Выводит отладочное сообщение.
        
        Args:
            message: Сообщение
        """
        if self.debug:
            print(f"info string {message}")
            sys.stdout.flush()


def main():
    """Главная функция для запуска UCI интерфейса."""
    uci = UCIInterface()
    uci.run()


if __name__ == '__main__':
    main()
