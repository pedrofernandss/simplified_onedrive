import os
import time
import hashlib
import threading
from typing import TypedDict, Optional

class FileMetadata(TypedDict):
    hash: Optional[str]
    size: int
    vector_clock: dict[str, int]
    deleted: bool

class FileMonitor:
    def __init__(self, sync_dir: str, node_id: str):
        self.sync_dir = sync_dir
        self.node_id = node_id
        self.files = {}
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

