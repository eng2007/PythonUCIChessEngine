"""
Тестовый скрипт для демонстрации UCI интерфейса
"""

import subprocess
import time

def test_uci():
    print("=== Тест UCI интерфейса ===\n")
    
    # Запускаем UCI интерфейс как подпроцесс
    process = subprocess.Popen(
        ['python', 'uci_interface.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    def send_command(cmd):
        print(f">> {cmd}")
        process.stdin.write(cmd + '\n')
        process.stdin.flush()
        time.sleep(0.1)
        
    def read_output():
        # Читаем доступный вывод
        output = []
        while True:
            try:
                # Используем небольшой таймаут для неблокирующего чтения
                line = process.stdout.readline()
                if line:
                    output.append(line.strip())
                    print(f"<< {line.strip()}")
                else:
                    break
            except:
                break
        return output
    
    try:
        # Тест 1: Инициализация UCI
        print("\n--- Тест 1: Инициализация ---")
        send_command("uci")
        time.sleep(0.2)
        read_output()
        
        # Тест 2: Проверка готовности
        print("\n--- Тест 2: Проверка готовности ---")
        send_command("isready")
        time.sleep(0.1)
        read_output()
        
        # Тест 3: Новая игра
        print("\n--- Тест 3: Новая игра ---")
        send_command("ucinewgame")
        send_command("isready")
        time.sleep(0.1)
        read_output()
        
        # Тест 4: Стартовая позиция
        print("\n--- Тест 4: Установка стартовой позиции ---")
        send_command("position startpos")
        send_command("display")
        time.sleep(0.1)
        read_output()
        
        # Тест 5: Поиск лучшего хода (глубина 2)
        print("\n--- Тест 5: Поиск лучшего хода (depth 2) ---")
        send_command("go depth 2")
        time.sleep(2)  # Даем время на расчет
        read_output()
        
        # Тест 6: Позиция с ходами
        print("\n--- Тест 6: Позиция после e2e4 e7e5 ---")
        send_command("position startpos moves e2e4 e7e5")
        send_command("display")
        time.sleep(0.1)
        read_output()
        
        # Тест 7: Еще один поиск
        print("\n--- Тест 7: Поиск лучшего хода из новой позиции ---")
        send_command("go depth 2")
        time.sleep(2)
        read_output()
        
        # Тест 8: Настройка глубины
        print("\n--- Тест 8: Настройка глубины через setoption ---")
        send_command("setoption name Depth value 1")
        send_command("isready")
        time.sleep(0.1)
        read_output()
        
        # Тест 9: Быстрый поиск с depth 1
        print("\n--- Тест 9: Быстрый поиск (depth 1) ---")
        send_command("go depth 1")
        time.sleep(1)
        read_output()
        
        # Завершение
        print("\n--- Завершение теста ---")
        send_command("quit")
        time.sleep(0.1)
        
        print("\n✓ Все тесты завершены успешно!")
        
    except Exception as e:
        print(f"\n✗ Ошибка во время тестирования: {e}")
    finally:
        try:
            process.terminate()
            process.wait(timeout=1)
        except:
            process.kill()

def test_manual_game():
    """Интерактивный тест с ручным вводом команд"""
    print("\n=== Интерактивный режим UCI ===")
    print("Введите UCI команды (или 'help' для справки, 'exit' для выхода):\n")
    
    process = subprocess.Popen(
        ['python', 'uci_interface.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    def show_help():
        print("""
Доступные команды:
  uci                          - инициализация движка
  isready                      - проверка готовности
  ucinewgame                   - новая игра
  position startpos            - стартовая позиция
  position startpos moves ...  - позиция с ходами (например: e2e4 e7e5)
  go depth N                   - найти лучший ход с глубиной N
  setoption name Depth value N - установить глубину по умолчанию
  display                      - показать доску
  quit                         - выход
        """)
    
    try:
        while True:
            cmd = input("UCI> ").strip()
            
            if cmd.lower() == 'exit':
                break
            elif cmd.lower() == 'help':
                show_help()
                continue
            elif not cmd:
                continue
            
            process.stdin.write(cmd + '\n')
            process.stdin.flush()
            
            if cmd.lower() == 'quit':
                break
            
            # Читаем вывод
            time.sleep(0.2 if cmd.startswith('go') else 0.05)
            while True:
                try:
                    line = process.stdout.readline()
                    if line:
                        print(line.strip())
                        if line.strip().startswith('bestmove') or line.strip() == 'readyok' or line.strip() == 'uciok':
                            break
                    else:
                        break
                except:
                    break
                    
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
    finally:
        try:
            process.terminate()
            process.wait(timeout=1)
        except:
            process.kill()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'interactive':
        test_manual_game()
    else:
        test_uci()
        print("\n" + "="*50)
        print("Для интерактивного режима запустите:")
        print("python test_uci.py interactive")
