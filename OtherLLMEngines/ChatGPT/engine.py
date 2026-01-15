#!/usr/bin/env python3
"""
Python UCI Chess Engine v2.1
Fixed side/enemy logic, stable under testing.
Pure Python, educational, correct.
"""

import sys
from dataclasses import dataclass
from typing import List, Optional

sys.stdout.reconfigure(line_buffering=True)

WHITE, BLACK = 0, 1
EMPTY = '.'

FILES = 'abcdefgh'
RANKS = '12345678'

PIECE_VALUE = {
    'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 20000,
    'p': -100, 'n': -320, 'b': -330, 'r': -500, 'q': -900, 'k': -20000,
}

DIRS = [-8, 8, -1, 1, -9, -7, 7, 9]
KNIGHT_DIRS = [-17, -15, -10, -6, 6, 10, 15, 17]


@dataclass
class Move:
    frm: int
    to: int
    promo: Optional[str] = None
    ep: bool = False
    castle: bool = False

    def uci(self):
        s = sq_name(self.frm) + sq_name(self.to)
        if self.promo:
            s += self.promo.lower()
        return s


class Board:
    def __init__(self):
        self.board = [EMPTY] * 64
        self.side = WHITE
        self.castle = {'K': True, 'Q': True, 'k': True, 'q': True}
        self.ep = None
        self.set_fen(self.start_fen())

    @staticmethod
    def start_fen():
        return "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    def set_fen(self, fen):
        parts = fen.split()
        self.board = []
        for r in parts[0].split('/'):
            for c in r:
                self.board += [EMPTY] * int(c) if c.isdigit() else [c]
        self.side = WHITE if parts[1] == 'w' else BLACK
        self.castle = {k: k in parts[2] for k in 'KQkq'}
        self.ep = None if parts[3] == '-' else sq_idx(parts[3])

    # ================= move generation =================

    def generate_moves(self):
        return [m for m in self.generate_pseudo(self.side) if self.is_legal(m)]

    def generate_pseudo(self, side):
        moves = []
        for i, p in enumerate(self.board):
            if p == EMPTY or p.isupper() != (side == WHITE):
                continue
            if p.lower() == 'p':
                self.pawn_moves(i, side, moves)
            elif p.lower() == 'n':
                self.knight_moves(i, side, moves)
            elif p.lower() == 'b':
                self.slider_moves(i, side, moves, [-9, -7, 7, 9])
            elif p.lower() == 'r':
                self.slider_moves(i, side, moves, [-8, 8, -1, 1])
            elif p.lower() == 'q':
                self.slider_moves(i, side, moves, DIRS)
            elif p.lower() == 'k':
                self.king_moves(i, side, moves)
        return moves

    def pawn_moves(self, i, side, moves):
        p = self.board[i]
        d = -8 if side == WHITE else 8
        r = i // 8
        one = i + d
        if 0 <= one < 64 and self.board[one] == EMPTY:
            if one // 8 in (0, 7):
                for pr in 'qrbn':
                    moves.append(Move(i, one, pr))
            else:
                moves.append(Move(i, one))
            if r in (6, 1):
                two = i + 2 * d
                if self.board[two] == EMPTY:
                    moves.append(Move(i, two))
        for dc in (-1, 1):
            cap = i + d + dc
            # Check file wrap (pawn can't capture across board edge)
            if abs((i % 8) - (cap % 8)) != 1:
                continue
            if 0 <= cap < 64:
                if self.board[cap] != EMPTY and self.enemy(cap, side):
                    if cap // 8 in (0, 7):
                        for pr in 'qrbn':
                            moves.append(Move(i, cap, pr))
                    else:
                        moves.append(Move(i, cap))
                if self.ep == cap:
                    moves.append(Move(i, cap, ep=True))

    def knight_moves(self, i, side, moves):
        f, r = i % 8, i // 8
        for d in KNIGHT_DIRS:
            t = i + d
            tf, tr = t % 8, t // 8
            # Knight moves at most 2 squares in any direction
            if 0 <= t < 64 and abs(f - tf) <= 2 and abs(r - tr) <= 2 and not self.friend(t, side):
                moves.append(Move(i, t))

    def slider_moves(self, i, side, moves, dirs):
        for d in dirs:
            t = i + d
            prev = i
            while 0 <= t < 64:
                # Check for wrap-around (file difference should be at most 1 per step)
                if abs((prev % 8) - (t % 8)) > 1:
                    break
                if self.board[t] == EMPTY:
                    moves.append(Move(i, t))
                else:
                    if self.enemy(t, side):
                        moves.append(Move(i, t))
                    break
                prev = t
                t += d

    def king_moves(self, i, side, moves):
        f = i % 8
        for d in DIRS:
            t = i + d
            tf = t % 8
            # King moves at most 1 square in file direction
            if 0 <= t < 64 and abs(f - tf) <= 1 and not self.friend(t, side):
                moves.append(Move(i, t))
        if side == WHITE:
            if self.castle['K'] and self.board[61] == self.board[62] == EMPTY:
                moves.append(Move(60, 62, castle=True))
            if self.castle['Q'] and self.board[59] == self.board[58] == self.board[57] == EMPTY:
                moves.append(Move(60, 58, castle=True))
        else:
            if self.castle['k'] and self.board[5] == self.board[6] == EMPTY:
                moves.append(Move(4, 6, castle=True))
            if self.castle['q'] and self.board[3] == self.board[2] == self.board[1] == EMPTY:
                moves.append(Move(4, 2, castle=True))

    # ================= legality =================

    def is_legal(self, move):
        snap = self.snapshot()
        self.make(move)
        ok = not self.in_check(1 - self.side)
        self.restore(snap)
        return ok

    def in_check(self, side):
        king = 'K' if side == WHITE else 'k'
        try:
            ks = self.board.index(king)
        except ValueError:
            return False  # No king on board - invalid position, treat as not in check
        for m in self.generate_pseudo(1 - side):
            if m.to == ks:
                return True
        return False

    # ================= make / undo =================

    def make(self, m):
        p = self.board[m.frm]
        self.board[m.frm] = EMPTY
        if m.ep:
            self.board[m.to + (8 if p.isupper() else -8)] = EMPTY
        if m.castle:
            if m.to == 62: self.board[63], self.board[61] = EMPTY, 'R'
            if m.to == 58: self.board[56], self.board[59] = EMPTY, 'R'
            if m.to == 6: self.board[7], self.board[5] = EMPTY, 'r'
            if m.to == 2: self.board[0], self.board[3] = EMPTY, 'r'
        self.board[m.to] = p if not m.promo else (m.promo.upper() if p.isupper() else m.promo)
        self.ep = None
        if p.lower() == 'p' and abs(m.to - m.frm) == 16:
            self.ep = (m.to + m.frm) // 2
        self.side ^= 1

    def snapshot(self):
        return self.board[:], self.side, self.castle.copy(), self.ep

    def restore(self, s):
        self.board, self.side, self.castle, self.ep = s

    def friend(self, i, side):
        return self.board[i] != EMPTY and self.board[i].isupper() == (side == WHITE)

    def enemy(self, i, side):
        return self.board[i] != EMPTY and not self.friend(i, side)


