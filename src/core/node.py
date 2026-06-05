from core.file_monitor import FileMonitor
from network.discovery import DiscoveryService

class Node:
    def __init__(self, sync_dir: str, node_id: str):
        self.node_id = node_id
        self.sync_dir = sync_dir

        self.discovery = DiscoveryService(self.node_id)
        self.monitor = FileMonitor(self.sync_dir, self.node_id)

    def start(self) -> None:
        self.discovery.start()
        self.monitor.start()

        print(f"[{self.node_id}] em operação. Aguardando eventos...\n")

    def stop(self) -> None:
        print(f"\n[{self.node_id}] encerrando atividades")
        self.discovery.running = False
        self.monitor.running = False