from __future__ import annotations

import os
import sys
import threading
from datetime import datetime


class TerminalUI:
    """Interface simples para padronizar mensagens no terminal."""

    # Cores ANSI usadas apenas para destacar partes importantes do log.
    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[90m",
        "blue": "\033[38;5;33m",
        "cyan": "\033[38;5;37m",
        "green": "\033[92m",
        "magenta": "\033[38;5;171m",
        "orange": "\033[38;5;208m",
        "yellow": "\033[38;5;220m",
        "red": "\033[91m",
    }

    # Cada categoria/severidade recebe uma cor para facilitar a leitura rápida.
    LEVEL_COLORS = {
        "INFO": "blue",
        "OK": "green",
        "WARN": "yellow",
        "ERROR": "red",
        "START": "green",
        "STOP": "yellow",
        "DISCOVER": "magenta",
        "SYNC": "blue",
        "FILE": "cyan",
        "DOWN": "orange",
    }

    # Evita que logs emitidos por threads diferentes sejam escritos na mesma linha.
    _write_lock = threading.Lock()

    def __init__(self, node_id: str, use_colors: bool | None = None, show_time: bool = True):
        self.node_id = node_id
        self.show_time = show_time
        self.use_colors = self._should_use_colors() if use_colors is None else use_colors

    def info(self, category: str, message: str) -> None:
        self.log(category, message)

    def success(self, category: str, message: str) -> None:
        self.log(category, message, level="OK")

    def warning(self, category: str, message: str) -> None:
        self.log(category, message, level="WARN")

    def error(self, category: str, message: str) -> None:
        self.log(category, message, level="ERROR")

    def start(self, message: str) -> None:
        self.log("START", message)

    def stop(self, message: str) -> None:
        self.log("STOP", message)

    def discover(self, message: str) -> None:
        self.log("DISCOVER", message)

    def sync(self, message: str) -> None:
        self.log("SYNC", message)

    def file(self, message: str) -> None:
        self.log("FILE", message)

    def down(self, message: str) -> None:
        self.log("DOWN", message)

    def log(self, category: str, message: str, level: str | None = None) -> None:
        category = category.upper()
        level = level or category
        prefix = self._build_prefix(category, level)
        line = f"{prefix} {message}"

        # Escreve a linha inteira de uma vez para manter a saída do terminal organizada.
        with self._write_lock:
            sys.stdout.write(f"{line}\n")
            sys.stdout.flush()

    def _build_prefix(self, category: str, level: str) -> str:
        parts = []

        if self.show_time:
            time_text = datetime.now().strftime("%H:%M:%S")
            parts.append(self._colorize(time_text, "dim") if self.use_colors else time_text)

        node_text = f"[{self.node_id}]"
        category_text = f"{category:<8}"

        # Horário e nó ficam discretos; a categoria é o principal ponto visual.
        if self.use_colors:
            color = self.LEVEL_COLORS.get(level.upper(), "dim")
            node_text = self._colorize(node_text, "dim")
            category_text = self._colorize(category_text, color, bold=True)

        parts.append(node_text)
        parts.append(category_text)
        return f"{' '.join(parts)} |"

    def _colorize(self, text: str, color: str, bold: bool = False) -> str:
        prefix = self.COLORS["bold"] if bold else ""
        return f"{prefix}{self.COLORS[color]}{text}{self.COLORS['reset']}"

    def _should_use_colors(self) -> bool:
        return os.environ.get("NO_COLOR") is None