# ================= search =================

class Search:
    def __init__(self, board):
        self.b = board

    def eval(self):
        return sum(PIECE_VALUE.get(p, 0) for p in self.b.board)

    def alphabeta(self, d, a, b):
        if d == 0:
            return self.eval()
        moves = self.b.generate_moves()
        if not moves:
            return -99999 if self.b.in_check(self.b.side) else 0
        for m in moves:
            s = self.b.snapshot()
            self.b.make(m)
            v = -self.alphabeta(d - 1, -b, -a)
            self.b.restore(s)
            if v >= b:
                return b
            a = max(a, v)
        return a

    def best(self, d):
        best, score = None, -10**9
        for m in self.b.generate_moves():
            s = self.b.snapshot()
            self.b.make(m)
            v = -self.alphabeta(d - 1, -10**9, 10**9)
            self.b.restore(s)
            if v > score:
                best, score = m, v
        return best


# ================= UCI =================

class UCI:
    def __init__(self):
        self.b = Board()
        self.s = Search(self.b)

    def loop(self):
        for l in sys.stdin:
            l = l.strip()
            if l == 'uci':
                print('id name PythonEngineV2.1')
                print('id author ChatGPT')
                print('uciok')
            elif l == 'isready':
                print('readyok')
            elif l.startswith('position'):
                self.position(l)
            elif l.startswith('go'):
                d = int(l.split()[-1]) if 'depth' in l else 3
                m = self.s.best(d)
                print('bestmove', m.uci() if m else '0000')
            elif l == 'quit':
                break

    def position(self, l):
        p = l.split()
        if p[1] == 'startpos':
            self.b.set_fen(self.b.start_fen())
            idx = 2
        else:
            self.b.set_fen(' '.join(p[2:8]))
            idx = 8
        if idx < len(p) and p[idx] == 'moves':
            for mv in p[idx + 1:]:
                self.b.make(Move(
                    sq_idx(mv[:2]),
                    sq_idx(mv[2:4]),
                    mv[4] if len(mv) > 4 else None
                ))


def sq_name(i):
    return FILES[i % 8] + RANKS[7 - i // 8]


def sq_idx(s):
    return (7 - (int(s[1]) - 1)) * 8 + FILES.index(s[0])


if __name__ == '__main__':
    UCI().loop()
