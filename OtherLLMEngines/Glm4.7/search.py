# search.py

import time
import random
from board import *

class Searcher:
    """Класс для поиска лучшего хода."""
    def __init__(self, board):
        self.board = board
        self.move_gen = None
        self.searching = False
        self.start_time = 0
        self.time_limit = 0
        
        # Таблицы ценностей фигур
        self.piece_values = {
            wP: 100, wN: 320, wB: 330, wR: 500, wQ: 900, wK: 20000,
            bP: -100, bN: -320, bB: -330, bR: -500, bQ: -900, bK: -20000
        }

        # Позиционные таблицы (PST - Piece-Square Tables)
        # Упрощенные PST для примера
        self.pst_pawn = [
            0,  0,  0,  0,  0,  0,  0,  0,
            50, 50, 50, 50, 50, 50, 50, 50,
            10, 10, 20, 30, 30, 20, 10, 10,
            5,  5, 10, 25, 25, 10,  5,  5,
            0,  0,  0, 20, 20,  0,  0,  0,
            5, -5,-10,  0,  0,-10, -5,  5,
            5, 10, 10,-20,-20, 10, 10,  5,
            0,  0,  0,  0,  0,  0,  0,  0
        ]
        self.pst_knight = [
            -50,-40,-30,-30,-30,-30,-40,-50,
            -40,-20,  0,  0,  0,  0,-20,-40,
            -30,  0, 10, 15, 15, 10,  0,-30,
            -30,  5, 15, 20, 20, 15,  5,-30,
            -30,  0, 15, 20, 20, 15,  0,-30,
            -30,  5, 10, 15, 15, 10,  5,-30,
            -40,-20,  0,  5,  5,  0,-20,-40,
            -50,-40,-30,-30,-30,-30,-40,-50,
        ]

    def search(self, depth, time_limit=0):
        """Запускает поиск лучшего хода."""
        self.move_gen = moves.MoveGenerator(self.board)
        self.searching = True
        self.start_time = time.time()
        self.time_limit = time_limit

        best_move = None
        # Итеративное углубление для лучшего использования времени
        for d in range(1, depth + 1):
            if not self.searching: break
            # Если есть лимит времени и мы его превышаем, выходим
            if time_limit > 0 and (time.time() - self.start_time) * 1000 > time_limit:
                break
            
            moves = self.move_gen.generate_moves()
            if not moves:
                return None # Мат или пат
            
            # Перемешивание ходов для разнообразия в равных позициях
            random.shuffle(moves)
            
            max_eval = -float('inf')
            current_best_move = None
            
            for move in moves:
                undo_info = self.board.make_move(move)
                
                # Если ход нелегальный (оставляет короля под шахом), пропускаем
                # (хотя generate_moves уже должен это фильтровать)
                if self.board.is_square_attacked(self._find_king('b' if self.board.turn == 'w' else 'w'), self.board.turn):
                    self.board.unmake_move(undo_info)
                    continue

                eval = self._alpha_beta(d - 1, -float('inf'), float('inf'), False)
                self.board.unmake_move(undo_info)

                if eval > max_eval:
                    max_eval = eval
                    current_best_move = move
            
            if current_best_move:
                best_move = current_best_move

        self.searching = False
        return best_move

    def _alpha_beta(self, depth, alpha, beta, is_null_move):
        """Рекурсивный алгоритм Alpha-Beta."""
        if not self.searching or (self.time_limit > 0 and (time.time() - self.start_time) * 1000 > self.time_limit):
            return 0

        # Условия выхода из рекурсии
        if depth == 0:
            return self._evaluate()
        
        moves = self.move_gen.generate_moves()
        if not moves:
            if self.board.is_square_attacked(self._find_king(self.board.turn), 'b' if self.board.turn == 'w' else 'w'):
                return -10000 - depth # Мат (чем быстрее, тем лучше)
            else:
                return 0 # Пат

        # Упорядочивание ходов: сначала взятия
        moves.sort(key=lambda move: self.board.get_piece(move[1]) != EMPTY, reverse=True)

        for move in moves:
            undo_info = self.board.make_move(move)
            eval = -self._alpha_beta(depth - 1, -beta, -alpha, False)
            self.board.unmake_move(undo_info)
            
            if eval >= beta:
                return beta # Beta-cutoff
            if eval > alpha:
                alpha = eval
        
        return alpha

    def _evaluate(self):
        """Оценочная функция позиции."""
        eval = 0
        for sq in range(64):
            piece = self.board.get_piece(sq)
            if piece == EMPTY:
                continue
            
            # Материальная ценность
            eval += self.piece_values.get(piece, 0)
            
            # Позиционная ценность
            piece_type = piece % 8
            # Для черных фигур инвертируем таблицу
            if piece > wK:
                sq_pst = 63 - sq
            else:
                sq_pst = sq

            if piece_type == wP % 8:
                eval += self.pst_pawn[sq_pst] if piece < wK else -self.pst_pawn[sq_pst]
            elif piece_type == wN % 8:
                eval += self.pst_knight[sq_pst] if piece < wK else -self.pst_knight[sq_pst]
        
        return eval if self.board.turn == 'w' else -eval

    def _find_king(self, color):
        """Находит короля (аналогично в moves.py)."""
        king_piece = wK if color == 'w' else bK
        for sq in range(64):
            if self.board.get_piece(sq) == king_piece:
                return sq
        return -1

    def stop(self):
        """Останавливает поиск."""
        self.searching = False