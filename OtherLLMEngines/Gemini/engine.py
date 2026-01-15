import sys
import time
import copy

# --- 1. Константы и Настройки ---

# Фигуры
EMPTY = 0
PAWN = 1
KNIGHT = 2
BISHOP = 3
ROOK = 4
QUEEN = 5
KING = 6

# Цвета
WHITE = 8
BLACK = 16

# Оценка материала (P, N, B, R, Q, K)
PIECE_VALUES = {
    PAWN: 100,
    KNIGHT: 320,
    BISHOP: 330,
    ROOK: 500,
    QUEEN: 900,
    KING: 20000
}

# Таблицы ценности полей (PST) для улучшения позиционной игры
# Перевернуты для черных автоматически в функции оценки
PST_PAWN = [
    0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
    5,  5, 10, 25, 25, 10,  5,  5,
    0,  0,  0, 20, 20,  0,  0,  0,
    5, -5,-10,  0,  0,-10, -5,  5,
    5, 10, 10,-20,-20, 10, 10,  5,
    0,  0,  0,  0,  0,  0,  0,  0
]

PST_KNIGHT = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]

# Направления движения фигур (смещения индексов в массиве 120 полей, см. ниже)
# Для упрощения используем представление 64 клетки, но логику проверки краев.
# A1=56, H1=63 ... A8=0, H8=7 (стандартная FEN ориентация в массиве)

# Преобразование координат (0..63)
SQUARES = [
    'a8', 'b8', 'c8', 'd8', 'e8', 'f8', 'g8', 'h8',
    'a7', 'b7', 'c7', 'd7', 'e7', 'f7', 'g7', 'h7',
    'a6', 'b6', 'c6', 'd6', 'e6', 'f6', 'g6', 'h6',
    'a5', 'b5', 'c5', 'd5', 'e5', 'f5', 'g5', 'h5',
    'a4', 'b4', 'c4', 'd4', 'e4', 'f4', 'g4', 'h4',
    'a3', 'b3', 'c3', 'd3', 'e3', 'f3', 'g3', 'h3',
    'a2', 'b2', 'c2', 'd2', 'e2', 'f2', 'g2', 'h2',
    'a1', 'b1', 'c1', 'd1', 'e1', 'f1', 'g1', 'h1'
]

# --- 2. Класс Доски (Логика и Правила) ---

