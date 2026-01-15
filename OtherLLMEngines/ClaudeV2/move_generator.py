"""
Модуль генерации и проверки ходов.
"""

from typing import List, Tuple, Optional
from chess_board import ChessBoard, Move


class MoveGenerator:
    """Класс для генерации и валидации ходов."""
    
    def __init__(self, board: ChessBoard):
        """
        Инициализация генератора ходов.
        
        Args:
            board: Шахматная доска
        """
        self.board = board
    
    def generate_legal_moves(self) -> List[Move]:
        """
        Генерирует все легальные ходы для текущей позиции.
        
        Returns:
            Список легальных ходов
        """
        pseudo_legal_moves = self._generate_pseudo_legal_moves()
        legal_moves = []
        
        for move in pseudo_legal_moves:
            if self._is_legal_move(move):
                legal_moves.append(move)
        
        return legal_moves
    
    def _generate_pseudo_legal_moves(self) -> List[Move]:
        """
        Генерирует псевдо-легальные ходы (без проверки на шах).
        
        Returns:
            Список псевдо-легальных ходов
        """
        moves = []
        is_white = self.board.white_to_move
        
        for row in range(8):
            for col in range(8):
                piece = self.board.get_piece(row, col)
                if piece == ChessBoard.EMPTY:
                    continue
                
                # Проверяем, что это наша фигура
                if (is_white and not self.board.is_white_piece(piece)) or \
                   (not is_white and not self.board.is_black_piece(piece)):
                    continue
                
                # Генерируем ходы для фигуры
                piece_moves = self._generate_piece_moves(row, col, piece)
                moves.extend(piece_moves)
        
        return moves
    
    def _generate_piece_moves(self, row: int, col: int, piece: str) -> List[Move]:
        """
        Генерирует ходы для конкретной фигуры.
        
        Args:
            row: Строка
            col: Колонка
            piece: Фигура
            
        Returns:
            Список ходов для фигуры
        """
        piece_type = piece.lower()
        
        if piece_type == 'p':
            return self._generate_pawn_moves(row, col, piece)
        elif piece_type == 'n':
            return self._generate_knight_moves(row, col, piece)
        elif piece_type == 'b':
            return self._generate_bishop_moves(row, col, piece)
        elif piece_type == 'r':
            return self._generate_rook_moves(row, col, piece)
        elif piece_type == 'q':
            return self._generate_queen_moves(row, col, piece)
        elif piece_type == 'k':
            return self._generate_king_moves(row, col, piece)
        
        return []
    
    def _generate_pawn_moves(self, row: int, col: int, piece: str) -> List[Move]:
        """Генерирует ходы пешки."""
        moves = []
        is_white = self.board.is_white_piece(piece)
        direction = -1 if is_white else 1
        start_row = 6 if is_white else 1
        
        # Ход вперед
        new_row = row + direction
        if 0 <= new_row < 8 and self.board.get_piece(new_row, col) == ChessBoard.EMPTY:
            if (is_white and new_row == 0) or (not is_white and new_row == 7):
                # Превращение пешки
                for promotion in ['q', 'r', 'b', 'n']:
                    promotion_piece = promotion.upper() if is_white else promotion
                    moves.append(Move((row, col), (new_row, col), self.board, promotion_piece))
            else:
                moves.append(Move((row, col), (new_row, col), self.board))
            
            # Двойной ход с начальной позиции
            if row == start_row:
                double_row = row + 2 * direction
                if self.board.get_piece(double_row, col) == ChessBoard.EMPTY:
                    moves.append(Move((row, col), (double_row, col), self.board))
        
        # Взятие
        for dcol in [-1, 1]:
            new_col = col + dcol
            if 0 <= new_col < 8:
                target_piece = self.board.get_piece(new_row, new_col)
                if target_piece != ChessBoard.EMPTY and \
                   self.board.is_enemy_piece(target_piece, is_white):
                    if (is_white and new_row == 0) or (not is_white and new_row == 7):
                        # Превращение при взятии
                        for promotion in ['q', 'r', 'b', 'n']:
                            promotion_piece = promotion.upper() if is_white else promotion
                            moves.append(Move((row, col), (new_row, new_col), self.board, promotion_piece))
                    else:
                        moves.append(Move((row, col), (new_row, new_col), self.board))
        
        # Взятие на проходе
        if self.board.en_passant_square:
            en_passant_coords = self.board.algebraic_to_coords(self.board.en_passant_square)
            if en_passant_coords[0] == new_row:
                for dcol in [-1, 1]:
                    new_col = col + dcol
                    if new_col == en_passant_coords[1]:
                        moves.append(Move((row, col), en_passant_coords, self.board))
        
        return moves
    
    def _generate_knight_moves(self, row: int, col: int, piece: str) -> List[Move]:
        """Генерирует ходы коня."""
        moves = []
        is_white = self.board.is_white_piece(piece)
        
        # Все возможные ходы коня
        knight_moves = [
            (-2, -1), (-2, 1), (-1, -2), (-1, 2),
            (1, -2), (1, 2), (2, -1), (2, 1)
        ]
        
        for drow, dcol in knight_moves:
            new_row, new_col = row + drow, col + dcol
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                target_piece = self.board.get_piece(new_row, new_col)
                if target_piece == ChessBoard.EMPTY or \
                   self.board.is_enemy_piece(target_piece, is_white):
                    moves.append(Move((row, col), (new_row, new_col), self.board))
        
        return moves
    
    def _generate_sliding_moves(self, row: int, col: int, piece: str, 
                                 directions: List[Tuple[int, int]]) -> List[Move]:
        """
        Генерирует ходы для скользящих фигур (слон, ладья, ферзь).
        
        Args:
            row: Строка
            col: Колонка
            piece: Фигура
            directions: Направления движения
            
        Returns:
            Список ходов
        """
        moves = []
        is_white = self.board.is_white_piece(piece)
        
        for drow, dcol in directions:
            new_row, new_col = row + drow, col + dcol
            
            while 0 <= new_row < 8 and 0 <= new_col < 8:
                target_piece = self.board.get_piece(new_row, new_col)
                
                if target_piece == ChessBoard.EMPTY:
                    moves.append(Move((row, col), (new_row, new_col), self.board))
                elif self.board.is_enemy_piece(target_piece, is_white):
                    moves.append(Move((row, col), (new_row, new_col), self.board))
                    break
                else:
                    break
                
                new_row += drow
                new_col += dcol
        
        return moves
    
    def _generate_bishop_moves(self, row: int, col: int, piece: str) -> List[Move]:
        """Генерирует ходы слона."""
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        return self._generate_sliding_moves(row, col, piece, directions)
    
    def _generate_rook_moves(self, row: int, col: int, piece: str) -> List[Move]:
        """Генерирует ходы ладьи."""
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        return self._generate_sliding_moves(row, col, piece, directions)
    
    def _generate_queen_moves(self, row: int, col: int, piece: str) -> List[Move]:
        """Генерирует ходы ферзя."""
        directions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
        return self._generate_sliding_moves(row, col, piece, directions)
    
    def _generate_king_moves(self, row: int, col: int, piece: str) -> List[Move]:
        """Генерирует ходы короля."""
        moves = []
        is_white = self.board.is_white_piece(piece)
        
        # Обычные ходы короля
        king_moves = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
        
        for drow, dcol in king_moves:
            new_row, new_col = row + drow, col + dcol
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                target_piece = self.board.get_piece(new_row, new_col)
                if target_piece == ChessBoard.EMPTY or \
                   self.board.is_enemy_piece(target_piece, is_white):
                    moves.append(Move((row, col), (new_row, new_col), self.board))
        
        # Рокировка
        castling_moves = self._generate_castling_moves(row, col, is_white)
        moves.extend(castling_moves)
        
        return moves
    
    def _generate_castling_moves(self, row: int, col: int, is_white: bool) -> List[Move]:
        """Генерирует ходы рокировки."""
        moves = []
        
        # Проверяем, что король не под шахом
        if self.is_square_attacked(row, col, not is_white):
            return moves
        
        if is_white:
            # Короткая рокировка белых
            if self.board.castling_rights['K']:
                if self.board.get_piece(7, 5) == ChessBoard.EMPTY and \
                   self.board.get_piece(7, 6) == ChessBoard.EMPTY and \
                   not self.is_square_attacked(7, 5, False) and \
                   not self.is_square_attacked(7, 6, False):
                    moves.append(Move((7, 4), (7, 6), self.board))
            
            # Длинная рокировка белых
            if self.board.castling_rights['Q']:
                if self.board.get_piece(7, 3) == ChessBoard.EMPTY and \
                   self.board.get_piece(7, 2) == ChessBoard.EMPTY and \
                   self.board.get_piece(7, 1) == ChessBoard.EMPTY and \
                   not self.is_square_attacked(7, 3, False) and \
                   not self.is_square_attacked(7, 2, False):
                    moves.append(Move((7, 4), (7, 2), self.board))
        else:
            # Короткая рокировка черных
            if self.board.castling_rights['k']:
                if self.board.get_piece(0, 5) == ChessBoard.EMPTY and \
                   self.board.get_piece(0, 6) == ChessBoard.EMPTY and \
                   not self.is_square_attacked(0, 5, True) and \
                   not self.is_square_attacked(0, 6, True):
                    moves.append(Move((0, 4), (0, 6), self.board))
            
            # Длинная рокировка черных
            if self.board.castling_rights['q']:
                if self.board.get_piece(0, 3) == ChessBoard.EMPTY and \
                   self.board.get_piece(0, 2) == ChessBoard.EMPTY and \
                   self.board.get_piece(0, 1) == ChessBoard.EMPTY and \
                   not self.is_square_attacked(0, 3, True) and \
                   not self.is_square_attacked(0, 2, True):
                    moves.append(Move((0, 4), (0, 2), self.board))
        
        return moves
    
    def _is_legal_move(self, move: Move) -> bool:
        """
        Проверяет, является ли ход легальным (не оставляет короля под шахом).
        
        Args:
            move: Ход для проверки
            
        Returns:
            True если ход легальный
        """
        # Делаем ход на копии доски
        test_board = self.board.copy()
        test_board.make_move(move)
        
        # Находим короля (после хода очередь сменилась, поэтому инвертируем)
        king_pos = test_board.find_king(not test_board.white_to_move)
        
        if not king_pos:
            return False
        
        # Проверяем, атакован ли король
        return not self.is_square_attacked_on_board(test_board, *king_pos, test_board.white_to_move)
    
    def is_square_attacked(self, row: int, col: int, by_white: bool) -> bool:
        """
        Проверяет, атакована ли клетка фигурами указанного цвета.
        
        Args:
            row: Строка
            col: Колонка
            by_white: True если проверяем атаку белыми
            
        Returns:
            True если клетка атакована
        """
        return self.is_square_attacked_on_board(self.board, row, col, by_white)
    
    def is_square_attacked_on_board(self, board: ChessBoard, row: int, col: int, 
                                     by_white: bool) -> bool:
        """
        Проверяет, атакована ли клетка на указанной доске.
        
        Args:
            board: Доска для проверки
            row: Строка
            col: Колонка
            by_white: True если проверяем атаку белыми
            
        Returns:
            True если клетка атакована
        """
        # Проверка атаки пешками
        pawn_direction = 1 if by_white else -1
        pawn_row = row - pawn_direction
        pawn = ChessBoard.WHITE_PAWN if by_white else ChessBoard.BLACK_PAWN
        
        if 0 <= pawn_row < 8:
            for dcol in [-1, 1]:
                pawn_col = col + dcol
                if 0 <= pawn_col < 8 and board.get_piece(pawn_row, pawn_col) == pawn:
                    return True
        
        # Проверка атаки конями
        knight = ChessBoard.WHITE_KNIGHT if by_white else ChessBoard.BLACK_KNIGHT
        knight_moves = [
            (-2, -1), (-2, 1), (-1, -2), (-1, 2),
            (1, -2), (1, 2), (2, -1), (2, 1)
        ]
        for drow, dcol in knight_moves:
            new_row, new_col = row + drow, col + dcol
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                if board.get_piece(new_row, new_col) == knight:
                    return True
        
        # Проверка атаки слонами и ферзями (диагонали)
        bishop = ChessBoard.WHITE_BISHOP if by_white else ChessBoard.BLACK_BISHOP
        queen = ChessBoard.WHITE_QUEEN if by_white else ChessBoard.BLACK_QUEEN
        diagonal_directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        
        for drow, dcol in diagonal_directions:
            new_row, new_col = row + drow, col + dcol
            while 0 <= new_row < 8 and 0 <= new_col < 8:
                piece = board.get_piece(new_row, new_col)
                if piece != ChessBoard.EMPTY:
                    if piece == bishop or piece == queen:
                        return True
                    break
                new_row += drow
                new_col += dcol
        
        # Проверка атаки ладьями и ферзями (прямые)
        rook = ChessBoard.WHITE_ROOK if by_white else ChessBoard.BLACK_ROOK
        straight_directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        
        for drow, dcol in straight_directions:
            new_row, new_col = row + drow, col + dcol
            while 0 <= new_row < 8 and 0 <= new_col < 8:
                piece = board.get_piece(new_row, new_col)
                if piece != ChessBoard.EMPTY:
                    if piece == rook or piece == queen:
                        return True
                    break
                new_row += drow
                new_col += dcol
        
        # Проверка атаки королем
        king = ChessBoard.WHITE_KING if by_white else ChessBoard.BLACK_KING
        king_moves = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
        for drow, dcol in king_moves:
            new_row, new_col = row + drow, col + dcol
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                if board.get_piece(new_row, new_col) == king:
                    return True
        
        return False
    
    def is_in_check(self) -> bool:
        """
        Проверяет, находится ли текущий игрок под шахом.
        
        Returns:
            True если король под шахом
        """
        king_pos = self.board.find_king(self.board.white_to_move)
        if not king_pos:
            return False
        return self.is_square_attacked(*king_pos, not self.board.white_to_move)
    
    def is_checkmate(self) -> bool:
        """
        Проверяет, является ли позиция матом.
        
        Returns:
            True если мат
        """
        if not self.is_in_check():
            return False
        return len(self.generate_legal_moves()) == 0
    
    def is_stalemate(self) -> bool:
        """
        Проверяет, является ли позиция патом.
        
        Returns:
            True если пат
        """
        if self.is_in_check():
            return False
        return len(self.generate_legal_moves()) == 0
    
    def is_insufficient_material(self) -> bool:
        """
        Проверяет недостаточность материала для мата.
        
        Returns:
            True если недостаточно материала
        """
        pieces = []
        for row in range(8):
            for col in range(8):
                piece = self.board.get_piece(row, col)
                if piece != ChessBoard.EMPTY and piece.lower() != 'k':
                    pieces.append(piece)
        
        # Только короли
        if len(pieces) == 0:
            return True
        
        # Король и конь против короля
        if len(pieces) == 1 and pieces[0].lower() == 'n':
            return True
        
        # Король и слон против короля
        if len(pieces) == 1 and pieces[0].lower() == 'b':
            return True
        
        # Король и слон против короля и слона (одноцветные слоны)
        if len(pieces) == 2:
            if all(p.lower() == 'b' for p in pieces):
                # Находим слонов
                bishop_squares = []
                for row in range(8):
                    for col in range(8):
                        if self.board.get_piece(row, col).lower() == 'b':
                            bishop_squares.append((row, col))
                
                # Проверяем, что слоны на одноцветных полях
                if len(bishop_squares) == 2:
                    square1_color = (bishop_squares[0][0] + bishop_squares[0][1]) % 2
                    square2_color = (bishop_squares[1][0] + bishop_squares[1][1]) % 2
                    if square1_color == square2_color:
                        return True
        
        return False
    
    def is_fifty_move_rule(self) -> bool:
        """
        Проверяет правило 50 ходов.
        
        Returns:
            True если сработало правило 50 ходов
        """
        return self.board.halfmove_clock >= 100  # 50 полных ходов = 100 полуходов
    
    def is_threefold_repetition(self) -> bool:
        """
        Проверяет троекратное повторение позиции.
        
        Returns:
            True если позиция повторилась трижды
        """
        current_position = self.board.to_fen().split()[0]  # Только расстановка фигур
        count = 0
        
        for position in self.board.position_history:
            if position.split()[0] == current_position:
                count += 1
                if count >= 3:
                    return True
        
        return False
    
    def is_game_over(self) -> Tuple[bool, str]:
        """
        Проверяет, окончена ли игра.
        
        Returns:
            (is_over, reason) - кортеж с флагом окончания и причиной
        """
        if self.is_checkmate():
            winner = "Black" if self.board.white_to_move else "White"
            return (True, f"Checkmate - {winner} wins")
        
        if self.is_stalemate():
            return (True, "Stalemate - Draw")
        
        if self.is_insufficient_material():
            return (True, "Insufficient material - Draw")
        
        if self.is_fifty_move_rule():
            return (True, "Fifty move rule - Draw")
        
        if self.is_threefold_repetition():
            return (True, "Threefold repetition - Draw")
        
        return (False, "")
