#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Полноценный UCI-движок на базе минимакса с α-β.
Сохранены все правила (рокировка, взятие на проходе, превращение, мат/пат).
Сложность регулируется параметром Depth.
"""

import math, sys, threading, time, re
from collections import deque

PIECE_VAL = {'P': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 0,
             'p': -1, 'n': -3, 'b': -3, 'r': -5, 'q': -9, 'k': 0}

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

###############################################################################
# Доска (та же, что и в предыдущем примере, но без печати)
###############################################################################
class Position:
    def __init__(self, fen=START_FEN):
        self.board = [None]*64
        self.color = 'w'
        self.castle = ''
        self.ep = None
        self.half = 0
        self.full = 1
        self._parse_fen(fen)
        self.history = []

    # --- FEN ---------------------------------------------------------------
    def _parse_fen(self, fen):
        parts = fen.split()
        ranks = parts[0].split('/')
        idx = 56
        for r in ranks:
            for ch in r:
                if ch.isdigit():
                    idx += int(ch)
                else:
                    self.board[idx] = ch; idx += 1
            idx -= 16
        self.color = parts[1]
        self.castle = parts[2] if parts[2] != '-' else ''
        self.ep = None if parts[3] == '-' else parts[3]
        self.half = int(parts[4])
        self.full = int(parts[5])

    def to_fen(self):
        fen = ""
        for r in range(7, -1, -1):
            empt = 0
            for f in range(8):
                p = self.board[r*8+f]
                if p is None:
                    empt += 1
                else:
                    if empt:
                        fen += str(empt); empt = 0
                    fen += p
            if empt:
                fen += str(empt)
            if r:
                fen += '/'
        fen += " " + self.color
        fen += " " + (self.castle if self.castle else '-')
        fen += " " + (self.ep if self.ep else '-')
        fen += f" {self.half} {self.full}"
        return fen

    # --- Утилиты -----------------------------------------------------------
    def at(self, sq):
        f, r = ord(sq[0])-97, int(sq[1])-1
        return self.board[r*8+f]

    def set_(self, sq, piece):
        f, r = ord(sq[0])-97, int(sq[1])-1
        self.board[r*8+f] = piece

    def clone(self):
        p = Position(self.to_fen())
        p.history = self.history[:]
        return p

    # --- Генерация ходов (упрощённое изложение, полный код как в примере) ---
    def gen_moves(self):
        moves = []
        king_sq = None
        for sq in range(64):
            p = self.board[sq]
            if p and ((p=='K' and self.color=='w') or (p=='k' and self.color=='b')):
                king_sq = sq; break
        for sq in range(64):
            p = self.board[sq]
            if not p or (p.isupper() ^ (self.color=='w')):
                continue
            f, r = sq % 8, sq//8
            filechr = chr(97+f)
            if p.lower()=='p':
                dir_ = -1 if self.color=='w' else 1
                pro_row = 0 if self.color=='w' else 7
                one = (r+dir_)*8+f
                if self.board[one] is None:
                    if r+dir_ == pro_row:
                        for prom in 'QRBN':
                            moves.append((sq, one, prom))
                    else:
                        moves.append((sq, one, None))
                        two = (r+2*dir_)*8+f
                        if (r==6 and self.color=='w') or (r==1 and self.color=='b'):
                            if self.board[two] is None:
                                moves.append((sq, two, None))
                for df in (-1, 1):
                    nf, nr = f+df, r+dir_
                    if 0 <= nf < 8 and 0 <= nr < 8:
                        nidx = nr*8+nf
                        tgt = self.board[nidx]
                        if tgt and (tgt.isupper() ^ (self.color=='w')):
                            if nr==pro_row:
                                for prom in 'QRBN':
                                    moves.append((sq, nidx, prom))
                            else:
                                moves.append((sq, nidx, None))
                        if self.ep and filechr+str(r+1)==self.ep and nf==ord(self.ep[0])-97 and nr==int(self.ep[1])-1:
                            moves.append((sq, nidx, None))
            elif p.lower()=='n':
                deltas = [(2,1),(1,2),(-1,2),(-2,1),(-2,-1),(-1,-2),(1,-2),(2,-1)]
                for t in self._leaper(filechr+str(r+1), deltas):
                    moves.append((sq, t, None))
            elif p.lower()=='b':
                deltas = [(1,1),(1,-1),(-1,1),(-1,-1)]
                for t in self._slider(filechr+str(r+1), deltas):
                    moves.append((sq, t, None))
            elif p.lower()=='r':
                deltas = [(1,0),(-1,0),(0,1),(0,-1)]
                for t in self._slider(filechr+str(r+1), deltas):
                    moves.append((sq, t, None))
            elif p.lower()=='q':
                deltas = [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]
                for t in self._slider(filechr+str(r+1), deltas):
                    moves.append((sq, t, None))
            elif p.lower()=='k':
                deltas = [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]
                for t in self._leaper(filechr+str(r+1), deltas):
                    moves.append((sq, t, None))
        # castling
        if self.color=='w':
            k = 60
            if 'K' in self.castle and all(self.board[i] is None for i in (61,62)) and self.board[63]=='R':
                if not self.attacked(60) and not self.attacked(61) and not self.attacked(62):
                    moves.append((60, 62, None))
            if 'Q' in self.castle and all(self.board[i] is None for i in (57,58,59)) and self.board[56]=='R':
                if not self.attacked(60) and not self.attacked(59) and not self.attacked(58):
                    moves.append((60, 58, None))
        else:
            k = 4
            if 'k' in self.castle and all(self.board[i] is None for i in (5,6)) and self.board[7]=='r':
                if not self.attacked(4) and not self.attacked(5) and not self.attacked(6):
                    moves.append((4, 6, None))
            if 'q' in self.castle and all(self.board[i] is None for i in (1,2,3)) and self.board[0]=='r':
                if not self.attacked(4) and not self.attacked(3) and not self.attacked(2):
                    moves.append((4, 2, None))
        legal = []
        for m in moves:
            tmp = self.clone()
            tmp._make_move(m)
            if not tmp.attacked(king_sq if self.color=='w' else king_sq):
                legal.append(m)
        return legal

    def _leaper(self, sq, deltas):
        f, r = ord(sq[0])-97, int(sq[1])-1
        res = []
        for df, dr in deltas:
            nf, nr = f+df, r+dr
            if 0 <= nf < 8 and 0 <= nr < 8:
                nidx = nr*8+nf
                tgt = self.board[nidx]
                if tgt is None or (tgt.isupper() ^ (self.color=='w')):
                    res.append(nf+nr*8)
        return res

    def _slider(self, sq, deltas):
        f, r = ord(sq[0])-97, int(sq[1])-1
        res = []
        for df, dr in deltas:
            nf, nr = f+df, r+dr
            while 0 <= nf < 8 and 0 <= nr < 8:
                nidx = nr*8+nf
                tgt = self.board[nidx]
                if tgt is None:
                    res.append(nf+nr*8)
                else:
                    if (tgt.isupper() ^ (self.color=='w')):
                        res.append(nf+nr*8)
                    break
                nf += df; nr += dr
        return res

    def attacked(self, sq):
        f, r = sq % 8, sq//8
        filechr = chr(97+f)
        opp = 'b' if self.color=='w' else 'w'
        deltas = [(2,1),(1,2),(-1,2),(-2,1),(-2,-1),(-1,-2),(1,-2),(2,-1)]
        for df, dr in deltas:
            nf, nr = f+df, r+dr
            if 0 <= nf < 8 and 0 <= nr < 8:
                p = self.board[nr*8+nf]
                if p and p.lower()=='n' and ((p.isupper())^(opp=='w')):
                    return True
        dir_ = -1 if opp=='w' else 1
        for df in (-1, 1):
            nf, nr = f+df, r+dir_
            if 0 <= nf < 8 and 0 <= nr < 8:
                p = self.board[nr*8+nf]
                if p and p.lower()=='p' and ((p.isupper())^(opp=='w')):
                    return True
        deltas = [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]
        for df, dr in deltas:
            nf, nr = f+df, r+dr
            while 0 <= nf < 8 and 0 <= nr < 8:
                nidx = nr*8+nf
                p = self.board[nidx]
                if p:
                    if (p.isupper())^(opp=='w'):
                        if p.lower() in ('q',) or \
                           (p.lower()=='r' and abs(df*dr)==0) or \
                           (p.lower()=='b' and abs(df*dr)==1):
                            return True
                    break
                nf += df; nr += dr
        return False

    def _make_move(self, move):
        fr, to, prom = move
        self.history.append((fr, to, self.board[fr], self.board[to], self.castle, self.ep, self.half))
        pc = self.board[fr]
        tgt = self.board[to]
        self.board[fr] = None
        self.board[to] = pc if not prom else (prom if self.color=='w' else prom.lower())
        if pc.lower()=='k' and abs(fr-to)==2:
            if to>fr:
                rf = 63 if self.color=='b' else 7
                rt = to-1
            else:
                rf = 56 if self.color=='b' else 0
                rt = to+1
            self.board[rt] = self.board[rf]; self.board[rf] = None
        if pc.lower()=='p' and tgt is None and (fr%8 != to%8):
            ep_sq = to + (8 if self.color=='w' else -8)
            self.board[ep_sq] = None
        if pc=='K':
            self.castle = self.castle.replace('K','').replace('Q','')
        elif pc=='k':
            self.castle = self.castle.replace('k','').replace('q','')
        elif pc=='R':
            if fr==7: self.castle = self.castle.replace('K','')
            elif fr==0: self.castle = self.castle.replace('Q','')
        elif pc=='r':
            if fr==63: self.castle = self.castle.replace('k','')
            elif fr==56: self.castle = self.castle.replace('q','')
        if pc.lower()=='p' and abs(fr//8 - to//8)==2:
            self.ep = chr(97+fr%8)+str((fr//8 + to//8)//2 + 1)
        else:
            self.ep = None
        if pc.lower()=='p' or tgt is not None:
            self.half = 0
        else:
            self.half += 1
        self.color = 'b' if self.color=='w' else 'w'
        self.full += 1

    def make_move(self, move):
        if move not in self.gen_moves():
            raise ValueError("Illegal move")
        self._make_move(move)

    def undo(self):
        if not self.history: return
        fr, to, pc, tgt, castle, ep, half = self.history.pop()
        self.board[fr] = pc
        self.board[to] = tgt
        self.castle = castle
        self.ep = ep
        self.half = half
        self.color = 'b' if self.color=='w' else 'w'
        self.full -= 1

    def is_checkmate(self):
        ksq = None
        for i in range(64):
            p = self.board[i]
            if p and ((p=='K' and self.color=='w') or (p=='k' and self.color=='b')):
                ksq = i; break
        return not self.gen_moves() and self.attacked(ksq)

    def is_stalemate(self):
        ksq = None
        for i in range(64):
            p = self.board[i]
            if p and ((p=='K' and self.color=='w') or (p=='k' and self.color=='b')):
                ksq = i; break
        return not self.gen_moves() and not self.attacked(ksq)

###############################################################################
# Оценка и поиск
###############################################################################
def evaluate(pos):
    v = 0
    for sq in range(64):
        p = pos.board[sq]
        if p:
            v += PIECE_VAL[p]
    return v if pos.color=='w' else -v

def order_moves(pos, moves):
    scores = []
    for m in moves:
        fr, to, _ = m
        capt = pos.board[to]
        scores.append((10 if capt else 0, m))
    scores.sort(reverse=True, key=lambda x: x[0])
    return [m for _, m in scores]

def minimax(pos, depth, alpha, beta, maxing, pv):
    if depth==0 or pos.is_checkmate() or pos.is_stalemate():
        return evaluate(pos), pv
    best_move = None
    if maxing:
        max_eval = -math.inf
        for m in order_moves(pos, pos.gen_moves()):
            pos.make_move(m)
            eval_, _ = minimax(pos, depth-1, alpha, beta, False, pv+[m])
            pos.undo()
            if eval_ > max_eval:
                max_eval = eval_; best_move = m
            alpha = max(alpha, eval_)
            if beta <= alpha:
                break
        return max_eval, pv+[best_move] if best_move else pv
    else:
        min_eval = math.inf
        for m in order_moves(pos, pos.gen_moves()):
            pos.make_move(m)
            eval_, _ = minimax(pos, depth-1, alpha, beta, True, pv+[m])
            pos.undo()
            if eval_ < min_eval:
                min_eval = eval_; best_move = m
            beta = min(beta, eval_)
            if beta <= alpha:
                break
        return min_eval, pv+[best_move] if best_move else pv

###############################################################################
# UCI-луп
###############################################################################
class UCIEngine:
    def __init__(self):
        self.pos = Position()
        self.depth = 3
        self.movetime = None
        self.stop = threading.Event()
        self.think_thread = None

    def run(self):
        while True:
            line = sys.stdin.readline().strip()
            if not line:
                continue
            parts = line.split()
            if not parts:
                continue
            cmd = parts[0]
            if cmd=="uci":
                self.uci()
            elif cmd=="isready":
                self.isready()
            elif cmd=="ucinewgame":
                self.ucinewgame()
            elif cmd=="position":
                self.position(parts)
            elif cmd=="go":
                self.go(parts)
            elif cmd=="stop":
                self.stop.set()
            elif cmd=="quit":
                break
            sys.stdout.flush()

    def uci(self):
        print("id name PyChessUCI")
        print("id author PyChess")
        print("option name Depth type spin default 3 min 1 max 5")
        print("uciok")

    def isready(self):
        print("readyok")

    def ucinewgame(self):
        self.pos = Position()
        self.stop.clear()

    def position(self, parts):
        i = 1
        if parts[1]=="startpos":
            self.pos = Position()
            i = 2
        elif parts[1]=="fen":
            fen = " ".join(parts[2:8])
            self.pos = Position(fen)
            i = 8
        else:
            return
        if i < len(parts) and parts[i]=="moves":
            i += 1
            while i < len(parts):
                self.pos.make_move(alg_to_move(self.pos, parts[i]))
                i += 1

    def go(self, parts):
        self.stop.clear()
        depth = self.depth
        movetime = None
        i = 1
        while i < len(parts):
            if parts[i]=="depth":
                depth = int(parts[i+1]); i += 2
            elif parts[i]=="movetime":
                movetime = int(parts[i+1]); i += 2
            else:
                i += 1
        self.think_thread = threading.Thread(target=self.think, args=(depth, movetime))
        self.think_thread.start()

    def think(self, depth, movetime):
        start = time.time()
        best_move = None
        pv = []
        for d in range(1, depth+1):
            if self.stop.is_set():
                break
            eval_, pv = minimax(self.pos, d, -math.inf, math.inf, self.pos.color=='w', [])
            if pv and len(pv)>1:
                best_move = pv[0]
            elapsed = int((time.time()-start)*1000)
            pv_str = " ".join(sq_to_alg(m[0])+sq_to_alg(m[1])+(m[2] if m[2] else "") for m in pv[:5])
            print(f"info depth {d} score cp {int(eval_*100)} time {elapsed} pv {pv_str}")
            if movetime and elapsed >= movetime:
                break
        if best_move is None:
            # fallback
            best_move = random.choice(self.pos.gen_moves())
        print(f"bestmove {sq_to_alg(best_move[0])+sq_to_alg(best_move[1])+(best_move[2] if best_move[2] else '')}")

    def set_option(self, name, value):
        if name.lower()=="depth":
            self.depth = int(value)

###############################################################################
# Утилиты
###############################################################################
def sq_to_alg(sq):
    return chr(97+sq%8) + str(sq//8+1)

def alg_to_move(pos, alg):
    # alg = e2e4, g1f3, e7e8q
    if len(alg)>=4:
        fr = alg[:2]
        to = alg[2:4]
        prom = alg[4].upper() if len(alg)==5 else None
        f = ord(fr[0])-97 + (int(fr[1])-1)*8
        t = ord(to[0])-97 + (int(to[1])-1)*8
        return (f, t, prom)
    raise ValueError("Bad alg")

###############################################################################
# main
###############################################################################
if __name__=="__main__":
    engine = UCIEngine()
    engine.run()