class Board:
    def __init__(self):
        self.board = [EMPTY] * 64
        self.side_to_move = WHITE
        self.en_passant_sq = None  # Индекс клетки или None
        self.castling_rights = 0b1111  # KQkq (1: K, 2: Q, 4: k, 8: q)
        self.half_move_clock = 0
        self.full_move_number = 1
        self.move_history = [] # Для отмены ходов и проверок повторений

    def parse_fen(self, fen):
        """Загрузка позиции из FEN строки."""
        parts = fen.split()
        rows = parts[0].split('/')
        self.board = [EMPTY] * 64
        
        sq = 0
        for row in rows:
            for char in row:
                if char.isdigit():
                    sq += int(char)
                else:
                    color = WHITE if char.isupper() else BLACK
                    piece_type = {'p': PAWN, 'n': KNIGHT, 'b': BISHOP, 'r': ROOK, 'q': QUEEN, 'k': KING}[char.lower()]
                    self.board[sq] = color | piece_type
                    sq += 1
        
        self.side_to_move = WHITE if parts[1] == 'w' else BLACK
        
        self.castling_rights = 0
        if 'K' in parts[2]: self.castling_rights |= 1
        if 'Q' in parts[2]: self.castling_rights |= 2
        if 'k' in parts[2]: self.castling_rights |= 4
        if 'q' in parts[2]: self.castling_rights |= 8
        
        if parts[3] != '-':
            col = ord(parts[3][0]) - ord('a')
            row = 8 - int(parts[3][1])
            self.en_passant_sq = row * 8 + col
        else:
            self.en_passant_sq = None
            
        self.half_move_clock = int(parts[4]) if len(parts) > 4 else 0
        self.full_move_number = int(parts[5]) if len(parts) > 5 else 1

    def is_square_attacked(self, sq, by_color):
        """Проверка, атакована ли клетка sq фигурами цвета by_color."""
        # Пешки
        pawn_dir = -8 if by_color == WHITE else 8
        opp_pawn = by_color | PAWN
        # Атака пешки идет по диагонали назад от цели
        for dx in [-1, 1]:
            attacker_sq = sq - pawn_dir + dx # Ищем пешку "сзади" (относительно хода пешки)
            if 0 <= attacker_sq < 64:
                col_diff = abs((sq % 8) - (attacker_sq % 8))
                if col_diff == 1 and self.board[attacker_sq] == opp_pawn:
                    return True

        # Конь
        knight_offsets = [-17, -15, -10, -6, 6, 10, 15, 17]
        for offset in knight_offsets:
            target = sq + offset
            if 0 <= target < 64:
                # Проверка перескока края доски
                current_col = sq % 8
                target_col = target % 8
                if abs(current_col - target_col) > 2: continue
                if self.board[target] == (by_color | KNIGHT):
                    return True

        # Король (для проверки атак)
        king_offsets = [-9, -8, -7, -1, 1, 7, 8, 9]
        for offset in king_offsets:
            target = sq + offset
            if 0 <= target < 64:
                current_col = sq % 8
                target_col = target % 8
                if abs(current_col - target_col) > 1: continue
                if self.board[target] == (by_color | KING):
                    return True
        
        # Скользящие фигуры (Слон/Ферзь и Ладья/Ферзь)
        dirs_diag = [-9, -7, 7, 9]
        dirs_ortho = [-8, -1, 1, 8]
        
        # Диагонали (Слон, Ферзь)
        for d in dirs_diag:
            curr = sq
            while True:
                curr += d
                if not (0 <= curr < 64): break
                # Проверка перехода строки
                curr_col = (curr - d) % 8
                next_col = curr % 8
                if abs(curr_col - next_col) > 1: break 
                
                piece = self.board[curr]
                if piece != EMPTY:
                    if piece == (by_color | BISHOP) or piece == (by_color | QUEEN):
                        return True
                    break

        # Прямые (Ладья, Ферзь)
        for d in dirs_ortho:
            curr = sq
            while True:
                curr += d
                if not (0 <= curr < 64): break
                if abs((curr - d) % 8 - (curr % 8)) > 1: break # Перескок строки для горизонт. ходов
                
                piece = self.board[curr]
                if piece != EMPTY:
                    if piece == (by_color | ROOK) or piece == (by_color | QUEEN):
                        return True
                    break
        return False

    def generate_moves(self):
        """Генерация всех псевдолегальных ходов."""
        moves = []
        color = self.side_to_move
        opp_color = BLACK if color == WHITE else WHITE
        
        for sq in range(64):
            piece = self.board[sq]
            if piece == EMPTY or (piece & color) == 0:
                continue
            
            p_type = piece & 7
            
            # --- Пешка ---
            if p_type == PAWN:
                direction = -8 if color == WHITE else 8
                start_row = 6 if color == WHITE else 1
                curr_row = sq // 8
                
                # Тихий ход на 1 клетку
                target = sq + direction
                if 0 <= target < 64 and self.board[target] == EMPTY:
                    # Превращение
                    if (color == WHITE and target < 8) or (color == BLACK and target >= 56):
                        for promo in [QUEEN, ROOK, BISHOP, KNIGHT]:
                            moves.append((sq, target, promo))
                    else:
                        moves.append((sq, target, None))
                        
                        # Двойной ход
                        if curr_row == start_row:
                            target2 = sq + (direction * 2)
                            if self.board[target2] == EMPTY:
                                moves.append((sq, target2, None))
                
                # Взятия
                for dx in [-1, 1]:
                    target = sq + direction + dx
                    if 0 <= target < 64 and abs((target % 8) - (sq % 8)) == 1:
                        # Обычное взятие
                        if self.board[target] != EMPTY and (self.board[target] & opp_color):
                            # Превращение при взятии
                            if (color == WHITE and target < 8) or (color == BLACK and target >= 56):
                                for promo in [QUEEN, ROOK, BISHOP, KNIGHT]:
                                    moves.append((sq, target, promo))
                            else:
                                moves.append((sq, target, None))
                        # Взятие на проходе
                        elif target == self.en_passant_sq:
                            moves.append((sq, target, None)) # is_en_passant флаг не нужен, определим по контексту

            # --- Конь ---
            elif p_type == KNIGHT:
                offsets = [-17, -15, -10, -6, 6, 10, 15, 17]
                for o in offsets:
                    target = sq + o
                    if 0 <= target < 64:
                        if abs((sq % 8) - (target % 8)) <= 2:
                            if self.board[target] == EMPTY or (self.board[target] & opp_color):
                                moves.append((sq, target, None))

            # --- Король ---
            elif p_type == KING:
                offsets = [-9, -8, -7, -1, 1, 7, 8, 9]
                for o in offsets:
                    target = sq + o
                    if 0 <= target < 64:
                        if abs((sq % 8) - (target % 8)) <= 1:
                            if self.board[target] == EMPTY or (self.board[target] & opp_color):
                                moves.append((sq, target, None))
                
                # Рокировка
                # Не под шахом
                if not self.is_square_attacked(sq, opp_color):
                    # Короткая (K/k)
                    if (color == WHITE and (self.castling_rights & 1)) or (color == BLACK and (self.castling_rights & 4)):
                        if self.board[sq+1] == EMPTY and self.board[sq+2] == EMPTY:
                            if not self.is_square_attacked(sq+1, opp_color) and not self.is_square_attacked(sq+2, opp_color):
                                moves.append((sq, sq+2, None))
                    # Длинная (Q/q)
                    if (color == WHITE and (self.castling_rights & 2)) or (color == BLACK and (self.castling_rights & 8)):
                        if self.board[sq-1] == EMPTY and self.board[sq-2] == EMPTY and self.board[sq-3] == EMPTY:
                            if not self.is_square_attacked(sq-1, opp_color) and not self.is_square_attacked(sq-2, opp_color):
                                moves.append((sq, sq-2, None))

            # --- Слон, Ладья, Ферзь ---
            else:
                dirs = []
                if p_type == BISHOP or p_type == QUEEN:
                    dirs.extend([-9, -7, 7, 9])
                if p_type == ROOK or p_type == QUEEN:
                    dirs.extend([-8, -1, 1, 8])
                
                for d in dirs:
                    curr = sq
                    while True:
                        curr += d
                        if not (0 <= curr < 64): break
                        # Проверка горизонтальных переходов
                        if abs((curr - d) % 8 - (curr % 8)) > 1: break 

                        if self.board[curr] == EMPTY:
                            moves.append((sq, curr, None))
                        elif self.board[curr] & opp_color:
                            moves.append((sq, curr, None))
                            break
                        else: # Своя фигура
                            break
        return moves

    def make_move(self, move):
        """Выполняет ход и обновляет состояние. Возвращает False, если ход нелегален (король под шахом)."""
        # Сохраняем состояние для отката
        state = {
            'board': list(self.board),
            'turn': self.side_to_move,
            'ep': self.en_passant_sq,
            'castling': self.castling_rights,
            'clock': self.half_move_clock,
            'full': self.full_move_number
        }
        self.move_history.append(state)

        start, end, promo = move
        piece = self.board[start]
        p_type = piece & 7
        target_piece = self.board[end]

        # Обнуляем счетчик 50 ходов, если пешка или взятие
        if p_type == PAWN or target_piece != EMPTY:
            self.half_move_clock = 0
        else:
            self.half_move_clock += 1

        # Логика перемещения
        self.board[end] = piece
        self.board[start] = EMPTY
        
        # Превращение пешки
        if promo:
            self.board[end] = self.side_to_move | promo

        # Взятие на проходе
        if p_type == PAWN and end == self.en_passant_sq:
            # Удаляем пешку соперника
            offset = 8 if self.side_to_move == WHITE else -8
            self.board[end + offset] = EMPTY

        # Обновление флага en passant
        self.en_passant_sq = None
        if p_type == PAWN and abs(start - end) == 16:
            self.en_passant_sq = (start + end) // 2

        # Рокировка (перемещение ладьи)
        if p_type == KING and abs(start - end) == 2:
            # Короткая
            if end > start:
                rook_start, rook_end = start + 3, start + 1
            # Длинная
            else:
                rook_start, rook_end = start - 4, start - 1
            
            # Перемещаем ладью
            self.board[rook_end] = self.board[rook_start]
            self.board[rook_start] = EMPTY

        # Обновление прав на рокировку
        # Если король или ладья двигаются/берутся, права теряются
        self.castling_rights &= self._get_castling_mask(start)
        self.castling_rights &= self._get_castling_mask(end)

        # Смена очереди хода
        self.side_to_move = BLACK if self.side_to_move == WHITE else WHITE
        if self.side_to_move == WHITE:
            self.full_move_number += 1

        # Проверка легальности (не остался ли король под шахом)
        # Находим короля того, кто сделал ход
        my_color = BLACK if self.side_to_move == WHITE else WHITE
        king_sq = -1
        for i in range(64):
            if self.board[i] == (my_color | KING):
                king_sq = i
                break
        
        if self.is_square_attacked(king_sq, self.side_to_move): # side_to_move уже соперника
            self.unmake_move()
            return False
            
        return True

    def unmake_move(self):
        """Откат последнего хода."""
        if not self.move_history: return
        state = self.move_history.pop()
        self.board = state['board']
        self.side_to_move = state['turn']
        self.en_passant_sq = state['ep']
        self.castling_rights = state['castling']
        self.half_move_clock = state['clock']
        self.full_move_number = state['full']

    def _get_castling_mask(self, sq):
        # Возвращает маску, которую нужно применить (AND) к правам рокировки
        # 0 - a8, 7 - h8, 56 - a1, 63 - h1
        # Права: 1-K(h1), 2-Q(a1), 4-k(h8), 8-q(a8)
        mask = 0b1111
        if sq == 63: mask &= ~1 # Белая ладья h1
        if sq == 56: mask &= ~2 # Белая ладья a1
        if sq == 60: mask &= ~3 # Белый король e1
        if sq == 7: mask &= ~4  # Черная ладья h8
        if sq == 0: mask &= ~8  # Черная ладья a8
        if sq == 4: mask &= ~12 # Черный король e8
        return mask
        
    def get_legal_moves(self):
        moves = self.generate_moves()
        legal_moves = []
        for move in moves:
            if self.make_move(move):
                legal_moves.append(move)
                self.unmake_move()
        return legal_moves

