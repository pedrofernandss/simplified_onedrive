import time
import threading
from core.file_monitor import FileMonitor
from network.discovery import DiscoveryService
from network.sync_service import SyncService

class Node:
    def __init__(self, sync_dir: str, node_id: str):
        self.node_id = node_id
        self.sync_dir = sync_dir

        self.discovery = DiscoveryService(self.node_id)
        self.monitor = FileMonitor(self.sync_dir, self.node_id)
        self.sync_service = SyncService(self.sync_dir, self.node_id)
        self.discovery.on_new_peer = self._on_peer_discovered

    def _on_peer_discovered(self, peer_id: str, peer_ip: str) -> None:
        def sync_after_delay():
            time.sleep(1)
            self.sync_service.sync_with_peer(peer_id, peer_ip)

        threading.Thread(target=sync_after_delay, daemon=True).start()

    def start(self) -> None:
        self.sync_service.start() 
        self.discovery.start()
        self.monitor.start()

        print(f"[{self.node_id}] em operação. Aguardando eventos...\n")

    def stop(self) -> None:
        print(f"\n[{self.node_id}] encerrando atividades")
        self.discovery.running = False
        self.monitor.running = False
        self.sync_service.running = False