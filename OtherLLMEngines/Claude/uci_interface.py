"""
UCI (Universal Chess Interface) протокол для шахматного движка
Позволяет использовать движок с UCI-совместимыми GUI (Arena, Cutechess, etc.)
"""

import sys
from chess_game import GameState, Move, ChessAI

class UCIInterface:
    def __init__(self):
        self.gs = GameState()
        self.depth = 3  # По умолчанию средняя сложность
        
    def uci_command(self):
        """Ответ на команду 'uci'"""
        print("id name PythonChessEngine")
        print("id author Claude")
        print("option name Depth type spin default 3 min 1 max 5")
        print("uciok")
        
    def isready_command(self):
        """Ответ на команду 'isready'"""
        print("readyok")
        
    def setoption_command(self, tokens):
        """Обработка команды 'setoption'"""
        if len(tokens) >= 5 and tokens[1] == "name" and tokens[3] == "value":
            option_name = tokens[2]
            option_value = tokens[4]
            if option_name.lower() == "depth":
                try:
                    self.depth = int(option_value)
                    self.depth = max(1, min(5, self.depth))  # Ограничиваем от 1 до 5
                except ValueError:
                    pass
                    
    def ucinewgame_command(self):
        """Новая игра"""
        self.gs = GameState()
        
    def position_command(self, tokens):
        """Обработка команды 'position'"""
        if len(tokens) < 2:
            return
            
        if tokens[1] == "startpos":
            self.gs = GameState()
            moves_index = -1
            
            # Ищем ключевое слово "moves"
            for i, token in enumerate(tokens):
                if token == "moves":
                    moves_index = i
                    break
                    
            # Применяем ходы если они есть
            if moves_index != -1 and moves_index + 1 < len(tokens):
                for i in range(moves_index + 1, len(tokens)):
                    move_str = tokens[i]
                    self.apply_uci_move(move_str)
                    
    def apply_uci_move(self, move_str):
        """Применяет ход в формате UCI (например, 'e2e4')"""
        if len(move_str) < 4:
            return
            
        # Преобразуем UCI нотацию в координаты доски
        start_col = ord(move_str[0]) - ord('a')
        start_row = 8 - int(move_str[1])
        end_col = ord(move_str[2]) - ord('a')
        end_row = 8 - int(move_str[3])
        
        # Находим соответствующий ход среди возможных
        valid_moves = self.gs.get_valid_moves()
        for move in valid_moves:
            if (move.start_row == start_row and move.start_col == start_col and
                move.end_row == end_row and move.end_col == end_col):
                self.gs.make_move(move)
                return
                
    def go_command(self, tokens):
        """Обработка команды 'go' - найти лучший ход"""
        # Можно обрабатывать параметры типа depth, movetime и т.д.
        depth = self.depth
        
        for i, token in enumerate(tokens):
            if token == "depth" and i + 1 < len(tokens):
                try:
                    depth = int(tokens[i + 1])
                except ValueError:
                    pass
                    
        valid_moves = self.gs.get_valid_moves()
        
        if not valid_moves:
            print("bestmove 0000")  # Нет доступных ходов
            return
            
        # Сохраняем глубину для AI
        ChessAI._current_depth = depth
        best_move = ChessAI.find_best_move(self.gs, valid_moves, depth)
        
        if best_move:
            uci_move = self.move_to_uci(best_move)
            print(f"bestmove {uci_move}")
        else:
            # Если AI не нашёл лучший ход, но есть легальные ходы - выбираем первый
            uci_move = self.move_to_uci(valid_moves[0])
            print(f"bestmove {uci_move}")
            
    def move_to_uci(self, move):
        """Преобразует Move объект в UCI нотацию"""
        start_file = chr(ord('a') + move.start_col)
        start_rank = str(8 - move.start_row)
        end_file = chr(ord('a') + move.end_col)
        end_rank = str(8 - move.end_row)
        
        uci_str = start_file + start_rank + end_file + end_rank
        
        # Добавляем промоцию если есть
        if move.pawn_promotion:
            uci_str += 'q'  # По умолчанию промоция в ферзя
            
        return uci_str
        
    def quit_command(self):
        """Выход из программы"""
        sys.exit(0)
        
    def display_command(self):
        """Показать текущую позицию (не стандартная UCI команда, но полезна для отладки)"""
        print("\n  a b c d e f g h")
        for i, row in enumerate(self.gs.board):
            print(f"{8-i} {' '.join(row)} {8-i}")
        print("  a b c d e f g h\n")
        print(f"Turn: {'White' if self.gs.white_to_move else 'Black'}")
        
    def run(self):
        """Главный цикл UCI интерфейса"""
        while True:
            try:
                line = input().strip()
                if not line:
                    continue
                    
                tokens = line.split()
                command = tokens[0].lower()
                
                if command == "uci":
                    self.uci_command()
                elif command == "isready":
                    self.isready_command()
                elif command == "setoption":
                    self.setoption_command(tokens)
                elif command == "ucinewgame":
                    self.ucinewgame_command()
                elif command == "position":
                    self.position_command(tokens)
                elif command == "go":
                    self.go_command(tokens)
                elif command == "quit":
                    self.quit_command()
                elif command == "display" or command == "d":
                    self.display_command()
                    
            except EOFError:
                break
            except Exception as e:
                print(f"info string Error: {e}", file=sys.stderr)

if __name__ == "__main__":
    uci = UCIInterface()
    uci.run()
