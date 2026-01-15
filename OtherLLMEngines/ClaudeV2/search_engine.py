"""
Модуль поиска лучшего хода с использованием алгоритма Minimax и альфа-бета отсечения.
"""

from typing import Tuple, Optional, List
from chess_board import ChessBoard, Move
from move_generator import MoveGenerator
import time


class SearchEngine:
    """Класс для поиска лучшего хода."""
    
    # Значения фигур для оценки
    PIECE_VALUES = {
        'p': 100,
        'n': 320,
        'b': 330,
        'r': 500,
        'q': 900,
        'k': 20000
    }
    
    # Таблицы позиционных бонусов для фигур (piece-square tables)
    # Индексы от 0 до 63, где 0 - a8, 7 - h8, 56 - a1, 63 - h1
    
    PAWN_TABLE = [
        0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
        5,  5, 10, 25, 25, 10,  5,  5,
        0,  0,  0, 20, 20,  0,  0,  0,
        5, -5,-10,  0,  0,-10, -5,  5,
        5, 10, 10,-20,-20, 10, 10,  5,
        0,  0,  0,  0,  0,  0,  0,  0
    ]
    
    KNIGHT_TABLE = [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50
    ]
    
    BISHOP_TABLE = [
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -20,-10,-10,-10,-10,-10,-10,-20
    ]
    
    ROOK_TABLE = [
        0,  0,  0,  0,  0,  0,  0,  0,
        5, 10, 10, 10, 10, 10, 10,  5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        0,  0,  0,  5,  5,  0,  0,  0
    ]
    
    QUEEN_TABLE = [
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5,  5,  5,  5,  0,-10,
        -5,  0,  5,  5,  5,  5,  0, -5,
        0,  0,  5,  5,  5,  5,  0, -5,
        -10,  5,  5,  5,  5,  5,  0,-10,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20
    ]
    
    KING_MIDDLE_TABLE = [
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
        20, 20,  0,  0,  0,  0, 20, 20,
        20, 30, 10,  0,  0, 10, 30, 20
    ]
    
    def __init__(self):
        """Инициализация поискового движка."""
        self.nodes_searched = 0
        self.max_time = None
        self.start_time = None
        self.stop_search = False
    
    def search(self, board: ChessBoard, depth: int = 4, max_time: Optional[float] = None) -> Optional[Move]:
        """
        Ищет лучший ход для текущей позиции.
        
        Args:
            board: Шахматная доска
            depth: Глубина поиска
            max_time: Максимальное время на поиск в секундах
            
        Returns:
            Лучший найденный ход или None
        """
        self.nodes_searched = 0
        self.max_time = max_time
        self.start_time = time.time()
        self.stop_search = False
        
        move_gen = MoveGenerator(board)
        legal_moves = move_gen.generate_legal_moves()
        
        if not legal_moves:
            return None
        
        # Сортируем ходы для лучшего отсечения
        legal_moves = self._order_moves(board, legal_moves)
        
        best_move = None
        best_value = float('-inf')
        alpha = float('-inf')
        beta = float('inf')
        
        for move in legal_moves:
            if self._should_stop():
                break
            
            # Делаем ход
            test_board = board.copy()
            test_board.make_move(move)
            
            # Оцениваем позицию
            value = -self._minimax(test_board, depth - 1, -beta, -alpha, False)
            
            if value > best_value:
                best_value = value
                best_move = move
            
            alpha = max(alpha, value)
        
        return best_move
    
    def _minimax(self, board: ChessBoard, depth: int, alpha: float, beta: float, 
                 maximizing: bool) -> float:
        """
        Алгоритм Minimax с альфа-бета отсечением.
        
        Args:
            board: Шахматная доска
            depth: Глубина поиска
            alpha: Альфа значение
            beta: Бета значение
            maximizing: True если максимизируем
            
        Returns:
            Оценка позиции
        """
        self.nodes_searched += 1
        
        if self._should_stop():
            return 0
        
        # Проверка на окончание игры
        move_gen = MoveGenerator(board)
        
        if depth == 0:
            return self._quiescence_search(board, alpha, beta, 3)
        
        legal_moves = move_gen.generate_legal_moves()
        
        if not legal_moves:
            if move_gen.is_in_check():
                # Мат
                return -20000 + (10 - depth)  # Быстрый мат лучше
            else:
                # Пат
                return 0
        
        # Сортируем ходы
        legal_moves = self._order_moves(board, legal_moves)
        
        if maximizing:
            max_eval = float('-inf')
            for move in legal_moves:
                if self._should_stop():
                    break
                
                test_board = board.copy()
                test_board.make_move(move)
                eval_score = self._minimax(test_board, depth - 1, alpha, beta, False)
                max_eval = max(max_eval, eval_score)
                alpha = max(alpha, eval_score)
                
                if beta <= alpha:
                    break  # Бета отсечение
            
            return max_eval
        else:
            min_eval = float('inf')
            for move in legal_moves:
                if self._should_stop():
                    break
                
                test_board = board.copy()
                test_board.make_move(move)
                eval_score = self._minimax(test_board, depth - 1, alpha, beta, True)
                min_eval = min(min_eval, eval_score)
                beta = min(beta, eval_score)
                
                if beta <= alpha:
                    break  # Альфа отсечение
            
            return min_eval
    
    def _quiescence_search(self, board: ChessBoard, alpha: float, beta: float, 
                           depth: int) -> float:
        """
        Quiescence search - поиск спокойных позиций для избежания горизонт-эффекта.
        
        Args:
            board: Шахматная доска
            alpha: Альфа значение
            beta: Бета значение
            depth: Оставшаяся глубина
            
        Returns:
            Оценка позиции
        """
        self.nodes_searched += 1
        
        if self._should_stop() or depth == 0:
            return self.evaluate(board)
        
        stand_pat = self.evaluate(board)
        
        if stand_pat >= beta:
            return beta
        
        if alpha < stand_pat:
            alpha = stand_pat
        
        move_gen = MoveGenerator(board)
        legal_moves = move_gen.generate_legal_moves()
        
        # Рассматриваем только взятия
        capture_moves = [move for move in legal_moves if move.is_capture]
        capture_moves = self._order_moves(board, capture_moves)
        
        for move in capture_moves:
            if self._should_stop():
                break
            
            test_board = board.copy()
            test_board.make_move(move)
            
            score = -self._quiescence_search(test_board, -beta, -alpha, depth - 1)
            
            if score >= beta:
                return beta
            
            if score > alpha:
                alpha = score
        
        return alpha
    
    def _order_moves(self, board: ChessBoard, moves: List[Move]) -> List[Move]:
        """
        Сортирует ходы для оптимизации альфа-бета отсечения.
        
        Args:
            board: Шахматная доска
            moves: Список ходов
            
        Returns:
            Отсортированный список ходов
        """
        def move_priority(move: Move) -> int:
            priority = 0
            
            # Приоритет взятиям
            if move.is_capture:
                # MVV-LVA (Most Valuable Victim - Least Valuable Attacker)
                victim_value = self.PIECE_VALUES.get(move.captured_piece.lower(), 0)
                attacker_value = self.PIECE_VALUES.get(move.piece.lower(), 0)
                priority += 10 * victim_value - attacker_value
            
            # Превращение пешки
            if move.is_promotion:
                priority += 800
            
            # Центральные поля
            to_row, to_col = move.to_pos
            if 2 <= to_row <= 5 and 2 <= to_col <= 5:
                priority += 10
            
            return priority
        
        return sorted(moves, key=move_priority, reverse=True)
    
    def evaluate(self, board: ChessBoard) -> float:
        """
        Оценивает позицию на доске.
        
        Args:
            board: Шахматная доска
            
        Returns:
            Оценка позиции (положительная для белых, отрицательная для черных)
        """
        move_gen = MoveGenerator(board)
        
        # Проверка на мат и пат
        legal_moves = move_gen.generate_legal_moves()
        if not legal_moves:
            if move_gen.is_in_check():
                # Мат
                return -20000 if board.white_to_move else 20000
            else:
                # Пат
                return 0
        
        score = 0
        
        # Материал и позиционная оценка
        for row in range(8):
            for col in range(8):
                piece = board.get_piece(row, col)
                if piece == ChessBoard.EMPTY:
                    continue
                
                piece_value = self._evaluate_piece(piece, row, col)
                
                if board.is_white_piece(piece):
                    score += piece_value
                else:
                    score -= piece_value
        
        # Мобильность (количество доступных ходов)
        if board.white_to_move:
            score += len(legal_moves) * 10
        else:
            score -= len(legal_moves) * 10
        
        return score
    
    def _evaluate_piece(self, piece: str, row: int, col: int) -> int:
        """
        Оценивает стоимость фигуры с учетом позиции.
        
        Args:
            piece: Фигура
            row: Строка
            col: Колонка
            
        Returns:
            Оценка фигуры
        """
        piece_type = piece.lower()
        is_white = piece.isupper()
        
        # Базовая стоимость
        value = self.PIECE_VALUES.get(piece_type, 0)
        
        # Позиционный бонус
        square_index = row * 8 + col
        
        # Для черных инвертируем таблицу
        if not is_white:
            square_index = (7 - row) * 8 + col
        
        if piece_type == 'p':
            value += self.PAWN_TABLE[square_index]
        elif piece_type == 'n':
            value += self.KNIGHT_TABLE[square_index]
        elif piece_type == 'b':
            value += self.BISHOP_TABLE[square_index]
        elif piece_type == 'r':
            value += self.ROOK_TABLE[square_index]
        elif piece_type == 'q':
            value += self.QUEEN_TABLE[square_index]
        elif piece_type == 'k':
            value += self.KING_MIDDLE_TABLE[square_index]
        
        return value
    
    def _should_stop(self) -> bool:
        """
        Проверяет, нужно ли остановить поиск.
        
        Returns:
            True если нужно остановить
        """
        if self.stop_search:
            return True
        
        if self.max_time and self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed >= self.max_time:
                return True
        
        return False
    
    def stop(self) -> None:
        """Останавливает текущий поиск."""
        self.stop_search = True
