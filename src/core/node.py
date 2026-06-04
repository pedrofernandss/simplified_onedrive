from network.discovery import DiscoveryService

class Node:
    def __init__(self, node_id, sync_dir):
        self.node_id = node_id
        self.sync_dir = sync_dir

        self.discovery = DiscoveryService(self.node_id)

    def start(self):
        self.discovery.start()

        print(f"[{self.node_id}] Nó operacional. Aguardando eventos...\n")

    def stop(self):
        print(f"\n[{self.node_id}] Encerrando atividades do Nó...")
        self.discovery.running = False