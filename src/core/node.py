import os
import time
import threading

from core.file_monitor import FileMonitor
from network.discovery import DiscoveryService
from network.sync_service import SyncService
from utils.merge import has_merge_conflict_marks

class Node:
    def __init__(self, sync_dir: str, node_id: str):
        self.node_id = node_id
        self.sync_dir = sync_dir

        self.discovery = DiscoveryService(self.node_id)
        self.monitor = FileMonitor(self.sync_dir, self.node_id)
        self.sync_service = SyncService(self.sync_dir, self.node_id, self.monitor)
        self.discovery.has_new_peer = self._on_peer_discovered
        self.monitor.on_file_changed = self._on_file_changed

    def _on_peer_discovered(self, peer_id: str, peer_ip: str) -> None:
        time.sleep(1)
        self.sync_service.sync_with_peer(peer_id, peer_ip)

    def _on_file_changed(self, filename: str) -> None:
        filepath = os.path.join(self.sync_dir, filename)

        if not os.path.exists(filepath):
            peers = self.discovery.peers
            for peer_id, info in peers.items():
                peer_ip = info["ip"]
                threading.Thread(
                    target=self.sync_service.spread_deletion,
                    args=(peer_ip, filename),
                    daemon=True
                ).start()
            return

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if has_merge_conflict_marks(content):
            print(f"[{self.node_id}] Não é possível compartilhar suas alterações do arquivo '{filename}'. Resolva os conflitos manualmente entrando no container e editando o arquivo.")
            return

        force_overwrite = self.monitor.consume_force_overwrite_after_resolution(filename)

        peers = self.discovery.peers
        for peer_id, info in peers.items():
            peer_ip = info["ip"]

            threading.Thread(
                target=self.sync_service.spread_modifications,
                args=(peer_ip, filename, force_overwrite),
                daemon=True
            ).start()

    def start(self) -> None:
        self.sync_service.start() 
        self.discovery.start()
        self.monitor.start()

        print(f"[{self.node_id}] iniciado e em operação.\n")

    def stop(self) -> None:
        print(f"\n[{self.node_id}] encerrando atividades")
        self.discovery.running = False
        self.monitor.running = False
        self.sync_service.running = False