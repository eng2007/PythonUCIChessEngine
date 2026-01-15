# moves.py

from board import *

class MoveGenerator:
    """Класс для генерации легальных ходов."""
    def __init__(self, board):
        self.board = board
        # Направления для скользящих фигур
        self.bishop_directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        self.rook_directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        self.queen_directions = self.bishop_directions + self.rook_directions

    def generate_moves(self):
        """Генерирует все легальные ходы для текущего игрока."""
        moves = []
        my_color = self.board.turn
        opponent_color = 'b' if my_color == 'w' else 'w'
        
        for sq in range(64):
            piece = self.board.get_piece(sq)
            if piece == EMPTY or COLORS[piece] != my_color:
                continue
            
            piece_type = piece % 8
            if piece_type == wP % 8: # Пешка
                moves.extend(self._generate_pawn_moves(sq, my_color))
            elif piece_type == wN % 8: # Конь
                moves.extend(self._generate_knight_moves(sq, my_color))
            elif piece_type == wB % 8: # Слон
                moves.extend(self._generate_sliding_moves(sq, self.bishop_directions, my_color))
            elif piece_type == wR % 8: # Ладья
                moves.extend(self._generate_sliding_moves(sq, self.rook_directions, my_color))
            elif piece_type == wQ % 8: # Ферзь
                moves.extend(self._generate_sliding_moves(sq, self.queen_directions, my_color))
            elif piece_type == wK % 8: # Король
                moves.extend(self._generate_king_moves(sq, my_color))

        # Фильтр нелегальных ходов (которые оставляют короля под шахом)
        legal_moves = []
        king_sq = self._find_king(my_color)
        
        for move in moves:
            undo_info = self.board.make_move(move)
            # После хода противника, проверяем, атакован ли наш король
            if not self.board.is_square_attacked(king_sq, opponent_color):
                legal_moves.append(move)
            self.board.unmake_move(undo_info)
            
        return legal_moves

    def _find_king(self, color):
        """Находит позицию короля указанного цвета."""
        king_piece = wK if color == 'w' else bK
        for sq in range(64):
            if self.board.get_piece(sq) == king_piece:
                return sq
        return -1 # Не должно произойти

    def _generate_pawn_moves(self, sq, color):
        """Генерирует ходы для пешки."""
        moves = []
        direction = -8 if color == 'w' else 8
        start_rank = 6 if color == 'w' else 1
        
        # Ход на 1 клетку
        move_sq = sq + direction
        if 0 <= move_sq < 64 and self.board.get_piece(move_sq) == EMPTY:
            # Превращение
            if move_sq // 8 == 0 or move_sq // 8 == 7:
                for promo_piece in [wQ, wR, wB, wN] if color == 'w' else [bQ, bR, bB, bN]:
                    moves.append((sq, move_sq, promo_piece))
            else:
                moves.append((sq, move_sq, None))
                
                # Ход на 2 клетки
                if sq // 8 == start_rank:
                    move_sq_2 = sq + 2 * direction
                    if self.board.get_piece(move_sq_2) == EMPTY:
                        moves.append((sq, move_sq_2, None))

        # Взятия
        for offset in [-1, 1]:
            if (sq % 8 == 0 and offset == -1) or (sq % 8 == 7 and offset == 1):
                continue
            capture_sq = sq + direction + offset
            if 0 <= capture_sq < 64:
                piece_on_target = self.board.get_piece(capture_sq)
                if piece_on_target != EMPTY and COLORS[piece_on_target] != color:
                    if capture_sq // 8 == 0 or capture_sq // 8 == 7:
                        for promo_piece in [wQ, wR, wB, wN] if color == 'w' else [bQ, bR, bB, bN]:
                            moves.append((sq, capture_sq, promo_piece))
                    else:
                        moves.append((sq, capture_sq, None))

        # Взятие на проходе
        if self.board.en_passant_sq != -1:
            ep_sq = self.board.en_passant_sq
            if abs(sq - ep_sq) in [7, 9]: # Пешка рядом с полем для взятия
                moves.append((sq, ep_sq, None))
                
        return moves

    def _generate_knight_moves(self, sq, color):
        """Генерирует ходы для коня."""
        moves = []
        offsets = [-17, -15, -10, -6, 6, 10, 15, 17]
        for offset in offsets:
            target_sq = sq + offset
            if 0 <= target_sq < 64 and abs(sq % 8 - target_sq % 8) <= 2:
                piece_on_target = self.board.get_piece(target_sq)
                if piece_on_target == EMPTY or COLORS[piece_on_target] != color:
                    moves.append((sq, target_sq, None))
        return moves

    def _generate_sliding_moves(self, sq, directions, color):
        """Генерирует ходы для слонящихся фигур (слон, ладья, ферзь)."""
        moves = []
        for dr, dc in directions:
            for i in range(1, 8):
                target_sq = sq + dr * 8 + dc
                if not (0 <= target_sq < 64): break
                
                # Проверка на "переход" через край доски по горизонтали
                if abs((sq % 8) - (target_sq % 8)) != i and dc != 0: break
                
                piece_on_target = self.board.get_piece(target_sq)
                if piece_on_target == EMPTY:
                    moves.append((sq, target_sq, None))
                else:
                    if COLORS[piece_on_target] != color:
                        moves.append((sq, target_sq, None))
                    break
        return moves

    def _generate_king_moves(self, sq, color):
        """Генерирует ходы для короля, включая рокировку."""
        moves = []
        offsets = [-9, -8, -7, -1, 1, 7, 8, 9]
        for offset in offsets:
            target_sq = sq + offset
            if 0 <= target_sq < 64 and abs(sq % 8 - target_sq % 8) <= 1:
                piece_on_target = self.board.get_piece(target_sq)
                if piece_on_target == EMPTY or COLORS[piece_on_target] != color:
                    moves.append((sq, target_sq, None))
        
        # Рокировка
        if color == 'w':
            if 'K' in self.board.castle_rights and self.board.get_piece(61) == EMPTY and self.board.get_piece(62) == EMPTY:
                if not self.board.is_square_attacked(60, 'b') and not self.board.is_square_attacked(61, 'b') and not self.board.is_square_attacked(62, 'b'):
                    moves.append((60, 62, None)) # Короткая
            if 'Q' in self.board.castle_rights and self.board.get_piece(59) == EMPTY and self.board.get_piece(58) == EMPTY and self.board.get_piece(57) == EMPTY:
                if not self.board.is_square_attacked(60, 'b') and not self.board.is_square_attacked(59, 'b') and not self.board.is_square_attacked(58, 'b'):
                    moves.append((60, 58, None)) # Длинная
        else: # color == 'b'
            if 'k' in self.board.castle_rights and self.board.get_piece(5) == EMPTY and self.board.get_piece(6) == EMPTY:
                if not self.board.is_square_attacked(4, 'w') and not self.board.is_square_attacked(5, 'w') and not self.board.is_square_attacked(6, 'w'):
                    moves.append((4, 6, None)) # Короткая
            if 'q' in self.board.castle_rights and self.board.get_piece(3) == EMPTY and self.board.get_piece(2) == EMPTY and self.board.get_piece(1) == EMPTY:
                if not self.board.is_square_attacked(4, 'w') and not self.board.is_square_attacked(3, 'w') and not self.board.is_square_attacked(2, 'w'):
                    moves.append((4, 2, None)) # Длинная
        
        return moves