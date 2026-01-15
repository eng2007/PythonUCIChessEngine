"""
Примеры использования шахматного движка.
"""

from chess_board import ChessBoard, Move
from move_generator import MoveGenerator
from search_engine import SearchEngine


def example_1_basic_usage():
    """Пример 1: Базовое использование - создание доски и генерация ходов."""
    print("=== Example 1: Basic Usage ===\n")
    
    # Создаем доску в начальной позиции
    board = ChessBoard()
    print("Initial position:")
    print(board)
    print()
    
    # Генерируем легальные ходы
    move_gen = MoveGenerator(board)
    legal_moves = move_gen.generate_legal_moves()
    
    print(f"Number of legal moves: {len(legal_moves)}")
    print("First 10 moves:")
    for move in legal_moves[:10]:
        print(f"  {move.to_uci(board)}")
    print()


def example_2_making_moves():
    """Пример 2: Выполнение ходов."""
    print("=== Example 2: Making Moves ===\n")
    
    board = ChessBoard()
    move_gen = MoveGenerator(board)
    
    # Делаем несколько ходов
    moves_to_make = ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1c4', 'f8c5']
    
    for move_uci in moves_to_make:
        legal_moves = move_gen.generate_legal_moves()
        move = None
        
        for m in legal_moves:
            if m.to_uci(board) == move_uci:
                move = m
                break
        
        if move:
            print(f"Making move: {move_uci}")
            board.make_move(move)
        
        move_gen = MoveGenerator(board)
    
    print("\nPosition after moves:")
    print(board)
    print(f"FEN: {board.to_fen()}")
    print()


def example_3_fen_notation():
    """Пример 3: Работа с FEN нотацией."""
    print("=== Example 3: FEN Notation ===\n")
    
    # Загружаем известную позицию (мат дурака)
    board = ChessBoard()
    fen = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
    board.load_fen(fen)
    
    print("Fool's mate position:")
    print(board)
    print()
    
    # Проверяем мат
    move_gen = MoveGenerator(board)
    print(f"Is checkmate: {move_gen.is_checkmate()}")
    print(f"Is in check: {move_gen.is_in_check()}")
    print(f"Legal moves: {len(move_gen.generate_legal_moves())}")
    print()


def example_4_special_moves():
    """Пример 4: Специальные ходы."""
    print("=== Example 4: Special Moves ===\n")
    
    # Рокировка
    print("Castling:")
    board = ChessBoard()
    board.load_fen("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1")
    print(board)
    
    move_gen = MoveGenerator(board)
    for move in move_gen.generate_legal_moves():
        if move.is_castling:
            print(f"  Castling move: {move.to_uci(board)}")
    print()
    
    # En passant
    print("En Passant:")
    board = ChessBoard()
    board.load_fen("rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 1")
    print(board)
    
    move_gen = MoveGenerator(board)
    for move in move_gen.generate_legal_moves():
        if move.is_en_passant:
            print(f"  En passant move: {move.to_uci(board)}")
    print()
    
    # Превращение пешки
    print("Pawn Promotion:")
    board = ChessBoard()
    board.load_fen("4k3/P7/8/8/8/8/8/4K3 w - - 0 1")
    print(board)
    
    move_gen = MoveGenerator(board)
    for move in move_gen.generate_legal_moves():
        if move.is_promotion:
            print(f"  Promotion move: {move.to_uci(board)}")
    print()


