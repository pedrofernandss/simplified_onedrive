import os
import time
from core.node import Node

if __name__ == "__main__":
    node_id = os.environ.get("NODE_ID", "No_Desconhecido")
    sync_dir = os.environ.get("SYNC_DIR", "/app/documents")

    node = Node(sync_dir, node_id)

    node.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        node.stop()