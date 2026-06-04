import os
import time
from network.discovery import DiscoveryService

node_id = os.environ.get("NODE_ID", "No_Desconhecido")
sync_dir = os.environ.get("SYNC_DIR", "/app/documents")

print(f"[{node_id}] Conteiner iniciado com sucesso!")
print(f"[{node_id}] Monitorando a pasta virtual: {sync_dir}")

discovery = DiscoveryService(node_id)
discovery.start()

print(f"[{node_id}] Sistema ativo. Pressione Ctrl+C para sair.\n")

try:
    while True:
        time.sleep(10)
except KeyboardInterrupt:
    print(f"\n[{node_id}] A desligar os motores...")
    discovery.running = False