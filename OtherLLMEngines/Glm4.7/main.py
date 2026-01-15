# main.py

import sys
import time
from board import Board
from search import Searcher
import moves # Импортируем для доступа к MoveGenerator

class UCIEngine:
    """Основной класс движка, реализующий протокол UCI."""
    def __init__(self):
        self.board = Board()
        self.searcher = Searcher(self.board)
        self.position_history = []

    def run(self):
        """Главный цикл обработки команд UCI."""
        while True:
            command = sys.stdin.readline().strip()
            if not command:
                continue
            
            parts = command.split()
            if not parts:
                continue

            cmd = parts[0]
            
            if cmd == 'uci':
                self._uci()
            elif cmd == 'isready':
                self._isready()
            elif cmd == 'ucinewgame':
                self._ucinewgame()
            elif cmd == 'position':
                self._position(command)
            elif cmd == 'go':
                self._go(command)
            elif cmd == 'stop':
                self._stop()
            elif cmd == 'quit':
                break
            # Можно добавить свои команды для отладки, например, 'd' (display)
            elif cmd == 'd':
                self._display_board()

    def _uci(self):
        """Отвечает на команду uci."""
        print("id name Python Chess Engine")
        print("id author GLM 4.7")
        print("uciok")

    def _isready(self):
        """Отвечает на команду isready."""
        print("readyok")

    def _ucinewgame(self):
        """Начинает новую игру."""
        self.board.reset_to_start_pos()
        self.position_history = []

    def _position(self, command_str):
        """Устанавливает позицию из команды."""
        parts = command_str.split()
        if parts[1] == 'startpos':
            self.board.reset_to_start_pos()
            moves_idx = 2
        elif parts[1] == 'fen':
            fen_str = " ".join(parts[2:8])
            self.board.load_fen(fen_str)
            moves_idx = 8
        else:
            return

        if 'moves' in parts:
            moves_idx = parts.index('moves') + 1
            for i in range(moves_idx, len(parts)):
                move_str = parts[i]
                from_sq = self.board.algebraic_to_index(move_str[:2])
                to_sq = self.board.algebraic_to_index(move_str[2:4])
                
                promotion_piece = None
                if len(move_str) == 5:
                    promo_char = move_str[4]
                    color = 'w' if self.board.turn == 'b' else 'b' # Ход уже сделан
                    piece_map = {'q': wQ, 'r': wR, 'b': wB, 'n': wN}
                    promotion_piece = piece_map[promo_char]
                    if color == 'b':
                        promotion_piece += 8
                
                # Выполняем ход
                self.board.make_move((from_sq, to_sq, promotion_piece))

    def _go(self, command_str):
        """Запускает поиск лучшего хода."""
        parts = command_str.split()
        depth = 4 # Глубина по умолчанию
        movetime = 0 # Время на ход в мс
        
        for i in range(1, len(parts)):
            if parts[i] == 'depth' and i + 1 < len(parts):
                depth = int(parts[i+1])
            elif parts[i] == 'movetime' and i + 1 < len(parts):
                movetime = int(parts[i+1])
        
        # Запуск поиска в отдельном потоке для поддержки команды stop
        # Для простоты, здесь мы запускаем синхронно, но реальный движок использует потоки.
        best_move = self.searcher.search(depth, movetime)
        
        if best_move:
            from_sq = self.board.index_to_algebraic(best_move[0])
            to_sq = self.board.index_to_algebraic(best_move[1])
            promo = ''
            if best_move[2]:
                promo_map = {wQ: 'q', wR: 'r', wB: 'b', wN: 'n',
                             bQ: 'q', bR: 'r', bB: 'b', bN: 'n'}
                promo = promo_map[best_move[2]]
            print(f"bestmove {from_sq}{to_sq}{promo}")
        else:
            # Если ходов нет (мат/пат), UCI не требует особого ответа,
            # но некоторые GUI ожидают что-то.
            # Просто ничего не делаем.
            pass

    def _stop(self):
        """Останавливает поиск."""
        self.searcher.stop()

    def _display_board(self):
        """Отображает доску в консоли (для отладки)."""
        print("   a b c d e f g h")
        print("  +-----------------+")
        for rank in range(7, -1, -1):
            line = f"{rank+1} | "
            for file in range(8):
                sq = rank * 8 + file
                piece = self.board.get_piece(sq)
                line += f"{self.board.PIECE_SYMBOLS.get(piece, '.')} "
            line += "|"
            print(line)
        print("  +-----------------+")
        print(f"Turn: {self.board.turn}, FEN: {self.board.to_fen()}")


if __name__ == "__main__":
    engine = UCIEngine()
    engine.run()