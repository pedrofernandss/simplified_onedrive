import json
import time
import socket
import threading

from core.terminal_ui import TerminalUI

class DiscoveryService:
    def __init__(self, node_id, ui: TerminalUI | None = None):
        self.node_id = node_id
        self.ui = ui or TerminalUI(node_id)
        self.udp_port = 9999
        self.peers = {}
        self.timeout = 5
        self.running = True
        self.has_new_peer = None

    def listen_for_peers(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', self.udp_port))

        self.ui.discover(f"Ouvindo a rede UDP na porta {self.udp_port}")

        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))

                peer_id = message.get('node_id')

                if peer_id and (peer_id != self.node_id):
                    now = time.time()
                    new_peer = peer_id not in self.peers

                    if new_peer:
                        self.ui.discover(f"Novo nó descoberto: {peer_id} no IP {addr[0]}")

                    self.peers[peer_id] = {
                        "ip": addr[0],
                        "last_seen": now
                    }

                    if new_peer and self.has_new_peer:
                        self.has_new_peer(peer_id, addr[0])

            except Exception as e:
                pass

    def check_timeouts(self):
        while self.running:
            now = time.time()
            unplugged_nodes = []

            for peer_id, info in self.peers.items():
                if (now - info["last_seen"]) > self.timeout:
                    unplugged_nodes.append(peer_id)

            for peer_id in unplugged_nodes:
                del self.peers[peer_id]
                self.ui.warning("DISCOVER", f"Nó desconectado: {peer_id}")

            time.sleep(2)

    def broadcast(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        message = json.dumps({
            "event": "Hello!",
            "node_id": self.node_id
        }).encode('utf-8')

        while self.running:
            try:
                sock.sendto(message, ('255.255.255.255', self.udp_port))
                time.sleep(3)
            except Exception as e:
                time.sleep(3)

    def start(self):
        threading.Thread(target=self.listen_for_peers, daemon=True).start() # Thread para ouvir
        threading.Thread(target=self.broadcast, daemon=True).start() # Thread para falar
        threading.Thread(target=self.check_timeouts, daemon=True).start()  # Thread para vigiar desconexão (timeout)