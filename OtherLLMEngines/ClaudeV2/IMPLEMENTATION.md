# Техническая реализация шахматного движка

## Обзор архитектуры

Движок состоит из пяти основных модулей, каждый из которых отвечает за отдельный аспект функциональности:

```
chess_board.py       → Представление доски и ходов
move_generator.py    → Генерация и валидация ходов
search_engine.py     → Поиск лучшего хода (AI)
uci_interface.py     → Интерфейс UCI протокола
chess_engine.py      → Главный модуль и CLI
```

## 1. Представление доски (chess_board.py)

### ChessBoard класс

**Структура данных:**
```python
board: List[List[str]]  # 8x8 массив символов
white_to_move: bool     # Очередь хода
castling_rights: dict   # {'K': bool, 'Q': bool, 'k': bool, 'q': bool}
en_passant_square: str  # Алгебраическая нотация или None
halfmove_clock: int     # Для правила 50 ходов
fullmove_number: int    # Номер хода
position_history: list  # Для троекратного повторения
```

**Ключевые методы:**
- `load_fen(fen)` - Загрузка позиции из FEN
- `to_fen()` - Экспорт в FEN
- `make_move(move)` - Выполнение хода
- `copy()` - Глубокое копирование доски

**Представление фигур:**
```python
Белые: P N B R Q K (uppercase)
Черные: p n b r q k (lowercase)
Пусто: . (точка)
```

### Move класс

**Атрибуты:**
```python
from_pos: (row, col)       # Начальная позиция
to_pos: (row, col)         # Конечная позиция
piece: str                 # Фигура
captured_piece: str        # Взятая фигура
is_capture: bool           # Флаг взятия
is_promotion: bool         # Флаг превращения
is_castling: bool          # Флаг рокировки
is_en_passant: bool        # Флаг en passant
promotion_piece: str       # Фигура для превращения
```

**Методы:**
- `to_uci(board)` - Конвертация в UCI формат
- `_determine_special_moves()` - Определение типа хода

## 2. Генератор ходов (move_generator.py)

### MoveGenerator класс

**Алгоритм генерации:**

1. **Псевдо-легальные ходы** (`_generate_pseudo_legal_moves`):
   - Перебор всех фигур текущего игрока
   - Генерация ходов для каждой фигуры по правилам
   - Не проверяется шах королю

2. **Проверка легальности** (`_is_legal_move`):
   - Делается ход на копии доски
   - Проверяется, атакован ли король
   - Если король под атакой - ход нелегален

**Генерация для фигур:**

```python
Пешка:
  - Ход на 1 вперед (2 с начальной позиции)
  - Взятие по диагонали
  - En passant
  - Превращение на последней горизонтали

Конь:
  - 8 направлений: (-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1)

Слон:
  - 4 диагонали: (-1,-1), (-1,1), (1,-1), (1,1)
  - До края доски или встречи с фигурой

Ладья:
  - 4 направления: (-1,0), (1,0), (0,-1), (0,1)
  - До края доски или встречи с фигурой

Ферзь:
  - Комбинация слона и ладьи (8 направлений)

Король:
  - 8 соседних клеток
  - Рокировка (с проверками)
```

**Рокировка:**
```python
Условия:
1. Король не двигался (флаг в castling_rights)
2. Ладья не двигалась (флаг в castling_rights)
3. Между королем и ладьей нет фигур
4. Король не под шахом
5. Король не проходит через атакованное поле
6. Король не становится под шах
```

**Определение состояний игры:**
- `is_checkmate()` - Шах и нет легальных ходов
- `is_stalemate()` - Нет шаха и нет легальных ходов
- `is_insufficient_material()` - K vs K, KN vs K, KB vs K, KB vs KB (одноцветные)
- `is_fifty_move_rule()` - 50 ходов без взятий и движения пешек
- `is_threefold_repetition()` - Позиция повторилась трижды

## 3. Поисковый движок (search_engine.py)

### SearchEngine класс

**Алгоритм Minimax с альфа-бета отсечением:**

```python
function minimax(board, depth, alpha, beta, maximizing):
    if depth == 0:
        return quiescence_search(board, alpha, beta)
    
    moves = generate_legal_moves(board)
    moves = order_moves(moves)  # Сортировка для оптимизации
    
    if maximizing:
        for move in moves:
            make_move(move)
            eval = minimax(board, depth-1, alpha, beta, false)
            undo_move(move)
            
            if eval >= beta:
                return beta  # Бета отсечение
            alpha = max(alpha, eval)
        return alpha
    else:
        for move in moves:
            make_move(move)
            eval = minimax(board, depth-1, alpha, beta, true)
            undo_move(move)
            
            if eval <= alpha:
                return alpha  # Альфа отсечение
            beta = min(beta, eval)
        return beta
```

**Quiescence Search:**
- Расширенный поиск только для взятий
- Избегает "горизонт-эффекта"
- Глубина 3 дополнительных уровня

**Упорядочивание ходов (Move Ordering):**
```python
Приоритет:
1. Взятия (MVV-LVA: Most Valuable Victim - Least Valuable Attacker)
2. Превращения пешки
3. Центральные ходы
```

**Оценочная функция:**

```python
score = 0

# 1. Материал
for each piece:
    score += piece_value * color

# 2. Позиционные бонусы (piece-square tables)
for each piece:
    score += position_bonus[piece_type][square]

# 3. Мобильность
score += num_legal_moves * 10

# 4. Специальные случаи
if checkmate:
    return ±20000
if stalemate:
    return 0
```

