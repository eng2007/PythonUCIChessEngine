#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pygame
import sys
from copy import deepcopy

# Инициализация Pygame
pygame.init()

# Константы
WIDTH, HEIGHT = 800, 800
DIMENSION = 8
SQ_SIZE = WIDTH // DIMENSION
MAX_FPS = 15
IMAGES = {}

# Цвета
WHITE = (238, 238, 210)
GRAY = (118, 150, 86)
YELLOW = (247, 247, 105)
HIGHLIGHT_COLOR = (186, 202, 68)

# Загрузка изображений фигур
def load_images():
    pieces = ['wp', 'wR', 'wN', 'wB', 'wQ', 'wK', 'bp', 'bR', 'bN', 'bB', 'bQ', 'bK']
    for piece in pieces:
        # Создаем простые изображения фигур с помощью текста
        font = pygame.font.SysFont('Arial', 50, True, False)
        piece_symbols = {
            'wp': '♙', 'wR': '♖', 'wN': '♘', 'wB': '♗', 'wQ': '♕', 'wK': '♔',
            'bp': '♟', 'bR': '♜', 'bN': '♞', 'bB': '♝', 'bQ': '♛', 'bK': '♚'
        }
        text = font.render(piece_symbols[piece], True, (0, 0, 0) if piece[0] == 'w' else (255, 255, 255))
        IMAGES[piece] = pygame.transform.scale(text, (SQ_SIZE - 10, SQ_SIZE - 10))

