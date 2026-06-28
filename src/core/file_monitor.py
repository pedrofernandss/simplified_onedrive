import os
import time
import hashlib
import threading
from typing import TypedDict, Optional

from core.terminal_ui import TerminalUI

class FileMetadata(TypedDict):
    hash: Optional[str]
    size: int
    updated_at: float
    deleted: bool

class FileMonitor:
    def __init__(self, sync_dir: str, node_id: str, ui: TerminalUI | None = None):
        self.sync_dir = sync_dir
        self.node_id = node_id
        self.ui = ui or TerminalUI(node_id)
        self.files_state = {}
        self.running = True
        self.on_file_changed = None
        self.ignore_next_scan = set()
        self.force_overwrite_after_resolution = set()
        self.previous_hashes: dict[str, str | None] = {}
        self._state_lock = threading.Lock()

        if not os.path.exists(self.sync_dir):
            os.makedirs(self.sync_dir)

    def get_file_hash(self, filepath: str) -> Optional[str]:
        sha256_hash = hashlib.sha256()

        try:
            with open(filepath, "rb") as file:
                for byte_block in iter(lambda: file.read(65536), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except FileNotFoundError:
            return None

    def mark_force_overwrite_after_resolution(self, relative_path: str) -> None:
        with self._state_lock:
            self.force_overwrite_after_resolution.add(relative_path)

    def consume_force_overwrite_after_resolution(self, relative_path: str) -> bool:
        with self._state_lock:
            if relative_path in self.force_overwrite_after_resolution:
                self.force_overwrite_after_resolution.remove(relative_path)
                return True
            return False

    def has_pending_force_overwrite(self, relative_path: str) -> bool:
        with self._state_lock:
            return relative_path in self.force_overwrite_after_resolution

    def consume_previous_hash(self, relative_path: str) -> str | None:
        return self.previous_hashes.pop(relative_path, None)

    def scan_directory(self) -> None:
        current_files = set()

        for root, _, files in os.walk(self.sync_dir):
            for file in files:
                if file.startswith('.') or file.endswith('.swp') or file.endswith('~'):
                    continue

                filepath = os.path.join(root, file)
                relative_path = os.path.relpath(filepath, self.sync_dir)
                current_files.add(relative_path)

                file_hash = self.get_file_hash(filepath)
                file_timestamp = os.path.getmtime(filepath)

                if relative_path not in self.files_state or self.files_state[relative_path]['hash'] != file_hash:
                    previous_hash = None
                    if relative_path in self.files_state:
                        previous_hash = self.files_state[relative_path]['hash']
                    self.previous_hashes[relative_path] = previous_hash

                    self.files_state[relative_path] = {
                        'hash': file_hash,
                        'size': os.path.getsize(filepath),
                        'updated_at': file_timestamp,
                        'deleted': False
                    }

                    if relative_path in self.ignore_next_scan:
                        self.ignore_next_scan.remove(relative_path)
                        continue

                    self.ui.file(f"Arquivo detectado/alterado: {relative_path}")

                    if self.on_file_changed:
                        self.on_file_changed(relative_path)

            for relative_path in list(self.files_state.keys()):
                if relative_path not in current_files and not self.files_state[relative_path]['deleted']:
                    self.files_state[relative_path]['deleted'] = True

                    now = time.time()
                    self.files_state[relative_path]['updated_at'] = now
                    self.ui.file(f"Arquivo deletado: {relative_path}")

                    if self.on_file_changed:
                        self.on_file_changed(relative_path)

    def loop(self) -> None:
        while self.running:
            self.scan_directory()
            time.sleep(2)

    def start(self) -> None:
        threading.Thread(target=self.loop, daemon=True).start()
