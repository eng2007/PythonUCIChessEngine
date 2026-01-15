# board.py

import copy

# Константы для фигур
EMPTY = 0
wP, wN, wB, wR, wQ, wK = 1, 2, 3, 4, 5, 6
bP, bN, bB, bR, bQ, bK = 9, 10, 11, 12, 13, 14

# Словари для преобразования
PIECE_SYMBOLS = {
    1: 'P', 2: 'N', 3: 'B', 4: 'R', 5: 'Q', 6: 'K',
    9: 'p', 10: 'n', 11: 'b', 12: 'r', 13: 'q', 14: 'k'
}
COLORS = {wP: 'w', wN: 'w', wB: 'w', wR: 'w', wQ: 'w', wK: 'w',
          bP: 'b', bN: 'b', bB: 'b', bR: 'b', bQ: 'b', bK: 'b'}

class Board:
    """Класс для представления и управления шахматной доской."""
    def __init__(self, fen=None):
        if fen:
            self.load_fen(fen)
        else:
            self.reset_to_start_pos()

    def reset_to_start_pos(self):
        """Устанавливает начальную позицию."""
        self.load_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

    def load_fen(self, fen_str):
        """Загружает позицию из строки FEN."""
        parts = fen_str.split()
        # Расстановка фигур
        piece_placement = parts[0]
        self.squares = [EMPTY] * 64
        rank = 7
        file = 0
        for char in piece_placement:
            if char == '/':
                rank -= 1
                file = 0
            elif char.isdigit():
                file += int(char)
            else:
                piece_char = char.lower()
                color = 'w' if char.isupper() else 'b'
                piece_map = {'p': wP, 'n': wN, 'b': wB, 'r': wR, 'q': wQ, 'k': wK}
                piece = piece_map[piece_char]
                if color == 'b':
                    piece += 8
                self.squares[rank * 8 + file] = piece
                file += 1
        
        # Ход
        self.turn = parts[1]
        
        # Правила рокировки
        self.castle_rights = parts[2]
        
        # Взятие на проходе
        self.en_passant_sq = -1 if parts[3] == '-' else self.algebraic_to_index(parts[3])
        
        # Счетчик полуходов (правило 50 ходов)
        self.halfmove_clock = int(parts[4])
        
        # Номер хода
        self.fullmove_number = int(parts[5])

        # История позиций для определения ничьи по троекратному повторению
        self.position_history = [self.get_board_hash()]

    def to_fen(self):
        """Преобразует текущую позицию в строку FEN."""
        # Расстановка
        fen_parts = []
        for rank in range(8):
            empty_count = 0
            rank_str = ""
            for file in range(8):
                piece = self.squares[rank * 8 + file]
                if piece == EMPTY:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        rank_str += str(empty_count)
                        empty_count = 0
                    rank_str += PIECE_SYMBOLS[piece]
            if empty_count > 0:
                rank_str += str(empty_count)
            fen_parts.append(rank_str)
        fen = "/".join(fen_parts)
        
        # Ход
        fen += f" {self.turn}"
        
        # Рокировка
        fen += f" {self.castle_rights}"
        
        # Взятие на проходе
        ep_str = self.index_to_algebraic(self.en_passant_sq) if self.en_passant_sq != -1 else '-'
        fen += f" {ep_str}"
        
        # Счетчики
        fen += f" {self.halfmove_clock} {self.fullmove_number}"
        return fen

    def algebraic_to_index(self, alg):
        """Конвертирует алгебраическую нотацию (e.g., 'e2') в индекс (0-63)."""
        file = ord(alg[0]) - ord('a')
        rank = int(alg[1]) - 1
        return rank * 8 + file

    def index_to_algebraic(self, idx):
        """Конвертирует индекс (0-63) в алгебраическую нотацию."""
        if idx == -1: return '-'
        rank = idx // 8
        file = idx % 8
        return chr(ord('a') + file) + str(rank + 1)

    def get_piece(self, sq):
        """Возвращает фигуру на клетке."""
        return self.squares[sq]

    def set_piece(self, sq, piece):
        """Устанавливает фигуру на клетку."""
        self.squares[sq] = piece

    def make_move(self, move):
        """Выполняет ход на доске."""
        from_sq, to_sq, promotion_piece = move
        piece = self.get_piece(from_sq)
        captured_piece = self.get_piece(to_sq)
        
        # Сохраняем состояние для undo
        undo_info = {
            'move': move,
            'captured_piece': captured_piece,
            'castle_rights': self.castle_rights,
            'en_passant_sq': self.en_passant_sq,
            'halfmove_clock': self.halfmove_clock,
            'fullmove_number': self.fullmove_number,
        }

        # Обновляем счетчик полуходов
        if (piece in (wP, bP)) or (captured_piece != EMPTY):
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        
        # Обновляем номер полного хода
        if self.turn == 'b':
            self.fullmove_number += 1
        
        # Сброс взятия на проходе
        self.en_passant_sq = -1

        # Специальные ходы
        if piece in (wP, bP):
            # Ход на 2 клетки -> устанавливаем возможность en passant
            if abs(to_sq - from_sq) == 16:
                self.en_passant_sq = (from_sq + to_sq) // 2
            # Взятие на проходе
            elif to_sq == self.en_passant_sq:
                captured_pawn_sq = to_sq + 8 if piece == wP else to_sq - 8
                self.set_piece(captured_pawn_sq, EMPTY)
            # Превращение
            elif to_sq // 8 == 0 or to_sq // 8 == 7:
                piece = promotion_piece

        # Рокировка
        if piece in (wK, bK) and abs(to_sq - from_sq) == 2:
            is_kingside = to_sq > from_sq
            rook_from = to_sq + 1 if is_kingside else to_sq - 2
            rook_to = to_sq - 1 if is_kingside else to_sq + 1
            self.set_piece(rook_to, self.get_piece(rook_from))
            self.set_piece(rook_from, EMPTY)
        
        # Обновление прав рокировки
        if piece == wK: self.castle_rights = self.castle_rights.replace('K', '').replace('Q', '')
        if piece == bK: self.castle_rights = self.castle_rights.replace('k', '').replace('q', '')
        if piece == wR:
            if from_sq == 63: self.castle_rights = self.castle_rights.replace('K', '')
            if from_sq == 56: self.castle_rights = self.castle_rights.replace('Q', '')
        if piece == bR:
            if from_sq == 7: self.castle_rights = self.castle_rights.replace('k', '')
            if from_sq == 0: self.castle_rights = self.castle_rights.replace('q', '')

        # Выполнение основного хода
        self.set_piece(to_sq, piece)
        self.set_piece(from_sq, EMPTY)
        
        # Смена хода
        self.turn = 'b' if self.turn == 'w' else 'w'
        
        # Добавляем хэш позиции в историю
        self.position_history.append(self.get_board_hash())
        
        return undo_info

    def unmake_move(self, undo_info):
        """Отменяет ход, используя сохраненную информацию."""
        move = undo_info['move']
        from_sq, to_sq, promotion_piece = move
        
        # Восстанавливаем счетчики и флаги
        self.castle_rights = undo_info['castle_rights']
        self.en_passant_sq = undo_info['en_passant_sq']
        self.halfmove_clock = undo_info['halfmove_clock']
        self.fullmove_number = undo_info['fullmove_number']
        
        # Возвращаем ход
        self.turn = 'b' if self.turn == 'w' else 'w'
        
        piece = self.get_piece(to_sq)
        captured_piece = undo_info['captured_piece']
        
        # Отмена рокировки
        if piece in (wK, bK) and abs(to_sq - from_sq) == 2:
            is_kingside = to_sq > from_sq
            rook_from = to_sq + 1 if is_kingside else to_sq - 2
            rook_to = to_sq - 1 if is_kingside else to_sq + 1
            self.set_piece(rook_from, self.get_piece(rook_to))
            self.set_piece(rook_to, EMPTY)

        # Отмена взятия на проходе
        if piece in (wP, bP) and to_sq == undo_info['en_passant_sq']:
            captured_pawn_sq = to_sq + 8 if piece == wP else to_sq - 8
            self.set_piece(captured_pawn_sq, bP if piece == wP else wP)
            self.set_piece(to_sq, EMPTY)
        else:
            # Отмена превращения пешки
            if promotion_piece:
                piece = wP if self.turn == 'w' else bP
            
            # Отмена обычного хода/взятия
            self.set_piece(from_sq, piece)
            self.set_piece(to_sq, captured_piece)
        
        # Удаляем последний хэш из истории
        self.position_history.pop()

    def is_square_attacked(self, sq, by_color):
        """Проверяет, атакована ли клетка sq фигурами цвета by_color."""
        # Пешки
        pawn_dir = -1 if by_color == 'w' else 1
        if 0 <= sq + pawn_dir * 8 - 1 < 64 and (sq % 8) != 0:
            if self.get_piece(sq + pawn_dir * 8 - 1) == (wP if by_color == 'w' else bP):
                return True
        if 0 <= sq + pawn_dir * 8 + 1 < 64 and (sq % 8) != 7:
            if self.get_piece(sq + pawn_dir * 8 + 1) == (wP if by_color == 'w' else bP):
                return True

        # Конь
        knight_offsets = [-17, -15, -10, -6, 6, 10, 15, 17]
        for offset in knight_offsets:
            target_sq = sq + offset
            if 0 <= target_sq < 64 and abs(sq % 8 - target_sq % 8) <= 2:
                if self.get_piece(target_sq) == (wN if by_color == 'w' else bN):
                    return True
        
        # Слоники, Ладьи, Ферзи (скользящие фигуры)
        sliding_offsets = {
            (wB, bR): [(-1, -1), (-1, 1), (1, -1), (1, 1)], # Слон
            (wR, bB): [(-1, 0), (1, 0), (0, -1), (0, 1)],   # Ладья
            (wQ, bQ): [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)] # Ферзь
        }
        for pieces, offsets in sliding_offsets.items():
            for dr, dc in offsets:
                for i in range(1, 8):
                    target_sq = sq + dr * 8 + dc
                    if not (0 <= target_sq < 64): break
                    if abs((sq % 8) - (target_sq % 8)) != abs(dc) * i and dc != 0: break
                    
                    piece_on_target = self.get_piece(target_sq)
                    if piece_on_target == EMPTY: continue
                    
                    if (by_color == 'w' and piece_on_target in pieces[0]) or \
                       (by_color == 'b' and piece_on_target in pieces[1]):
                        return True
                    break
        
        # Король
        king_offsets = [-9, -8, -7, -1, 1, 7, 8, 9]
        for offset in king_offsets:
            target_sq = sq + offset
            if 0 <= target_sq < 64 and abs(sq % 8 - target_sq % 8) <= 1:
                if self.get_piece(target_sq) == (wK if by_color == 'w' else bK):
                    return True
        
        return False

    def get_board_hash(self):
        """Возвращает хэш текущей позиции (используется для определения повторения)."""
        # Для простоты используем FEN как хэш. В реальных движках используются Zobrist keys.
        return f"{self.to_fen()}_{self.turn}"