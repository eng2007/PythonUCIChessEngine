# Быстрый старт

## Установка

Движок не требует установки дополнительных пакетов. Требуется только Python 3.8+.

```bash
python --version  # Проверьте версию Python
```

## Запуск

### 1. Тестирование движка

```bash
python chess_engine.py --test
```

Это запустит все тесты и покажет работу различных компонентов:
- Инициализация доски
- Генерация ходов
- Специальные ходы (рокировка, en passant, превращение)
- Определение мата/пата
- Поиск лучшего хода

### 2. Игра против движка

```bash
python chess_engine.py --game
```

Вы играете белыми. Вводите ходы в UCI формате:
- `e2e4` - переместить фигуру с e2 на e4
- `e7e8q` - превращение пешки в ферзя
- `quit` - выход
- `undo` - отменить последний ход

### 3. UCI режим (для подключения к GUI)

```bash
python chess_engine.py
```

Движок ждет UCI команды через stdin. Пример:

```
uci
isready
position startpos
go depth 5
quit
```

### 4. Примеры использования

```bash
python examples.py
```

Это запустит интерактивные примеры использования API движка.

## Подключение к шахматному GUI

Движок совместим с UCI-шахматными интерфейсами:

### Arena Chess (Windows)
1. Скачайте Arena с http://www.playwitharena.de/
2. Engines → Install New Engine
3. Выберите `chess_engine.py`
4. Тип протокола: UCI

### Cute Chess (Windows/Linux/Mac)
1. Скачайте Cute Chess с https://cutechess.com/
2. Tools → Settings → Engines → Add
3. Команда: `python /path/to/chess_engine.py`
4. Протокол: UCI

### PyChess (Linux)
1. Установите PyChess: `sudo apt-get install pychess`
2. Edit → Engines → Add Engine
3. Путь: `/path/to/chess_engine.py`

## Быстрый тест UCI

```bash
echo -e "uci\nisready\nposition startpos moves e2e4\ngo depth 3\nquit" | python chess_engine.py
```

Ожидаемый вывод:
```
id name ChessEngine
id author AI Chess Developer
uciok
readyok
bestmove [ход]
```

## Структура проекта

```
chess_engine/
├── chess_engine.py      # Главный файл (запуск здесь)
├── chess_board.py       # Доска и ходы
├── move_generator.py    # Генератор ходов
├── search_engine.py     # Алгоритм поиска
├── uci_interface.py     # UCI протокол
├── examples.py          # Примеры использования
├── README.md            # Полная документация
└── QUICKSTART.md        # Этот файл
```

## Использование в коде

```python
from chess_board import ChessBoard
from move_generator import MoveGenerator
from search_engine import SearchEngine

# Создать доску
board = ChessBoard()

# Получить легальные ходы
move_gen = MoveGenerator(board)
moves = move_gen.generate_legal_moves()

# Найти лучший ход
engine = SearchEngine()
best_move = engine.search(board, depth=4)

# Сделать ход
board.make_move(best_move)
```

## Настройка силы игры

Сила игры зависит от глубины поиска:
- Глубина 1-2: Начинающий
- Глубина 3-4: Средний уровень
- Глубина 5-6: Продвинутый
- Глубина 7+: Очень сильный (медленно)

Задается в команде `go depth N` или в `engine.search(board, depth=N)`

## Проблемы?

1. **"Python не найден"**: Установите Python 3.8+ с https://python.org
2. **"Модуль не найден"**: Убедитесь, что все файлы в одной директории
3. **"Слишком медленно"**: Уменьшите глубину поиска до 3-4
4. **GUI не видит движок**: Проверьте путь к python и chess_engine.py

## Дополнительная информация

См. README.md для полной документации.
