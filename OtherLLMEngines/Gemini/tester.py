import subprocess
import time
import sys
from typing import List

ENGINE_CMD = [sys.executable, "engine.py"]
TIMEOUT = 5.0


class UCITester:
    def __init__(self, cmd):
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

    def send(self, cmd: str):
        print(f">>> {cmd}")
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def read_until(self, keywords: List[str], timeout=TIMEOUT):
        start = time.time()
        lines = []
        while time.time() - start < timeout:
            line = self.proc.stdout.readline()
            if not line:
                continue
            line = line.strip()
            print(f"<<< {line}")
            lines.append(line)
            for kw in keywords:
                if line.startswith(kw):
                    return lines
        raise TimeoutError(f"Timeout waiting for {keywords}")

    def uci_handshake(self):
        self.send("uci")
        self.read_until(["uciok"])
        self.send("isready")
        self.read_until(["readyok"])

    def new_game(self):
        self.send("ucinewgame")
        self.send("isready")
        self.read_until(["readyok"])

    def test_position(self, fen: str, depth=4):
        self.send(f"position fen {fen}")
        self.send(f"go depth {depth}")
        lines = self.read_until(["bestmove"])
        best = [l for l in lines if l.startswith("bestmove")][0]
        move = best.split()[1]
        print(f"✔ bestmove = {move}")
        return move

    def quit(self):
        self.send("quit")
        self.proc.terminate()


def run_basic_tests():
    engine = UCITester(ENGINE_CMD)

    try:
        print("\n=== UCI HANDSHAKE ===")
        engine.uci_handshake()

        print("\n=== STARTPOS TEST ===")
        engine.new_game()
        engine.send("position startpos")
        engine.send("go depth 3")
        engine.read_until(["bestmove"])

        print("\n=== TACTICAL TESTS ===")

        tests = {
            "mate_in_1":
                "6k1/5ppp/8/8/8/5Q2/5PPP/6K1 w - - 0 1",
            "simple_capture":
                "8/8/8/4p3/3P4/8/8/4K3 w - - 0 1",
            "promotion":
                "8/P7/8/8/8/8/7p/7K w - - 0 1"
        }

        for name, fen in tests.items():
            print(f"\n--- {name} ---")
            engine.test_position(fen, depth=4)

        print("\n=== OK ===")

    finally:
        engine.quit()


if __name__ == "__main__":
    run_basic_tests()
