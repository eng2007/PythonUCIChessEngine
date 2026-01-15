"""
Модуль представления шахматной доски и базовых операций.
"""

from typing import List, Tuple, Optional, Set
from copy import deepcopy


class ChessBoard:
    """Класс для представления шахматной доски и позиции."""
    
    # Константы для фигур
    EMPTY = '.'
    
    # Белые фигуры
    WHITE_PAWN = 'P'
    WHITE_KNIGHT = 'N'
    WHITE_BISHOP = 'B'
    WHITE_ROOK = 'R'
    WHITE_QUEEN = 'Q'
    WHITE_KING = 'K'
    
    # Черные фигуры
    BLACK_PAWN = 'p'
    BLACK_KNIGHT = 'n'
    BLACK_BISHOP = 'b'
    BLACK_ROOK = 'r'
    BLACK_QUEEN = 'q'
    BLACK_KING = 'k'
    
    # Наборы фигур
    WHITE_PIECES = {WHITE_PAWN, WHITE_KNIGHT, WHITE_BISHOP, WHITE_ROOK, WHITE_QUEEN, WHITE_KING}
    BLACK_PIECES = {BLACK_PAWN, BLACK_KNIGHT, BLACK_BISHOP, BLACK_ROOK, BLACK_QUEEN, BLACK_KING}
    ALL_PIECES = WHITE_PIECES | BLACK_PIECES
    
    def __init__(self):
        """Инициализация доски в начальной позиции."""
        self.board = self._create_initial_board()
        self.white_to_move = True
        self.castling_rights = {
            'K': True,  # Белые короткая рокировка
            'Q': True,  # Белые длинная рокировка
            'k': True,  # Черные короткая рокировка
            'q': True   # Черные длинная рокировка
        }
        self.en_passant_square = None  # Поле для взятия на проходе (алгебраическая нотация)
        self.halfmove_clock = 0  # Счетчик полуходов для правила 50 ходов
        self.fullmove_number = 1  # Номер хода
        self.position_history = []  # История позиций для проверки троекратного повторения
        
    def _create_initial_board(self) -> List[List[str]]:
        """Создает начальную расстановку фигур."""
        board = [
            ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],  # 8-я горизонталь (черные)
            ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],  # 7-я горизонталь
            ['.', '.', '.', '.', '.', '.', '.', '.'],  # 6-я
            ['.', '.', '.', '.', '.', '.', '.', '.'],  # 5-я
            ['.', '.', '.', '.', '.', '.', '.', '.'],  # 4-я
            ['.', '.', '.', '.', '.', '.', '.', '.'],  # 3-я
            ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],  # 2-я горизонталь (белые)
            ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']   # 1-я горизонталь
        ]
        return board
    
    def load_fen(self, fen: str) -> None:
        """
        Загружает позицию из FEN нотации.
        
        Args:
            fen: Строка в формате FEN
        """
        parts = fen.split()
        
        # Разбор позиции фигур
        rows = parts[0].split('/')
        self.board = []
        for row in rows:
            board_row = []
            for char in row:
                if char.isdigit():
                    board_row.extend([self.EMPTY] * int(char))
                else:
                    board_row.append(char)
            self.board.append(board_row)
        
        # Чья очередь ходить
        self.white_to_move = (parts[1] == 'w')
        
        # Права на рокировку
        castling = parts[2]
        self.castling_rights = {
            'K': 'K' in castling,
            'Q': 'Q' in castling,
            'k': 'k' in castling,
            'q': 'q' in castling
        }
        
        # En passant
        self.en_passant_square = None if parts[3] == '-' else parts[3]
        
        # Счетчики ходов
        self.halfmove_clock = int(parts[4]) if len(parts) > 4 else 0
        self.fullmove_number = int(parts[5]) if len(parts) > 5 else 1
        
        self.position_history = []
    
    def to_fen(self) -> str:
        """
        Преобразует текущую позицию в FEN нотацию.
        
        Returns:
            Строка FEN
        """
        # Позиция фигур
        fen_rows = []
        for row in self.board:
            empty_count = 0
            fen_row = ""
            for square in row:
                if square == self.EMPTY:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        fen_row += str(empty_count)
                        empty_count = 0
                    fen_row += square
            if empty_count > 0:
                fen_row += str(empty_count)
            fen_rows.append(fen_row)
        
        position = '/'.join(fen_rows)
        
        # Очередь хода
        turn = 'w' if self.white_to_move else 'b'
        
        # Рокировка
        castling = ''
        if self.castling_rights['K']:
            castling += 'K'
        if self.castling_rights['Q']:
            castling += 'Q'
        if self.castling_rights['k']:
            castling += 'k'
        if self.castling_rights['q']:
            castling += 'q'
        if not castling:
            castling = '-'
        
        # En passant
        en_passant = self.en_passant_square if self.en_passant_square else '-'
        
        return f"{position} {turn} {castling} {en_passant} {self.halfmove_clock} {self.fullmove_number}"
    
    def get_piece(self, row: int, col: int) -> str:
        """Получить фигуру на указанной позиции."""
        if 0 <= row < 8 and 0 <= col < 8:
            return self.board[row][col]
        return None
    
    def set_piece(self, row: int, col: int, piece: str) -> None:
        """Установить фигуру на указанную позицию."""
        if 0 <= row < 8 and 0 <= col < 8:
            self.board[row][col] = piece
    
    def is_white_piece(self, piece: str) -> bool:
        """Проверяет, является ли фигура белой."""
        return piece in self.WHITE_PIECES
    
    def is_black_piece(self, piece: str) -> bool:
        """Проверяет, является ли фигура черной."""
        return piece in self.BLACK_PIECES
    
    def is_enemy_piece(self, piece: str, is_white: bool) -> bool:
        """Проверяет, является ли фигура вражеской."""
        if is_white:
            return self.is_black_piece(piece)
        else:
            return self.is_white_piece(piece)
    
    def is_friendly_piece(self, piece: str, is_white: bool) -> bool:
        """Проверяет, является ли фигура дружественной."""
        if is_white:
            return self.is_white_piece(piece)
        else:
            return self.is_black_piece(piece)
    
    def algebraic_to_coords(self, square: str) -> Tuple[int, int]:
        """
        Преобразует алгебраическую нотацию в координаты доски.
        
        Args:
            square: Клетка в формате 'e4'
            
        Returns:
            (row, col) координаты
        """
        col = ord(square[0]) - ord('a')
        row = 8 - int(square[1])
        return (row, col)
    
    def coords_to_algebraic(self, row: int, col: int) -> str:
        """
        Преобразует координаты доски в алгебраическую нотацию.
        
        Args:
            row: Строка (0-7)
            col: Колонка (0-7)
            
        Returns:
            Клетка в формате 'e4'
        """
        return chr(ord('a') + col) + str(8 - row)
    
    def find_king(self, is_white: bool) -> Optional[Tuple[int, int]]:
        """
        Находит позицию короля указанного цвета.
        
        Args:
            is_white: True для белого короля, False для черного
            
        Returns:
            (row, col) координаты короля или None
        """
        king = self.WHITE_KING if is_white else self.BLACK_KING
        for row in range(8):
            for col in range(8):
                if self.board[row][col] == king:
                    return (row, col)
        return None
    
    def make_move(self, move: 'Move') -> None:
        """
        Выполняет ход на доске.
        
        Args:
            move: Объект хода
        """
        # Сохраняем позицию для истории
        self.position_history.append(self.to_fen())
        
        from_row, from_col = move.from_pos
        to_row, to_col = move.to_pos
        piece = self.get_piece(from_row, from_col)
        
        # Обновление счетчика полуходов
        if piece.lower() == 'p' or move.is_capture:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        
        # Сброс en passant
        old_en_passant = self.en_passant_square
        self.en_passant_square = None
        
        # Обработка специальных ходов
        if move.is_castling:
            # Рокировка
            self._execute_castling(move)
        elif move.is_en_passant:
            # Взятие на проходе
            self._execute_en_passant(move)
        elif move.is_promotion:
            # Превращение пешки
            self.set_piece(from_row, from_col, self.EMPTY)
            self.set_piece(to_row, to_col, move.promotion_piece)
        else:
            # Обычный ход
            self.set_piece(to_row, to_col, piece)
            self.set_piece(from_row, from_col, self.EMPTY)
            
            # Проверка на двойной ход пешки (для en passant)
            if piece.lower() == 'p' and abs(to_row - from_row) == 2:
                en_passant_row = (from_row + to_row) // 2
                self.en_passant_square = self.coords_to_algebraic(en_passant_row, to_col)
        
        # Обновление прав на рокировку
        self._update_castling_rights(piece, from_row, from_col, to_row, to_col)
        
        # Смена хода
        self.white_to_move = not self.white_to_move
        
        # Обновление номера хода
        if not self.white_to_move:
            self.fullmove_number += 1
    
    def _execute_castling(self, move: 'Move') -> None:
        """Выполняет рокировку."""
        from_row, from_col = move.from_pos
        to_row, to_col = move.to_pos
        
        # Перемещаем короля
        king = self.get_piece(from_row, from_col)
        self.set_piece(to_row, to_col, king)
        self.set_piece(from_row, from_col, self.EMPTY)
        
        # Перемещаем ладью
        if to_col > from_col:  # Короткая рокировка
            rook = self.get_piece(from_row, 7)
            self.set_piece(from_row, 5, rook)
            self.set_piece(from_row, 7, self.EMPTY)
        else:  # Длинная рокировка
            rook = self.get_piece(from_row, 0)
            self.set_piece(from_row, 3, rook)
            self.set_piece(from_row, 0, self.EMPTY)
    
    def _execute_en_passant(self, move: 'Move') -> None:
        """Выполняет взятие на проходе."""
        from_row, from_col = move.from_pos
        to_row, to_col = move.to_pos
        
        # Перемещаем пешку
        pawn = self.get_piece(from_row, from_col)
        self.set_piece(to_row, to_col, pawn)
        self.set_piece(from_row, from_col, self.EMPTY)
        
        # Убираем захваченную пешку
        captured_pawn_row = from_row
        self.set_piece(captured_pawn_row, to_col, self.EMPTY)
    
    def _update_castling_rights(self, piece: str, from_row: int, from_col: int, 
                                to_row: int, to_col: int) -> None:
        """Обновляет права на рокировку после хода."""
        # Если король сходил
        if piece == self.WHITE_KING:
            self.castling_rights['K'] = False
            self.castling_rights['Q'] = False
        elif piece == self.BLACK_KING:
            self.castling_rights['k'] = False
            self.castling_rights['q'] = False
        
        # Если ладья сходила
        if piece == self.WHITE_ROOK:
            if from_row == 7 and from_col == 7:
                self.castling_rights['K'] = False
            elif from_row == 7 and from_col == 0:
                self.castling_rights['Q'] = False
        elif piece == self.BLACK_ROOK:
            if from_row == 0 and from_col == 7:
                self.castling_rights['k'] = False
            elif from_row == 0 and from_col == 0:
                self.castling_rights['q'] = False
        
        # Если ладья была взята
        if to_row == 7 and to_col == 7:
            self.castling_rights['K'] = False
        elif to_row == 7 and to_col == 0:
            self.castling_rights['Q'] = False
        elif to_row == 0 and to_col == 7:
            self.castling_rights['k'] = False
        elif to_row == 0 and to_col == 0:
            self.castling_rights['q'] = False
    
    def copy(self) -> 'ChessBoard':
        """Создает копию доски."""
        new_board = ChessBoard()
        new_board.board = deepcopy(self.board)
        new_board.white_to_move = self.white_to_move
        new_board.castling_rights = self.castling_rights.copy()
        new_board.en_passant_square = self.en_passant_square
        new_board.halfmove_clock = self.halfmove_clock
        new_board.fullmove_number = self.fullmove_number
        new_board.position_history = self.position_history.copy()
        return new_board
    
    def __str__(self) -> str:
        """Строковое представление доски."""
        result = []
        for i, row in enumerate(self.board):
            result.append(f"{8-i} {' '.join(row)}")
        result.append("  a b c d e f g h")
        return '\n'.join(result)


