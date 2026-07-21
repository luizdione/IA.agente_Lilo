"""
scanner/watcher.py -- Monitora pastas e dispara um callback para cada PDF novo.

A lógica de filtro/aceite é pura e testável; o observador (watchdog) é import lazy,
então o pacote não exige watchdog instalado para os testes do núcleo.
"""
from __future__ import annotations
from pathlib import Path

from .crawler import MIN_SIZE_BYTES


class PaperWatcher:
    def __init__(self, roots, on_pdf, min_size: int = MIN_SIZE_BYTES):
        self.roots = [str(r) for r in roots]
        self.on_pdf = on_pdf            # callback(Path) -> None (injetável; testável)
        self.min_size = min_size

    def accept(self, path) -> bool:
        """True se o caminho é um PDF válido (extensão .pdf + tamanho mínimo)."""
        p = Path(path)
        if p.suffix.lower() != ".pdf":
            return False
        try:
            return p.is_file() and p.stat().st_size >= self.min_size
        except OSError:
            return False

    def handle(self, path) -> bool:
        """Avalia um caminho recém-visto; chama on_pdf se aceito. Retorna se disparou."""
        if self.accept(path):
            self.on_pdf(Path(path))
            return True
        return False

    def start(self, block: bool = True):
        """Inicia o monitoramento recursivo via watchdog (import lazy)."""
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        watcher = self

        class _Handler(FileSystemEventHandler):
            def on_created(self, event):
                if not event.is_directory:
                    watcher.handle(event.src_path)

            def on_moved(self, event):
                if not event.is_directory:
                    watcher.handle(event.dest_path)

        obs = Observer()
        for root in self.roots:
            obs.schedule(_Handler(), root, recursive=True)
        obs.start()
        if not block:
            return obs
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            obs.stop()
        obs.join()
        return obs