def example_5_game_ending_conditions():
    """Пример 5: Условия окончания игры."""
    print("=== Example 5: Game Ending Conditions ===\n")
    
    # Мат
    print("Checkmate:")
    board = ChessBoard()
    board.load_fen("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
    move_gen = MoveGenerator(board)
    is_over, reason = move_gen.is_game_over()
    print(f"  {reason}\n")
    
    # Пат
    print("Stalemate:")
    board = ChessBoard()
    board.load_fen("7k/8/8/8/8/8/8/K6Q b - - 0 1")
    move_gen = MoveGenerator(board)
    is_over, reason = move_gen.is_game_over()
    print(f"  {reason}\n")
    
    # Недостаточность материала
    print("Insufficient Material:")
    board = ChessBoard()
    board.load_fen("7k/8/8/8/8/8/8/K7 w - - 0 1")
    move_gen = MoveGenerator(board)
    is_over, reason = move_gen.is_game_over()
    print(f"  {reason}\n")


def example_6_search_engine():
    """Пример 6: Использование поискового движка."""
    print("=== Example 6: Search Engine ===\n")
    
    board = ChessBoard()
    engine = SearchEngine()
    
    print("Searching for best move from starting position...")
    print("Depth 1:")
    best_move = engine.search(board, depth=1)
    print(f"  Best move: {best_move.to_uci(board)}")
    print(f"  Nodes searched: {engine.nodes_searched}")
    print()
    
    print("Depth 3:")
    best_move = engine.search(board, depth=3)
    print(f"  Best move: {best_move.to_uci(board)}")
    print(f"  Nodes searched: {engine.nodes_searched}")
    print()
    
    print("Depth 5:")
    best_move = engine.search(board, depth=5)
    print(f"  Best move: {best_move.to_uci(board)}")
    print(f"  Nodes searched: {engine.nodes_searched}")
    print()


def example_7_position_evaluation():
    """Пример 7: Оценка позиции."""
    print("=== Example 7: Position Evaluation ===\n")
    
    engine = SearchEngine()
    
    # Начальная позиция
    board = ChessBoard()
    score = engine.evaluate(board)
    print(f"Starting position evaluation: {score}")
    print("(Should be close to 0 - equal position)\n")
    
    # Позиция с материальным преимуществом
    board = ChessBoard()
    board.load_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBN1 w Qkq - 0 1")  # Белые без ладьи
    score = engine.evaluate(board)
    print(f"Position without white rook: {score}")
    print("(Should be negative - black is better)\n")
    
    # Позиция близкая к мату
    board = ChessBoard()
    board.load_fen("6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1")
    score = engine.evaluate(board)
    print(f"Position with extra rook: {score}")
    print("(Should be positive - white is better)\n")


def example_8_full_game():
    """Пример 8: Симуляция полной партии."""
    print("=== Example 8: Full Game Simulation ===\n")
    
    board = ChessBoard()
    engine = SearchEngine()
    move_count = 0
    max_moves = 20  # Ограничиваем для примера
    
    print("Simulating a game (first 20 moves):\n")
    
    while move_count < max_moves:
        move_gen = MoveGenerator(board)
        
        # Проверка на окончание игры
        is_over, reason = move_gen.is_game_over()
        if is_over:
            print(f"\nGame Over: {reason}")
            break
        
        # Поиск хода
        best_move = engine.search(board, depth=3, max_time=1.0)
        
        if not best_move:
            print("No legal moves available")
            break
        
        # Выполнение хода
        move_number = board.fullmove_number
        if board.white_to_move:
            print(f"{move_number}. {best_move.to_uci(board)}", end=" ")
        else:
            print(f"{best_move.to_uci(board)}")
        
        board.make_move(best_move)
        move_count += 1
    
    print("\n\nFinal position:")
    print(board)
    print()


def example_9_analyzing_tactics():
    """Пример 9: Анализ тактических позиций."""
    print("=== Example 9: Tactical Analysis ===\n")
    
    engine = SearchEngine()
    
    # Тактика: вилка конем
    print("Knight fork position:")
    board = ChessBoard()
    board.load_fen("r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1")
    print(board)
    
    best_move = engine.search(board, depth=4)
    print(f"Best move: {best_move.to_uci(board)}")
    print(f"(Engine should find a good tactical move)\n")
    
    # Тактика: связка
    print("Pin position:")
    board = ChessBoard()
    board.load_fen("r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1")
    print(board)
    
    best_move = engine.search(board, depth=4)
    print(f"Best move: {best_move.to_uci(board)}\n")


def main():
    """Запуск всех примеров."""
    examples = [
        example_1_basic_usage,
        example_2_making_moves,
        example_3_fen_notation,
        example_4_special_moves,
        example_5_game_ending_conditions,
        example_6_search_engine,
        example_7_position_evaluation,
        example_8_full_game,
        example_9_analyzing_tactics
    ]
    
    for i, example in enumerate(examples, 1):
        example()
        if i < len(examples):
            input("Press Enter to continue to next example...")
            print("\n" + "="*60 + "\n")


if __name__ == '__main__':
    main()
