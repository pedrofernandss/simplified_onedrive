import os
import time

node_id = os.environ.get("NODE_ID", "No_Desconhecido")
sync_dir = os.environ.get("SYNC_DIR", "/app/sync_folder")

print(f"[{node_id}] Contêiner iniciado com sucesso!")
print(f"[{node_id}] Monitorando a pasta virtual: {sync_dir}")
print(f"[{node_id}] Aguardando arquivos... (Pressione Ctrl+C para sair)\n")

while True:
    time.sleep(10)