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
        self.discovery.has_new_peer = self._on_peer_discovered
        self.monitor.on_file_changed = self._on_file_changed

    def _on_peer_discovered(self, peer_id: str, peer_ip: str) -> None:
        time.sleep(1)
        self.sync_service.sync_with_peer(peer_id, peer_ip)

    def _on_file_changed(self, filename: str) -> None:
        print(f"[{self.node_id}] _on_file_changed disparado para o arquivo: {filename}")

        peers_descobertos = self.discovery.peers
        print(
            f"[{self.node_id}] Peers conhecidos no momento do envio: {list(peers_descobertos.keys())}")  # <--- ADICIONE ESTE PRINT

        for peer_id, info in peers_descobertos.items():
            peer_ip = info["ip"]
            print(f"[{self.node_id}] Enviando para {peer_id} no IP {peer_ip}")  # <--- ADICIONE ESTE PRINT

            threading.Thread(
                target=self.sync_service.spread_modifications,
                args=(peer_ip, filename),
                daemon=True
            ).start()

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