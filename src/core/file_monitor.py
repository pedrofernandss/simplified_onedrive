import os
import time
import hashlib
import threading
from typing import TypedDict, Optional

class FileMetadata(TypedDict):
    hash: Optional[str]
    size: int
    updated_at: float
    deleted: bool

class FileMonitor:
    def __init__(self, sync_dir: str, node_id: str):
        self.sync_dir = sync_dir
        self.node_id = node_id
        self.files_state = {}
        self.running = True

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

    def scan_directory(self) -> None:
        current_files = set()

        for root, _, files in os.walk(self.sync_dir):
            for file in files:
                filepath = os.path.join(root, file)
                relative_path = os.path.relpath(filepath, self.sync_dir)
                current_files.add(relative_path)

                file_hash = self.get_file_hash(filepath)
                file_timestamp = os.path.getmtime(filepath)

                if relative_path not in self.files_state or self.files_state[relative_path]['hash'] != file_hash:
                    self.files_state[relative_path] = {
                        'hash': file_hash,
                        'size': os.path.getsize(filepath),
                        'updated_at': file_timestamp,
                        'deleted': False
                    }

                    print(f"ATENÇÃO! O arquivo {relative_path} foi detectado/alterado pelo [{self.node_id}]")

            for relative_path in list(self.files_state.keys()):
                if relative_path not in current_files and not self.files_state[relative_path]['deleted']:
                    self.files_state[relative_path]['deleted'] = True

                    now = time.time()
                    self.files_state[relative_path]['updated_at'] = now
                    print(f"Arquivo {relative_path} pelo [{self.node_id}]")
