#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import math, sys, re, random

PIECE_VAL = {'P': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 0,
             'p': -1, 'n': -3, 'b': -3, 'r': -5, 'q': -9, 'k': 0}

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

###############################################################################
# Доска / ходы
###############################################################################
class Position:
    def __init__(self, fen=START_FEN):
        self.board = [None]*64          # 0..63 = a1..h8
        self.color = 'w'                # кто ходит
        self.castle = ''                # KQkq
        self.ep = None                  # проходное поле
        self.half = 0                   # 50-move rule
        self.full = 1                   # номер хода
        self._parse_fen(fen)
        self.history = []               # для undo

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
    def at(self, sq):               # 'e4' -> 'P'
        f, r = ord(sq[0])-97, int(sq[1])-1
        return self.board[r*8+f]

    def set_(self, sq, piece):      # 'e4','Q'
        f, r = ord(sq[0])-97, int(sq[1])-1
        self.board[r*8+f] = piece

    def clone(self):
        p = Position(self.to_fen())
        p.history = self.history[:]   # shallow копия
        return p

    # --- Генерация ходов ---------------------------------------------------
    def _slider(self, sq, deltas):
        f, r = ord(sq[0])-97, int(sq[1])-1
        idx = r*8+f
        res = []
        for df, dr in deltas:
            nf, nr = f+df, r+dr
            while 0 <= nf < 8 and 0 <= nr < 8:
                nidx = nr*8+nf
                tgt = self.board[nidx]
                if tgt is None:
                    res.append(nf+nr*8)
                else:
                    if (tgt.isupper() ^ self.color=='w'):
                        res.append(nf+nr*8)
                    break
                nf += df; nr += dr
        return res

    def _leaper(self, sq, deltas):
        f, r = ord(sq[0])-97, int(sq[1])-1
        idx = r*8+f
        res = []
        for df, dr in deltas:
            nf, nr = f+df, r+dr
            if 0 <= nf < 8 and 0 <= nr < 8:
                tgt = self.board[nr*8+nf]
                if tgt is None or (tgt.isupper() ^ self.color=='w'):
                    res.append(nf+nr*8)
        return res

    def gen_moves(self):
        moves = []
        king_sq = None
        # найдём короля
        for sq in range(64):
            p = self.board[sq]
            if p and ((p=='K' and self.color=='w') or (p=='k' and self.color=='b')):
                king_sq = sq; break
        # все фигуры
        for sq in range(64):
            p = self.board[sq]
            if not p or (p.isupper() ^ (self.color=='w')):
                continue
            f, r = sq % 8, sq//8
            filechr = chr(97+f)
            # пешка
            if p.lower()=='p':
                dir_ = -1 if self.color=='w' else 1
                start_r = 6 if self.color=='w' else 1
                pro_row = 0 if self.color=='w' else 7
                # 1 вперёд
                one = (r+dir_)*8+f
                if self.board[one] is None:
                    if r+dir_ == pro_row:
                        for prom in 'QRBN':
                            moves.append((sq, one, prom))
                    else:
                        moves.append((sq, one, None))
                        # 2 вперёд
                        if r==start_r:
                            two = (r+2*dir_)*8+f
                            if self.board[two] is None:
                                moves.append((sq, two, None))
                # взятия
                for df in (-1, 1):
                    nf = f+df
                    if 0 <= nf < 8:
                        nr = r+dir_
                        if 0 <= nr < 8:
                            nidx = nr*8+nf
                            tgt = self.board[nidx]
                            if tgt and (tgt.isupper() ^ (self.color=='w')):
                                if nr==pro_row:
                                    for prom in 'QRBN':
                                        moves.append((sq, nidx, prom))
                                else:
                                    moves.append((sq, nidx, None))
                            # взятие на проходе
                            if self.ep and filechr+str(r+1)==self.ep and nf==ord(self.ep[0])-97 and nr==int(self.ep[1])-1:
                                moves.append((sq, nidx, None))
            # рыцарь
            elif p.lower()=='n':
                deltas = [(2,1),(1,2),(-1,2),(-2,1),(-2,-1),(-1,-2),(1,-2),(2,-1)]
                for t in self._leaper(filechr+str(r+1), deltas):
                    moves.append((sq, t, None))
            # слон
            elif p.lower()=='b':
                deltas = [(1,1),(1,-1),(-1,1),(-1,-1)]
                for t in self._slider(filechr+str(r+1), deltas):
                    moves.append((sq, t, None))
            # ладья
            elif p.lower()=='r':
                deltas = [(1,0),(-1,0),(0,1),(0,-1)]
                for t in self._slider(filechr+str(r+1), deltas):
                    moves.append((sq, t, None))
            # ферзь
            elif p.lower()=='q':
                deltas = [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]
                for t in self._slider(filechr+str(r+1), deltas):
                    moves.append((sq, t, None))
            # король
            elif p.lower()=='k':
                deltas = [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]
                for t in self._leaper(filechr+str(r+1), deltas):
                    moves.append((sq, t, None))
        # рокировки
        if self.color=='w':
            k = 4; kr = 7; qr = 0
            if 'K' in self.castle and all(self.board[i] is None for i in (5,6)) and self.board[kr]=='R':
                if not self.attacked(60) and not self.attacked(61) and not self.attacked(62):
                    moves.append((60, 62, None))
            if 'Q' in self.castle and all(self.board[i] is None for i in (1,2,3)) and self.board[qr]=='R':
                if not self.attacked(60) and not self.attacked(59) and not self.attacked(58):
                    moves.append((60, 58, None))
        else:
            k = 60+4; kr = 63; qr = 56
            if 'k' in self.castle and all(self.board[i] is None for i in (61,62)) and self.board[kr]=='r':
                if not self.attacked(60) and not self.attacked(61) and not self.attacked(62):
                    moves.append((60, 62, None))
            if 'q' in self.castle and all(self.board[i] is None for i in (57,58,59)) and self.board[qr]=='r':
                if not self.attacked(60) and not self.attacked(59) and not self.attacked(58):
                    moves.append((60, 58, None))
        # фильтр шахов
        legal = []
        for m in moves:
            tmp = self.clone()
            tmp._make_move(m)
            if not tmp.attacked(king_sq if self.color=='w' else king_sq):
                legal.append(m)
        return legal

    def attacked(self, sq):
        f, r = sq % 8, sq//8
        filechr = chr(97+f)
        opp = 'b' if self.color=='w' else 'w'
        # рыцарь
        deltas = [(2,1),(1,2),(-1,2),(-2,1),(-2,-1),(-1,-2),(1,-2),(2,-1)]
        for df, dr in deltas:
            nf, nr = f+df, r+dr
            if 0 <= nf < 8 and 0 <= nr < 8:
                p = self.board[nr*8+nf]
                if p and p.lower()=='n' and ((p.isupper())^(opp=='w')):
                    return True
        # пешка
        dir_ = -1 if opp=='w' else 1
        for df in (-1, 1):
            nf, nr = f+df, r+dir_
            if 0 <= nf < 8 and 0 <= nr < 8:
                p = self.board[nr*8+nf]
                if p and p.lower()=='p' and ((p.isupper())^(opp=='w')):
                    return True
        # линейные
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
        # рокировка
        if pc.lower()=='k' and abs(fr-to)==2:
            if to>fr:   # K-side
                rf = 63 if self.color=='b' else 7
                rt = to-1
            else:       # Q-side
                rf = 56 if self.color=='b' else 0
                rt = to+1
            self.board[rt] = self.board[rf]; self.board[rf] = None
        # взятие на проходе
        if pc.lower()=='p' and tgt is None and (fr%8 != to%8):
            ep_sq = to + (8 if self.color=='w' else -8)
            self.board[ep_sq] = None
        # обновить права рокировки
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
        # поле en-passant
        if pc.lower()=='p' and abs(fr//8 - to//8)==2:
            self.ep = chr(97+fr%8)+str((fr//8 + to//8)//2 + 1)
        else:
            self.ep = None
        # 50-move
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
        if not self.gen_moves() and self.attacked([i for i in range(64) if self.board[i] and ((self.board[i]=='K' and self.color=='w') or (self.board[i]=='k' and self.color=='b'))][0]):
            return True
        return False

    def is_stalemate(self):
        if not self.gen_moves() and not self.attacked([i for i in range(64) if self.board[i] and ((self.board[i]=='K' and self.color=='w') or (self.board[i]=='k' and self.color=='b'))][0]):
            return True
        return False

###############################################################################
# ИИ
###############################################################################
def evaluate(pos):
    "Табличная + позиционная оценка (очень примитивно)"
    mg = 0
    for sq in range(64):
        p = pos.board[sq]
        if p:
            mg += PIECE_VAL[p]
    return mg if pos.color=='w' else -mg

def order_moves(pos, moves):
    "Простая сортировка: сначала захваты, потом остальное"
    scores = []
    for m in moves:
        fr, to, _ = m
        capt = pos.board[to]
        scores.append((10 if capt else 0, m))
    scores.sort(reverse=True, key=lambda x: x[0])
    return [m for _, m in scores]

def minimax(pos, depth, alpha, beta, maxing):
    if depth==0 or pos.is_checkmate() or pos.is_stalemate():
        return evaluate(pos), None
    best_move = None
    if maxing:
        max_eval = -math.inf
        for m in order_moves(pos, pos.gen_moves()):
            pos.make_move(m)
            eval_, _ = minimax(pos, depth-1, alpha, beta, False)
            pos.undo()
            if eval_ > max_eval:
                max_eval = eval_; best_move = m
            alpha = max(alpha, eval_)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = math.inf
        for m in order_moves(pos, pos.gen_moves()):
            pos.make_move(m)
            eval_, _ = minimax(pos, depth-1, alpha, beta, True)
            pos.undo()
            if eval_ < min_eval:
                min_eval = eval_; best_move = m
            beta = min(beta, eval_)
            if beta <= alpha:
                break
        return min_eval, best_move

def ai_move(pos, depth):
    _, m = minimax(pos, depth, -math.inf, math.inf, pos.color=='w')
    return m

###############################################################################
# Ввод/вывод
###############################################################################
def print_board(pos):
    print("   +-----------------+")
    for r in range(7, -1, -1):
        print(f" {r+1} |", end="")
        for f in range(8):
            p = pos.board[r*8+f]
            print(" " + (p if p else '.'), end="")
        print(" |")
    print("   +-----------------+")
    print("    a b c d e f g h")

SAN_RE = re.compile(r"^([KQRBN])?([a-h])?([1-8])?x?([a-h][1-8])(=[QRBN])?$")

def san_to_move(pos, san):
    san = san.strip()
    if san in ("O-O", "o-o", "0-0"):
        # K-side
        r = 1 if pos.color=='b' else 8
        return (60 if pos.color=='w' else 4, 62 if pos.color=='w' else 6, None)
    if san in ("O-O-O", "o-o-o", "0-0-0"):
        r = 1 if pos.color=='b' else 8
        return (60 if pos.color=='w' else 4, 58 if pos.color=='w' else 2, None)
    m = SAN_RE.match(san)
    if not m:
        # попробуем как координаты
        if len(san)==4 and san[0] in 'abcdefgh' and san[2] in 'abcdefgh':
            fr_sq = san[:2]
            to_sq = san[2:]
            f = ord(fr_sq[0])-97 + (int(fr_sq[1])-1)*8
            t = ord(to_sq[0])-97 + (int(to_sq[1])-1)*8
            # без превращения
            return (f, t, None)
        raise ValueError("Bad SAN")
    piece, file_, rank_, to_sq, prom = m.groups()
    if not piece:
        piece = 'P'
    pc = piece if pos.color=='w' else piece.lower()
    candidates = []
    for m in pos.gen_moves():
        fr, to, pr = m
        if pos.board[fr] and pos.board[fr].lower()==pc.lower() and sq_to_alg(to)==to_sq:
            if prom:
                if not pr or pr.upper()!=prom[1]:
                    continue
            else:
                if pr: continue
            candidates.append(m)
    if not candidates:
        raise ValueError("No matching move")
    if len(candidates)==1:
        return candidates[0]
    # уточнение по file_/rank_
    for m in candidates:
        fr, to, pr = m
        f = fr % 8
        r = fr // 8
        if file_ and ord(file_)-97 != f:
            continue
        if rank_ and int(rank_)-1 != r:
            continue
        return m
    return candidates[0]

def sq_to_alg(sq):
    return chr(97+sq%8) + str(sq//8+1)

###############################################################################
# main
###############################################################################
def main():
    print("=== шахматы-python ===")
    depth = 3
    try:
        d = input("Глубина ИИ (1-5, Enter=3): ").strip()
        if d:
            depth = int(d)
    except:
        depth = 3
    pos = Position()
    human = 'w'
    while True:
        print_board(pos)
        if pos.is_checkmate():
            print("Мат! ", "Вы выиграли!" if pos.color!=human else "ИИ выиграл!")
            break
        if pos.is_stalemate() or pos.half>=100:
            print("Пат / ничья!")
            break
        if pos.color == human:
            try:
                san = input("Ваш ход (SAN, например e2e4, Nf3, O-O): ").strip()
                if san in ("q", "quit", "exit"):
                    break
                m = san_to_move(pos, san)
                pos.make_move(m)
            except Exception as e:
                print("Ошибка:", e)
        else:
            print("ИИ думает…")
            m = ai_move(pos, depth)
            if m is None:
                print("ИИ сдаётся!")
                break
            pos.make_move(m)
            print("ИИ:", sq_to_alg(m[0])+sq_to_alg(m[1]) + (m[2] if m[2] else ""))

if __name__=="__main__":
    main()