# --- 3. Модуль Поиска и Оценки ---

class Searcher:
    def __init__(self, board):
        self.board = board
        self.nodes_visited = 0
        self.start_time = 0
        self.time_limit = 0

    def evaluate(self):
        """Оценочная функция: Материал + Позиция."""
        score = 0
        for i in range(64):
            piece = self.board.board[i]
            if piece == EMPTY: continue
            
            p_type = piece & 7
            color = piece & 24 # 8 or 16
            
            # Базовая ценность
            val = PIECE_VALUES[p_type]
            
            # Позиционная оценка (только для пешек и коней для краткости)
            pst_val = 0
            if p_type == PAWN:
                pst_val = PST_PAWN[i] if color == WHITE else PST_PAWN[63 - i]
            elif p_type == KNIGHT:
                pst_val = PST_KNIGHT[i] if color == WHITE else PST_KNIGHT[63 - i]
            
            total = val + pst_val
            
            if color == WHITE:
                score += total
            else:
                score -= total
                
        # Возвращаем оценку со стороны того, чей ход (Negamax)
        return score if self.board.side_to_move == WHITE else -score

    def order_moves(self, moves):
        """Сортировка ходов: взятия первыми."""
        # Простая эвристика: взятие более ценной фигуры
        def score_move(move):
            start, end, _ = move
            victim = self.board.board[end] & 7
            if victim:
                return 10 * victim - (self.board.board[start] & 7)
            return 0
        
        return sorted(moves, key=score_move, reverse=True)

    def negamax(self, depth, alpha, beta):
        self.nodes_visited += 1
        
        # Проверка времени
        if self.nodes_visited % 2048 == 0:
            if time.time() - self.start_time > self.time_limit:
                raise TimeoutError

        # Условие выхода для листа
        if depth == 0:
            return self.evaluate()
        
        legal_moves = self.board.get_legal_moves()
        
        # Проверка конца игры
        if not legal_moves:
            # Если шах - мат, иначе пат
            king_sq = -1
            my_color = self.board.side_to_move
            for i in range(64):
                if self.board.board[i] == (my_color | KING):
                    king_sq = i
                    break
            
            opp_color = BLACK if my_color == WHITE else WHITE
            if self.board.is_square_attacked(king_sq, opp_color):
                return -50000 + (100 - depth) # Мат, предпочтение более быстрому
            return 0 # Пат

        legal_moves = self.order_moves(legal_moves)
        
        best_val = -float('inf')
        
        for move in legal_moves:
            self.board.make_move(move)
            val = -self.negamax(depth - 1, -beta, -alpha)
            self.board.unmake_move()
            
            if val > best_val:
                best_val = val
            
            alpha = max(alpha, best_val)
            if alpha >= beta:
                break # Отсечение
                
        return best_val

    def find_best_move(self, depth=3, move_time=5.0):
        self.start_time = time.time()
        self.time_limit = move_time
        self.nodes_visited = 0
        
        best_move = None
        
        # Итеративное углубление (упрощенное)
        try:
            for d in range(1, depth + 1):
                best_val = -float('inf')
                alpha = -float('inf')
                beta = float('inf')
                
                legal_moves = self.board.get_legal_moves()
                legal_moves = self.order_moves(legal_moves)
                
                if not legal_moves: break

                current_best_in_depth = legal_moves[0]
                
                for move in legal_moves:
                    self.board.make_move(move)
                    val = -self.negamax(d - 1, -beta, -alpha)
                    self.board.unmake_move()
                    
                    if val > best_val:
                        best_val = val
                        current_best_in_depth = move
                    
                    alpha = max(alpha, best_val)
                
                best_move = current_best_in_depth
                
                # Простейший вывод info
                elapsed = time.time() - self.start_time
                nps = int(self.nodes_visited / (elapsed + 0.001))
                print(f"info depth {d} score cp {int(best_val)} nodes {self.nodes_visited} nps {nps} pv {self.format_move(best_move)}")
                
        except TimeoutError:
            pass # Возвращаем лучший найденный ход
            
        return best_move

    def format_move(self, move):
        start, end, promo = move
        m = SQUARES[start] + SQUARES[end]
        if promo:
            m += {QUEEN: 'q', ROOK: 'r', BISHOP: 'b', KNIGHT: 'n'}[promo]
        return m

