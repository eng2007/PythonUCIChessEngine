import sys
import time
import re
from collections import defaultdict
from typing import Optional, List, Tuple, Dict, Set
from enum import Enum

class Color(Enum):
    WHITE = 0
    BLACK = 1

class PieceType(Enum):
    PAWN = 0
    KNIGHT = 1
    BISHOP = 2
    ROOK = 3
    QUEEN = 4
    KING = 5

class Move:
    def __init__(self, from_sq: int, to_sq: int, promotion: Optional[PieceType] = None):
        self.from_sq = from_sq
        self.to_sq = to_sq
        self.promotion = promotion
    
    def __eq__(self, other):
        return (self.from_sq == other.from_sq and 
                self.to_sq == other.to_sq and 
                self.promotion == other.promotion)
    
    def __str__(self):
        from_str = square_to_coords(self.from_sq)
        to_str = square_to_coords(self.to_sq)
        if self.promotion:
            promo = {PieceType.QUEEN: 'q', PieceType.ROOK: 'r', 
                     PieceType.BISHOP: 'b', PieceType.KNIGHT: 'n'}
            return f"{from_str}{to_str}{promo[self.promotion]}"
        return f"{from_str}{to_str}"
    
    def uci(self) -> str:
        return str(self)

class Board:
    def __init__(self, fen: str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"):
        self.pieces = [None] * 64
        self.color_to_move = Color.WHITE
        self.castling_rights = {"K": True, "Q": True, "k": True, "q": True}
        self.en_passant_square = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.zobrist_hash = 0
        self.position_history = []
        self.from_fen(fen)
    
    def from_fen(self, fen: str):
        """Инициализация позиции из FEN строки"""
        parts = fen.split()
        
        # Часть 1: Расстановка фигур
        board_part = parts[0]
        row = 7
        col = 0
        for char in board_part:
            if char == '/':
                row -= 1
                col = 0
            elif char.isdigit():
                col += int(char)
            else:
                piece_type = self._char_to_piece_type(char.lower())
                color = Color.WHITE if char.isupper() else Color.BLACK
                square = row * 8 + col
                self.pieces[square] = (piece_type, color)
                col += 1
        
        # Часть 2: Очередь хода
        self.color_to_move = Color.WHITE if parts[1] == 'w' else Color.BLACK
        
        # Часть 3: Права на рокировку
        self.castling_rights = {"K": 'K' in parts[2], "Q": 'Q' in parts[2],
                               "k": 'k' in parts[2], "q": 'q' in parts[2]}
        
        # Часть 4: Взятие на проходе
        self.en_passant_square = None
        if parts[3] != '-':
            self.en_passant_square = self._coord_to_square(parts[3])
        
        # Часть 5: Счетчик полуходов
        self.halfmove_clock = int(parts[4])
        
        # Часть 6: Номер хода
        self.fullmove_number = int(parts[5])
    
    def _char_to_piece_type(self, char: str) -> PieceType:
        mapping = {
            'p': PieceType.PAWN,
            'n': PieceType.KNIGHT,
            'b': PieceType.BISHOP,
            'r': PieceType.ROOK,
            'q': PieceType.QUEEN,
            'k': PieceType.KING
        }
        return mapping[char]
    
    def _coord_to_square(self, coord: str) -> int:
        """Конвертация координат (например, 'e4') в индекс квадрата"""
        col = ord(coord[0]) - ord('a')
        row = int(coord[1]) - 1
        return row * 8 + col
    
    def to_fen(self) -> str:
        """Преобразование позиции в FEN строку"""
        # Часть 1: Фигуры
        fen_parts = []
        piece_chars = {
            (PieceType.PAWN, Color.WHITE): 'P', (PieceType.PAWN, Color.BLACK): 'p',
            (PieceType.KNIGHT, Color.WHITE): 'N', (PieceType.KNIGHT, Color.BLACK): 'n',
            (PieceType.BISHOP, Color.WHITE): 'B', (PieceType.BISHOP, Color.BLACK): 'b',
            (PieceType.ROOK, Color.WHITE): 'R', (PieceType.ROOK, Color.BLACK): 'r',
            (PieceType.QUEEN, Color.WHITE): 'Q', (PieceType.QUEEN, Color.BLACK): 'q',
            (PieceType.KING, Color.WHITE): 'K', (PieceType.KING, Color.BLACK): 'k'
        }
        
        for row in range(7, -1, -1):
            empty_count = 0
            row_str = ""
            for col in range(8):
                square = row * 8 + col
                piece = self.pieces[square]
                if piece:
                    if empty_count > 0:
                        row_str += str(empty_count)
                        empty_count = 0
                    row_str += piece_chars[piece]
                else:
                    empty_count += 1
            if empty_count > 0:
                row_str += str(empty_count)
            fen_parts.append(row_str)
        
        fen = "/".join(fen_parts)
        
        # Часть 2: Очередь хода
        fen += " w" if self.color_to_move == Color.WHITE else " b"
        
        # Часть 3: Рокировки
        castling = ""
        for right in ["K", "Q", "k", "q"]:
            if self.castling_rights[right]:
                castling += right
        fen += f" {castling if castling else '-'}"
        
        # Часть 4: Взятие на проходе
        ep = "-"
        if self.en_passant_square is not None:
            ep = square_to_coords(self.en_passant_square)
        fen += f" {ep}"
        
        # Часть 5 и 6: Счетчики
        fen += f" {self.halfmove_clock} {self.fullmove_number}"
        
        return fen
    
    def make_move(self, move: Move) -> bool:
        """Выполнение хода, возвращает True если ход легальный"""
        # Проверка базовых условий
        if move.from_sq < 0 or move.from_sq > 63 or move.to_sq < 0 or move.to_sq > 63:
            return False
        
        piece = self.pieces[move.from_sq]
        if not piece:
            return False
        
        piece_type, color = piece
        if color != self.color_to_move:
            return False
        
        # Генерация всех легальных ходов для проверки
        legal_moves = self.generate_legal_moves()
        if move not in legal_moves:
            return False
        
        # Сохраняем состояние для отмены хода
        self.position_history.append(self.to_fen())
        
        # Выполняем ход
        self._execute_move(move, piece_type, color)
        
        # Меняем сторону
        self.color_to_move = Color.BLACK if self.color_to_move == Color.WHITE else Color.WHITE
        
        # Обновляем счетчик ходов
        if self.color_to_move == Color.WHITE:
            self.fullmove_number += 1
        
        return True
    
    def _execute_move(self, move: Move, piece_type: PieceType, color: Color):
        """Внутренний метод для выполнения хода"""
        # Взятие на проходе
        if piece_type == PieceType.PAWN and move.to_sq == self.en_passant_square:
            direction = -1 if color == Color.WHITE else 1
            captured_pawn_square = move.to_sq + (direction * 8)
            self.pieces[captured_pawn_square] = None
            self.halfmove_clock = 0
        # Обычное взятие
        elif self.pieces[move.to_sq]:
            self.halfmove_clock = 0
        # Тихий ход пешки
        elif piece_type == PieceType.PAWN:
            self.halfmove_clock = 0
        # Тихий ход фигуры
        else:
            self.halfmove_clock += 1
        
        # Рокировка
        if piece_type == PieceType.KING:
            # Короткая рокировка белых
            if move.from_sq == 4 and move.to_sq == 6 and color == Color.WHITE:
                self.pieces[7] = None
                self.pieces[5] = (PieceType.ROOK, Color.WHITE)
            # Длинная рокировка белых
            elif move.from_sq == 4 and move.to_sq == 2 and color == Color.WHITE:
                self.pieces[0] = None
                self.pieces[3] = (PieceType.ROOK, Color.WHITE)
            # Короткая рокировка черных
            elif move.from_sq == 60 and move.to_sq == 62 and color == Color.BLACK:
                self.pieces[63] = None
                self.pieces[61] = (PieceType.ROOK, Color.BLACK)
            # Длинная рокировка черных
            elif move.from_sq == 60 and move.to_sq == 58 and color == Color.BLACK:
                self.pieces[56] = None
                self.pieces[59] = (PieceType.ROOK, Color.BLACK)
            
            # Обновляем права на рокировку
            if color == Color.WHITE:
                self.castling_rights["K"] = False
                self.castling_rights["Q"] = False
            else:
                self.castling_rights["k"] = False
                self.castling_rights["q"] = False
        
        # Обновляем права на рокировку при движении ладей
        if piece_type == PieceType.ROOK:
            if move.from_sq == 0:  # Белая ладья a1
                self.castling_rights["Q"] = False
            elif move.from_sq == 7:  # Белая ладья h1
                self.castling_rights["K"] = False
            elif move.from_sq == 56:  # Черная ладья a8
                self.castling_rights["q"] = False
            elif move.from_sq == 63:  # Черная ладья h8
                self.castling_rights["k"] = False
        
        # Превращение пешки
        if piece_type == PieceType.PAWN:
            if (color == Color.WHITE and move.to_sq >= 56) or (color == Color.BLACK and move.to_sq <= 7):
                promotion_type = move.promotion if move.promotion else PieceType.QUEEN
                self.pieces[move.to_sq] = (promotion_type, color)
                self.pieces[move.from_sq] = None
                return
        
        # Обычный ход
        self.pieces[move.to_sq] = (piece_type, color)
        self.pieces[move.from_sq] = None
        
        # Обновляем поле для взятия на проходе
        self.en_passant_square = None
        if piece_type == PieceType.PAWN:
            if abs(move.to_sq - move.from_sq) == 16:  # Двойной ход пешки
                direction = -1 if color == Color.WHITE else 1
                self.en_passant_square = move.from_sq + (direction * 8)
    
    def generate_legal_moves(self) -> List[Move]:
        """Генерация всех легальных ходов"""
        moves = []
        for from_sq in range(64):
            piece = self.pieces[from_sq]
            if not piece:
                continue
            
            piece_type, color = piece
            if color != self.color_to_move:
                continue
            
            moves.extend(self._generate_moves_for_piece(from_sq, piece_type, color))
        
        # Фильтрация ходов, оставляющих короля под шахом
        legal_moves = []
        for move in moves:
            if self._is_move_legal(move):
                legal_moves.append(move)
        
        return legal_moves
    
    def _generate_moves_for_piece(self, square: int, piece_type: PieceType, color: Color) -> List[Move]:
        """Генерация псевдолегальных ходов для фигуры"""
        moves = []
        
        if piece_type == PieceType.PAWN:
            moves = self._generate_pawn_moves(square, color)
        elif piece_type == PieceType.KNIGHT:
            moves = self._generate_knight_moves(square, color)
        elif piece_type == PieceType.BISHOP:
            moves = self._generate_sliding_moves(square, color, [(1, 1), (1, -1), (-1, 1), (-1, -1)])
        elif piece_type == PieceType.ROOK:
            moves = self._generate_sliding_moves(square, color, [(1, 0), (-1, 0), (0, 1), (0, -1)])
        elif piece_type == PieceType.QUEEN:
            moves = self._generate_sliding_moves(square, color, 
                [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)])
        elif piece_type == PieceType.KING:
            moves = self._generate_king_moves(square, color)
        
        return moves
    
    def _generate_pawn_moves(self, square: int, color: Color) -> List[Move]:
        """Генерация ходов пешки"""
        moves = []
        row, col = divmod(square, 8)
        
        direction = 1 if color == Color.WHITE else -1
        start_row = 1 if color == Color.WHITE else 6
        promotion_row = 7 if color == Color.WHITE else 0
        
        # Ход вперед на одну клетку
        new_row = row + direction
        if 0 <= new_row < 8:
            forward_square = new_row * 8 + col
            if not self.pieces[forward_square]:
                if new_row == promotion_row:
                    for promo in [PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT]:
                        moves.append(Move(square, forward_square, promo))
                else:
                    moves.append(Move(square, forward_square))
                
                # Ход вперед на две клетки
                if row == start_row:
                    double_row = row + 2 * direction
                    double_square = double_row * 8 + col
                    if not self.pieces[double_square]:
                        moves.append(Move(square, double_square))
        
        # Взятия
        for dcol in [-1, 1]:
            new_col = col + dcol
            if 0 <= new_col < 8:
                new_row = row + direction
                if 0 <= new_row < 8:
                    capture_square = new_row * 8 + new_col
                    target_piece = self.pieces[capture_square]
                    
                    # Обычное взятие
                    if target_piece and target_piece[1] != color:
                        if new_row == promotion_row:
                            for promo in [PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT]:
                                moves.append(Move(square, capture_square, promo))
                        else:
                            moves.append(Move(square, capture_square))
                    
                    # Взятие на проходе
                    if capture_square == self.en_passant_square:
                        moves.append(Move(square, capture_square))
        
        return moves
    
    def _generate_knight_moves(self, square: int, color: Color) -> List[Move]:
        """Генерация ходов коня"""
        moves = []
        row, col = divmod(square, 8)
        knight_moves = [(2, 1), (2, -1), (-2, 1), (-2, -1),
                       (1, 2), (1, -2), (-1, 2), (-1, -2)]
        
        for dr, dc in knight_moves:
            new_row, new_col = row + dr, col + dc
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                target_square = new_row * 8 + new_col
                target_piece = self.pieces[target_square]
                if not target_piece or target_piece[1] != color:
                    moves.append(Move(square, target_square))
        
        return moves
    
    def _generate_sliding_moves(self, square: int, color: Color, directions: List[Tuple[int, int]]) -> List[Move]:
        """Генерация ходов для ферзя, ладьи, слона"""
        moves = []
        row, col = divmod(square, 8)
        
        for dr, dc in directions:
            r, c = row + dr, col + dc
            while 0 <= r < 8 and 0 <= c < 8:
                target_square = r * 8 + c
                target_piece = self.pieces[target_square]
                
                if not target_piece:
                    moves.append(Move(square, target_square))
                else:
                    if target_piece[1] != color:
                        moves.append(Move(square, target_square))
                    break
                
                r += dr
                c += dc
        
        return moves
    
    def _generate_king_moves(self, square: int, color: Color) -> List[Move]:
        """Генерация ходов короля"""
        moves = []
        row, col = divmod(square, 8)
        
        # Обычные ходы
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                
                new_row, new_col = row + dr, col + dc
                if 0 <= new_row < 8 and 0 <= new_col < 8:
                    target_square = new_row * 8 + new_col
                    target_piece = self.pieces[target_square]
                    if not target_piece or target_piece[1] != color:
                        moves.append(Move(square, target_square))
        
        # Рокировки
        if color == Color.WHITE and square == 4:  # Белый король на e1
            if self.castling_rights["K"]:  # Короткая рокировка
                if (not self.pieces[5] and not self.pieces[6] and  # Путь свободен
                    not self._is_square_attacked(4, Color.BLACK) and  # Король не под шахом
                    not self._is_square_attacked(5, Color.BLACK) and  # Клетки не атакованы
                    not self._is_square_attacked(6, Color.BLACK)):
                    moves.append(Move(4, 6))
            
            if self.castling_rights["Q"]:  # Длинная рокировка
                if (not self.pieces[1] and not self.pieces[2] and not self.pieces[3] and
                    not self._is_square_attacked(4, Color.BLACK) and
                    not self._is_square_attacked(3, Color.BLACK) and
                    not self._is_square_attacked(2, Color.BLACK)):
                    moves.append(Move(4, 2))
        
        elif color == Color.BLACK and square == 60:  # Черный король на e8
            if self.castling_rights["k"]:  # Короткая рокировка
                if (not self.pieces[61] and not self.pieces[62] and
                    not self._is_square_attacked(60, Color.WHITE) and
                    not self._is_square_attacked(61, Color.WHITE) and
                    not self._is_square_attacked(62, Color.WHITE)):
                    moves.append(Move(60, 62))
            
            if self.castling_rights["q"]:  # Длинная рокировка
                if (not self.pieces[57] and not self.pieces[58] and not self.pieces[59] and
                    not self._is_square_attacked(60, Color.WHITE) and
                    not self._is_square_attacked(59, Color.WHITE) and
                    not self._is_square_attacked(58, Color.WHITE)):
                    moves.append(Move(60, 58))
        
        return moves
    
    def _is_move_legal(self, move: Move) -> bool:
        """Проверка легальности хода (не оставляет ли короля под шахом)"""
        # Сохраняем текущее состояние
        backup_pieces = self.pieces.copy()
        backup_state = (
            self.color_to_move,
            self.castling_rights.copy(),
            self.en_passant_square,
            self.halfmove_clock,
            self.fullmove_number
        )
        
        # Выполняем ход
        from_piece = self.pieces[move.from_sq]
        if not from_piece:
            return False
        
        piece_type, color = from_piece
        
        # Временное выполнение хода
        self._execute_move(move, piece_type, color)
        
        # Проверяем, остался ли король под шахом
        king_square = self._find_king(color)
        in_check = self._is_square_attacked(king_square, 
            Color.BLACK if color == Color.WHITE else Color.WHITE)
        
        # Восстанавливаем состояние
        self.pieces = backup_pieces
        (self.color_to_move, self.castling_rights, 
         self.en_passant_square, self.halfmove_clock, 
         self.fullmove_number) = backup_state
        
        return not in_check
    
    def _find_king(self, color: Color) -> int:
        """Поиск короля заданного цвета"""
        for square in range(64):
            piece = self.pieces[square]
            if piece and piece[0] == PieceType.KING and piece[1] == color:
                return square
        return -1
    
    def _is_square_attacked(self, square: int, attacker_color: Color) -> bool:
        """Проверка, атакована ли клетка фигурами заданного цвета"""
        # Пешки
        direction = 1 if attacker_color == Color.BLACK else -1
        for dcol in [-1, 1]:
            attack_row = (square // 8) - direction
            attack_col = (square % 8) + dcol
            if 0 <= attack_row < 8 and 0 <= attack_col < 8:
                attack_square = attack_row * 8 + attack_col
                piece = self.pieces[attack_square]
                if piece and piece[0] == PieceType.PAWN and piece[1] == attacker_color:
                    return True
        
        # Кони
        knight_moves = [(2, 1), (2, -1), (-2, 1), (-2, -1),
                       (1, 2), (1, -2), (-1, 2), (-1, -2)]
        row, col = divmod(square, 8)
        for dr, dc in knight_moves:
            r, c = row + dr, col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                target_square = r * 8 + c
                piece = self.pieces[target_square]
                if piece and piece[0] == PieceType.KNIGHT and piece[1] == attacker_color:
                    return True
        
        # Слоны, ладьи, ферзи (скользящие фигуры)
        # Диагонали
        for dr, dc in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
            r, c = row + dr, col + dc
            while 0 <= r < 8 and 0 <= c < 8:
                target_square = r * 8 + c
                piece = self.pieces[target_square]
                if piece:
                    if piece[1] == attacker_color and (
                        piece[0] == PieceType.BISHOP or piece[0] == PieceType.QUEEN):
                        return True
                    break
                r += dr
                c += dc
        
        # Горизонтали/вертикали
        for dr, dc in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            r, c = row + dr, col + dc
            while 0 <= r < 8 and 0 <= c < 8:
                target_square = r * 8 + c
                piece = self.pieces[target_square]
                if piece:
                    if piece[1] == attacker_color and (
                        piece[0] == PieceType.ROOK or piece[0] == PieceType.QUEEN):
                        return True
                    break
                r += dr
                c += dc
        
        # Короли
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                r, c = row + dr, col + dc
                if 0 <= r < 8 and 0 <= c < 8:
                    target_square = r * 8 + c
                    piece = self.pieces[target_square]
                    if piece and piece[0] == PieceType.KING and piece[1] == attacker_color:
                        return True
        
        return False
    
    def is_checkmate(self) -> bool:
        """Проверка на мат"""
        if not self.is_in_check():
            return False
        return len(self.generate_legal_moves()) == 0
    
    def is_stalemate(self) -> bool:
        """Проверка на пат"""
        if self.is_in_check():
            return False
        return len(self.generate_legal_moves()) == 0
    
    def is_in_check(self) -> bool:
        """Проверка, находится ли текущий король под шахом"""
        king_square = self._find_king(self.color_to_move)
        if king_square == -1:
            return False
        opponent = Color.BLACK if self.color_to_move == Color.WHITE else Color.WHITE
        return self._is_square_attacked(king_square, opponent)
    
    def is_insufficient_material(self) -> bool:
        """Проверка на недостаточность материала"""
        pieces = []
        for square in range(64):
            piece = self.pieces[square]
            if piece:
                pieces.append(piece[0])
        
        # Только короли
        if len(pieces) == 2:
            return True
        
        # Король + конь против короля
        if len(pieces) == 3 and any(p == PieceType.KNIGHT for p in pieces):
            return True
        
        # Король + слон против короля
        if len(pieces) == 3 and any(p == PieceType.BISHOP for p in pieces):
            return True
        
        return False
    
    def is_draw_by_repetition(self) -> bool:
        """Проверка на ничью по троекратному повторению"""
        if len(self.position_history) < 3:
            return False
        
        current_fen = self.to_fen().split()
        # Убираем счетчики для сравнения позиций
        current_pos = ' '.join(current_fen[:4])
        
        count = 1
        for fen in self.position_history[-8:]:  # Проверяем последние 8 позиций
            pos = fen.split()
            pos = ' '.join(pos[:4])
            if pos == current_pos:
                count += 1
                if count >= 3:
                    return True
        
        return False
    
    def is_draw_by_50_moves(self) -> bool:
        """Проверка на ничью по правилу 50 ходов"""
        return self.halfmove_clock >= 100  # 100 полуходов = 50 ходов

class Engine:
    def __init__(self):
        self.board = Board()
        self.search_depth = 3
        self.nodes_searched = 0
        self.transposition_table = {}
    
    def evaluate_position(self) -> float:
        """Оценочная функция позиции"""
        score = 0
        piece_values = {
            PieceType.PAWN: 100,
            PieceType.KNIGHT: 320,
            PieceType.BISHOP: 330,
            PieceType.ROOK: 500,
            PieceType.QUEEN: 900,
            PieceType.KING: 20000
        }
        
        # Материальный счет
        for square in range(64):
            piece = self.board.pieces[square]
            if piece:
                piece_type, color = piece
                value = piece_values[piece_type]
                if color == Color.WHITE:
                    score += value
                else:
                    score -= value
        
        # Позиционная оценка (простая)
        # Центральные клетки более ценны для пешек
        center_squares = [27, 28, 35, 36]  # d4, e4, d5, e5
        for square in center_squares:
            piece = self.board.pieces[square]
            if piece and piece[0] == PieceType.PAWN:
                if piece[1] == Color.WHITE:
                    score += 10
                else:
                    score -= 10
        
        return score if self.board.color_to_move == Color.WHITE else -score
    
    def order_moves(self, moves: List[Move]) -> List[Move]:
        """Упорядочивание ходов для лучшей производительности альфа-бета"""
        ordered = []
        for move in moves:
            score = 0
            
            # Взятия
            target_piece = self.board.pieces[move.to_sq]
            if target_piece:
                piece_values = {
                    PieceType.PAWN: 100,
                    PieceType.KNIGHT: 320,
                    PieceType.BISHOP: 330,
                    PieceType.ROOK: 500,
                    PieceType.QUEEN: 900
                }
                attacker_piece = self.board.pieces[move.from_sq]
                if attacker_piece:
                    attacker_value = piece_values.get(attacker_piece[0], 0)
                    target_value = piece_values.get(target_piece[0], 0)
                    
                    # MVV-LVA (Most Valuable Victim - Least Valuable Aggressor)
                    score = target_value - attacker_value + 10000
            
            # Превращения пешек
            if move.promotion:
                score += 800
            
            ordered.append((score, move))
        
        ordered.sort(reverse=True, key=lambda x: x[0])
        return [move for _, move in ordered]
    
    def negamax(self, depth: int, alpha: float, beta: float) -> float:
        """Алгоритм Negamax с альфа-бета отсечением"""
        self.nodes_searched += 1
        
        # Проверка терминальных позиций
        if self.board.is_checkmate():
            return -100000 + (self.search_depth - depth)  # Мат на глубине лучше
        
        if self.board.is_stalemate():
            return 0
        
        if self.board.is_insufficient_material():
            return 0
        
        if self.board.is_draw_by_repetition():
            return 0
        
        if self.board.is_draw_by_50_moves():
            return 0
        
        if depth == 0:
            return self.evaluate_position()
        
        moves = self.board.generate_legal_moves()
        if not moves:
            if self.board.is_in_check():
                return -100000 + (self.search_depth - depth)
            return 0
        
        moves = self.order_moves(moves)
        best_value = -float('inf')
        
        for move in moves:
            # Сохраняем состояние
            backup_fen = self.board.to_fen()
            
            # Делаем ход
            self.board.make_move(move)
            
            # Рекурсивный поиск
            value = -self.negamax(depth - 1, -beta, -alpha)
            
            # Отменяем ход
            self.board.from_fen(backup_fen)
            
            if value > best_value:
                best_value = value
            
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        
        return best_value
    
    def find_best_move(self, depth: int = None) -> Optional[Move]:
        """Поиск лучшего хода"""
        if depth is None:
            depth = self.search_depth
        
        self.nodes_searched = 0
        moves = self.board.generate_legal_moves()
        
        if not moves:
            return None
        
        best_move = None
        best_value = -float('inf')
        
        for move in moves:
            # Сохраняем состояние
            backup_fen = self.board.to_fen()
            
            # Делаем ход
            self.board.make_move(move)
            
            # Оценка позиции
            value = -self.negamax(depth - 1, -float('inf'), float('inf'))
            
            # Отменяем ход
            self.board.from_fen(backup_fen)
            
            if value > best_value:
                best_value = value
                best_move = move
        
        return best_move
    
    def search_with_time(self, time_ms: int) -> Optional[Move]:
        """Поиск с ограничением по времени"""
        start_time = time.time() * 1000
        best_move = None
        
        # Итеративное углубление
        for depth in range(1, self.search_depth + 1):
            current_best = self.find_best_move(depth)
            if current_best:
                best_move = current_best
            
            # Проверка времени
            elapsed = time.time() * 1000 - start_time
            if elapsed > time_ms * 0.9:  # Используем 90% времени
                break
        
        return best_move

class UCIInterface:
    def __init__(self):
        self.engine = Engine()
        self.running = True
    
    def run(self):
        """Главный цикл UCI"""
        while self.running:
            try:
                command = input().strip()
                if command:
                    self.process_command(command)
            except EOFError:
                break
            except KeyboardInterrupt:
                break
    
    def process_command(self, command: str):
        """Обработка UCI команд"""
        parts = command.split()
        
        if command == "uci":
            self.uci()
        elif command == "isready":
            print("readyok")
        elif command == "ucinewgame":
            self.ucinewgame()
        elif parts[0] == "position":
            self.position(command)
        elif parts[0] == "go":
            self.go(command)
        elif command == "stop":
            self.stop()
        elif command == "quit":
            self.quit()
        elif command == "d":  # Debug - показать доску
            self.print_board()
    
    def uci(self):
        """Команда uci - идентификация движка"""
        print("id name Python Chess Engine")
        print("id author DeepSeek")
        print("uciok")
    
    def ucinewgame(self):
        """Новая игра"""
        self.engine = Engine()
    
    def position(self, command: str):
        """Установка позиции"""
        parts = command.split()
        
        if parts[1] == "startpos":
            self.engine.board = Board()
            if len(parts) > 2 and parts[2] == "moves":
                moves = parts[3:]
                for move_str in moves:
                    move = self._parse_move(move_str)
                    if move:
                        self.engine.board.make_move(move)
        
        elif parts[1] == "fen":
            fen = ' '.join(parts[2:8])
            self.engine.board = Board(fen)
            if len(parts) > 8 and parts[8] == "moves":
                moves = parts[9:]
                for move_str in moves:
                    move = self._parse_move(move_str)
                    if move:
                        self.engine.board.make_move(move)
    
    def _parse_move(self, move_str: str) -> Optional[Move]:
        """Парсинг хода в UCI формате"""
        if len(move_str) < 4:
            return None
        
        from_col = ord(move_str[0]) - ord('a')
        from_row = int(move_str[1]) - 1
        to_col = ord(move_str[2]) - ord('a')
        to_row = int(move_str[3]) - 1
        
        from_sq = from_row * 8 + from_col
        to_sq = to_row * 8 + to_col
        
        promotion = None
        if len(move_str) == 5:
            promo_map = {
                'q': PieceType.QUEEN,
                'r': PieceType.ROOK,
                'b': PieceType.BISHOP,
                'n': PieceType.KNIGHT
            }
            promotion = promo_map.get(move_str[4])
        
        return Move(from_sq, to_sq, promotion)
    
    def go(self, command: str):
        """Поиск лучшего хода"""
        parts = command.split()
        depth = 3
        movetime = None
        
        for i in range(1, len(parts)):
            if parts[i] == "depth" and i + 1 < len(parts):
                depth = int(parts[i + 1])
            elif parts[i] == "movetime" and i + 1 < len(parts):
                movetime = int(parts[i + 1])
        
        best_move = None
        
        if movetime:
            best_move = self.engine.search_with_time(movetime)
        else:
            self.engine.search_depth = depth
            best_move = self.engine.find_best_move()
        
        if best_move:
            print(f"bestmove {best_move.uci()}")
        else:
            print("bestmove 0000")  # Нет легальных ходов
    
    def stop(self):
        """Остановка поиска (заглушка)"""
        pass
    
    def quit(self):
        """Выход из программы"""
        self.running = False
    
    def print_board(self):
        """Отладочный вывод доски"""
        piece_symbols = {
            (PieceType.PAWN, Color.WHITE): '♙', (PieceType.PAWN, Color.BLACK): '♟',
            (PieceType.KNIGHT, Color.WHITE): '♘', (PieceType.KNIGHT, Color.BLACK): '♞',
            (PieceType.BISHOP, Color.WHITE): '♗', (PieceType.BISHOP, Color.BLACK): '♝',
            (PieceType.ROOK, Color.WHITE): '♖', (PieceType.ROOK, Color.BLACK): '♜',
            (PieceType.QUEEN, Color.WHITE): '♕', (PieceType.QUEEN, Color.BLACK): '♛',
            (PieceType.KING, Color.WHITE): '♔', (PieceType.KING, Color.BLACK): '♚'
        }
        
        print("  +-----------------+")
        for row in range(7, -1, -1):
            print(f"{row + 1} |", end=" ")
            for col in range(8):
                square = row * 8 + col
                piece = self.engine.board.pieces[square]
                if piece:
                    print(piece_symbols[piece], end=" ")
                else:
                    print(".", end=" ")
            print("|")
        print("  +-----------------+")
        print("    a b c d e f g h")
        print(f"FEN: {self.engine.board.to_fen()}")
        print(f"To move: {'White' if self.engine.board.color_to_move == Color.WHITE else 'Black'}")

def square_to_coords(square: int) -> str:
    """Конвертация индекса квадрата в координаты (например, 0 -> 'a1')"""
    row = square // 8
    col = square % 8
    return f"{chr(col + ord('a'))}{row + 1}"

if __name__ == "__main__":
    uci = UCIInterface()
    uci.run()