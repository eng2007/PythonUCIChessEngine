#!/usr/bin/env python3
"""
Шахматный движок с поддержкой UCI протокола.

Использование:
    python chess_engine.py              - Запуск в UCI режиме
    python chess_engine.py --test       - Запуск тестового режима
    python chess_engine.py --game       - Интерактивная игра
"""

import sys
import argparse
from chess_board import ChessBoard, Move
from move_generator import MoveGenerator
from search_engine import SearchEngine
from uci_interface import UCIInterface


def test_mode():
    """Тестовый режим для проверки работы движка."""
    print("=== Chess Engine Test Mode ===\n")
    
    # Тест 1: Инициализация доски
    print("Test 1: Board initialization")
    board = ChessBoard()
    print(board)
    print(f"FEN: {board.to_fen()}")
    print()
    
    # Тест 2: Генерация ходов
    print("Test 2: Move generation from starting position")
    move_gen = MoveGenerator(board)
    legal_moves = move_gen.generate_legal_moves()
    print(f"Number of legal moves: {len(legal_moves)}")
    print("Sample moves:")
    for i, move in enumerate(legal_moves[:5]):
        print(f"  {move.to_uci(board)}")
    print()
    
    # Тест 3: Выполнение хода
    print("Test 3: Making a move (e2e4)")
    move = None
    for m in legal_moves:
        if m.to_uci(board) == 'e2e4':
            move = m
            break
    
    if move:
        board.make_move(move)
        print(board)
        print(f"FEN: {board.to_fen()}")
    print()
    
    # Тест 4: Проверка мата
    print("Test 4: Testing checkmate detection")
    mate_board = ChessBoard()
    mate_board.load_fen("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
    print(mate_board)
    mate_gen = MoveGenerator(mate_board)
    print(f"Is checkmate: {mate_gen.is_checkmate()}")
    print(f"Is in check: {mate_gen.is_in_check()}")
    print()
    
    # Тест 5: Поиск лучшего хода
    print("Test 5: Searching for best move")
    board = ChessBoard()
    engine = SearchEngine()
    print("Searching at depth 3...")
    best_move = engine.search(board, depth=3)
    if best_move:
        print(f"Best move: {best_move.to_uci(board)}")
        print(f"Nodes searched: {engine.nodes_searched}")
    print()
    
    # Тест 6: Рокировка
    print("Test 6: Testing castling")
    castling_board = ChessBoard()
    castling_board.load_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    print(castling_board)
    castling_gen = MoveGenerator(castling_board)
    castling_moves = castling_gen.generate_legal_moves()
    print("Castling moves available:")
    for move in castling_moves:
        if move.is_castling:
            print(f"  {move.to_uci(castling_board)}")
    print()
    
    # Тест 7: En passant
    print("Test 7: Testing en passant")
    ep_board = ChessBoard()
    ep_board.load_fen("rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 1")
    print(ep_board)
    ep_gen = MoveGenerator(ep_board)
    ep_moves = ep_gen.generate_legal_moves()
    print("En passant moves available:")
    for move in ep_moves:
        if move.is_en_passant:
            print(f"  {move.to_uci(ep_board)}")
    print()
    
    # Тест 8: Превращение пешки
    print("Test 8: Testing pawn promotion")
    promo_board = ChessBoard()
    promo_board.load_fen("8/P7/8/8/8/8/8/K6k w - - 0 1")
    print(promo_board)
    promo_gen = MoveGenerator(promo_board)
    promo_moves = promo_gen.generate_legal_moves()
    print("Promotion moves available:")
    for move in promo_moves:
        if move.is_promotion:
            print(f"  {move.to_uci(promo_board)}")
    print()
    
    print("=== All tests completed ===")


def interactive_game():
    """Интерактивная игра человек против движка."""
    print("=== Interactive Chess Game ===")
    print("You play as White. Enter moves in UCI format (e.g., e2e4)")
    print("Type 'quit' to exit, 'undo' to undo last move\n")
    
    board = ChessBoard()
    engine = SearchEngine()
    move_history = []
    
    while True:
        print(board)
        print(f"FEN: {board.to_fen()}\n")
        
        move_gen = MoveGenerator(board)
        
        # Проверка на окончание игры
        is_over, reason = move_gen.is_game_over()
        if is_over:
            print(f"Game Over: {reason}")
            break
        
        if board.white_to_move:
            # Ход игрока
            while True:
                move_input = input("Your move: ").strip().lower()
                
                if move_input == 'quit':
                    return
                
                if move_input == 'undo':
                    if len(move_history) >= 2:
                        # Отменяем два последних хода (игрок и компьютер)
                        move_history.pop()
                        move_history.pop()
                        board = ChessBoard()
                        for move in move_history:
                            board.make_move(move)
                        print("Undo completed\n")
                        break
                    else:
                        print("Nothing to undo\n")
                        continue
                
                # Парсинг хода
                legal_moves = move_gen.generate_legal_moves()
                move = None
                
                for m in legal_moves:
                    if m.to_uci(board) == move_input:
                        move = m
                        break
                
                if move:
                    board.make_move(move)
                    move_history.append(move)
                    break
                else:
                    print(f"Illegal move: {move_input}")
                    print("Legal moves:", ', '.join([m.to_uci(board) for m in legal_moves[:10]]))
                    if len(legal_moves) > 10:
                        print(f"... and {len(legal_moves) - 10} more")
        else:
            # Ход компьютера
            print("Computer is thinking...")
            best_move = engine.search(board, depth=4, max_time=5.0)
            
            if best_move:
                print(f"Computer plays: {best_move.to_uci(board)}")
                print(f"(Searched {engine.nodes_searched} nodes)\n")
                board.make_move(best_move)
                move_history.append(best_move)
            else:
                print("Computer has no legal moves\n")
                break


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(description='Chess Engine with UCI support')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--game', action='store_true', help='Play interactive game')
    
    args = parser.parse_args()
    
    if args.test:
        test_mode()
    elif args.game:
        interactive_game()
    else:
        # UCI режим по умолчанию
        uci = UCIInterface()
        uci.run()


if __name__ == '__main__':
    main()