# --- 4. UCI Интерфейс ---

class UCI:
    def __init__(self):
        self.board = Board()
        self.searcher = Searcher(self.board)
        self.board.parse_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

    def input_loop(self):
        while True:
            try:
                line = input().strip()
                if not line: continue
                self.handle_command(line)
            except EOFError:
                break
            except Exception as e:
                # В продакшене лучше логировать, здесь игнорируем, чтобы не крашить движок
                continue

    def handle_command(self, line):
        parts = line.split()
        cmd = parts[0]
        
        if cmd == 'uci':
            print("id name SimplePythonEngine 1.0")
            print("id author User")
            print("uciok")
            
        elif cmd == 'isready':
            print("readyok")
            
        elif cmd == 'ucinewgame':
            self.board.parse_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
            
        elif cmd == 'position':
            # position startpos moves e2e4 ...
            # position fen ... moves ...
            idx = 0
            if parts[1] == 'startpos':
                self.board.parse_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
                idx = 2
            elif parts[1] == 'fen':
                # Склеиваем fen (обычно 6 частей)
                fen_parts = []
                idx = 2
                while idx < len(parts) and parts[idx] != 'moves':
                    fen_parts.append(parts[idx])
                    idx += 1
                self.board.parse_fen(" ".join(fen_parts))
            
            if idx < len(parts) and parts[idx] == 'moves':
                for move_str in parts[idx+1:]:
                    self.apply_uci_move(move_str)
                    
        elif cmd == 'go':
            # Парсинг параметров go (depth, wtime, btime и т.д.)
            depth = 4 # Стандартная глубина
            movetime = 5.0
            
            # Простой парсинг wtime/btime для управления временем
            wtime = None
            btime = None
            
            for i in range(1, len(parts)):
                if parts[i] == 'depth': depth = int(parts[i+1])
                if parts[i] == 'movetime': movetime = int(parts[i+1]) / 1000.0
                if parts[i] == 'wtime': wtime = int(parts[i+1])
                if parts[i] == 'btime': btime = int(parts[i+1])

            # Автоматический расчет времени, если даны часы
            if wtime is not None and btime is not None:
                remaining = wtime if self.board.side_to_move == WHITE else btime
                movetime = (remaining / 1000.0) / 30.0 # Примерно 1/30 оставшегося времени

            best_move = self.searcher.find_best_move(depth=depth, move_time=movetime)
            if best_move:
                print(f"bestmove {self.searcher.format_move(best_move)}")
            else:
                # Пат или мат, но протокол требует ответа
                print("bestmove 0000")

        elif cmd == 'quit':
            sys.exit()

    def apply_uci_move(self, move_str):
        start_sq = SQUARES.index(move_str[:2])
        end_sq = SQUARES.index(move_str[2:4])
        promo = None
        if len(move_str) > 4:
            promo = {'q': QUEEN, 'r': ROOK, 'b': BISHOP, 'n': KNIGHT}[move_str[4]]
        
        move = (start_sq, end_sq, promo)
        # Мы предполагаем, что GUI шлет только легальные ходы
        self.board.make_move(move)

if __name__ == "__main__":
    uci = UCI()
    uci.input_loop()