class GameState:
    def __init__(self):
        # Доска 8x8, "--" означает пустую клетку
        self.board = [
            ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
            ["bp", "bp", "bp", "bp", "bp", "bp", "bp", "bp"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["wp", "wp", "wp", "wp", "wp", "wp", "wp", "wp"],
            ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"]
        ]
        self.white_to_move = True
        self.move_log = []
        self.white_king_location = (7, 4)
        self.black_king_location = (0, 4)
        self.checkmate = False
        self.stalemate = False
        self.enpassant_possible = ()  # координаты клетки, где возможно взятие на проходе
        self.enpassant_possible_log = [self.enpassant_possible]
        self.current_castling_right = CastleRights(True, True, True, True)
        self.castle_rights_log = [CastleRights(self.current_castling_right.wks, self.current_castling_right.bks,
                                                self.current_castling_right.wqs, self.current_castling_right.bqs)]
        
    def make_move(self, move):
        self.board[move.start_row][move.start_col] = "--"
        self.board[move.end_row][move.end_col] = move.piece_moved
        self.move_log.append(move)
        self.white_to_move = not self.white_to_move
        
        # Обновление позиции короля
        if move.piece_moved == 'wK':
            self.white_king_location = (move.end_row, move.end_col)
        elif move.piece_moved == 'bK':
            self.black_king_location = (move.end_row, move.end_col)
            
        # Превращение пешки
        if move.pawn_promotion:
            self.board[move.end_row][move.end_col] = move.piece_moved[0] + 'Q'
        
        # Взятие на проходе
        if move.is_enpassant_move:
            self.board[move.start_row][move.end_col] = '--'  # убираем пешку
        
        # Обновление переменной enpassant_possible
        if move.piece_moved[1] == 'p' and abs(move.start_row - move.end_row) == 2:
            self.enpassant_possible = ((move.start_row + move.end_row) // 2, move.start_col)
        else:
            self.enpassant_possible = ()
        
        # Рокировка
        if move.is_castle_move:
            if move.end_col - move.start_col == 2:  # Короткая рокировка
                self.board[move.end_row][move.end_col - 1] = self.board[move.end_row][move.end_col + 1]
                self.board[move.end_row][move.end_col + 1] = '--'
            else:  # Длинная рокировка
                self.board[move.end_row][move.end_col + 1] = self.board[move.end_row][move.end_col - 2]
                self.board[move.end_row][move.end_col - 2] = '--'
        
        self.enpassant_possible_log.append(self.enpassant_possible)
        
        # Обновление прав на рокировку
        self.update_castle_rights(move)
        self.castle_rights_log.append(CastleRights(self.current_castling_right.wks, self.current_castling_right.wqs,
                                                     self.current_castling_right.bks, self.current_castling_right.bqs))
    
    def undo_move(self):
        if len(self.move_log) != 0:
            move = self.move_log.pop()
            self.board[move.start_row][move.start_col] = move.piece_moved
            self.board[move.end_row][move.end_col] = move.piece_captured
            self.white_to_move = not self.white_to_move
            
            if move.piece_moved == 'wK':
                self.white_king_location = (move.start_row, move.start_col)
            elif move.piece_moved == 'bK':
                self.black_king_location = (move.start_row, move.start_col)
            
            # Отмена взятия на проходе
            if move.is_enpassant_move:
                self.board[move.end_row][move.end_col] = '--'
                self.board[move.start_row][move.end_col] = move.piece_captured
            
            self.enpassant_possible_log.pop()
            self.enpassant_possible = self.enpassant_possible_log[-1]
            
            # Отмена рокировки
            if move.is_castle_move:
                if move.end_col - move.start_col == 2:  # Короткая рокировка
                    self.board[move.end_row][move.end_col + 1] = self.board[move.end_row][move.end_col - 1]
                    self.board[move.end_row][move.end_col - 1] = '--'
                else:  # Длинная рокировка
                    self.board[move.end_row][move.end_col - 2] = self.board[move.end_row][move.end_col + 1]
                    self.board[move.end_row][move.end_col + 1] = '--'
            
            # Отмена изменений прав на рокировку
            self.castle_rights_log.pop()
            self.current_castling_right = self.castle_rights_log[-1]
    
    def update_castle_rights(self, move):
        """Обновляет права на рокировку после хода"""
        if move.piece_moved == 'wK':
            self.current_castling_right.wks = False
            self.current_castling_right.wqs = False
        elif move.piece_moved == 'bK':
            self.current_castling_right.bks = False
            self.current_castling_right.bqs = False
        elif move.piece_moved == 'wR':
            if move.start_row == 7:
                if move.start_col == 0:
                    self.current_castling_right.wqs = False
                elif move.start_col == 7:
                    self.current_castling_right.wks = False
        elif move.piece_moved == 'bR':
            if move.start_row == 0:
                if move.start_col == 0:
                    self.current_castling_right.bqs = False
                elif move.start_col == 7:
                    self.current_castling_right.bks = False
        
        # Если ладья была взята
        if move.piece_captured == 'wR':
            if move.end_row == 7:
                if move.end_col == 0:
                    self.current_castling_right.wqs = False
                elif move.end_col == 7:
                    self.current_castling_right.wks = False
        elif move.piece_captured == 'bR':
            if move.end_row == 0:
                if move.end_col == 0:
                    self.current_castling_right.bqs = False
                elif move.end_col == 7:
                    self.current_castling_right.bks = False
    
    def get_valid_moves(self):
        # Получение всех возможных ходов с учетом шахов
        temp_castle_rights = CastleRights(self.current_castling_right.wks, self.current_castling_right.wqs,
                                          self.current_castling_right.bks, self.current_castling_right.bqs)
        moves = self.get_all_possible_moves()
        if self.white_to_move:
            self.get_castle_moves(self.white_king_location[0], self.white_king_location[1], moves)
        else:
            self.get_castle_moves(self.black_king_location[0], self.black_king_location[1], moves)
        
        # Фильтрация ходов, которые оставляют короля под шахом
        for i in range(len(moves) - 1, -1, -1):
            self.make_move(moves[i])
            self.white_to_move = not self.white_to_move
            if self.in_check():
                moves.remove(moves[i])
            self.white_to_move = not self.white_to_move
            self.undo_move()
        
        if len(moves) == 0:
            if self.in_check():
                self.checkmate = True
            else:
                self.stalemate = True
        else:
            self.checkmate = False
            self.stalemate = False
        
        self.current_castling_right = temp_castle_rights
        return moves
    
    def in_check(self):
        if self.white_to_move:
            return self.square_under_attack(self.white_king_location[0], self.white_king_location[1])
        else:
            return self.square_under_attack(self.black_king_location[0], self.black_king_location[1])
    
    def square_under_attack(self, r, c):
        self.white_to_move = not self.white_to_move
        opp_moves = self.get_all_possible_moves()
        self.white_to_move = not self.white_to_move
        for move in opp_moves:
            if move.end_row == r and move.end_col == c:
                return True
        return False
    
    def get_all_possible_moves(self):
        moves = []
        for r in range(len(self.board)):
            for c in range(len(self.board[r])):
                turn = self.board[r][c][0]
                if (turn == 'w' and self.white_to_move) or (turn == 'b' and not self.white_to_move):
                    piece = self.board[r][c][1]
                    if piece == 'p':
                        self.get_pawn_moves(r, c, moves)
                    elif piece == 'R':
                        self.get_rook_moves(r, c, moves)
                    elif piece == 'N':
                        self.get_knight_moves(r, c, moves)
                    elif piece == 'B':
                        self.get_bishop_moves(r, c, moves)
                    elif piece == 'Q':
                        self.get_queen_moves(r, c, moves)
                    elif piece == 'K':
                        self.get_king_moves(r, c, moves)
        return moves
    
    def get_pawn_moves(self, r, c, moves):
        if self.white_to_move:
            if self.board[r-1][c] == "--":
                moves.append(Move((r, c), (r-1, c), self.board))
                if r == 6 and self.board[r-2][c] == "--":
                    moves.append(Move((r, c), (r-2, c), self.board))
            if c - 1 >= 0:
                if self.board[r-1][c-1][0] == 'b':
                    moves.append(Move((r, c), (r-1, c-1), self.board))
                elif (r-1, c-1) == self.enpassant_possible:
                    moves.append(Move((r, c), (r-1, c-1), self.board, is_enpassant_move=True))
            if c + 1 <= 7:
                if self.board[r-1][c+1][0] == 'b':
                    moves.append(Move((r, c), (r-1, c+1), self.board))
                elif (r-1, c+1) == self.enpassant_possible:
                    moves.append(Move((r, c), (r-1, c+1), self.board, is_enpassant_move=True))
        else:
            if self.board[r+1][c] == "--":
                moves.append(Move((r, c), (r+1, c), self.board))
                if r == 1 and self.board[r+2][c] == "--":
                    moves.append(Move((r, c), (r+2, c), self.board))
            if c - 1 >= 0:
                if self.board[r+1][c-1][0] == 'w':
                    moves.append(Move((r, c), (r+1, c-1), self.board))
                elif (r+1, c-1) == self.enpassant_possible:
                    moves.append(Move((r, c), (r+1, c-1), self.board, is_enpassant_move=True))
            if c + 1 <= 7:
                if self.board[r+1][c+1][0] == 'w':
                    moves.append(Move((r, c), (r+1, c+1), self.board))
                elif (r+1, c+1) == self.enpassant_possible:
                    moves.append(Move((r, c), (r+1, c+1), self.board, is_enpassant_move=True))
    
    def get_rook_moves(self, r, c, moves):
        directions = ((-1, 0), (0, -1), (1, 0), (0, 1))
        enemy_color = "b" if self.white_to_move else "w"
        for d in directions:
            for i in range(1, 8):
                end_row = r + d[0] * i
                end_col = c + d[1] * i
                if 0 <= end_row < 8 and 0 <= end_col < 8:
                    end_piece = self.board[end_row][end_col]
                    if end_piece == "--":
                        moves.append(Move((r, c), (end_row, end_col), self.board))
                    elif end_piece[0] == enemy_color:
                        moves.append(Move((r, c), (end_row, end_col), self.board))
                        break
                    else:
                        break
                else:
                    break
    
    def get_knight_moves(self, r, c, moves):
        knight_moves = ((-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1))
        ally_color = "w" if self.white_to_move else "b"
        for m in knight_moves:
            end_row = r + m[0]
            end_col = c + m[1]
            if 0 <= end_row < 8 and 0 <= end_col < 8:
                end_piece = self.board[end_row][end_col]
                if end_piece[0] != ally_color:
                    moves.append(Move((r, c), (end_row, end_col), self.board))
    
    def get_bishop_moves(self, r, c, moves):
        directions = ((-1, -1), (-1, 1), (1, -1), (1, 1))
        enemy_color = "b" if self.white_to_move else "w"
        for d in directions:
            for i in range(1, 8):
                end_row = r + d[0] * i
                end_col = c + d[1] * i
                if 0 <= end_row < 8 and 0 <= end_col < 8:
                    end_piece = self.board[end_row][end_col]
                    if end_piece == "--":
                        moves.append(Move((r, c), (end_row, end_col), self.board))
                    elif end_piece[0] == enemy_color:
                        moves.append(Move((r, c), (end_row, end_col), self.board))
                        break
                    else:
                        break
                else:
                    break
    
    def get_queen_moves(self, r, c, moves):
        self.get_rook_moves(r, c, moves)
        self.get_bishop_moves(r, c, moves)
    
    def get_king_moves(self, r, c, moves):
        king_moves = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
        ally_color = "w" if self.white_to_move else "b"
        for i in range(8):
            end_row = r + king_moves[i][0]
            end_col = c + king_moves[i][1]
            if 0 <= end_row < 8 and 0 <= end_col < 8:
                end_piece = self.board[end_row][end_col]
                if end_piece[0] != ally_color:
                    moves.append(Move((r, c), (end_row, end_col), self.board))
    
    def get_castle_moves(self, r, c, moves):
        """Генерирует все возможные рокировки для короля на позиции (r, c)"""
        if self.square_under_attack(r, c):
            return  # Нельзя рокироваться под шахом
        if (self.white_to_move and self.current_castling_right.wks) or (not self.white_to_move and self.current_castling_right.bks):
            self.get_kingside_castle_moves(r, c, moves)
        if (self.white_to_move and self.current_castling_right.wqs) or (not self.white_to_move and self.current_castling_right.bqs):
            self.get_queenside_castle_moves(r, c, moves)
    
    def get_kingside_castle_moves(self, r, c, moves):
        if self.board[r][c+1] == '--' and self.board[r][c+2] == '--':
            if not self.square_under_attack(r, c+1) and not self.square_under_attack(r, c+2):
                moves.append(Move((r, c), (r, c+2), self.board, is_castle_move=True))
    
    def get_queenside_castle_moves(self, r, c, moves):
        if self.board[r][c-1] == '--' and self.board[r][c-2] == '--' and self.board[r][c-3] == '--':
            if not self.square_under_attack(r, c-1) and not self.square_under_attack(r, c-2):
                moves.append(Move((r, c), (r, c-2), self.board, is_castle_move=True))

class CastleRights:
    def __init__(self, wks, wqs, bks, bqs):
        self.wks = wks  # white kingside
        self.wqs = wqs  # white queenside
        self.bks = bks  # black kingside
        self.bqs = bqs  # black queenside

class Move:
    ranks_to_rows = {"1": 7, "2": 6, "3": 5, "4": 4, "5": 3, "6": 2, "7": 1, "8": 0}
    rows_to_ranks = {v: k for k, v in ranks_to_rows.items()}
    files_to_cols = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5, "g": 6, "h": 7}
    cols_to_files = {v: k for k, v in files_to_cols.items()}
    
    def __init__(self, start_sq, end_sq, board, is_enpassant_move=False, is_castle_move=False):
        self.start_row = start_sq[0]
        self.start_col = start_sq[1]
        self.end_row = end_sq[0]
        self.end_col = end_sq[1]
        self.piece_moved = board[self.start_row][self.start_col]
        self.piece_captured = board[self.end_row][self.end_col]
        self.pawn_promotion = False
        if (self.piece_moved == 'wp' and self.end_row == 0) or (self.piece_moved == 'bp' and self.end_row == 7):
            self.pawn_promotion = True
        self.is_enpassant_move = is_enpassant_move
        if self.is_enpassant_move:
            self.piece_captured = 'wp' if self.piece_moved == 'bp' else 'bp'
        self.is_castle_move = is_castle_move
        self.is_capture = self.piece_captured != '--'
        self.move_id = self.start_row * 1000 + self.start_col * 100 + self.end_row * 10 + self.end_col
    
    def __eq__(self, other):
        if isinstance(other, Move):
            return self.move_id == other.move_id
        return False
    
    def get_chess_notation(self):
        return self.get_rank_file(self.start_row, self.start_col) + self.get_rank_file(self.end_row, self.end_col)
    
    def get_rank_file(self, r, c):
        return self.cols_to_files[c] + self.rows_to_ranks[r]

class ChessAI:
    piece_score = {"K": 0, "Q": 9, "R": 5, "B": 3, "N": 3, "p": 1}
    CHECKMATE = 1000
    STALEMATE = 0
    
    @staticmethod
    def find_best_move(gs, valid_moves, depth):
        """Находит лучший ход с использованием минимакса и альфа-бета отсечения"""
        global next_move
        next_move = None
        ChessAI.find_move_negamax_alpha_beta(gs, valid_moves, depth, -ChessAI.CHECKMATE, ChessAI.CHECKMATE, 1 if gs.white_to_move else -1)
        return next_move
    
    @staticmethod
    def find_move_negamax_alpha_beta(gs, valid_moves, depth, alpha, beta, turn_multiplier):
        global next_move
        if depth == 0:
            return turn_multiplier * ChessAI.score_board(gs)
        
        max_score = -ChessAI.CHECKMATE
        for move in valid_moves:
            gs.make_move(move)
            next_moves = gs.get_valid_moves()
            score = -ChessAI.find_move_negamax_alpha_beta(gs, next_moves, depth - 1, -beta, -alpha, -turn_multiplier)
            if score > max_score:
                max_score = score
                if depth == ChessAI.get_initial_depth(gs):
                    next_move = move
            gs.undo_move()
            if max_score > alpha:
                alpha = max_score
            if alpha >= beta:
                break
        return max_score
    
    @staticmethod
    def score_board(gs):
        """Оценивает позицию на доске"""
        if gs.checkmate:
            if gs.white_to_move:
                return -ChessAI.CHECKMATE
            else:
                return ChessAI.CHECKMATE
        elif gs.stalemate:
            return ChessAI.STALEMATE
        
        score = 0
        for row in gs.board:
            for square in row:
                if square[0] == 'w':
                    score += ChessAI.piece_score[square[1]]
                elif square[0] == 'b':
                    score -= ChessAI.piece_score[square[1]]
        return score
    
    @staticmethod
    def get_initial_depth(gs):
        # Возвращаем глубину поиска, которая используется для определения хода на верхнем уровне
        return getattr(ChessAI, '_current_depth', 2)

def draw_game_state(screen, gs, valid_moves, sq_selected):
    draw_board(screen)
    highlight_squares(screen, gs, valid_moves, sq_selected)
    draw_pieces(screen, gs.board)

def draw_board(screen):
    colors = [WHITE, GRAY]
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            color = colors[((r + c) % 2)]
            pygame.draw.rect(screen, color, pygame.Rect(c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE))

def highlight_squares(screen, gs, valid_moves, sq_selected):
    if sq_selected != ():
        r, c = sq_selected
        if gs.board[r][c][0] == ('w' if gs.white_to_move else 'b'):
            # Подсветка выбранной клетки
            s = pygame.Surface((SQ_SIZE, SQ_SIZE))
            s.set_alpha(100)
            s.fill(YELLOW)
            screen.blit(s, (c * SQ_SIZE, r * SQ_SIZE))
            # Подсветка возможных ходов
            s.fill(HIGHLIGHT_COLOR)
            for move in valid_moves:
                if move.start_row == r and move.start_col == c:
                    screen.blit(s, (move.end_col * SQ_SIZE, move.end_row * SQ_SIZE))

def draw_pieces(screen, board):
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            piece = board[r][c]
            if piece != "--":
                screen.blit(IMAGES[piece], pygame.Rect(c * SQ_SIZE + 5, r * SQ_SIZE + 5, SQ_SIZE, SQ_SIZE))

def draw_text(screen, text):
    font = pygame.font.SysFont("Arial", 32, True, False)
    text_object = font.render(text, 0, pygame.Color('Red'))
    text_location = pygame.Rect(0, 0, WIDTH, HEIGHT).move(WIDTH/2 - text_object.get_width()/2, HEIGHT/2 - text_object.get_height()/2)
    screen.blit(text_object, text_location)
    text_object = font.render(text, 0, pygame.Color('Black'))
    screen.blit(text_object, text_location.move(2, 2))

def draw_menu(screen):
    """Рисует меню выбора сложности"""
    screen.fill((50, 50, 50))
    font_title = pygame.font.SysFont("Arial", 48, True, False)
    font_option = pygame.font.SysFont("Arial", 32, True, False)
    
    title = font_title.render("ШАХМАТЫ", True, (255, 255, 255))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
    
    subtitle = font_option.render("Выберите сложность ИИ:", True, (200, 200, 200))
    screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 200))
    
    options = [
        ("1. Легкий (глубина 1)", 1),
        ("2. Средний (глубина 2)", 2),
        ("3. Сложный (глубина 3)", 3),
        ("4. Эксперт (глубина 4)", 4)
    ]
    
    y_offset = 300
    for text, _ in options:
        option_text = font_option.render(text, True, (255, 255, 255))
        screen.blit(option_text, (WIDTH//2 - option_text.get_width()//2, y_offset))
        y_offset += 60
    
    instruction = font_option.render("Нажмите 1-4 для выбора", True, (150, 150, 150))
    screen.blit(instruction, (WIDTH//2 - instruction.get_width()//2, 600))

def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    screen.fill(pygame.Color("white"))
    pygame.display.set_caption('Шахматы')
    load_images()
    
    # Меню выбора сложности
    difficulty = None
    in_menu = True
    
    while in_menu:
        draw_menu(screen)
        pygame.display.flip()
        
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1:
                    difficulty = 1
                    in_menu = False
                elif e.key == pygame.K_2:
                    difficulty = 2
                    in_menu = False
                elif e.key == pygame.K_3:
                    difficulty = 3
                    in_menu = False
                elif e.key == pygame.K_4:
                    difficulty = 4
                    in_menu = False
    
    # Сохраняем сложность в класс AI
    ChessAI._current_depth = difficulty
    
    gs = GameState()
    valid_moves = gs.get_valid_moves()
    move_made = False
    running = True
    sq_selected = ()
    player_clicks = []
    game_over = False
    player_one = True  # True если человек играет белыми
    player_two = False  # True если человек играет черными
    ai_thinking = False
    
    while running:
        human_turn = (gs.white_to_move and player_one) or (not gs.white_to_move and player_two)
        
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.MOUSEBUTTONDOWN:
                if not game_over and human_turn:
                    location = pygame.mouse.get_pos()
                    col = location[0] // SQ_SIZE
                    row = location[1] // SQ_SIZE
                    if sq_selected == (row, col):
                        sq_selected = ()
                        player_clicks = []
                    else:
                        sq_selected = (row, col)
                        player_clicks.append(sq_selected)
                    if len(player_clicks) == 2:
                        move = Move(player_clicks[0], player_clicks[1], gs.board)
                        for i in range(len(valid_moves)):
                            if move == valid_moves[i]:
                                gs.make_move(valid_moves[i])
                                move_made = True
                                sq_selected = ()
                                player_clicks = []
                        if not move_made:
                            player_clicks = [sq_selected]
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_z:
                    gs.undo_move()
                    move_made = True
                    game_over = False
                    ai_thinking = False
                if e.key == pygame.K_r:
                    gs = GameState()
                    valid_moves = gs.get_valid_moves()
                    sq_selected = ()
                    player_clicks = []
                    move_made = False
                    game_over = False
                    ai_thinking = False
        
        # Ход ИИ
        if not game_over and not human_turn and not ai_thinking:
            ai_thinking = True
            ai_move = ChessAI.find_best_move(gs, valid_moves, difficulty)
            if ai_move is None:
                ai_move = valid_moves[0] if valid_moves else None
            if ai_move:
                gs.make_move(ai_move)
                move_made = True
            ai_thinking = False
        
        if move_made:
            valid_moves = gs.get_valid_moves()
            move_made = False
        
        draw_game_state(screen, gs, valid_moves, sq_selected)
        
        if gs.checkmate:
            game_over = True
            if gs.white_to_move:
                draw_text(screen, 'Черные победили матом!')
            else:
                draw_text(screen, 'Белые победили матом!')
        elif gs.stalemate:
            game_over = True
            draw_text(screen, 'Пат!')
        
        clock.tick(MAX_FPS)
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main()
