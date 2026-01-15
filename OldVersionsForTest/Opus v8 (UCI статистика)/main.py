#!/usr/bin/env python3
"""
OpusChess - UCI Chess Engine

A chess engine written in pure Python with support for:
- Full FIDE chess rules
- UCI protocol
- Minimax search with alpha-beta pruning
- Position evaluation with piece-square tables

Usage:
    python main.py

The engine reads UCI commands from stdin and writes responses to stdout.
Compatible with any UCI chess GUI (Arena, CuteChess, etc.)
"""

from uci import UCIProtocol


def main():
    """Entry point for the chess engine."""
    uci = UCIProtocol()
    uci.run()


if __name__ == "__main__":
    main()