**Piece-Square Tables:**
- Предвычисленные бонусы за позицию фигур
- Пешки: бонус за продвижение
- Кони/Слоны: бонус за центр
- Король: бонус за безопасность

## 4. UCI интерфейс (uci_interface.py)

### UCIInterface класс

**Поддерживаемые команды:**

```
uci                 → Идентификация движка
isready             → Проверка готовности
ucinewgame          → Новая игра
position [args]     → Установка позиции
go [args]           → Начать поиск
stop                → Остановить поиск
quit                → Выход
d                   → Отладка (показать доску)
```

**Формат команды position:**
```
position startpos
position startpos moves e2e4 e7e5 g1f3
position fen <FEN_STRING>
position fen <FEN_STRING> moves e2e4
```

**Формат команды go:**
```
go depth N              → Искать на глубину N
go movetime N          → Искать N миллисекунд
go wtime N btime M     → Время на часах (мс)
go infinite            → Бесконечный поиск
```

**Вывод:**
```
bestmove e2e4          → Лучший найденный ход
info string [text]     → Отладочная информация
```

## 5. Главный модуль (chess_engine.py)

**Режимы работы:**

1. **UCI режим** (по умолчанию):
   ```bash
   python chess_engine.py
   ```
   - Ждет команды через stdin
   - Совместим с GUI

2. **Тестовый режим**:
   ```bash
   python chess_engine.py --test
   ```
   - Запускает 8 тестов
   - Проверяет все компоненты

3. **Интерактивная игра**:
   ```bash
   python chess_engine.py --game
   ```
   - Человек vs компьютер
   - Консольный интерфейс

## Производительность и оптимизации

### Текущие оптимизации:

1. **Альфа-бета отсечение:**
   - Пропуск ветвей дерева поиска
   - Экономия ~90% узлов при хорошем упорядочивании

2. **Move ordering:**
   - Взятия первыми (MVV-LVA)
   - Улучшает эффективность альфа-бета

3. **Quiescence search:**
   - Избегает тактических просмотров
   - Стабильная оценка позиции

4. **Piece-square tables:**
   - Быстрая оценка позиции
   - Без дополнительных вычислений

### Статистика производительности:

```
Глубина | Узлы     | Время (сек)
--------|----------|-------------
1       | ~40      | <0.01
2       | ~400     | <0.01
3       | ~4,000   | 0.05-0.1
4       | ~20,000  | 0.2-0.5
5       | ~100,000 | 1-3
6       | ~500,000 | 5-15
```

## Возможные улучшения

### 1. Поиск:
- **Iterative Deepening**: Постепенное увеличение глубины
- **Транспозиционная таблица**: Кеширование оценок позиций
- **Killer moves**: Запоминание хороших ходов
- **History heuristic**: Статистика успешных ходов
- **Principal Variation Search**: Оптимизация альфа-бета
- **Null Move Pruning**: Эвристика для отсечения

### 2. Оценка:
- **Безопасность короля**: Атаки на короля, защита
- **Структура пешек**: Сдвоенные, изолированные, проходные
- **Открытые линии**: Для ладей и ферзей
- **Фазы игры**: Разные оценки для дебюта/миттельшпиля/эндшпиля
- **Мобильность**: Более точный расчет
- **Контроль центра**: Дополнительные бонусы

### 3. Данные:
- **Дебютная книга**: База данных дебютов
- **Эндшпильные таблицы**: Syzygy tablebase
- **Обучение**: Neural networks для оценки

### 4. Технические:
- **Битборды**: Более эффективное представление доски
- **Многопоточность**: Parallel search
- **SIMD**: Векторизация вычислений
- **GPU**: Ускорение на видеокарте

## Тестирование

### Юнит-тесты:
```python
# Тест генерации ходов
assert len(generate_moves(starting_position)) == 20

# Тест мата
assert is_checkmate(fools_mate_position) == True

# Тест FEN
board.load_fen(fen)
assert board.to_fen() == fen
```

### Интеграционные тесты:
```python
# Полная игра
board = ChessBoard()
for _ in range(100):
    move = engine.search(board, depth=3)
    if not move:
        break
    board.make_move(move)
```

### Perft тесты:
```python
# Проверка количества позиций на глубине
def perft(board, depth):
    if depth == 0:
        return 1
    count = 0
    for move in generate_moves(board):
        make_move(move)
        count += perft(board, depth-1)
        undo_move(move)
    return count

# Стартовая позиция, глубина 5: 4,865,609 узлов
```

## Заключение

Движок реализует полный функционал шахматных правил и UCI протокола. Архитектура модульная и расширяемая. Код документирован и готов к использованию как автономно, так и через GUI интерфейсы.

**Сильные стороны:**
- ✅ Полная реализация правил FIDE
- ✅ UCI протокол
- ✅ Чистый Python (без зависимостей)
- ✅ Модульная архитектура
- ✅ Документированный код
- ✅ Работающий AI (Minimax + Alpha-Beta)

**Ограничения:**
- Глубина поиска ограничена (~6 полуходов)
- Нет дебютной книги
- Нет эндшпильных таблиц
- Простая оценочная функция

Движок подходит для обучения, экспериментов и игры на среднем уровне.