class Move:
    """Класс для представления хода."""
    
    def __init__(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int],
                 board: ChessBoard, promotion_piece: str = None):
        """
        Инициализация хода.
        
        Args:
            from_pos: Начальная позиция (row, col)
            to_pos: Конечная позиция (row, col)
            board: Доска для анализа хода
            promotion_piece: Фигура для превращения пешки
        """
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.piece = board.get_piece(*from_pos)
        self.captured_piece = board.get_piece(*to_pos)
        self.is_capture = self.captured_piece != ChessBoard.EMPTY
        self.promotion_piece = promotion_piece
        self.is_promotion = False
        self.is_castling = False
        self.is_en_passant = False
        
        # Определение специальных ходов
        self._determine_special_moves(board)
    
    def _determine_special_moves(self, board: ChessBoard) -> None:
        """Определяет специальные типы ходов."""
        from_row, from_col = self.from_pos
        to_row, to_col = self.to_pos
        
        # Превращение пешки
        if self.piece.lower() == 'p':
            if (board.is_white_piece(self.piece) and to_row == 0) or \
               (board.is_black_piece(self.piece) and to_row == 7):
                self.is_promotion = True
                if not self.promotion_piece:
                    # По умолчанию превращаем в ферзя
                    self.promotion_piece = 'Q' if board.is_white_piece(self.piece) else 'q'
        
        # Рокировка
        if self.piece.lower() == 'k' and abs(to_col - from_col) == 2:
            self.is_castling = True
        
        # Взятие на проходе
        if self.piece.lower() == 'p' and board.en_passant_square:
            en_passant_coords = board.algebraic_to_coords(board.en_passant_square)
            if to_row == en_passant_coords[0] and to_col == en_passant_coords[1]:
                self.is_en_passant = True
                self.is_capture = True
    
    def to_uci(self, board: ChessBoard) -> str:
        """
        Преобразует ход в UCI формат.
        
        Args:
            board: Доска для контекста
            
        Returns:
            Строка в формате UCI (например, 'e2e4', 'e7e8q')
        """
        from_square = board.coords_to_algebraic(*self.from_pos)
        to_square = board.coords_to_algebraic(*self.to_pos)
        
        if self.is_promotion:
            return f"{from_square}{to_square}{self.promotion_piece.lower()}"
        else:
            return f"{from_square}{to_square}"
    
    def __str__(self) -> str:
        """Строковое представление хода."""
        return f"{self.from_pos} -> {self.to_pos}"
    
    def __eq__(self, other) -> bool:
        """Сравнение ходов."""
        if not isinstance(other, Move):
            return False
        return (self.from_pos == other.from_pos and 
                self.to_pos == other.to_pos and
                self.promotion_piece == other.promotion_piece)
    
    def __hash__(self) -> int:
        """Хеш для использования в множествах и словарях."""
        return hash((self.from_pos, self.to_pos, self.promotion_piece))
